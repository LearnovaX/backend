import logging
import pandas as pd
from datetime import timedelta

from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import Count
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.http import HttpResponse, FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response

from src.api.courses.serializers import CourseGroupReadLightSerializer
from src.api.users.serializers import (
    AdminCreateUserSerializer,
    AdminUpdateUserSerializer,
    AdminUserReadSerializer,
    StatisticsSerializer,
    BulkActionsSerializer,
    ExportUserSerializer,
    ImportUserSerializer,
    HistoricalStatisticsSerializer,
)
from src.apps.common.permissions.group_permissions import IsAdmin
from src.apps.common.utils.files.export_users import export_users_to_csv, export_users_to_xlsx
from src.apps.courses.models import CourseGroup
from src.apps.users.models import User, DailyUserStatistics
from src.apps.users.service import send_activation_invite
from src.apps.users.pagination import AdminUserPagination
from src.apps.users.filters import UserFilter

logger = logging.getLogger(__name__)


@extend_schema(tags=["Admin - Users Management"])
class AdminUserModelViewSet(viewsets.ModelViewSet):
    """
    USER endpoint with nested profile.
    """
    permission_classes = [IsAdmin]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = AdminUserPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    queryset = User.objects.select_related('profile')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return AdminUserReadSerializer
        elif self.action in ['create']:
            return AdminCreateUserSerializer
        elif self.action in ['update', 'partial_update']:
            return AdminUpdateUserSerializer
        elif self.action == 'statistics':
            return StatisticsSerializer
        elif self.action == "extended_statistics":
            return HistoricalStatisticsSerializer
        elif self.action == "bulk_actions":
            return BulkActionsSerializer
        elif self.action == "groups":
            return CourseGroupReadLightSerializer
        elif self.action == "export_users":
            return ExportUserSerializer
        elif self.action == "import_users":
            return ImportUserSerializer
        return AdminUserReadSerializer

    @extend_schema(request=AdminCreateUserSerializer, responses=AdminUserReadSerializer)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info("users.create START payload_keys=%s", sorted(list(dict(request.data).keys())))
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_activation_invite(user.email, user.first_name, uid, token)

        out = AdminUserReadSerializer(user, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        logger.info("users.create SUCCESS user_id=%s email=%s", user.id, user.email)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        request={"multipart/form-data": AdminUpdateUserSerializer},
        responses=AdminUserReadSerializer,
    )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        logger.info("users.update START partial=%s payload_keys=%s", partial,
                    sorted(list(dict(request.data).keys())))
        user = self.get_object()
        ser = self.get_serializer(user, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        out = AdminUserReadSerializer(user, context=self.get_serializer_context())
        logger.info("users.update SUCCESS user_id=%s partial=%s", user.id, partial)
        return Response(out.data)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        hard = request.query_params.get("hard") == "true"
        logger.info("users.destroy START hard=%s", hard)
        user: User = self.get_object()
        if user.is_superuser:
            logger.warning(
                f"users.destroy. User with id {request.user.pk} tried to"
                f" delete superuser with id {user.id}")
            return Response({"message": f"Unknown error occurred."},
                            status=status.HTTP_200_OK)
        target_id = user.id
        target_email = user.email

        if hard:
            # TODO -> move deleted users to archive
            resp = super().destroy(request, *args, **kwargs)
            logger.info("users.destroy SUCCESS hard=%s deleted_user_id=%s email=%s status=%s",
                        hard, target_id, target_email, getattr(resp, "status_code", None))
            return resp

        user.is_active = False
        user.save(update_fields=["is_active"])

        logger.info("users.destroy SUCCESS hard=%s deactivated_user_id=%s email=%s", hard,
                    target_id, target_email)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=None)
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def resend_invite(self, request, pk=None):
        logger.info("users.resend_invite START user_pk=%s", pk)
        user: User = self.get_object()
        if user.is_active and not getattr(user, "must_set_password", False):
            logger.warning("users.resend_invite SKIP already_activated user_id=%s", user.id)
            return Response({"message": "User already activated."},
                            status=status.HTTP_400_BAD_REQUEST)

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_activation_invite(user.email, user.first_name, uid, token)

        logger.info("users.resend_invite SUCCESS user_id=%s email=%s", user.id, user.email)
        return Response({"message": "Invitation re-sent successfully."}, status=status.HTTP_200_OK)

    @extend_schema(methods=['get'], responses={200: StatisticsSerializer})
    @action(methods=['get'], detail=False, url_path="statistics")
    def statistics(self, request):
        serializer = self.get_serializer()
        statistics_data = serializer.calculate_statistics()
        return Response(statistics_data, status=status.HTTP_200_OK)

    @extend_schema(methods=["get"], responses={200: HistoricalStatisticsSerializer})
    @action(methods=['get'], detail=False, url_path="historical-statistics")
    def historical_statistics(self, request):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = DailyUserStatistics.objects.filter(date__gte=start_date).order_by('date')
        serializer = HistoricalStatisticsSerializer(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_actions(self, request):
        logger.info("users.bulk_actions START payload_keys=%s",
                    sorted(list(dict(request.data).items())))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.perform_bulk_action()

        if isinstance(result, (HttpResponse, FileResponse)):
            logger.info("users.bulk_actions SUCCESS result_type=%s", type(result).__name__)
            return result

        logger.info(
            "users.bulk_actions SUCCESS result_keys=%s",
            sorted(list(result.keys())) if isinstance(result, dict) else type(result).__name__
        )
        return Response(result)

    @action(methods=['get'], detail=False, url_path="groups")
    def groups(self, request):
        groups = CourseGroup.objects.select_related(
            "course"
        ).annotate(members_count=Count("members", distinct=True))

        total_enrolled_members_count = sum(group.members_count for group in groups)
        groups_count = groups.count()

        serializer = self.get_serializer(groups, many=True)
        return Response({
            "total_enrolled_members_count": total_enrolled_members_count,
            "groups_count": groups_count,
            "groups": serializer.data
        }, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=False, url_path="export-users")
    def export_users(self, request):
        file_type = (request.query_params.get("file-type") or "csv").lower()
        logger.info("users.export_users START file_type=%s", file_type)

        if file_type not in ("csv", "xlsx"):
            logger.warning("users.export_users UNSUPPORTED file_type=%s", file_type)
            return Response({"detail": "Unsupported file type"}, status=400)

        qs = User.objects.select_related("profile").all()
        serializer = self.get_serializer(qs, many=True)
        data = serializer.data
        records = len(data)

        resp = export_users_to_csv(data) if file_type == "csv" else export_users_to_xlsx(data)
        logger.info("users.export_users SUCCESS file_type=%s records=%s status=%s",
                    file_type, records, getattr(resp, "status_code", None))
        return resp

    @action(methods=["post"], detail=False, url_path="import-users")
    def import_users(self, request):
        file = request.FILES.get("file")
        logger.info("users.import_users START has_file=%s filename=%s size=%s",
                    bool(file), getattr(file, "name", None), getattr(file, "size", None))

        if not file:
            logger.warning("users.import_users NO_FILE")
            return Response({"error": "No file uploaded"}, status=400)

        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            ftype = "csv"
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
            ftype = "xlsx"
        else:
            logger.warning("users.import_users UNSUPPORTED_FORMAT filename=%s", file.name)
            return Response({"error": "Unsupported file format"}, status=400)

        rows = len(df.index)
        logger.info("users.import_users PARSED file_type=%s rows=%s", ftype, rows)

        data = df.to_dict(orient="records")
        serializer = ImportUserSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        imported = len(serializer.data)
        logger.info("users.import_users SUCCESS file_type=%s filename=%s imported=%s", ftype,
                    file.name, imported)
        return Response({"status": f"Imported {imported} users"})
