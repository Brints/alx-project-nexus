from rest_framework import serializers


class InitializePaymentSerializer(serializers.Serializer):
    return_url = serializers.URLField(
        required=False, help_text="The URL to redirect the user to after payment."
    )
    phone_number = serializers.CharField(
        required=False, help_text="User's phone number (required by Chapa)"
    )


class VerifyPaymentSerializer(serializers.Serializer):
    tx_ref = serializers.CharField(
        help_text="The unique transaction reference returned by Chapa."
    )


class WebhookSerializer(serializers.Serializer):
    tx_ref = serializers.CharField()
    status = serializers.CharField()
    email = serializers.EmailField()
    currency = serializers.CharField()
    amount = serializers.CharField()
    reference = serializers.CharField()
