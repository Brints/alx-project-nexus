from django.conf import settings
from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Transaction
from .utils import ChapaService


class PaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    # Hardcoded for now, but could be dynamic
    PREMIUM_PRICE = 500.00

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """
        Step 1: User clicks 'Upgrade'.
        Returns: { "checkout_url": "..." }
        """
        user = request.user

        # Define where Chapa should redirect back to your FRONTEND
        # e.g., http://localhost:3000/payment/success
        frontend_return_url = request.data.get(
            'return_url',
            f"{settings.FRONTEND_VERIFICATION_URL}/payment-status"
        )

        chapa = ChapaService()

        try:
            # Call Chapa API
            data = chapa.initialize_payment(
                email=user.email,
                amount=self.PREMIUM_PRICE,
                first_name=user.first_name,
                last_name=user.last_name,
                return_url=frontend_return_url
            )

            # Create Local Record (Pending)
            Transaction.objects.create(
                user=user,
                reference=data['reference'],
                amount=self.PREMIUM_PRICE,
                email=user.email,
                status='PENDING'
            )

            return Response({
                "checkout_url": data['checkout_url'],
                "reference": data['reference']
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Step 2: User is redirected back to Frontend, Frontend sends the 'tx_ref' here.
        We verify with Chapa and update User status.
        """
        tx_ref = request.data.get('tx_ref')
        if not tx_ref:
            return Response({"error": "Transaction reference required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            txn = Transaction.objects.get(reference=tx_ref, user=request.user)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'SUCCESS':
            return Response({"message": "Payment already verified"}, status=status.HTTP_200_OK)

        # Verify with Chapa
        chapa = ChapaService()
        verification_data = chapa.verify_payment(tx_ref)

        if verification_data and verification_data.get('status') == 'success':
            # Ensure the amount paid matches what we expected
            # Note: Chapa returns amount as string or float, allow for slight mismatch logic if needed
            # paid_amount = float(verification_data['data']['amount'])

            with transaction.atomic():
                # 1. Update Transaction
                txn.status = 'SUCCESS'
                txn.gateway_response = verification_data
                txn.save()

                # 2. Update User Status
                user = request.user
                user.is_premium = True
                # user.premium_expiry = timezone.now() + timedelta(days=30) # If doing monthly
                user.save()

            return Response({"message": "Upgrade successful", "is_premium": True})

        else:
            txn.status = 'FAILED'
            txn.save()
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)