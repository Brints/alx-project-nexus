from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from django_redis import get_redis_connection

from .models import Vote, PollOption

@receiver(post_save, sender=Vote)
def handle_new_vote(sender, instance, created, **kwargs):
    """
    Triggered when a Vote is saved.
    1. Atomically increments the PollOption count (DB).
    2. Marks the poll as 'dirty' in Redis for the background worker to pick up.
    """
    if created:
        # Atomic Increment (DB Side)
        # Keeps data integrity without race conditions
        PollOption.objects.filter(id=instance.option.id).update(
            vote_count=F("vote_count") + 1
        )

        try:
            con = get_redis_connection("default")
            con.sadd("dirty_polls", str(instance.poll.poll_id))
        except Exception as e:
            # The vote is safe in the DB, just the real-time update might delay.
            print(f"Failed to flag dirty poll in Redis: {e}")