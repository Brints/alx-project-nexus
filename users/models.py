import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from core import settings


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    user_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    phone_number = models.CharField(max_length=20, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    email_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False, db_index=True)
    premium_expiry_date = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    country = models.CharField(max_length=50, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def get_verification_link(self):
        """Generate verification link for the user"""
        try:
            verification = self.verifications.filter(
                verification_type="email",
                is_verified=False,
                expires_at__gt=timezone.now(),
            ).latest("created_at")

            return f"{settings.SITE_URL}auth/verify-email/{verification.verification_code}/"
        except UserVerification.DoesNotExist:
            from datetime import timedelta
            import secrets

            verification_code = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=24)

            verification = UserVerification.create_verification(
                user=self,
                verification_type="email",
                verification_code=verification_code,
                expires_at=expires_at,
            )

            return f"{settings.SITE_URL}auth/verify-email/{verification_code}/"

    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = self.first_name.capitalize()
        if self.last_name:
            self.last_name = self.last_name.capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def id(self):
        return self.user_id


class UserVerification(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verifications"
    )
    verification_type = models.CharField(max_length=50)  # 'email', 'phone'
    verification_code = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} - {self.verification_type}"

    def is_expired(self):
        """Check if the verification code has expired."""
        return timezone.now() > self.expires_at

    @classmethod
    def create_verification(
        cls, user, verification_type, verification_code, expires_at
    ):
        """Create an email verification record with expiration."""
        return cls.objects.create(
            user=user,
            verification_type=verification_type,
            verification_code=verification_code,
            expires_at=expires_at,
        )
