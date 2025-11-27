from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import health_check, root_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # --- API Documentation ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # --- API URLs ---
    path("api/v1/", include("authentication.urls")),
    path("api/v1/", include("users.urls")),
    path("api/v1/organizations/", include("organizations.urls")),
    path("api/v1/polls/", include("polls.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("health/", health_check),
    path("", root_view),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
