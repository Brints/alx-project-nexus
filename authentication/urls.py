from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterViewSet, LoginViewSet, LogoutViewSet

router = DefaultRouter()
router.register(r'register', RegisterViewSet, basename='authentication-register')
router.register(r'login', LoginViewSet, basename='authentication-login')
router.register(r'logout', LogoutViewSet, basename='authentication-logout')

urlpatterns = [
    path('api/auth/', include(router.urls)),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
