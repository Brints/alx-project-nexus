import logging
from typing import cast

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils.http import urlsafe_base64_decode
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
from notifications.tasks import send_email_task
from users.models import UserVerification
from users.tokens import email_verification_token
from users.utils import build_email_verification_link

logger = logging.getLogger("authentication")

UserModel = get_user_model()


def _schedule_verification_email(self, user, verification_link):
    try:
        send_email_task.delay(
            subject="Verify your Agora account",
            recipients=[user.email],
            template_name="email/send_email_verification_token.html",
            context={
                "first_name": user.first_name,
                "verification_link": verification_link,
            },
        )
    except Exception as e:
        logger.error(f"Failed to queue email task: {str(e)}", exc_info=True)


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

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = request.data.get("uid")
        token = request.data.get("token")

        if not uidb64 or not token:
            raise ValidationError({"message": "UID and token are required."})

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = UserModel.objects.get(pk=uid)
        except (UserModel.DoesNotExist, ValueError, TypeError, OverflowError) as e:
            raise ValidationError({"message": "Invalid verification link."}) from e

        if user.email_verified:
            UserVerification.objects.filter(
                user=user,
                verification_type="email",
            ).delete()
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
        except UserVerification.DoesNotExist as e:
            raise ValidationError({"message": "Invalid verification link."}) from e

        if verification.is_expired():
            verification.delete()
            raise ValidationError(
                {"message": "Verification link has expired. Request a new one."}
            )

        if not email_verification_token.check_token(user, token):
            raise ValidationError({"message": "Invalid or expired token."})

        with transaction.atomic():
            user.email_verified = True
            user.save(update_fields=["email_verified"])
            verification.delete()

        return Response(
            {"message": "Email verified successfully."}, status=status.HTTP_200_OK
        )
