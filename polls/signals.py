from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

from .models import Vote, PollOption

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Vote)
def handle_new_vote(sender, instance, created, **kwargs):
    """
    Triggered when a Vote is saved.
    1. Atomically increments the PollOption count.
    2. Broadcasts the new count to WebSocket via Redis.
    """
    if created:
        try:
            # 1. Atomic Increment (DB Side)
            PollOption.objects.filter(id=instance.option.id).update(
                vote_count=F("vote_count") + 1
            )

            # 2. Real-time Broadcast
            channel_layer = get_channel_layer()
            # Use raw poll_id to avoid extra DB lookup for the Poll object
            poll_id = str(instance.poll_id)
            room_group_name = f"poll_{poll_id}"

            # Fetch fresh counts
            # We fetch all options for this poll to ensure the frontend is fully synced
            options = PollOption.objects.filter(poll_id=poll_id).only(
                "index", "vote_count"
            )

            # Format data: Map 'index' to 'id' for the frontend
            formatted_data = [
                {"id": opt.index, "vote_count": opt.vote_count} for opt in options
            ]

            # Send the updated counts to the group
            async_to_sync(channel_layer.group_send)(
                room_group_name, {"type": "poll_update", "results": formatted_data}
            )

        except Exception as e:
            # Log the error but DO NOT crash the request.
            # The vote is already saved, so we shouldn't return a 500 error
            # just because the real-time update failed.
            logger.error(f"Error broadcasting poll update: {e}", exc_info=True)
