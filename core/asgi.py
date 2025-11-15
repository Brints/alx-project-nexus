import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import polls.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Get the standard Django HTTP application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        # HTTP requests are handled by the default Django ASGI app
        "http": django_asgi_app,
        # WebSocket requests
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(polls.routing.websocket_urlpatterns))
        ),
    }
)
