import logging
import secrets
from datetime import timedelta

from django.db import transaction, models
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from core import settings
from .models import Organization, OrganizationMember, OrganizationInvite
from .serializers import (
    OrganizationSerializer,
    OrganizationMemberSerializer,
    CreateInviteSerializer,
    AcceptInviteSerializer
)
from .permissions import IsOrgAdminOrReadOnly
from notifications.tasks import send_email_task

logger = logging.getLogger(__name__)


@extend_schema(tags=["Organizations"])
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Manage Organizations, Members, and Invites.
    """
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdminOrReadOnly]
    lookup_field = 'org_id'

    def get_queryset(self):
        """
        Users see organizations they OWN or are a MEMBER of.
        Exception: For 'members' action, allow fetching any org for permission checking.
        """
        user = self.request.user
        if user.is_anonymous:
            return Organization.objects.none()

        if self.action == 'members':
            return Organization.objects.all()

        return Organization.objects.filter(
            models.Q(owner=user) | models.Q(members__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """
        1. Check if user is premium or superuser
        2. Create Org
        3. Generate unique slug
        4. Add creator as ADMIN member
        5. Send confirmation email
        """
        user = self.request.user

        # Only premium users or superusers can create organizations
        if not user.is_superuser and not user.is_premium:
            raise PermissionDenied(
                "Only premium users can create organizations. Please upgrade your account."
            )

        with transaction.atomic():
            name = serializer.validated_data['org_name']
            slug = f"{slugify(name)}-{secrets.token_hex(4)}"

            org = serializer.save(owner=user, slug=slug)

            # Add owner as Admin Member
            OrganizationMember.objects.create(
                organization=org,
                user=user,
                role=OrganizationMember.Role.ADMIN
            )

            # Extract organization email from validated data
            org_email = serializer.validated_data.get('org_email')

            # Send confirmation email
            send_email_task.delay(
                subject=f"Your organization '{org.org_name}' has been created",
                recipients=[user.email, org_email],
                template_name="email/new_organization_created.html",
                context={
                    "user_name": user.first_name or user.email,
                    "org_name": org.org_name,
                    "org_url": org.org_url,
                    "org_email": org.org_email,
                    "join_code": org.join_code,
                    "dashboard_url": f"{settings.SITE_URL}/organizations/{org.org_id}"
                },
                from_email=org.org_email
            )

            logger.info(f"Organization created: {org.org_name} by {user.email}")

    def perform_update(self, serializer):
        """
        Updates the organization and sends notification email to owner.
        If 'org_name' is present in the update data, regenerate the slug.
        """
        instance = serializer.instance
        old_name = instance.org_name

        # Track what fields are being updated
        updated_fields = list(serializer.validated_data.keys())

        if 'org_name' in serializer.validated_data:
            name = serializer.validated_data['org_name']
            new_slug = f"{slugify(name)}-{secrets.token_hex(4)}"
            serializer.save(slug=new_slug)
            logger.info(f"Organization updated with new slug: {new_slug}")
        else:
            serializer.save()
            logger.info(f"Organization {instance.org_name} updated")

        # Refresh instance to get updated data
        instance.refresh_from_db()

        # Send update notification email
        self._send_update_notification(instance, old_name, updated_fields)

    def _send_update_notification(self, org, old_name, updated_fields):
        """Send email notification about organization update."""
        # Prepare context with old vs new values
        changes = []
        field_labels = {
            'org_name': 'Organization Name',
            'org_email': 'Organization Email',
            'org_url': 'Organization URL',
            'org_description': 'Description'
        }

        for field in updated_fields:
            if field in field_labels:
                changes.append({
                    'field': field_labels[field],
                    'updated': True
                })

        send_email_task.delay(
            subject=f"Your organization '{org.org_name}' has been updated",
            recipients=[org.owner.email, org.org_email],
            template_name="email/organization_updated.html",
            context={
                "user_name": org.owner.first_name or org.owner.email,
                "org_name": org.org_name,
                "old_name": old_name,
                "org_email": org.org_email,
                "org_url": org.org_url,
                "org_description": org.org_description,
                "changes": changes,
                "updated_by": self.request.user.email,
                "dashboard_url": f"{settings.SITE_URL}/organizations/{org.org_id}"
            },
            from_email=org.org_email
        )

        logger.info(f"Update notification sent for organization: {org.org_name}")

    @extend_schema(
        summary="Send an Email Invite",
        request=CreateInviteSerializer,
        responses={200: {"description": "Invite sent"}}
    )
    @action(detail=True, methods=['post'], url_path='invite')
    @action(detail=True, methods=['post'], url_path='invite')
    def send_invite(self, request, org_id=None):
        """Send an email invite to join the organization."""
        org = self.get_object()
        serializer = CreateInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        if OrganizationMember.objects.filter(organization=org, user__email=email).exists():
            return Response(
                {"message": "User is already a member of this organization."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = secrets.token_urlsafe(32)
        expiry = timezone.now() + timedelta(days=7)

        invite, _ = OrganizationInvite.objects.update_or_create(
            organization=org,
            email=email,
            defaults={
                'token': token,
                'expires_at': expiry,
                'status': OrganizationInvite.Status.PENDING
            }
        )

        invite_link = f"{settings.SITE_URL}v1/organizations/join/?token={token}"

        send_email_task.delay(
            subject=f"Invite to join {org.org_name}",
            recipients=[email],
            template_name="email/organization_invite.html",
            context={
                "org_name": org.org_name,
                "invite_link": invite_link,
                "org_description": org.org_description,
                "inviter_name": request.user.first_name or request.user.email
            }
        )

        logger.info(f"Invite sent to {email} for organization {org.org_name}")

        return Response({"message": f"Invite sent to {email}"}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Join Organization via Token",
        request=AcceptInviteSerializer,
        responses={200: {"description": "Successfully joined"}}
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='join')
    def join_organization(self, request):
        token = request.query_params.get('token') or request.data.get('token')

        if not token:
            return Response(
                {"error": "Token is required either in query params or request body."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to find an OrganizationInvite
        invite = None
        target_org = None

        try:
            invite = OrganizationInvite.objects.get(token=token, status=OrganizationInvite.Status.PENDING)

            # Email Invite Validation Logic
            if invite.expires_at < timezone.now():
                invite.status = OrganizationInvite.Status.EXPIRED
                invite.save()
                return Response({"error": "Invite has expired."}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.email != invite.email:
                return Response({
                    "error": f"This invite was sent to {invite.email}. Please login with that email to accept."
                }, status=status.HTTP_403_FORBIDDEN)

            target_org = invite.organization

        except OrganizationInvite.DoesNotExist:
            # If no invite found, try to find an Organization by join_code
            try:
                target_org = Organization.objects.get(join_code=token)
            except Organization.DoesNotExist:
                return Response({"error": "Invalid invite token or join code."}, status=status.HTTP_404_NOT_FOUND)

        # Add User to Organization
        with transaction.atomic():
            member, created = OrganizationMember.objects.get_or_create(
                organization=target_org,
                user=request.user,
                defaults={'role': OrganizationMember.Role.MEMBER}
            )

            # If this was an email invite, mark it as accepted
            if invite:
                invite.status = OrganizationInvite.Status.ACCEPTED
                invite.save()

            if not created:
                return Response({
                    "message": f"You are already a member of {target_org.org_name}",
                    "org_id": str(target_org.org_id),
                    "org_name": target_org.org_name
                }, status=status.HTTP_200_OK)

        # 4. Send welcome email (Only if they weren't already a member)
        send_email_task.delay(
            subject=f"Welcome to {target_org.org_name}",
            recipients=[request.user.email],
            template_name="email/organization_welcome.html",
            context={
                "user_name": request.user.first_name or request.user.email,
                "org_name": target_org.org_name,
                "org_description": target_org.org_description,
                "dashboard_url": f"{settings.SITE_URL}v1/organizations/{target_org.org_id}"
            },
            from_email=target_org.org_email
        )

        logger.info(f"User {request.user.email} joined organization {target_org.org_name}")

        return Response({
            "message": f"Successfully joined {target_org.org_name}",
            "org_id": str(target_org.org_id),
            "org_name": target_org.org_name
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List Organization Members",
        responses=OrganizationMemberSerializer(many=True)
    )
    @action(detail=True, methods=['get'])
    def members(self, request, org_id=None):
        """List all members of the organization, including admins."""
        org = self.get_object()
        user = request.user

        # Check if user is a member of this organization
        is_member = OrganizationMember.objects.filter(
            organization=org,
            user=user
        ).exists()

        if not is_member and org.owner != user:
            return Response(
                {"error": "You must be a member of this organization to view its members."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user is admin or owner
        is_admin = org.owner == user or OrganizationMember.objects.filter(
            organization=org,
            user=user,
            role=OrganizationMember.Role.ADMIN
        ).exists()

        # Get ALL members (both ADMIN and MEMBER roles)
        members = OrganizationMember.objects.filter(
            organization=org
        ).select_related('user').order_by('-role', 'joined_at')  # Admins first, then by join date

        serializer = OrganizationMemberSerializer(
            members,
            many=True,
            context={
                'request': request,
                'is_admin': is_admin,
                'current_user_id': user.user_id
            }
        )

        return Response(serializer.data)
