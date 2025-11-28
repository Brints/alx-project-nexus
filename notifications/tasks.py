import logging
from celery import shared_task

from django.db import transaction as db_transaction

from notifications.email_service import send_email
from organizations.models import OrganizationMember
from payments.invoice_service import InvoiceService
from payments.models import Transaction

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
        attachments: list[tuple[str, bytes, str]] | None = None,
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
            attachments=attachments,
        )
        logger.info(f"Email sent successfully to {recipients}")
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}", exc_info=True)
        logger.error(f"Retry attempt {self.request.retries}/{self.max_retries}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
    retry_kwargs={"max_retries": 5},
)
def process_successful_payment_actions(self, transaction_id):
    """
    Generates invoice, uploads to Cloudinary, and sends email with attachment.
    """
    logger.info(f"Starting post-payment processing for transaction {transaction_id}")

    try:
        transaction = Transaction.objects.select_related('user').get(id=transaction_id)

        # Prepare Invoice Context
        context = {
            "transaction": transaction,
            "user": transaction.user,
            "date": transaction.updated_at.strftime("%B %d, %Y"),
            "company_name": "Agora Online Polls",
            "company_address": "123 Tech Street, Abuja, Nigeria",
        }

        # Generate PDF
        pdf_bytes = InvoiceService.generate_pdf(context)
        if not pdf_bytes:
            raise Exception("Failed to generate PDF bytes")

        filename = f"invoice_{transaction.reference}.pdf"

        # Upload to Cloudinary
        invoice_url = InvoiceService.upload_to_cloudinary(pdf_bytes, filename)

        if invoice_url:
            with db_transaction.atomic():
                transaction.invoice_url = invoice_url
                transaction.save(update_fields=["invoice_url"])
                logger.info(f"Invoice uploaded to Cloudinary: {invoice_url}")
        else:
            # If upload fails, log it but continue to send email without the URL.
            logger.warning("Failed to upload invoice to Cloudinary. The invoice URL will be missing.")

        # 4. Send Email with Attachment
        email_context = {
            "user_name": transaction.user.first_name,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "invoice_url": invoice_url
        }

        send_email_task.delay(
            subject="Payment Successful - Your Invoice",
            recipients=[transaction.email],
            template_name="email/payment_status.html",
            context=email_context,
            attachments=[(filename, pdf_bytes, "application/pdf")]
        )

        logger.info(f"Invoice generated and email task queued for transaction {transaction.reference}")

    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found")
    except Exception as e:
        logger.error(f"Error processing successful payment: {str(e)}", exc_info=True)
        raise


@shared_task
def send_daily_summary_emails():
    """Send daily summary emails to organization admins"""
    from organizations.models import Organization

    logger.info("Starting daily summary email task")

    organizations = Organization.objects.prefetch_related("members", "polls").all()
    sent_count = 0

    for org in organizations:
        admin_emails = list(
            org.members.filter(role=OrganizationMember.Role.ADMIN).values_list("user__email", flat=True)
        )

        if admin_emails:
            # Get org statistics
            context = {
                "organization_name": org.org_name,
                "total_polls": org.polls.count(),
                "active_polls": org.polls.filter(is_active=True).count(),
            }

            send_email_task.delay(
                subject=f"Daily Summary for {org.org_name}",
                recipients=admin_emails,
                template_name="email/send_daily_summary_emails_to_org_admin.html",
                context=context,
            )
            sent_count += 1

    logger.info(f"Daily summary emails queued for {sent_count} organizations")
    return f"Sent summaries to {sent_count} organizations"
