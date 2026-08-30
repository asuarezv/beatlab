from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Company
from .quota import grant_demo
from .tenant import ensure_membership

User = get_user_model()


class HubProfilePasswordTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Labbe 2", slug="labbe-2")
        grant_demo(self.company)
        self.staff = User.objects.create_user(
            username="hubadmin",
            email="hubadmin@labbe.test",
            password="password12",
            first_name="Beto",
            last_name="Admin",
            is_staff=True,
        )
        ensure_membership(self.staff, self.company)

    def _hub_session(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session["company_id"] = self.company.id
        session.save()

    def test_me_includes_email_and_name(self):
        self._hub_session()
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], "hubadmin")
        self.assertEqual(response.json()["user"]["email"], "hubadmin@labbe.test")
        self.assertEqual(response.json()["user"]["display_name"], "Beto Admin")

    def test_change_password_rejects_anonymous(self):
        response = self.client.post(
            "/api/auth/password/",
            {
                "current_password": "password12",
                "password": "nuevaClave99",
                "password2": "nuevaClave99",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_change_password_rejects_wrong_current(self):
        self._hub_session()
        response = self.client.post(
            "/api/auth/password/",
            {
                "current_password": "incorrecta",
                "password": "nuevaClave99",
                "password2": "nuevaClave99",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "La contraseña actual no es correcta.",
        )
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("password12"))

    def test_change_password_rejects_mismatch(self):
        self._hub_session()
        response = self.client.post(
            "/api/auth/password/",
            {
                "current_password": "password12",
                "password": "nuevaClave99",
                "password2": "otraClave99",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Las contraseñas no coinciden.")

    def test_change_password_updates_and_keeps_session(self):
        self._hub_session()
        response = self.client.post(
            "/api/auth/password/",
            {
                "current_password": "password12",
                "password": "nuevaClave99",
                "password2": "nuevaClave99",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Contraseña actualizada.")
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("nuevaClave99"))
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["username"], "hubadmin")
