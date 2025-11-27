import logging
from datetime import timedelta

from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core import settings
from users.models import UserVerification
from users.tokens import email_verification_token

logger = logging.getLogger("users.utils")


class UserFormatter:
    @staticmethod
    def format_user_name(first_name, last_name):
        return f"{first_name.strip().title()} {last_name.strip().title()}"

    @staticmethod
    def format_email(email):
        return email.strip().lower()

    @staticmethod
    def capitalize_name(first_name, last_name):
        return first_name.capitalize(), last_name.capitalize()

    @staticmethod
    def check_strong_password(password):
        import re

        if (
            len(password) < 8
            or not re.search(r"[A-Z]", password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"[0-9]", password)
            or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
        ):
            return False
        return True

    @staticmethod
    def format_phone_number(phone_number):
        import re

        digits = re.sub(r"\D", "", phone_number)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone_number


def build_email_verification_link(user) -> str:
    """Generate email verification link for a user"""

    # Remove existing tokens
    deleted_count = UserVerification.objects.filter(
        user=user, verification_type="email", is_verified=False
    ).delete()[0]

    logger.info(
        f"Deleted {deleted_count} unverified email verification records for user {user.email}"
    )

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)

    expiration = timezone.now() + timedelta(hours=2)

    # Create a new verification record
    UserVerification.create_verification(user, "email", token, expiration)

    base_url = getattr(settings, "FRONTEND_VERIFICATION_URL", None) or settings.SITE_URL
    verification_link = (
        f"{settings.SITE_URL}v1/auth/verify-email/?uid={uid}&token={token}"
    )

    return verification_link
    ############ Alternative if frontend URL is different ############
    # return f"{base_url.rstrip('/')}/auth/verify-email?uid={uid}&token={token}"
