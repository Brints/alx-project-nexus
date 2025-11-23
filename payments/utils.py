import requests
import uuid
from django.conf import settings
from rest_framework.exceptions import APIException


class ChapaService:
    def __init__(self):
        self.secret_key = settings.CHAPPA_SECRET_KEY
        self.base_url = "https://api.chapa.co/v1"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def initialize_payment(self, email, amount, first_name, last_name, return_url):
        """
        Generates a unique reference and gets the checkout URL from Chapa.
        """
        tx_ref = f"agora-tx-{uuid.uuid4()}"

        payload = {
            "amount": str(amount),
            "currency": "ETB",  # Or NGN, USD based on your account
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": tx_ref,
            "callback_url": f"{settings.SITE_URL}payments/webhook/",  # For async confirmation
            "return_url": return_url,  # Where user is redirected after payment
            "customization[title]": "Agora Premium Upgrade",
            "customization[description]": "Unlock unlimited polling."
        }

        try:
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            if data['status'] != 'success':
                raise APIException(f"Chapa Error: {data.get('message')}")

            return {
                "checkout_url": data['data']['checkout_url'],
                "reference": tx_ref
            }

        except requests.exceptions.RequestException as e:
            raise APIException(f"Payment Gateway Error: {str(e)}")

    def verify_payment(self, tx_ref):
        """
        Queries Chapa to check the actual status of a transaction.
        """
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{tx_ref}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None