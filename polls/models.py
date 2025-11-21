from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class PollCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Poll(models.Model):
    poll_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll_question = models.CharField(max_length=255)
    poll_category = models.ForeignKey(PollCategory, on_delete=models.PROTECT)

    # Ownership & Context
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='polls')

    # Lifecycle
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    manually_closed = models.BooleanField(default=False)

    # Restrictions
    is_public = models.BooleanField(default=True)  # If False, requires Org membership
    allowed_country = models.CharField(max_length=2, blank=True,
                                       help_text="ISO Country Code (e.g., NG, US). Leave empty for global.")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date.')

    @property
    def is_expired(self):
        return timezone.now() > self.end_date


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    image = models.ImageField(upload_to='poll_options/', null=True, blank=True)

    # Optimization: Store count here for read speed, update via Signals
    vote_count = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.poll.poll_question} ({self.text})"


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE)

    # Identity (One must be present)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['poll', 'user']),
            models.Index(fields=['poll', 'ip_address']),
        ]