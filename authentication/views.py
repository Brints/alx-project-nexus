import logging
from typing import cast

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

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


class RegisterViewSet(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        logger.info(f"Registration attempt for email: {request.data.get('email')}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use atomic transaction to ensure data integrity
            # don't send an email if the DB save fails
            with transaction.atomic():
                user = serializer.save()
                verification_link = build_email_verification_link(user)

                # Only schedule the task after the DB transaction is fully committed
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
            logger.error(
                f"Error during registration for email {request.data.get('email')}: {
                    str(e)
                }"
            )
            raise e


class LoginViewSet(viewsets.GenericViewSet):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite_token = request.data.get('invite_token')
        if invite_token:
            from organizations.models import OrganizationInvite, OrganizationMember
            # ... Logic to find invite by token and add user to OrganizationMember immediately ...
            # This ensures they are members the instant they register.

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(email=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid email or password.")

        custom_user = cast(UserModel, user)

        if not custom_user.email_verified:
            raise AuthenticationFailed("Email is not verified.")

        if not custom_user.is_active:
            raise AuthenticationFailed("Your account is not active.")

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


class LogoutViewSet(viewsets.GenericViewSet):
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

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


class VerifyEmailViewSet(viewsets.GenericViewSet):
    serializer_class = VerifyEmailSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        """Handle GET requests from email verification links"""
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')

        if not uid or not token:
            return Response(
                {"message": "Invalid verification link. Missing parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return _verify_email(uid, token)

    def create(self, request):
        """Handle POST requests with JSON body"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']

        return _verify_email(uid, token)

