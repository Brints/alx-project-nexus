import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from notifications.tasks import send_email_task

User = get_user_model()
logger = logging.getLogger("authentication.tasks")


@shared_task
def cleanup_expired_tokens():
    """Clean up expired verification tokens"""
    from users.models import UserVerification

    logger.info("Starting token cleanup task")
    expired = UserVerification.objects.filter(
        expires_at__lt=timezone.now(), is_verified=False
    )
    count = expired.count()
    expired.delete()

    logger.info(f"Deleted {count} expired verification tokens")
    return f"Deleted {count} expired verification records"


@shared_task
def send_reminder_email_to_unverified_users():
    """Send reminder emails to users who haven't verified their email"""
    logger.info("Starting unverified user reminder task")

    # Find users who registered more than 3 days ago but haven't verified
    cutoff_date = timezone.now() - timedelta(days=3)
    unverified_users = User.objects.filter(
        is_email_verified=False,
        date_joined__lte=cutoff_date,
        date_joined__gte=timezone.now() - timedelta(days=30),
    )

    sent_count = 0
    for user in unverified_users:
        context = {
            "user_name": user.get_full_name() or user.username,
            "verification_link": f"{user.get_verification_link()}",
        }

        send_email_task.delay(
            subject="Reminder: Verify Your Email",
            recipients=[user.email],
            template_name="send_reminder_to_verify_email.html",
            context=context,
        )
        sent_count += 1

    logger.info(f"Sent verification reminders to {sent_count} users")
    return f"Sent reminders to {sent_count} unverified users"
