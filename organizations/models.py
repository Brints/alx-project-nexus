from django.db import models
from django.conf import settings
import uuid
import secrets


class Organization(models.Model):
    org_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    org_name = models.CharField(max_length=100)
    org_email = models.EmailField()
    org_url = models.URLField()
    org_description = models.TextField()
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    join_code = models.CharField(
        max_length=50, unique=True, default=secrets.token_urlsafe
    )

    def __str__(self):
        return self.org_name


class OrganizationMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"

    member_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members", db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user.email} - {self.organization.org_name} ({self.role})"


class OrganizationInvite(models.Model):
    """Handles the email invite flow"""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        EXPIRED = "EXPIRED", "Expired"

    invite_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return (
            f"Invite to {self.email} for {self.organization.org_name} ({self.status})"
        )
