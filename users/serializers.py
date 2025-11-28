from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from organizations.serializers import OrganizationSerializer

User = get_user_model()


class UserOrganizationSerializer(serializers.Serializer):
    """Serializer for user's organization membership"""

    organization_id = serializers.UUIDField(source="organization.org_id")
    organization_name = serializers.CharField(source="organization.org_name")
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for users to view and update their own profile.
    """

    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "country",
            "is_premium",
            "date_joined",
            "organizations",
        ]
        read_only_fields = ["user_id", "email", "is_premium", "date_joined"]

    @extend_schema_field(UserOrganizationSerializer(many=True))
    def get_organizations(self, obj):
        memberships = obj.organization_memberships.select_related("organization").all()
        if not memberships:
            return []
        return UserOrganizationSerializer(memberships, many=True).data


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        normalized_email = value.strip().lower()

        try:
            user = User.objects.get(email=normalized_email)
        except User.DoesNotExist:
            return normalized_email

        if user.email_verified:
            raise serializers.ValidationError(
                "This email is already verified. Please log in."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive. Please contact support."
            )

        self.context["target_user"] = user
        return normalized_email
