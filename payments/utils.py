import requests
import uuid
import hmac
import hashlib
from django.conf import settings
from rest_framework.exceptions import APIException


class ChapaService:
    def __init__(self):
        self.secret_key = settings.CHAPA_SECRET_KEY
        self.base_url = "https://api.chapa.co/v1"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_payment(
        self,
        email,
        amount,
        first_name,
        last_name,
        return_url,
        phone_number="08098194719",
    ):
        """
        Generates a unique reference and gets the checkout URL from Chapa.
        """
        tx_ref = f"agora-tx-{uuid.uuid4()}"
        callback_url = f"{settings.SITE_URL}v1/payments/webhook/"
        # callback_url = "https://af64ab7848ce.ngrok-free.app/api/v1/payments/webhook/"

        payload = {
            "amount": str(amount),
            "currency": "ETB",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number or "0900000000",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": return_url,
            "customization": {
                "title": "Agora Premium",
                "description": "Unlock unlimited polling features.",
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            if not response.ok:
                error_message = response.text
                raise APIException(f"Chapa Error: {error_message}")

            data = response.json()

            if data.get("status") != "success":
                raise APIException(
                    f"Chapa Error: {data.get('message', 'Unknown error')}"
                )

            return {"checkout_url": data["data"]["checkout_url"], "reference": tx_ref}

        except requests.exceptions.Timeout:
            raise APIException("Payment gateway timeout. Please try again.")
        except requests.exceptions.RequestException as e:
            raise APIException(f"Payment Gateway Error: {str(e)}")

    def verify_payment(self, tx_ref):
        """
        Verifies a transaction with Chapa API.
        """
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{tx_ref}",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    @staticmethod
    def verify_webhook_signature(request_body, signature_header):
        """
        Verifies webhook signature using HMAC SHA256.
        Chapa uses the webhook secret (different from API key).
        """
        if not signature_header:
            return False

        webhook_secret = getattr(
            settings, "CHAPA_WEBHOOK_SECRET", settings.CHAPA_SECRET_KEY
        )
        secret = webhook_secret.encode("utf-8")

        # Compute HMAC
        computed_signature = hmac.new(secret, request_body, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed_signature, signature_header)
