from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, OrganizationMember, OrganizationInvite

User = get_user_model()

class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'joined_at']
        read_only_fields = ['user', 'joined_at']

class OrganizationSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['org_id', 'org_name', 'slug', 'owner', 'created_at', 'is_admin']
        read_only_fields = ['org_id', 'owner', 'created_at', 'slug']

    def get_is_admin(self, obj):
        user = self.context['request'].user
        if obj.owner == user:
            return True
        return OrganizationMember.objects.filter(
            organization=obj, user=user, role=OrganizationMember.Role.ADMIN
        ).exists()

class CreateInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()

class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()