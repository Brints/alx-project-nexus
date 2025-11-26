from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, OrganizationMember

User = get_user_model()

class OrganizationMemberSerializer(serializers.ModelSerializer):
    member_id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(source='user.user_id', read_only=True)
    email = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMember
        fields = ['member_id', 'user_id', 'email', 'first_name', 'last_name', 'role', 'is_owner', 'joined_at']
        read_only_fields = ['member_id', 'user_id', 'email', 'first_name', 'last_name', 'joined_at']

    def get_is_owner(self, obj):
        """Indicate if this member is the organization owner."""
        return obj.organization.owner == obj.user

    def get_email(self, obj):
        """
        Show email only if:
        1. User is admin/owner (is_admin=True in context)
        2. User is viewing their own profile (current_user_id matches)
        """
        request = self.context.get('request')
        is_admin = self.context.get('is_admin', False)
        current_user_id = self.context.get('current_user_id')

        # Admins see all emails
        if is_admin:
            return obj.user.email

        # Users see their own email
        if current_user_id and obj.user.user_id == current_user_id:
            return obj.user.email

        # Others see masked email
        email = obj.user.email
        username, domain = email.split('@')
        masked_username = username[:2] + '*' * (len(username) - 2)
        return f"{masked_username}@{domain}"



class OrganizationSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'org_id', 'org_name', 'org_email', 'org_url', 'org_description',
            'slug', 'owner', 'created_at', 'is_admin', 'join_code'
        ]
        read_only_fields = ['org_id', 'created_at', 'slug', 'owner', 'join_code']

    def get_is_admin(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        if obj.owner == request.user:
            return True

        return OrganizationMember.objects.filter(
            organization=obj,
            user=request.user,
            role=OrganizationMember.Role.ADMIN
        ).exists()


class CreateInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
