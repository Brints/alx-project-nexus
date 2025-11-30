from django.urls import re_path
from polls import consumers

websocket_urlpatterns = [
    # WebSocket URL pattern for poll updates
    re_path(r"ws/poll/(?P<poll_id>[^/]+)/$", consumers.PollConsumer.as_asgi()),
]
