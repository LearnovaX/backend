from rest_framework import serializers

from src.apps.submissions.models import AnswerFile


class AnswerFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerFile
        fields = ["answer", "file"]

    def validate(self, attrs):
        answer = attrs.get("answer")
        if answer and answer.files.count() > 30:
            raise serializers.ValidationError("Maximum 30 files allowed per answer")
        return attrs
