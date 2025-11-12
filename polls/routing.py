from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # This regex matches ws://.../ws/poll/POLL_ID/
    re_path(r'ws/poll/(?P<poll_id>\w+)/$', consumers.PollConsumer.as_asgi()),
]