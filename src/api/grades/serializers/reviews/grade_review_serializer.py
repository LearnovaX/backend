from rest_framework import serializers

from src.apps.grades.models import Grade


class GradeReviewSerializer(serializers.ModelSerializer):
    """Specialized serializer for teacher review actions"""

    class Meta:
        model = Grade
        fields = ["score", "max_score", "feedback_text"]

    def validate(self, attrs):
        score = attrs.get("score")
        max_score = attrs.get("max_score", self.instance.max_score if self.instance else 100)

        if score is not None and score > max_score:
            raise serializers.ValidationError("Score cannot exceed maximum score")

        return attrs

    def update(self, instance, validated_data):
        # Update grade fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Set graded_by to current user
        if "request" in self.context:
            instance.graded_by = self.context["request"].user

        instance.save()
        return instance
