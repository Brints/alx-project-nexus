from rest_framework import permissions
from .models import Organization, OrganizationMember


class IsOrgAdminOrReadOnly(permissions.BasePermission):
    """
    Allows access only to Organization Admins or the Owner.
    Read-only for standard members.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        # (filtering is done in get_queryset to ensure they are members)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner or org admins
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
        # We expect 'organization_id' in the request data
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