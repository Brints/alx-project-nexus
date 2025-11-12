from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- API Documentation ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # --- Authentication Endpoints ---
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    # TODO: configure dj-rest-auth further (e.g., email verification)

    # --- App APIs ---
    # Include your app-specific URLs here
    # path('api/polls/', include('polls.urls')),
    # path('api/payments/', include('payments.urls')),
]