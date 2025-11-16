from typing import cast

from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

from authentication.serializers import RegisterSerializer, LoginSerializer

UserModel = get_user_model()

class RegisterViewSet(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Registration successful",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginViewSet(viewsets.GenericViewSet):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(email=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid email or password.")

        custom_user = cast(UserModel, user)

        if not custom_user.email_verified:
            raise AuthenticationFailed("Email is not verified.")

        if not custom_user.is_active:
            raise AuthenticationFailed("Your account is not active.")

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class LogoutViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                raise ValidationError({"message": "Refresh token is required."})

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Logout successful"})

        except TokenError:
            raise ValidationError({"message": "Invalid or expired token."})
        except Exception as e:
            raise e
