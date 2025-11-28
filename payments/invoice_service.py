import logging
from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import cloudinary.uploader
from django.conf import settings
import os
from django.contrib.staticfiles import finders


logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service to handle Invoice generation and Cloudinary uploads.
    """

    @staticmethod
    def fetch_resources(uri, rel):
        """
        Callback to allow pisa to resolve static files from STATIC_ROOT or finders.
        """
        # First, try resolving from STATIC_ROOT (for production/collectstatic)
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        if os.path.exists(path):
            return path

        # As a fallback (for development), use Django's static file finders
        normalized_uri = uri.replace(settings.STATIC_URL, "").lstrip('/')
        found_path = finders.find(normalized_uri)
        if found_path:
            return found_path

        logger.warning(f"Static resource not found: {uri}")
        return uri # Return the original URI if not found

    @staticmethod
    def generate_pdf(context: dict, template_name: str = "email/payment_invoice.html") -> bytes | None:
        """
        Render HTML template to PDF bytes.
        """
        try:
            html_string = render_to_string(template_name, context)
            result = BytesIO()
            # encoding='UTF-8' is crucial for currency symbols like ETB
            pdf = pisa.pisaDocument(
                BytesIO(html_string.encode("UTF-8")),
                result,
                encoding='UTF-8',
                link_callback=InvoiceService.fetch_resources
            )

            if not pdf.err:
                return result.getvalue()
            else:
                logger.error(f"PDF generation error: {pdf.err}")
                return None
        except Exception as e:
            logger.error(f"Failed to generate PDF invoice: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def upload_to_cloudinary(file_bytes: bytes, filename: str) -> str | None:
        """
        Uploads raw file bytes to Cloudinary and returns the secure URL.
        """
        try:
            # The public_id determines the full path in Cloudinary
            response = cloudinary.uploader.upload(
                file_bytes,
                resource_type="raw",
                public_id=f"agora/invoices/{filename}",
                overwrite=True
            )
            return response.get("secure_url")
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}", exc_info=True)
            return None
