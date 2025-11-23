from rest_framework import permissions
from organizations.models import Organization, OrganizationMember

class IsPollCreatorOrOrgAdmin(permissions.BasePermission):
    """
    Custom permission:
    - Allow owners of the poll to edit/delete.
    - Allow Organization Admins to edit/delete if it belongs to their org.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any user (filtering happens in QuerySet)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if personal poll
        if obj.organization is None:
            return obj.creator == request.user

        # Check if Organization Poll (User must be Org Admin)
        return OrganizationMember.objects.filter(
            organization=obj.organization,
            user=request.user,
            role=OrganizationMember.Role.ADMIN
        ).exists()
    