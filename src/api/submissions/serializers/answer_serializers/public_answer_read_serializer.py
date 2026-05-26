from rest_framework import serializers

from src.api.grades.serializers import GradeReadSerializer
from src.api.submissions.serializers import AnswerFileSerializer
from src.apps.submissions.models import Answer


class PublicAnswerReadSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()
    # files = AnswerFileSerializer(many=True, read_only=True)
    grade = GradeReadSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = [
            "id",
            "description",
            "status",
            "grade",
            "created_at",
            "updated_at",
            "files",
        ]

    def get_files(self, obj: Answer):
        request = self.context.get("request")
        return AnswerFileSerializer(obj.files, many=True, context={"request": request}).data
