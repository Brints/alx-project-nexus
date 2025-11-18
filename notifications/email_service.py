import logging
from typing import Iterable, Mapping, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _render_bodies(
    template_name: Optional[str], context: Optional[Mapping]
) -> tuple[str, str]:
    if not template_name:
        return "", ""
    html_body = render_to_string(template_name, context or {})
    return html_body, strip_tags(html_body)


def send_email(
    *,
    subject: str,
    recipients: Iterable[str],
    template_name: Optional[str] = None,
    context: Optional[Mapping] = None,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> None:
    try:
        html_body, rendered_text = _render_bodies(template_name, context)
        final_text = text_body or rendered_text or ""
        final_html = html_body or None

        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            fail_silently=getattr(settings, "EMAIL_FAIL_SILENTLY", False),
            timeout=getattr(settings, "EMAIL_TIMEOUT", 10),
        )

        message = EmailMultiAlternatives(
            subject=subject,
            body=final_text,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=list(recipients),
            connection=connection,
        )
        if final_html:
            message.attach_alternative(final_html, "text/html")
        for attachment in attachments or []:
            message.attach(*attachment)
        message.send()
        logger.info(f"Email sent successfully to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: {str(e)}", exc_info=True)
        raise
