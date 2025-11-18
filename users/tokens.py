from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator

UserModel = get_user_model()


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        custom_user = cast(UserModel, user)
        return f"{user.pk}{timestamp}{custom_user.email_verified}"


email_verification_token = EmailVerificationTokenGenerator()
