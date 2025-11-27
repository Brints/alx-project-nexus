from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import ResendEmailVerificationViewSet, UserViewSet

router = DefaultRouter()
router.register(r"", UserViewSet, basename="users")
router.register(
    r"resend-verification",
    ResendEmailVerificationViewSet,
    basename="resend-email-verification",
)

urlpatterns = [
    path("users/", include(router.urls)),
]
