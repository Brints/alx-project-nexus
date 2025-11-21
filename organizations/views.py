import logging
import secrets
from datetime import timedelta

from django.db import transaction, models
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from core import settings
from .models import Organization, OrganizationMember, OrganizationInvite
from .serializers import (
    OrganizationSerializer,
    OrganizationMemberSerializer,
    CreateInviteSerializer,
    AcceptInviteSerializer
)
from .permissions import IsOrgAdminOrReadOnly
from notifications.tasks import send_email_task  # Importing your existing task

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdminOrReadOnly]
    lookup_field = 'org_id'

    def get_queryset(self):
        # Users can only see organizations they belong to or own
        user = self.request.user
        return Organization.objects.filter(
            models.Q(owner=user) | models.Q(members__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """
        1. Create Org
        2. Generate unique slug
        3. Add creator as ADMIN member
        """
        with transaction.atomic():
            # Generate simple slug from name + random string to ensure uniqueness
            name = serializer.validated_data['org_name']
            slug = f"{slugify(name)}-{secrets.token_hex(4)}"

            org = serializer.save(owner=self.request.user, slug=slug)

            # Add owner as Admin Member
            OrganizationMember.objects.create(
                organization=org,
                user=self.request.user,
                role=OrganizationMember.Role.ADMIN
            )

    @action(detail=True, methods=['post'], url_path='invite')
    def send_invite(self, request, org_id=None):
        """
        Endpoint: POST /api/organizations/{id}/invite/
        Body: { "email": "user@example.com" }
        """
        org = self.get_object()  # Checks permission (IsOrgAdmin)
        serializer = CreateInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # Check if already a member
        if OrganizationMember.objects.filter(organization=org, user__email=email).exists():
            return Response({"message": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)

        # Create Invite Record
        token = secrets.token_urlsafe(32)
        expiry = timezone.now() + timedelta(days=7)

        invite, created = OrganizationInvite.objects.update_or_create(
            organization=org,
            email=email,
            defaults={
                'token': token,
                'expires_at': expiry,
                'status': OrganizationInvite.Status.PENDING
            }
        )

        # Generate Link (Assuming frontend URL structure)
        invite_link = f"{settings.FRONTEND_VERIFICATION_URL}/join?token={token}"

        # Trigger Celery Task
        send_email_task.delay(
            subject=f"Invite to join {org.org_name}",
            recipients=[email],
            template_name="email/organization_invite.html",
            context={
                "org_name": org.org_name,
                "invite_link": invite_link
            }
        )

        return Response({"message": "Invite sent successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='join')
    def join_organization(self, request):
        """
        Endpoint: POST /api/organizations/join/
        Body: { "token": "xyz..." }
        Logic: Validates token and adds current user to Org.
        """
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            invite = OrganizationInvite.objects.get(token=token, status=OrganizationInvite.Status.PENDING)
        except OrganizationInvite.DoesNotExist:
            return Response({"error": "Invalid invite."}, status=status.HTTP_404_NOT_FOUND)

        if invite.expires_at < timezone.now():
            invite.status = OrganizationInvite.Status.EXPIRED
            invite.save()
            return Response({"error": "Invite expired."}, status=status.HTTP_400_BAD_REQUEST)

        # Add to Organization
        with transaction.atomic():
            OrganizationMember.objects.get_or_create(
                organization=invite.organization,
                user=request.user,
                defaults={'role': OrganizationMember.Role.MEMBER}
            )

            invite.status = OrganizationInvite.Status.ACCEPTED
            invite.save()

        return Response({
            "message": f"Successfully joined {invite.organization.org_name}",
            "org_id": invite.organization.org_id
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def members(self, request, org_id=None):
        """List members of the organization"""
        org = self.get_object()
        members = OrganizationMember.objects.filter(organization=org)
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)