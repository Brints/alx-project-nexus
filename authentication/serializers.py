from django.contrib.auth import get_user_model
from rest_framework import serializers
from users.utils import UserFormatter

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    invite_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
            "phone_number",
            "invite_token",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs

    def validate_password(self, value):
        if not UserFormatter.check_strong_password(value):
            raise serializers.ValidationError(
                "Password must be at least 8 characters long and include uppercase, "
                "lowercase, number, and special character."
            )
        return value

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data.pop("invite_token", None)

        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    invite_token = serializers.CharField(write_only=True, required=False, allow_blank=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
