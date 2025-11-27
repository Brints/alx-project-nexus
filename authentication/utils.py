import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.response import Response

from users.models import UserVerification
from users.utils import email_verification_token

UserModel = get_user_model()
logger = logging.getLogger(__name__)


def _verify_email(uid, token):
    """Common verification logic for both GET and POST"""

    try:
        decoded_uid = urlsafe_base64_decode(uid).decode()
        user = UserModel.objects.get(pk=decoded_uid)
    except (UserModel.DoesNotExist, ValueError, TypeError, OverflowError):
        logger.warning(f"Invalid UID in verification: {uid}")
        return Response(
            {"message": "Invalid verification link."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.email_verified:
        UserVerification.objects.filter(user=user, verification_type="email").delete()
        return Response(
            {"message": "Email is already verified."}, status=status.HTTP_200_OK
        )

    try:
        verification = UserVerification.objects.get(
            user=user,
            verification_type="email",
            verification_code=token,
            is_verified=False,
        )
    except UserVerification.DoesNotExist:
        logger.warning(f"Token not found for user: {user.email}")
        return Response(
            {"message": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST
        )

    if verification.is_expired():
        verification.delete()
        logger.info(f"Expired token deleted for user: {user.email}")
        return Response(
            {"message": "Token has expired. Please request a new verification email."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not email_verification_token.check_token(user, token):
        verification.delete()
        logger.warning(f"Invalid token format for user: {user.email}")
        return Response(
            {"message": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        verification.delete()

    logger.info(f"Email verified successfully for: {user.email}")
    return Response(
        {"message": "Email verified successfully."}, status=status.HTTP_200_OK
    )
