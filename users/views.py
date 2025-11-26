import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from notifications.tasks import send_email_task
from users.serializers import ResendEmailVerificationSerializer, UserSerializer
from users.utils import build_email_verification_link

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.GenericViewSet):
    """
    Endpoints for User Profile Management.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk)

    @extend_schema(summary="Get My Profile", responses=UserSerializer)
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Retrieve the authenticated user's profile information.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(summary="Update My Profile", responses=UserSerializer)
    @me.mapping.patch
    def update_me(self, request):
        """
        Update the authenticated user's profile (First Name, Last Name, Phone, Country).
        """
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=["Authentication"])  # Grouped under Auth as it relates to login flow
class ResendEmailVerificationViewSet(viewsets.GenericViewSet):
    serializer_class = ResendEmailVerificationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'resend_verification'

    @extend_schema(summary="Resend Verification Email")
    def create(self, request):
        logger.info(f"Resend verification request for email: {request.data.get('email')}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Retrieved from validate_email logic
        user = serializer.context.get('target_user')

        # If user doesn't exist (but passed validation to prevent enumeration), just return 200
        if not user:
            logger.info("Resend verification requested for non-existent email (masking response).")
            return Response(
                {"message": "If an account exists, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )

        try:
            with transaction.atomic():
                verification_link = build_email_verification_link(user)

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

            return Response(
                {"message": "Verification email has been sent. Please check your inbox."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Failed to resend verification for {user.email}: {str(e)}", exc_info=True)
            return Response(
                {"message": "Failed to send verification email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )