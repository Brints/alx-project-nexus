import json

from channels.generic.websocket import AsyncWebsocketConsumer


class PollConsumer(AsyncWebsocketConsumer):
    """
    This consumer handles WebSocket connections for real-time poll results.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.poll_id = None

    async def connect(self):
        # Get poll_id from the URL route
        self.poll_id = self.scope["url_route"]["kwargs"]["poll_id"]
        self.room_group_name = f"poll_{self.poll_id}"

        # Join the room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

        # Send a simple "connected" message
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": f"Connected to poll {self.poll_id}",
                }
            )
        )

    async def disconnect(self, close_code):
        # Leave the room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Handler for messages broadcasted to the group
    async def poll_update(self, event):
        results = event["results"]
        await self.send(
            text_data=json.dumps({"type": "poll_update", "results": results})
        )
