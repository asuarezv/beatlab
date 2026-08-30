from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Company, Operator
from .quota import grant_demo
from .tenant import ensure_membership
from .tokens import issue_operator_jwt
from .validation import (
    EMAIL_INVALID,
    HUB_EMAIL_TAKEN,
    OPERATOR_EMAIL_TAKEN,
    PERSON_NAME_ERROR,
    PROFILE_UPDATED,
)

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
        self.assertEqual(response.json()["user"]["first_name"], "Beto")
        self.assertEqual(response.json()["user"]["last_name"], "Admin")
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

    def test_update_profile_rejects_anonymous(self):
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Beto",
                "last_name": "Admin",
                "email": "nuevo@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_profile_changes_name_and_email(self):
        self._hub_session()
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Roberto",
                "last_name": "Labbe",
                "email": "roberto@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], PROFILE_UPDATED)
        self.assertEqual(response.json()["user"]["first_name"], "Roberto")
        self.assertEqual(response.json()["user"]["last_name"], "Labbe")
        self.assertEqual(response.json()["user"]["email"], "roberto@labbe.test")
        self.assertEqual(response.json()["user"]["display_name"], "Roberto Labbe")
        self.assertEqual(response.json()["user"]["username"], "hubadmin")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Roberto")
        self.assertEqual(self.staff.email, "roberto@labbe.test")
        self.assertEqual(self.staff.username, "hubadmin")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "roberto@labbe.test")

    def test_update_profile_keeps_own_email(self):
        self._hub_session()
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Beto",
                "last_name": "Admin",
                "email": "HUBADMIN@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "hubadmin@labbe.test")

    def test_update_profile_rejects_operator_email(self):
        op_user = User.objects.create_user(
            username="opdemo",
            email="op@labbe.test",
            password="password12",
        )
        Operator.objects.create(
            company=self.company,
            user=op_user,
            first_name="Ana",
            last_name="Pérez",
            email="op@labbe.test",
        )
        self._hub_session()
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Beto",
                "last_name": "Admin",
                "email": "OP@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], OPERATOR_EMAIL_TAKEN)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "hubadmin@labbe.test")

    def test_update_profile_rejects_other_hub_email(self):
        User.objects.create_user(
            username="otroadmin",
            email="otro@labbe.test",
            password="password12",
            is_staff=True,
        )
        self._hub_session()
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Beto",
                "last_name": "Admin",
                "email": "otro@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], HUB_EMAIL_TAKEN)

    def test_update_profile_rejects_invalid_email_and_empty_name(self):
        self._hub_session()
        invalid = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Beto",
                "last_name": "Admin",
                "email": "no-es-correo",
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["detail"], EMAIL_INVALID)
        empty = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "  ",
                "last_name": "Admin",
                "email": "hubadmin@labbe.test",
            },
            format="json",
        )
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json()["detail"], PERSON_NAME_ERROR)


class MonitorProfileTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Labbe 2", slug="labbe-2")
        grant_demo(self.company)
        self.staff = User.objects.create_user(
            username="hubadmin",
            email="hubadmin@labbe.test",
            password="password12",
            is_staff=True,
        )
        ensure_membership(self.staff, self.company)
        self.op_user = User.objects.create_user(
            username="opdemo",
            email="op@labbe.test",
            password="password12",
            first_name="Ana",
            last_name="Pérez",
        )
        self.operator = Operator.objects.create(
            company=self.company,
            user=self.op_user,
            first_name="Ana",
            last_name="Pérez",
            email="op@labbe.test",
        )

    def _auth(self):
        return f"Bearer {issue_operator_jwt(self.operator)}"

    def test_update_profile_rejects_anonymous(self):
        response = self.client.patch(
            "/api/monitor/auth/me/",
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_profile_changes_name_and_email(self):
        response = self.client.patch(
            "/api/monitor/auth/me/",
            {
                "first_name": "Ana María",
                "last_name": "García",
                "email": "ana@labbe.test",
            },
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], PROFILE_UPDATED)
        self.assertEqual(response.data["operator"]["first_name"], "Ana María")
        self.assertEqual(response.data["operator"]["last_name"], "García")
        self.assertEqual(response.data["operator"]["email"], "ana@labbe.test")
        self.assertEqual(response.data["operator"]["display_name"], "Ana María García")
        self.operator.refresh_from_db()
        self.op_user.refresh_from_db()
        self.assertEqual(self.operator.email, "ana@labbe.test")
        self.assertEqual(self.op_user.email, "ana@labbe.test")
        self.assertEqual(self.op_user.first_name, "Ana María")
        me = self.client.get(
            "/api/monitor/auth/me/",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["operator"]["email"], "ana@labbe.test")

    def test_update_profile_rejects_other_operator_email(self):
        other_user = User.objects.create_user(
            username="opluis",
            email="luis@labbe.test",
            password="password12",
        )
        Operator.objects.create(
            company=self.company,
            user=other_user,
            first_name="Luis",
            last_name="García",
            email="luis@labbe.test",
        )
        response = self.client.patch(
            "/api/monitor/auth/me/",
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "LUIS@labbe.test",
            },
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], OPERATOR_EMAIL_TAKEN)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.email, "op@labbe.test")

    def test_update_profile_rejects_hub_admin_email(self):
        response = self.client.patch(
            "/api/monitor/auth/me/",
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "hubadmin@labbe.test",
            },
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], HUB_EMAIL_TAKEN)
