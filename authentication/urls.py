from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginViewSet, LogoutViewSet, RegisterViewSet, VerifyEmailViewSet

router = DefaultRouter()
router.register(r"register", RegisterViewSet, basename="authentication-register")
router.register(r"login", LoginViewSet, basename="authentication-login")
router.register(r"logout", LogoutViewSet, basename="authentication-logout")
router.register(
    r"verify-email", VerifyEmailViewSet, basename="authentication-verify-email"
)

urlpatterns = [
    path("auth/", include(router.urls)),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
