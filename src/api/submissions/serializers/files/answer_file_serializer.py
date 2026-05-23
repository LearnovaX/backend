from rest_framework import serializers

from src.apps.submissions.models import AnswerFile


class AnswerFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    is_video = serializers.SerializerMethodField()

    class Meta:
        model = AnswerFile
        fields = [
            "id",
            "answer",
            "file",
            "file_name",
            "file_size",
            "file_url",
            "created_at",
            "updated_at",
            "content_type",
            "is_image",
            "is_video",
        ]

    def get_file_name(self, instance: AnswerFile):
        return instance.original_name

    def get_file_size(self, instance: AnswerFile):
        return instance.size

    def get_content_type(self, instance: AnswerFile):
        return instance.content_type

    def get_file_url(self, instance: AnswerFile):
        if instance.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(instance.file.url)
            return instance.file.url
        return None

    def get_is_image(self, instance: AnswerFile):
        if instance.file:
            ext = instance.file.name.split(".")[-1]
            if ext in ["jpg", "jpeg", "png"]:
                return True
        return False

    def get_is_video(self, instance: AnswerFile):
        if instance.file:
            ext = instance.file.name.split(".")[-1]
            if ext in ["mp4", "m4v"]:
                return True
        return False
