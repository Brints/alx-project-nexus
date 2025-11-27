import logging
from pathlib import Path

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import os

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
    log_file = project_root / "user_statistics_report_log.txt"

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

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
    except Exception as e:
        logger.error(f"Failed to write statistics to file: {str(e)}")

    logger.info(f"Weekly stats: {stats}")
    return stats
