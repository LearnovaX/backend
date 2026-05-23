from rest_framework import serializers


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True)
    re_new_password = serializers.CharField(write_only=True, required=True)
    uid = serializers.CharField(write_only=True, required=True)
    token = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        password = attrs.get("new_password")
        re_password = attrs.get("re_new_password")

        if password != re_password:
            raise serializers.ValidationError("Passwords don't match.")

        return attrs
