from django.urls import path, include
from rest_framework.routers import DefaultRouter

from users.views import ResendEmailVerificationViewSet

router = DefaultRouter()
router.register(
    r"resend-verification",
    ResendEmailVerificationViewSet,
    basename="resend-email-verification"
)

urlpatterns = [
    path("api/users/", include(router.urls)),
]
