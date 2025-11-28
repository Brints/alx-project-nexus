from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status

from authentication.utils import _verify_email
from users.models import UserVerification
from users.utils import email_verification_token

UserModel = get_user_model()


class EmailVerificationUtilTest(TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.user = UserModel.objects.create_user(
            email="test@example.com", password="password123", email_verified=False
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = email_verification_token.make_token(self.user)

    def test_verify_email_success(self):
        """
        Test that email verification is successful with a valid UID and token.
        """
        UserVerification.objects.create(
            user=self.user,
            verification_type="email",
            verification_code=self.token,
        )

        response = _verify_email(self.uid, self.token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Email verified successfully.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

        # Check that the verification record has been deleted
        self.assertFalse(
            UserVerification.objects.filter(user=self.user, verification_type="email").exists()
        )
