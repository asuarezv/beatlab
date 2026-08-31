from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APITestCase

from .models import Company, EmailChangeChallenge, Operator
from .quota import grant_demo
from .tenant import ensure_membership
from .tokens import MonitorActor, issue_monitor_jwt, issue_operator_jwt
from .validation import (
    CURRENT_PASSWORD_ERROR,
    EMAIL_CHANGE_SENT,
    EMAIL_INVALID,
    HUB_EMAIL_TAKEN,
    OPERATOR_EMAIL_TAKEN,
    PASSWORD_CHANGE_REQUIRED,
    PASSWORD_UPDATED,
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
        with patch("hub.otp.secrets.choice", return_value="7"):
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
        self.assertEqual(response.json()["detail"], EMAIL_CHANGE_SENT)
        self.assertEqual(response.json()["pending_email"], "roberto@labbe.test")
        self.assertEqual(response.json()["user"]["first_name"], "Roberto")
        self.assertEqual(response.json()["user"]["last_name"], "Labbe")
        self.assertEqual(response.json()["user"]["email"], "hubadmin@labbe.test")
        self.assertEqual(response.json()["user"]["display_name"], "Roberto Labbe")
        self.assertEqual(response.json()["user"]["username"], "hubadmin")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Roberto")
        self.assertEqual(self.staff.last_name, "Labbe")
        self.assertEqual(self.staff.email, "hubadmin@labbe.test")
        self.assertEqual(self.staff.username, "hubadmin")
        self.assertEqual(
            EmailChangeChallenge.objects.filter(email="roberto@labbe.test").count(),
            1,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Confirma tu nuevo correo")
        self.assertEqual(mail.outbox[0].to, ["roberto@labbe.test"])
        confirmed = self.client.post(
            "/api/auth/profile/verify/",
            {"email": "roberto@labbe.test", "otp": "777777"},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["detail"], PROFILE_UPDATED)
        self.assertEqual(confirmed.json()["user"]["email"], "roberto@labbe.test")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "roberto@labbe.test")
        self.assertEqual(EmailChangeChallenge.objects.count(), 0)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "roberto@labbe.test")

    def test_update_profile_email_otp_rejects_wrong_code(self):
        self._hub_session()
        with patch("hub.otp.secrets.choice", return_value="3"):
            self.client.patch(
                "/api/auth/profile/",
                {
                    "first_name": "Beto",
                    "last_name": "Admin",
                    "email": "nuevo@labbe.test",
                },
                format="json",
            )
        wrong = self.client.post(
            "/api/auth/profile/verify/",
            {"email": "nuevo@labbe.test", "otp": "000000"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.json()["detail"], "El código no es válido.")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "hubadmin@labbe.test")

    def test_verify_profile_email_rejects_anonymous(self):
        response = self.client.post(
            "/api/auth/profile/verify/",
            {"email": "nuevo@labbe.test", "otp": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_profile_keeps_email_if_otp_send_fails(self):
        self._hub_session()
        with patch("hub.otp.send_email_change_otp", side_effect=RuntimeError("smtp")):
            response = self.client.patch(
                "/api/auth/profile/",
                {
                    "first_name": "Roberto",
                    "last_name": "Labbe",
                    "email": "roberto@labbe.test",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "No se pudo enviar el código. Inténtalo de nuevo.",
        )
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Roberto")
        self.assertEqual(self.staff.last_name, "Labbe")
        self.assertEqual(self.staff.email, "hubadmin@labbe.test")
        self.assertEqual(EmailChangeChallenge.objects.count(), 0)

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
        self.assertNotIn("pending_email", response.json())
        self.assertEqual(len(mail.outbox), 0)

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

    def test_me_includes_empty_name_fields(self):
        self.staff.first_name = ""
        self.staff.last_name = ""
        self.staff.save(update_fields=["first_name", "last_name"])
        self._hub_session()
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["first_name"], "")
        self.assertEqual(response.json()["user"]["last_name"], "")
        self.assertIn("email", response.json()["user"])

    def test_update_profile_fills_empty_names(self):
        self.staff.first_name = ""
        self.staff.last_name = ""
        self.staff.save(update_fields=["first_name", "last_name"])
        self._hub_session()
        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Roberto",
                "last_name": "Labbe",
                "email": "hubadmin@labbe.test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], PROFILE_UPDATED)
        self.assertEqual(response.json()["user"]["first_name"], "Roberto")
        self.assertEqual(response.json()["user"]["last_name"], "Labbe")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Roberto")
        self.assertEqual(self.staff.last_name, "Labbe")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.json()["user"]["first_name"], "Roberto")
        self.assertEqual(me.json()["user"]["last_name"], "Labbe")

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

    def test_verify_email_rejects_anonymous(self):
        response = self.client.post(
            "/api/monitor/auth/verify-email/",
            {"email": "ana@labbe.test", "otp": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_profile_changes_name_and_email(self):
        with patch("hub.otp.secrets.choice", return_value="8"):
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
        self.assertEqual(response.data["detail"], EMAIL_CHANGE_SENT)
        self.assertEqual(response.data["pending_email"], "ana@labbe.test")
        self.assertEqual(response.data["operator"]["first_name"], "Ana María")
        self.assertEqual(response.data["operator"]["last_name"], "García")
        self.assertEqual(response.data["operator"]["email"], "op@labbe.test")
        self.assertEqual(response.data["operator"]["display_name"], "Ana María García")
        self.operator.refresh_from_db()
        self.op_user.refresh_from_db()
        self.assertEqual(self.operator.email, "op@labbe.test")
        self.assertEqual(self.op_user.email, "op@labbe.test")
        self.assertEqual(self.op_user.first_name, "Ana María")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Confirma tu nuevo correo")
        self.assertEqual(mail.outbox[0].to, ["ana@labbe.test"])
        confirmed = self.client.post(
            "/api/monitor/auth/verify-email/",
            {"email": "ana@labbe.test", "otp": "888888"},
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["detail"], PROFILE_UPDATED)
        self.assertEqual(confirmed.data["operator"]["email"], "ana@labbe.test")
        self.operator.refresh_from_db()
        self.op_user.refresh_from_db()
        self.assertEqual(self.operator.email, "ana@labbe.test")
        self.assertEqual(self.op_user.email, "ana@labbe.test")
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


class MonitorAdminProfileTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Labbe 2", slug="labbe-2")
        grant_demo(self.company)
        self.staff = User.objects.create_user(
            username="hubadmin",
            email="hubadmin@labbe.test",
            password="password12",
            first_name="Hugo",
            last_name="Admin",
            is_staff=True,
        )
        ensure_membership(self.staff, self.company)
        self.op_user = User.objects.create_user(
            username="opdemo",
            email="op@labbe.test",
            password="password12",
        )
        self.operator = Operator.objects.create(
            company=self.company,
            user=self.op_user,
            first_name="Ana",
            last_name="Pérez",
            email="op@labbe.test",
        )

    def _auth(self):
        return (
            f"Bearer {issue_monitor_jwt(MonitorActor.from_admin(self.staff, self.company))}"
        )

    def test_admin_profile_updates_hub_user_not_operator(self):
        with patch("hub.otp.secrets.choice", return_value="8"):
            response = self.client.patch(
                "/api/monitor/auth/me/",
                {
                    "first_name": "Hugo",
                    "last_name": "García",
                    "email": "hugo@labbe.test",
                },
                format="json",
                HTTP_AUTHORIZATION=self._auth(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], EMAIL_CHANGE_SENT)
        self.assertEqual(response.data["role"], "admin")
        self.assertEqual(response.data["pending_email"], "hugo@labbe.test")
        self.assertEqual(response.data["operator"]["email"], "hubadmin@labbe.test")
        self.assertEqual(response.data["operator"]["last_name"], "García")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Hugo")
        self.assertEqual(self.staff.last_name, "García")
        self.assertEqual(self.staff.email, "hubadmin@labbe.test")
        self.assertFalse(Operator.objects.filter(user=self.staff).exists())
        confirmed = self.client.post(
            "/api/monitor/auth/verify-email/",
            {"email": "hugo@labbe.test", "otp": "888888"},
            format="json",
            HTTP_AUTHORIZATION=self._auth(),
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["detail"], PROFILE_UPDATED)
        self.assertEqual(confirmed.data["operator"]["email"], "hugo@labbe.test")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "hugo@labbe.test")
        self.assertFalse(Operator.objects.filter(email="hugo@labbe.test").exists())
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.email, "op@labbe.test")

    def test_admin_password_updates_django_user(self):
        token = self._auth()
        missing = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "NuevaClave99", "password2": "NuevaClave99"},
            format="json",
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.data["detail"], PASSWORD_CHANGE_REQUIRED)
        wrong = self.client.post(
            "/api/monitor/auth/password/",
            {
                "current_password": "no-es-esa",
                "password": "NuevaClave99",
                "password2": "NuevaClave99",
            },
            format="json",
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.data["detail"], CURRENT_PASSWORD_ERROR)
        updated = self.client.post(
            "/api/monitor/auth/password/",
            {
                "current_password": "password12",
                "password": "NuevaClave99",
                "password2": "NuevaClave99",
            },
            format="json",
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["detail"], PASSWORD_UPDATED)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("NuevaClave99"))
        self.assertFalse(self.staff.check_password("password12"))
        self.assertFalse(Operator.objects.filter(user=self.staff).exists())
        login = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "hubadmin@labbe.test", "password": "NuevaClave99"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["role"], "admin")


class HubOperatorProfileTests(APITestCase):
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
        self.operator.set_password("OperatorClave99")
        self.operator.save(update_fields=["password_hash"])

    def _login(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "op@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_hub_profile_updates_operator_and_confirms_email(self):
        self._login()
        with patch("hub.otp.secrets.choice", return_value="8"):
            response = self.client.patch(
                "/api/auth/profile/",
                {
                    "first_name": "Ana María",
                    "last_name": "García",
                    "email": "ana@labbe.test",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], EMAIL_CHANGE_SENT)
        self.assertEqual(response.json()["pending_email"], "ana@labbe.test")
        self.assertEqual(response.json()["role"], "operator")
        self.assertEqual(response.json()["user"]["email"], "op@labbe.test")
        self.assertEqual(response.json()["user"]["first_name"], "Ana María")
        confirmed = self.client.post(
            "/api/auth/profile/verify/",
            {"email": "ana@labbe.test", "otp": "888888"},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["detail"], PROFILE_UPDATED)
        self.assertEqual(confirmed.json()["user"]["email"], "ana@labbe.test")
        self.operator.refresh_from_db()
        self.op_user.refresh_from_db()
        self.assertEqual(self.operator.email, "ana@labbe.test")
        self.assertEqual(self.op_user.email, "ana@labbe.test")

    def test_hub_password_updates_operator_hash(self):
        self._login()
        updated = self.client.post(
            "/api/auth/password/",
            {
                "current_password": "OperatorClave99",
                "password": "OtraClave88",
                "password2": "OtraClave88",
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["detail"], PASSWORD_UPDATED)
        self.operator.refresh_from_db()
        self.assertTrue(self.operator.check_password("OtraClave88"))
        self.assertFalse(self.op_user.check_password("OtraClave88"))
        self.client.logout()
        again = self.client.post(
            "/api/auth/login/",
            {"email": "op@labbe.test", "password": "OtraClave88"},
            format="json",
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["role"], "operator")
