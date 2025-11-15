from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', 'users.views.UserViewSet', basename='user')

urlpatterns = router.urls
