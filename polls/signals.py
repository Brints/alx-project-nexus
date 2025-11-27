from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Vote, PollOption


@receiver(post_save, sender=Vote)
def handle_new_vote(sender, instance, created, **kwargs):
    """
    Triggered when a Vote is saved.
    1. Atomically increments the PollOption count.
    2. Broadcasts the new count to WebSocket via Redis.
    """
    if created:
        # Atomic Increment (Solves Race Conditions) ---
        # We use F() expressions to update the database directly without
        # fetching the object into Python memory first.
        (
            PollOption.objects.filter(id=instance.option.id).update(
                vote_count=F("vote_count") + 1
            )
        )

        # Real-time Broadcast (WebSockets) ---
        channel_layer = get_channel_layer()
        poll_id = str(instance.poll.poll_id)
        room_group_name = f"poll_{poll_id}"

        # Fetch the fresh counts for all options in this poll
        options_data = list(
            PollOption.objects.filter(poll_id=instance.poll.poll_id).values(
                "id", "vote_count"
            )
        )

        # Push to consumers.py
        async_to_sync(channel_layer.group_send)(
            room_group_name, {"type": "poll_update", "results": options_data}
        )
