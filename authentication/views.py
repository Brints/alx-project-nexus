import logging
from typing import cast

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
)
from authentication.utils import _verify_email
from notifications.tasks import send_email_task
from users.utils import build_email_verification_link

logger = logging.getLogger("authentication")
UserModel = get_user_model()


# Helper function to handle invite acceptance without circular imports
def process_invite_token(user, token):
    if not token:
        return
    try:
        # Import inside function to avoid circular dependency
        from organizations.models import OrganizationInvite, OrganizationMember

        invite = OrganizationInvite.objects.get(token=token, status="PENDING")

        if invite.expires_at > timezone.now():
            OrganizationMember.objects.get_or_create(
                organization=invite.organization, user=user, defaults={"role": "MEMBER"}
            )
            invite.status = "ACCEPTED"
            invite.save()
            logger.info(
                f"User {user.email} added to org {invite.organization.org_name} via token."
            )
    except Exception as e:
        # We don't want to fail registration/login just because an invite failed
        logger.warning(f"Failed to process invite token {token}: {str(e)}")


@extend_schema(tags=["Authentication"])
class RegisterViewSet(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Register a new user")
    def create(self, request):
        logger.info(f"Registration attempt for email: {request.data.get('email')}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite_token = serializer.validated_data.get("invite_token")

        try:
            with transaction.atomic():
                user = serializer.save()

                # Process Invite if it exists
                if invite_token:
                    process_invite_token(user, invite_token)

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

            data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
            }

            return Response(
                {
                    "message": "Registration successful. Please verify your email.",
                    "data": data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            raise e


@extend_schema(tags=["Authentication"])
class LoginViewSet(viewsets.GenericViewSet):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Login and obtain JWT tokens")
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        invite_token = serializer.validated_data.get("invite_token")

        user = authenticate(email=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid email or password.")

        custom_user = cast(UserModel, user)

        if not custom_user.email_verified:
            raise AuthenticationFailed("Email is not verified.")

        if not custom_user.is_active:
            raise AuthenticationFailed("Your account is not active.")

        # Process Invite if user logs in with a token (Scenario: clicked invite, already has account)
        if invite_token:
            process_invite_token(custom_user, invite_token)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class LogoutViewSet(viewsets.GenericViewSet):
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Logout and blacklist refresh token")
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logout successful."}, status=status.HTTP_200_OK
            )
        except TokenError as err:
            raise ValidationError({"message": "Invalid or expired token."}) from err


@extend_schema(tags=["Authentication"])
class VerifyEmailViewSet(viewsets.GenericViewSet):
    serializer_class = VerifyEmailSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Verify Email (via Link)",
        parameters=[
            OpenApiParameter(
                name="uid",
                location=OpenApiParameter.QUERY,
                description="Encoded User ID",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.QUERY,
                description="Verification Token",
                required=True,
                type=str,
            ),
        ],
    )
    def list(self, request):
        """Handle GET requests from email verification links"""
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response(
                {"message": "Invalid verification link. Missing parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return _verify_email(uid, token)

    @extend_schema(summary="Verify Email (via Manual Code/JSON)")
    def create(self, request):
        """Handle POST requests with JSON body"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]

        return _verify_email(uid, token)


@extend_schema(tags=["Authentication"], summary="Refresh Access Token")
class CustomTokenRefreshView(TokenRefreshView):
    """
    Takes a refresh token and returns a new access token.
    """

    pass
