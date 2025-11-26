from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='poll-categories')
router.register(r'', PollViewSet, basename='polls')

urlpatterns = [
    path('', include(router.urls)),
]