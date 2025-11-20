from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        normalized_email = value.strip().lower()

        try:
            user = User.objects.get(email=normalized_email)
        except User.DoesNotExist:
            # Generic message to avoid email enumeration
            raise serializers.ValidationError(
                "If an account with this email exists and is unverified, "
                "a verification email will be sent."
            )

        if user.email_verified:
            raise serializers.ValidationError(
                "This email is already verified. Please log in."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive. Please contact support."
            )

        # Store user in context for the view to use
        self.context['user'] = user
        return normalized_email
