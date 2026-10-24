from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse


class PasswordHashingTests(TestCase):
    password = "Test-only-password-7mG!5x"

    def test_registration_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing_user", email="same@example.com", password=self.password
        )

        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "another_user",
                "email": "same@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.filter(email="same@example.com").count(), 1)

    def test_registration_and_login_use_argon2id(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "new_user",
                "email": "new@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertRedirects(
            response, reverse("planner:dashboard"), fetch_redirect_response=False
        )
        user = get_user_model().objects.get(username="new_user")
        self.assertTrue(user.password.startswith("argon2$argon2id$"))
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))

    def test_legacy_password_upgrades_only_after_successful_login(self):
        legacy_hash = make_password(self.password, hasher="pbkdf2_sha256")
        user = get_user_model().objects.create(
            username="legacy_user", password=legacy_hash
        )

        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.username, "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        user.refresh_from_db()
        self.assertEqual(user.password, legacy_hash)

        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.username, "password": self.password},
        )
        self.assertRedirects(
            response, reverse("planner:dashboard"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        user.refresh_from_db()
        self.assertTrue(user.password.startswith("argon2$argon2id$"))
        self.assertTrue(user.check_password(self.password))
