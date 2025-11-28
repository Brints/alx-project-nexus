from django.db import models
from django.conf import settings
import uuid


class Transaction(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )

    # Chapa specific fields
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="ETB")
    email = models.EmailField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    gateway_response = models.JSONField(
        null=True, blank=True
    )

    invoice_url = models.URLField(null=True, blank=True, help_text="URL to the generated PDF invoice", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.reference} - {self.status}"