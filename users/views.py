import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from notifications.tasks import send_email_task
from users.serializers import ResendEmailVerificationSerializer
from users.utils import build_email_verification_link

User = get_user_model()
logger = logging.getLogger(__name__)


class ResendEmailVerificationViewSet(viewsets.GenericViewSet):
    serializer_class = ResendEmailVerificationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'resend_verification'

    def create(self, request):
        logger.info(f"Resend verification request for email: {request.data.get('email')}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context.get('user')

        if not user:
            logger.error("User not found in serializer context")
            return Response(
                {"message": "An error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            with transaction.atomic():
                verification_link = build_email_verification_link(user)
                logger.info(f"Generated new verification link for user: {user.email}")

                transaction.on_commit(
                    lambda: send_email_task.delay(
                        subject="Verify your Agora account",
                        recipients=[user.email],
                        template_name="email/send_email_verification_token.html",
                        context={
                            "first_name": user.first_name,
                            "verification_link": verification_link,
                        },
                    )
                )

            logger.info(f"Verification email queued for: {user.email}")
            return Response(
                {"message": "Verification email has been sent. Please check your inbox."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(
                f"Failed to resend verification email for {user.email}: {str(e)}",
                exc_info=True
            )
            return Response(
                {"message": "Failed to send verification email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
