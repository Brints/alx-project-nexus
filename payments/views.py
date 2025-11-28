import logging
from django.conf import settings
from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Transaction
from .utils import ChapaService
from notifications.tasks import process_successful_payment_actions
from .serializers import (
    InitializePaymentSerializer,
    VerifyPaymentSerializer,
    WebhookSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Payments"])
class PaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    PREMIUM_PRICE = 500.00

    def get_serializer_class(self):
        if self.action == "initialize":
            return InitializePaymentSerializer
        elif self.action == "verify":
            return VerifyPaymentSerializer
        elif self.action == "webhook":
            return WebhookSerializer
        return super().get_serializer_class()

    @extend_schema(
        summary="Initialize Payment",
        responses={200: {"description": "Returns Chapa checkout URL"}},
    )
    @action(detail=False, methods=["post"])
    def initialize(self, request):
        """
        Generates a secure Chapa payment link for premium upgrade.
        """
        user = request.user

        # Check if user is already premium
        if user.is_premium:
            return Response(
                {"message": "You are already a premium user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InitializePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        frontend_return_url = serializer.validated_data.get(
            "return_url", f"{settings.FRONTEND_VERIFICATION_URL}/payment-status"
        )

        chapa = ChapaService()

        try:
            phone_number = serializer.validated_data.get("phone_number", None)

            data = chapa.initialize_payment(
                email=user.email,
                amount=self.PREMIUM_PRICE,
                first_name=user.first_name or "User",
                last_name=user.last_name or "",
                return_url=frontend_return_url,
                phone_number=phone_number,
            )

            Transaction.objects.create(
                user=user,
                reference=data["reference"],
                amount=self.PREMIUM_PRICE,
                currency="ETB",
                email=user.email,
                status="PENDING",
            )

            logger.info(
                f"Payment initialized for {user.email} - Ref: {data['reference']}"
            )

            return Response(
                {"checkout_url": data["checkout_url"], "reference": data["reference"]}
            )

        except Exception as e:
            logger.error(f"Payment initialization failed for {user.email}: {str(e)}")
            return Response(
                {"error": "Unable to initialize payment. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @extend_schema(
        summary="Verify Payment",
        parameters=[
            OpenApiParameter(
                name="tx_ref",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Transaction reference from Chapa",
                required=True,
            )
        ],
        responses={200: {"description": "Payment status page rendered"}},
    )
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.AllowAny],  # Allow unauthenticated access
        authentication_classes=[],  # Bypass authentication
    )
    def verify(self, request):
        """
        Handles Chapa redirect callback and displays payment status.
        """
        tx_ref = request.query_params.get("tx_ref")

        if not tx_ref:
            from django.shortcuts import render

            context = {
                "success": False,
                "message": "Missing transaction reference",
                "is_premium": False,
            }
            return render(request, "email/payment_status.html", context)

        # Fetch transaction to get the user
        try:
            txn = Transaction.objects.select_related("user").get(reference=tx_ref)
            user = txn.user
        except Transaction.DoesNotExist:
            from django.shortcuts import render

            context = {
                "success": False,
                "message": "Transaction not found",
                "is_premium": False,
            }
            return render(request, "email/payment_status.html", context)

        # Process verification with the user from transaction
        result = self._process_payment_verification(tx_ref, user)

        # Prepare context for template
        if isinstance(result, dict):
            context = {
                "success": result.get("success", False),
                "message": result.get("message", "Unknown error"),
                "is_premium": result.get("is_premium", False),
                "transaction_ref": tx_ref if result.get("success") else None,
            }
        else:
            context = {
                "success": False,
                "message": "Payment verification failed",
                "is_premium": False,
            }

        from django.shortcuts import render

        return render(request, "email/payment_status.html", context)

    @extend_schema(
        summary="Webhook Handler",
        request=WebhookSerializer,
        responses={200: {"description": "Webhook processed"}},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        authentication_classes=[],
    )
    def webhook(self, request):
        """
        Server-side webhook handler called by Chapa.
        Verifies signature and processes payment.
        """
        # Extract signature from headers
        signature = (
            request.headers.get("x-chapa-signature")
            or request.headers.get("Chapa-Signature")
            or request.headers.get("X-Chapa-Signature")
        )

        # Verify signature
        if not ChapaService.verify_webhook_signature(request.body, signature):
            logger.warning(
                f"Invalid webhook signature attempt from {request.META.get('REMOTE_ADDR')}"
            )
            return Response(
                {"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN
            )

        # Validate payload
        serializer = WebhookSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid webhook payload: {request.data}")
            return Response(
                {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
            )

        tx_ref = serializer.validated_data["tx_ref"]
        webhook_status = serializer.validated_data["status"]

        # Find transaction
        try:
            txn = Transaction.objects.select_related("user").get(reference=tx_ref)
        except Transaction.DoesNotExist:
            logger.error(f"Webhook received for unknown transaction: {tx_ref}")
            return Response(status=status.HTTP_200_OK)  # prevent retries

        # Process based on webhook status
        if webhook_status.lower() == "success":
            self._process_payment_verification(tx_ref, txn.user, from_webhook=True)
        else:
            with transaction.atomic():
                txn.status = "FAILED"
                txn.gateway_response = request.data
                txn.save()
            logger.info(f"Webhook: Payment failed for {tx_ref}")

        return Response(status=status.HTTP_200_OK)

    def _process_payment_verification(self, tx_ref, user, from_webhook=False):
        """
        Shared verification logic for both client and webhook.
        """
        try:
            txn = Transaction.objects.select_related("user").get(
                reference=tx_ref, user=user
            )
        except Transaction.DoesNotExist:
            if from_webhook:
                return Response(status=status.HTTP_200_OK)
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Idempotency check
        if txn.status == "SUCCESS":
            message = "Payment already verified"
            logger.info(
                f"{'Webhook' if from_webhook else 'Verify'}: {message} for {tx_ref}"
            )
            if from_webhook:
                return Response(status=status.HTTP_200_OK)
            return Response(
                {"message": message, "is_premium": user.is_premium},
                status=status.HTTP_200_OK,
            )

        # Verify with Chapa API
        chapa = ChapaService()
        verification_data = chapa.verify_payment(tx_ref)

        if not verification_data:
            if from_webhook:
                return Response(status=status.HTTP_200_OK)
            return Response(
                {"error": "Unable to verify payment with gateway"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Process successful payment
        if verification_data.get("status") == "success":
            with transaction.atomic():
                # Update transaction
                txn.status = "SUCCESS"
                txn.gateway_response = verification_data
                txn.save()

                # Upgrade user to premium
                if not user.is_premium:
                    user.is_premium = True
                    user.save(update_fields=["is_premium"])

            logger.info(
                f"Payment successful for {user.email} "
                f"(Ref: {tx_ref}, Source: {'Webhook' if from_webhook else 'Client'})"
            )

            # Trigger Invoice Generation and Email Task
            try:
                process_successful_payment_actions.delay(txn.id)
            except Exception as e:
                logger.error(f"Failed to trigger invoice task for {tx_ref}: {e}")

            if from_webhook:
                return Response(status=status.HTTP_200_OK)

            return {
                "success": True,
                "message": "Payment verified successfully",
                "is_premium": True,
            }
        else:
            # Payment failed
            with transaction.atomic():
                txn.status = "FAILED"
                txn.gateway_response = verification_data
                txn.save()

            logger.warning(
                f"Payment verification failed for {tx_ref}: {verification_data}"
            )

            if from_webhook:
                return Response(status=status.HTTP_200_OK)

            return {"success": False, "message": "Payment verification failed"}
