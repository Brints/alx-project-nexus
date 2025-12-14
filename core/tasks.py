import logging
from pathlib import Path

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from django_redis import get_redis_connection

from polls.models import PollOption

User = get_user_model()
logger = logging.getLogger("core.tasks")


@shared_task
def generate_weekly_user_statistics():
    """Generate weekly user registration statistics"""
    logger.info("Generating weekly user statistics")

    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)

    new_users = User.objects.filter(
        date_joined__gte=start_date, date_joined__lte=end_date
    ).count()

    verified_users = User.objects.filter(
        email_verified=True, date_joined__gte=start_date, date_joined__lte=end_date
    ).count()

    stats = {
        "period": f"{start_date.date()} to {end_date.date()}",
        "new_users": new_users,
        "verified_users": verified_users,
        "verification_rate": (
            f"{(verified_users / new_users * 100):.2f}%" if new_users > 0 else "0%"
        ),
    }

    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "logs"
    log_file = log_dir / "user_statistics_report_log.txt"

    try:
        log_dir.mkdir(exist_ok=True)

        with open(log_file, "a") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(
                f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"Period: {stats['period']}\n")
            f.write(f"New Users: {stats['new_users']}\n")
            f.write(f"Verified Users: {stats['verified_users']}\n")
            f.write(f"Verification Rate: {stats['verification_rate']}\n")
            f.write(f"{'=' * 60}\n")

        logger.info(f"Statistics written to {log_file}")
    except (OSError, IOError) as e:
        logger.error(f"Failed to write statistics to file: {str(e)}")

    logger.info(f"Weekly stats: {stats}")
    return stats


@shared_task
def broadcast_poll_updates():
    """
    Periodically checks for 'dirty' polls (polls with new votes)
    and broadcasts the latest results to WebSockets.
    Prevents 'Thundering Herd' by batching updates.
    """
    redis_conn = get_redis_connection("default")
    channel_layer = get_channel_layer()

    # Check if there are any dirty polls
    if not redis_conn.exists("dirty_polls"):
        return

    # 1. Atomic Snapshot
    # Rename the key so we have a static list to process,
    # while new votes start filling a fresh 'dirty_polls' set.
    try:
        redis_conn.rename("dirty_polls", "dirty_polls_processing")
    except Exception:
        # Key might have disappeared or race condition; skip this tick.
        return

    # 2. Get all unique Poll IDs that need updates
    dirty_poll_ids = redis_conn.smembers("dirty_polls_processing")

    logger.info(f"Broadcasting updates for {len(dirty_poll_ids)} polls")

    for poll_id_bytes in dirty_poll_ids:
        try:
            poll_id = poll_id_bytes.decode("utf-8")
            room_group_name = f"poll_{poll_id}"

            # 3. Fetch Fresh Data (Once per batch, not per vote)
            options_data = list(
                PollOption.objects.filter(poll_id=poll_id).values("id", "vote_count")
            )

            # 4. Broadcast to WebSocket Group
            async_to_sync(channel_layer.group_send)(
                room_group_name, {"type": "poll_update", "results": options_data}
            )
        except Exception as e:
            logger.exception(f"Error broadcasting poll {poll_id}: {e}")

    # 5. Cleanup the processing key
    redis_conn.delete("dirty_polls_processing")
