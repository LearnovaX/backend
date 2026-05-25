from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from src.apps.notifications.models import Notification

from .serializers import NotificationReadSerializer, NotificationWriteSerializer


@extend_schema(tags=["Notifications"])
class NotificationViewSet(viewsets.GenericViewSet):
    queryset = Notification.objects.select_related("receiver", "sender").all()
    serializer_class = NotificationReadSerializer

    def get_queryset(self):
        if self.action == "inbox":
            return self.queryset.filter(receiver=self.request.user.id)
        elif self.action == "outbox":
            return self.queryset.filter(sender=self.request.user.id)
        return self.queryset.filter(Q(receiver=self.request.user) | Q(sender=self.request.user))

    def list(self, request):
        queryset = self.get_queryset().order_by("is_read", "-created_at")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # def create(self, request):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset().filter(id=pk)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action in ["create", "update", "delete"]:
            return NotificationWriteSerializer
        return NotificationReadSerializer

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def outbox(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
