from rest_framework import permissions
from .models import Organization, OrganizationMember


class IsOrgAdminOrReadOnly(permissions.BasePermission):
    """
    Allows access only to Organization Admins or the Owner.
    Read-only for standard members.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return self._is_admin(request.user, obj)

    def _is_admin(self, user, org):
        # Check if owner
        if org.owner == user:
            return True

        # Check if Admin member
        return OrganizationMember.objects.filter(
            organization=org,
            user=user,
            role=OrganizationMember.Role.ADMIN
        ).exists()


class IsOrgAdminForPolls(permissions.BasePermission):
    """
    Specific permission for when creating POLLS within an organization.
    Used in the Polls app, but logic belongs here.
    """

    def has_permission(self, request, view):
        org_id = request.data.get('organization')
        if not org_id:
            return True  # Not an org poll, standard rules apply

        try:
            org = Organization.objects.get(pk=org_id)
            return org.owner == request.user or OrganizationMember.objects.filter(
                organization=org,
                user=request.user,
                role=OrganizationMember.Role.ADMIN
            ).exists()
        except Organization.DoesNotExist:
            return False


class IsOrgMemberToViewMembers(permissions.BasePermission):
    """
    Only organization members can view the members list.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Check if user is owner
        if obj.owner == user:
            return True

        # Check if user is a member
        return OrganizationMember.objects.filter(
            organization=obj,
            user=user
        ).exists()
