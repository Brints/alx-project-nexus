import logging

from celery import shared_task
from django.utils import timezone

from notifications.email_service import send_email
from users.models import UserVerification

logger = logging.getLogger("notifications.tasks")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    max_retries=5,
)
def send_email_task(
    self,
    *,
    subject: str,
    recipients: list[str],
    template_name: str | None = None,
    context: dict | None = None,
    text_body: str | None = None,
    from_email: str | None = None,
) -> None:
    logger.info(f"Email task started: {subject} to {recipients}")
    try:
        send_email(
            subject=subject,
            recipients=recipients,
            template_name=template_name,
            context=context,
            text_body=text_body,
            from_email=from_email,
        )
        logger.info(f"Email sent successfully to {recipients}")
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}", exc_info=True)
        logger.error(f"Retry attempt {self.request.retries}/{self.max_retries}")
        raise


@shared_task
def cleanup_expired_verifications():
    """Remove expired verification tokens"""
    expired = UserVerification.objects.filter(
        expires_at__lt=timezone.now(), is_verified=False
    )
    count = expired.count()
    expired.delete()
    return f"Deleted {count} expired verification records"
