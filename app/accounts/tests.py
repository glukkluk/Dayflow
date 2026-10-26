from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class _FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {**attrs, "data": {}}
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None and "name" in attrs:
            self.current["data"][attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


@override_settings(
    ALLOWED_HOSTS=["localhost"],
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="test-client-id",
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="test-client-secret",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class GoogleLoginTests(TestCase):
    def test_google_forms_start_oauth_with_csrf_and_preserve_next(self):
        begin_url = reverse("social:begin", args=["google-oauth2"])
        origin = "https://localhost:8000"
        next_url = "/tasks/?status=todo&priority=high"
        for page in ("login", "register"):
            with self.subTest(page=page):
                client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost:8000")
                response = client.get(
                    reverse(f"accounts:{page}"), {"next": next_url}, secure=True
                )
                self.assertEqual(response.status_code, 200)
                parser = _FormParser()
                parser.feed(response.content.decode())
                form = next(form for form in parser.forms if form.get("action") == begin_url)
                self.assertEqual(form["method"], "post")
                self.assertTrue(form["data"]["csrfmiddlewaretoken"])

                response = client.post(
                    form["action"], form["data"], secure=True, HTTP_ORIGIN=origin
                )
                self.assertEqual(response.status_code, 302)
                location = urlsplit(response["Location"])
                self.assertEqual(location.hostname, "accounts.google.com")
                params = parse_qs(location.query)
                self.assertEqual(
                    params["redirect_uri"],
                    [origin + reverse("social:complete", args=["google-oauth2"])],
                )
                self.assertTrue(params["state"][0])
                if page == "login":
                    self.assertEqual(client.session["next"], next_url)

    def test_google_login_requires_csrf(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost:8000")
        response = client.post(
            reverse("social:begin", args=["google-oauth2"]),
            secure=True,
            HTTP_ORIGIN="https://localhost:8000",
        )
        self.assertEqual(response.status_code, 403)


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
