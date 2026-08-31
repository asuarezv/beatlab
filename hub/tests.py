from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from .models import (
    Beat,
    BeatPackage,
    BeatType,
    Company,
    Operator,
    OperatorInviteChallenge,
    System,
)
from .quota import grant_demo
from .tenant import ensure_membership
from .tokens import MonitorActor, issue_monitor_jwt, issue_operator_jwt, issue_system_jwt
from .validation import (
    CURRENT_PASSWORD_ERROR,
    EMAIL_INVALID,
    HUB_CREDENTIALS_ERROR,
    HUB_LOGIN_REQUIRED,
    MONITOR_CREDENTIALS_ERROR,
    MONITOR_LOGIN_REQUIRED,
    OPERATOR_ACTIVATE_OK,
    OPERATOR_EMAIL_TAKEN,
    OPERATOR_INVITE_SENT,
    OPERATOR_RECOVER_SENT,
    PASSWORD_CHANGE_REQUIRED,
    PASSWORD_CREATED,
    PASSWORD_MISMATCH_ERROR,
    PASSWORD_UPDATED,
)

User = get_user_model()


class CompanyFixtureTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Labbe 2", slug="labbe-2")
        grant_demo(self.company)
        self.system = System.objects.create(
            company=self.company,
            name="API Pagos",
            slug="api-pagos",
        )
        self.beat_type = BeatType.objects.create(
            company=self.company,
            name="Alerta",
            slug="alerta",
        )
        self.token = issue_system_jwt(self.system)
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
        self.operator.assigned_beat_types.add(self.beat_type)

    def _ingest(self, token=None, body=None, **extra):
        auth = token if token is not None else self.token
        headers = extra
        if auth:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {auth}"
        return self.client.post(
            "/api/ingest/beats/",
            body or {"type": "alerta", "title": "Cola recuperada"},
            format="json",
            **headers,
        )

    def _hub_session(self, user=None, company=None):
        self.client.force_login(user or self.staff)
        session = self.client.session
        session["company_id"] = (company or self.company).id
        session.save()

    def _operator_token(self):
        return issue_operator_jwt(self.operator)

    def _invite_and_activate(
        self,
        first_name,
        last_name,
        email,
        digit="7",
        password="OperatorClave99",
        receive_all_beat_types=False,
        beat_type_ids=None,
    ):
        with patch("hub.otp.secrets.choice", return_value=digit):
            invited = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "receive_all_beat_types": receive_all_beat_types,
                    "beat_type_ids": beat_type_ids or [],
                },
                format="json",
            )
        self.assertEqual(invited.status_code, 200)
        self.assertFalse(Operator.objects.filter(email__iexact=email).exists())
        challenge = OperatorInviteChallenge.objects.get(email=email.lower())
        verified = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": digit * 6},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertFalse(Operator.objects.filter(email__iexact=email).exists())
        activated = self.client.post(
            "/api/public/operator/password/",
            {
                "grant": verified.data["grant"],
                "password": password,
                "password2": password,
            },
            format="json",
        )
        self.assertEqual(activated.status_code, 201)
        return Operator.objects.get(email=email.lower())


class IngestAndMonitorTests(CompanyFixtureTests):
    def test_ingest_requires_jwt(self):
        response = self._ingest(token="")
        self.assertEqual(response.status_code, 401)

    def test_ingest_creates_beat_and_consumes_quota(self):
        remaining_before = self.company.beats_remaining()
        response = self._ingest()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Cola recuperada")
        self.assertEqual(response.data["system_name"], "API Pagos")
        self.assertEqual(Beat.objects.filter(company=self.company).count(), 1)
        self.company.refresh_from_db()
        self.assertEqual(self.company.beats_remaining(), remaining_before - 1)

    def test_ingest_unknown_type(self):
        response = self._ingest(body={"type": "no-existe", "title": "X"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tipo", response.data["detail"])

    def test_ingest_inactive_system(self):
        self.system.is_active = False
        self.system.save(update_fields=["is_active"])
        response = self._ingest()
        self.assertEqual(response.status_code, 403)

    def test_rotate_jwt_revokes_previous(self):
        old = self.token
        self.client.force_login(self.staff)
        session = self.client.session
        session["company_id"] = self.company.id
        session.save()
        issued = self.client.post(f"/api/systems/{self.system.id}/jwt/", {}, format="json")
        self.assertEqual(issued.status_code, 201)
        new_token = issued.data["token"]
        self.assertTrue(issued.data["rotated"])
        self.assertEqual(self._ingest(token=old).status_code, 401)
        self.assertEqual(self._ingest(token=new_token).status_code, 201)

    def test_hub_cannot_post_beats(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session["company_id"] = self.company.id
        session.save()
        response = self.client.post(
            "/api/beats/",
            {
                "system": self.system.id,
                "beat_type": self.beat_type.id,
                "title": "manual",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Beat.objects.count(), 0)

    def test_quota_exhausted(self):
        other = Company.objects.create(name="Sin cupo", slug="sin-cupo")
        BeatPackage.objects.create(company=other, beats=1, kind=BeatPackage.Kind.PURCHASE)
        system = System.objects.create(company=other, name="Job", slug="job")
        BeatType.objects.create(company=other, name="Error", slug="error")
        token = issue_system_jwt(system)
        first = self.client.post(
            "/api/ingest/beats/",
            {"type": "error", "title": "uno"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/api/ingest/beats/",
            {"type": "error", "title": "dos"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("Beats", second.data["detail"])

    def test_monitor_otp_login_and_list(self):
        self._ingest()
        unknown = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "nadie@labbe.test"},
            format="json",
        )
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        with patch("hub.otp.secrets.choice", return_value="4"):
            asked = self.client.post(
                "/api/monitor/auth/request-otp/",
                {"email": "op@labbe.test"},
                format="json",
            )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(asked.data["detail"], unknown.data["detail"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Tu código Monitor")
        self.assertIsNone(self.operator.last_login_at)
        wrong = self.client.post(
            "/api/monitor/auth/verify-otp/",
            {"email": "op@labbe.test", "otp": "000000"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        login = self.client.post(
            "/api/monitor/auth/verify-otp/",
            {"email": "op@labbe.test", "otp": "444444"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["role"], "operator")
        self.assertEqual(login.data["operator"]["display_name"], "Ana Pérez")
        self.operator.refresh_from_db()
        self.assertIsNotNone(self.operator.last_login_at)
        token = login.data["token"]
        beats = self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(beats.status_code, 200)
        self.assertEqual(len(beats.data), 1)
        self.assertEqual(beats.data[0]["title"], "Cola recuperada")
        self.assertFalse(login.data["operator"]["has_password"])
        denied = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "op@labbe.test", "password": "password12"},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(denied.data["detail"], MONITOR_CREDENTIALS_ERROR)

    def test_hub_operator_crud_is_tenant_scoped(self):
        other = Company.objects.create(name="Otra", slug="otra")
        grant_demo(other)
        other_staff = User.objects.create_user(
            username="otroadmin",
            email="otroadmin@otra.test",
            password="password12",
            is_staff=True,
        )
        ensure_membership(other_staff, other)
        self._hub_session()
        blocked = self.client.post(
            "/api/operators/",
            {
                "first_name": "Luis",
                "last_name": "García",
                "email": "luis@labbe.test",
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, 405)
        created = self._invite_and_activate("Luis", "García", "luis@labbe.test")
        operator_id = created.id
        self.assertEqual(created.email, "luis@labbe.test")
        self.assertIsNone(created.last_login_at)
        self.assertTrue(created.has_password())
        self.assertTrue(created.check_password("OperatorClave99"))
        self.assertNotEqual(created.password_hash, "OperatorClave99")
        listed = self.client.get("/api/operators/")
        self.assertEqual(listed.status_code, 200)
        emails = {item["email"] for item in listed.data}
        self.assertEqual(emails, {"op@labbe.test", "luis@labbe.test"})
        patched = self.client.patch(
            f"/api/operators/{operator_id}/",
            {"first_name": "Luis Miguel"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["first_name"], "Luis Miguel")
        self.client.logout()
        self._hub_session(other_staff, other)
        foreign_list = self.client.get("/api/operators/")
        self.assertEqual(foreign_list.status_code, 200)
        self.assertEqual(foreign_list.data, [])
        stolen = self.client.patch(
            f"/api/operators/{operator_id}/",
            {"first_name": "Hack"},
            format="json",
        )
        self.assertEqual(stolen.status_code, 404)
        self.client.logout()
        self._hub_session()
        deleted = self.client.delete(f"/api/operators/{operator_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Operator.objects.filter(pk=operator_id).exists())
        self.assertFalse(User.objects.filter(email="luis@labbe.test").exists())
        mail.outbox.clear()
        asked = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "luis@labbe.test"},
            format="json",
        )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_operator_invite_requires_otp_and_replaces_challenge(self):
        self._hub_session()
        with patch("hub.otp.secrets.choice", return_value="1"):
            first = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": "Luis",
                    "last_name": "García",
                    "email": "luis@labbe.test",
                },
                format="json",
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["detail"], OPERATOR_INVITE_SENT)
        self.assertEqual(mail.outbox[0].subject, "Te invitaron a Monitor")
        body = mail.outbox[0].body
        self.assertIn("111111", body)
        self.assertIn("/invitar?token=", body)
        self.assertIn("Labbe 2", body)
        self.assertIn("Monitor", body)
        self.assertEqual(OperatorInviteChallenge.objects.filter(email="luis@labbe.test").count(), 1)
        self.assertFalse(Operator.objects.filter(email="luis@labbe.test").exists())
        pending = self.client.get("/api/operators/pending/")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.data[0]["email"], "luis@labbe.test")
        hub_verify = self.client.post(
            "/api/operators/verify/",
            {"email": "luis@labbe.test", "otp": "111111"},
            format="json",
        )
        self.assertIn(hub_verify.status_code, {404, 405})
        with patch("hub.otp.secrets.choice", return_value="2"):
            second = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": "Luis",
                    "last_name": "García",
                    "email": "Luis@labbe.test",
                },
                format="json",
            )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(OperatorInviteChallenge.objects.filter(email="luis@labbe.test").count(), 1)
        challenge = OperatorInviteChallenge.objects.get(email="luis@labbe.test")
        stale = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "111111"},
            format="json",
        )
        self.assertEqual(stale.status_code, 400)
        self.assertFalse(Operator.objects.filter(email="luis@labbe.test").exists())
        verified = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "222222"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.data["grant"])
        self.assertFalse(Operator.objects.filter(email="luis@labbe.test").exists())
        self.assertEqual(OperatorInviteChallenge.objects.count(), 1)
        created = self.client.post(
            "/api/public/operator/password/",
            {
                "grant": verified.data["grant"],
                "password": "OperatorClave99",
                "password2": "OperatorClave99",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["detail"], OPERATOR_ACTIVATE_OK)
        operator = Operator.objects.get(email="luis@labbe.test")
        self.assertTrue(operator.check_password("OperatorClave99"))
        self.assertNotEqual(operator.password_hash, "OperatorClave99")
        self.assertEqual(OperatorInviteChallenge.objects.count(), 0)
        login = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "luis@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["token"])

    def test_operator_invite_cancel_keeps_challenge_and_recover_sets_password(self):
        self._hub_session()
        with patch("hub.otp.secrets.choice", return_value="3"):
            invited = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": "Luis",
                    "last_name": "García",
                    "email": "luis@labbe.test",
                },
                format="json",
            )
        self.assertEqual(invited.status_code, 200)
        challenge = OperatorInviteChallenge.objects.get(email="luis@labbe.test")
        info = self.client.get(f"/api/public/operator/invite/?token={challenge.token}")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.data["email"], "luis@labbe.test")
        self.assertEqual(info.data["company_name"], "Labbe 2")
        verified = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "333333"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertFalse(Operator.objects.filter(email="luis@labbe.test").exists())
        self.assertEqual(OperatorInviteChallenge.objects.count(), 1)
        reuse = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "333333"},
            format="json",
        )
        self.assertEqual(reuse.status_code, 200)
        denied = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "luis@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        mail.outbox.clear()
        with patch("hub.otp.secrets.choice", return_value="8"):
            recovered = self.client.post(
                "/api/public/operator/recover/",
                {"email": "luis@labbe.test"},
                format="json",
            )
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(recovered.data["detail"], OPERATOR_RECOVER_SENT)
        self.assertEqual(mail.outbox[0].subject, "Recupera tu cuenta Monitor")
        self.assertIn("/invitar?token=", mail.outbox[0].body)
        self.assertEqual(OperatorInviteChallenge.objects.count(), 1)
        again = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "888888"},
            format="json",
        )
        self.assertEqual(again.status_code, 200)
        saved = self.client.post(
            "/api/public/operator/password/",
            {
                "grant": again.data["grant"],
                "password": "OperatorClave99",
                "password2": "OperatorClave99",
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 201)
        operator = Operator.objects.get(email="luis@labbe.test")
        self.assertTrue(operator.check_password("OperatorClave99"))
        self.assertFalse(OperatorInviteChallenge.objects.filter(email="luis@labbe.test").exists())

    def test_operator_recover_resets_existing_password_without_session(self):
        self.operator.set_password("ViejaClave88")
        self.operator.save(update_fields=["password_hash"])
        with patch("hub.otp.secrets.choice", return_value="6"):
            asked = self.client.post(
                "/api/public/operator/recover/",
                {"email": "op@labbe.test"},
                format="json",
            )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(asked.data["detail"], OPERATOR_RECOVER_SENT)
        verified = self.client.post(
            "/api/public/operator/verify/",
            {"email": "op@labbe.test", "otp": "666666"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertNotIn("token", verified.data)
        saved = self.client.post(
            "/api/public/operator/password/",
            {
                "grant": verified.data["grant"],
                "password": "NuevaClave77",
                "password2": "NuevaClave77",
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.data["detail"], OPERATOR_ACTIVATE_OK)
        self.operator.refresh_from_db()
        self.assertTrue(self.operator.check_password("NuevaClave77"))
        self.assertFalse(self.operator.check_password("ViejaClave88"))
        login = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "op@labbe.test", "password": "NuevaClave77"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

    def test_pending_invite_cannot_use_monitor(self):
        self._hub_session()
        with patch("hub.otp.secrets.choice", return_value="5"):
            invited = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": "Luis",
                    "last_name": "García",
                    "email": "luis@labbe.test",
                },
                format="json",
            )
        self.assertEqual(invited.status_code, 200)
        mail.outbox.clear()
        asked = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "luis@labbe.test"},
            format="json",
        )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        denied = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "luis@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)

    def test_operator_email_is_globally_unique(self):
        other = Company.objects.create(name="Otra", slug="otra")
        grant_demo(other)
        other_staff = User.objects.create_user(
            username="otroadmin",
            email="otroadmin@otra.test",
            password="password12",
            is_staff=True,
        )
        ensure_membership(other_staff, other)
        self._hub_session()
        duplicate = self.client.post(
            "/api/operators/invite/",
            {
                "first_name": "Copia",
                "last_name": "Ana",
                "email": "OP@labbe.test",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data["detail"], OPERATOR_EMAIL_TAKEN)
        self.assertEqual(len(mail.outbox), 0)
        patched = self.client.patch(
            f"/api/operators/{self.operator.id}/",
            {"email": "op@labbe.test"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.client.logout()
        self._hub_session(other_staff, other)
        foreign = self.client.post(
            "/api/operators/invite/",
            {
                "first_name": "Otra",
                "last_name": "Ana",
                "email": "op@labbe.test",
            },
            format="json",
        )
        self.assertEqual(foreign.status_code, 400)
        self.assertEqual(foreign.data["detail"], OPERATOR_EMAIL_TAKEN)
        other_user = User.objects.create_user(
            username="opdup",
            email="otro@otra.test",
            password="password12",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Operator.objects.create(
                    company=other,
                    user=other_user,
                    first_name="Dup",
                    last_name="Mail",
                    email="op@labbe.test",
                )

    def test_hub_login_accepts_email_and_rejects_username(self):
        ok = self.client.post(
            "/api/auth/login/",
            {"email": "HUBADMIN@labbe.test", "password": "password12"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["user"]["email"], "hubadmin@labbe.test")
        self.assertEqual(ok.json()["role"], "admin")
        self.client.logout()
        by_username = self.client.post(
            "/api/auth/login/",
            {"username": "hubadmin", "password": "password12"},
            format="json",
        )
        self.assertEqual(by_username.status_code, 400)
        self.assertEqual(by_username.json()["detail"], HUB_LOGIN_REQUIRED)
        self.assertFalse(by_username.wsgi_request.user.is_authenticated)
        invalid = self.client.post(
            "/api/auth/login/",
            {"email": "hubadmin", "password": "password12"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["detail"], EMAIL_INVALID)

    def test_hub_login_accepts_operator_password_hash(self):
        by_user_password = self.client.post(
            "/api/auth/login/",
            {"email": "op@labbe.test", "password": "password12"},
            format="json",
        )
        self.assertEqual(by_user_password.status_code, 400)
        self.assertEqual(by_user_password.json()["detail"], HUB_CREDENTIALS_ERROR)
        self.assertFalse(by_user_password.wsgi_request.user.is_authenticated)
        self.operator.set_password("OperatorClave99")
        self.operator.save(update_fields=["password_hash"])
        ok = self.client.post(
            "/api/auth/login/",
            {"email": "OP@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["role"], "operator")
        self.assertEqual(ok.json()["user"]["email"], "op@labbe.test")
        self.assertEqual(ok.json()["user"]["first_name"], "Ana")
        self.assertEqual(ok.json()["user"]["last_name"], "Pérez")
        self.assertEqual(ok.json()["current_company"]["id"], self.company.id)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["role"], "operator")
        self.assertEqual(me.json()["user"]["display_name"], "Ana Pérez")
        self.client.logout()
        by_username = self.client.post(
            "/api/auth/login/",
            {"username": "opdemo", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(by_username.status_code, 400)
        self.assertEqual(by_username.json()["detail"], HUB_LOGIN_REQUIRED)
        unknown = self.client.post(
            "/api/auth/login/",
            {"email": "nadie@labbe.test", "password": "password12"},
            format="json",
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.json()["detail"], HUB_CREDENTIALS_ERROR)

    def test_monitor_otp_allows_hub_admin(self):
        self._ingest()
        unknown = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "nadie@labbe.test"},
            format="json",
        )
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        with patch("hub.otp.secrets.choice", return_value="3"):
            asked = self.client.post(
                "/api/monitor/auth/request-otp/",
                {"email": "hubadmin@labbe.test"},
                format="json",
            )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(asked.data["detail"], unknown.data["detail"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Tu código Monitor")
        self.assertEqual(mail.outbox[0].to, ["hubadmin@labbe.test"])
        verified = self.client.post(
            "/api/monitor/auth/verify-otp/",
            {"email": "hubadmin@labbe.test", "otp": "333333"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.data["role"], "admin")
        self.assertEqual(verified.data["company"]["id"], self.company.id)
        self.assertEqual(verified.data["operator"]["email"], "hubadmin@labbe.test")
        self.assertTrue(verified.data["token"])
        self.assertFalse(
            Operator.objects.filter(email__iexact="hubadmin@labbe.test").exists()
        )
        self.assertFalse(Operator.objects.filter(user=self.staff).exists())
        beats = self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {verified.data['token']}",
        )
        self.assertEqual(beats.status_code, 200)
        self.assertEqual(len(beats.data), 1)
        self.assertEqual(beats.data[0]["title"], "Cola recuperada")

    def test_monitor_password_create_change_and_login(self):
        token = self._operator_token()
        unauthorized = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "MonitorClave99", "password2": "MonitorClave99"},
            format="json",
        )
        self.assertEqual(unauthorized.status_code, 401)
        mismatch = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "MonitorClave99", "password2": "OtraClave88"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.data["detail"], PASSWORD_MISMATCH_ERROR)
        weak = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "123", "password2": "123"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(weak.status_code, 400)
        created = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "MonitorClave99", "password2": "MonitorClave99"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.data["detail"], PASSWORD_CREATED)
        self.assertTrue(created.data["has_password"])
        self.operator.refresh_from_db()
        self.assertTrue(self.operator.has_password())
        self.assertTrue(self.operator.check_password("MonitorClave99"))
        self.assertNotEqual(self.operator.password_hash, "MonitorClave99")
        missing_current = self.client.post(
            "/api/monitor/auth/password/",
            {"password": "OtraClave88", "password2": "OtraClave88"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(missing_current.status_code, 400)
        self.assertEqual(missing_current.data["detail"], PASSWORD_CHANGE_REQUIRED)
        wrong_current = self.client.post(
            "/api/monitor/auth/password/",
            {
                "current_password": "no-es-esa",
                "password": "OtraClave88",
                "password2": "OtraClave88",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(wrong_current.status_code, 400)
        self.assertEqual(wrong_current.data["detail"], CURRENT_PASSWORD_ERROR)
        updated = self.client.post(
            "/api/monitor/auth/password/",
            {
                "current_password": "MonitorClave99",
                "password": "OtraClave88",
                "password2": "OtraClave88",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["detail"], PASSWORD_UPDATED)
        me = self.client.get(
            "/api/monitor/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.data["operator"]["has_password"])
        empty = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "op@labbe.test"},
            format="json",
        )
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.data["detail"], MONITOR_LOGIN_REQUIRED)
        wrong = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "op@labbe.test", "password": "MonitorClave99"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.data["detail"], MONITOR_CREDENTIALS_ERROR)
        login = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "op@labbe.test", "password": "OtraClave88"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["token"])
        self.assertTrue(login.data["operator"]["has_password"])
        self.assertEqual(login.data["operator"]["display_name"], "Ana Pérez")
        self.assertEqual(login.data["role"], "operator")
        hub_admin = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "hubadmin@labbe.test", "password": "password12"},
            format="json",
        )
        self.assertEqual(hub_admin.status_code, 200)
        self.assertEqual(hub_admin.data["role"], "admin")
        self.assertEqual(hub_admin.data["company"]["id"], self.company.id)
        self.assertEqual(hub_admin.data["operator"]["email"], "hubadmin@labbe.test")
        self.assertTrue(hub_admin.data["operator"]["has_password"])
        self.assertTrue(hub_admin.data["token"])
        self.assertFalse(Operator.objects.filter(user=self.staff).exists())
        by_username = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "hubadmin", "password": "password12"},
            format="json",
        )
        self.assertEqual(by_username.status_code, 400)
        self.assertEqual(by_username.data["detail"], EMAIL_INVALID)
        wrong_admin = self.client.post(
            "/api/monitor/auth/login/",
            {"email": "hubadmin@labbe.test", "password": "no-es-esa"},
            format="json",
        )
        self.assertEqual(wrong_admin.status_code, 400)
        self.assertEqual(wrong_admin.data["detail"], MONITOR_CREDENTIALS_ERROR)
        admin_beats = self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {hub_admin.data['token']}",
        )
        self.assertEqual(admin_beats.status_code, 200)
        with patch("hub.otp.secrets.choice", return_value="2"):
            asked = self.client.post(
                "/api/monitor/auth/request-otp/",
                {"email": "op@labbe.test"},
                format="json",
            )
        self.assertEqual(asked.status_code, 200)
        otp_login = self.client.post(
            "/api/monitor/auth/verify-otp/",
            {"email": "op@labbe.test", "otp": "222222"},
            format="json",
        )
        self.assertEqual(otp_login.status_code, 200)
        self.assertTrue(otp_login.data["operator"]["has_password"])

    async def test_monitor_websocket_rejects_anonymous(self):
        from channels.testing import WebsocketCommunicator

        from config.asgi import application

        communicator = WebsocketCommunicator(application, "/ws/monitor/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_monitor_websocket_accepts_operator(self):
        from channels.testing import WebsocketCommunicator

        from config.asgi import application

        token = issue_operator_jwt(self.operator)
        communicator = WebsocketCommunicator(
            application, f"/ws/monitor/?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        hello = await communicator.receive_json_from()
        self.assertEqual(hello.get("type"), "ready")
        await communicator.disconnect()

    async def test_monitor_websocket_accepts_hub_admin(self):
        from channels.testing import WebsocketCommunicator

        from config.asgi import application

        token = issue_monitor_jwt(MonitorActor.from_admin(self.staff, self.company))
        communicator = WebsocketCommunicator(
            application, f"/ws/monitor/?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        hello = await communicator.receive_json_from()
        self.assertEqual(hello.get("type"), "ready")
        await communicator.disconnect()

    def test_operational_error_returns_json(self):
        from django.db.utils import OperationalError

        from .exceptions import api_exception_handler

        response = api_exception_handler(OperationalError("slots"), {})
        self.assertEqual(response.status_code, 503)
        self.assertIn("base de datos", response.data["detail"])


class BeatAssignmentTests(CompanyFixtureTests):
    def setUp(self):
        super().setUp()
        self.aviso = BeatType.objects.create(
            company=self.company,
            name="Aviso",
            slug="aviso",
        )
        self.other_company = Company.objects.create(name="Otra", slug="otra-asig")
        grant_demo(self.other_company)
        self.foreign_type = BeatType.objects.create(
            company=self.other_company,
            name="Ajeno",
            slug="ajeno",
        )

    def _monitor_beats(self, token):
        return self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_operator_without_assignment_lists_no_beats(self):
        self.operator.assigned_beat_types.clear()
        self.operator.receive_all_beat_types = False
        self.operator.save(update_fields=["receive_all_beat_types"])
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Solo aviso"})
        listed = self._monitor_beats(self._operator_token())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data, [])

    def test_operator_lists_only_assigned_types(self):
        self.operator.assigned_beat_types.set([self.aviso])
        self.operator.receive_all_beat_types = False
        self.operator.save(update_fields=["receive_all_beat_types"])
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Disco lleno"})
        listed = self._monitor_beats(self._operator_token())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["title"] for item in listed.data], ["Disco lleno"])

    def test_operator_all_types_lists_every_beat(self):
        self.operator.assigned_beat_types.clear()
        self.operator.receive_all_beat_types = True
        self.operator.save(update_fields=["receive_all_beat_types"])
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Disco lleno"})
        listed = self._monitor_beats(self._operator_token())
        self.assertEqual(listed.status_code, 200)
        titles = {item["title"] for item in listed.data}
        self.assertEqual(titles, {"Cola recuperada", "Disco lleno"})

    def test_hub_admin_lists_all_beats(self):
        self.operator.assigned_beat_types.clear()
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Disco lleno"})
        token = issue_monitor_jwt(MonitorActor.from_admin(self.staff, self.company))
        listed = self._monitor_beats(token)
        self.assertEqual(listed.status_code, 200)
        titles = {item["title"] for item in listed.data}
        self.assertEqual(titles, {"Cola recuperada", "Disco lleno"})

    def test_invite_stores_assignment_and_activate_applies_it(self):
        self._hub_session()
        created = self._invite_and_activate(
            "Luis",
            "García",
            "luis@labbe.test",
            beat_type_ids=[self.aviso.id],
        )
        self.assertFalse(created.receive_all_beat_types)
        self.assertEqual(
            list(created.assigned_beat_types.values_list("id", flat=True)),
            [self.aviso.id],
        )
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Disco lleno"})
        listed = self._monitor_beats(issue_operator_jwt(created))
        self.assertEqual([item["title"] for item in listed.data], ["Disco lleno"])

    def test_invite_all_types_applies_on_activate(self):
        self._hub_session()
        created = self._invite_and_activate(
            "Luis",
            "García",
            "luis@labbe.test",
            receive_all_beat_types=True,
            beat_type_ids=[self.aviso.id],
        )
        self.assertTrue(created.receive_all_beat_types)
        self.assertEqual(list(created.assigned_beat_types.all()), [])

    def test_invite_rejects_foreign_beat_type(self):
        self._hub_session()
        response = self.client.post(
            "/api/operators/invite/",
            {
                "first_name": "Luis",
                "last_name": "García",
                "email": "luis@labbe.test",
                "beat_type_ids": [self.foreign_type.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            OperatorInviteChallenge.objects.filter(email="luis@labbe.test").exists()
        )

    def test_pending_lists_and_updates_assignment(self):
        self._hub_session()
        with patch("hub.otp.secrets.choice", return_value="5"):
            invited = self.client.post(
                "/api/operators/invite/",
                {
                    "first_name": "Luis",
                    "last_name": "García",
                    "email": "luis@labbe.test",
                    "beat_type_ids": [self.beat_type.id],
                },
                format="json",
            )
        self.assertEqual(invited.status_code, 200)
        pending = self.client.get("/api/operators/pending/")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(pending.data), 1)
        self.assertEqual(pending.data[0]["beat_type_ids"], [self.beat_type.id])
        self.assertFalse(pending.data[0]["receive_all_beat_types"])
        invite_id = pending.data[0]["id"]
        updated = self.client.patch(
            f"/api/operators/pending/{invite_id}/",
            {
                "first_name": "Luis",
                "last_name": "García",
                "receive_all_beat_types": True,
                "beat_type_ids": [],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.data["receive_all_beat_types"])
        self.assertEqual(updated.data["beat_type_ids"], [])
        challenge = OperatorInviteChallenge.objects.get(pk=invite_id)
        self.assertTrue(challenge.receive_all_beat_types)
        verified = self.client.post(
            "/api/public/operator/verify/",
            {"token": challenge.token, "otp": "555555"},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        activated = self.client.post(
            "/api/public/operator/password/",
            {
                "grant": verified.data["grant"],
                "password": "OperatorClave99",
                "password2": "OperatorClave99",
            },
            format="json",
        )
        self.assertEqual(activated.status_code, 201)
        operator = Operator.objects.get(email="luis@labbe.test")
        self.assertTrue(operator.receive_all_beat_types)

    def test_patch_operator_assignment(self):
        self._hub_session()
        listed = self.client.get("/api/operators/")
        self.assertEqual(listed.status_code, 200)
        ana = next(item for item in listed.data if item["email"] == "op@labbe.test")
        self.assertEqual(ana["beat_type_ids"], [self.beat_type.id])
        patched = self.client.patch(
            f"/api/operators/{self.operator.id}/",
            {
                "receive_all_beat_types": False,
                "beat_type_ids": [self.aviso.id],
            },
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["beat_type_ids"], [self.aviso.id])
        self.operator.refresh_from_db()
        self.assertEqual(
            list(self.operator.assigned_beat_types.values_list("id", flat=True)),
            [self.aviso.id],
        )

    def test_patch_operator_rejects_foreign_type(self):
        self._hub_session()
        patched = self.client.patch(
            f"/api/operators/{self.operator.id}/",
            {"beat_type_ids": [self.foreign_type.id]},
            format="json",
        )
        self.assertEqual(patched.status_code, 400)

    async def test_monitor_websocket_routes_by_assignment(self):
        from asgiref.sync import sync_to_async
        from channels.testing import WebsocketCommunicator

        from config.asgi import application
        from .notify import notify_company_beat

        await sync_to_async(self.operator.assigned_beat_types.set)([self.aviso])
        self.operator.receive_all_beat_types = False
        await sync_to_async(self.operator.save)(update_fields=["receive_all_beat_types"])

        other_user = await sync_to_async(User.objects.create_user)(
            username="opsin",
            email="sin@labbe.test",
            password="password12",
        )
        other = await sync_to_async(Operator.objects.create)(
            company=self.company,
            user=other_user,
            first_name="Sin",
            last_name="Tipo",
            email="sin@labbe.test",
        )

        assigned = WebsocketCommunicator(
            application, f"/ws/monitor/?token={issue_operator_jwt(self.operator)}"
        )
        skipped = WebsocketCommunicator(
            application, f"/ws/monitor/?token={issue_operator_jwt(other)}"
        )
        admin = WebsocketCommunicator(
            application,
            f"/ws/monitor/?token={issue_monitor_jwt(MonitorActor.from_admin(self.staff, self.company))}",
        )
        for socket in (assigned, skipped, admin):
            connected, _ = await socket.connect()
            self.assertTrue(connected)
            hello = await socket.receive_json_from()
            self.assertEqual(hello.get("type"), "ready")

        beat = await sync_to_async(Beat.objects.create)(
            company=self.company,
            system=self.system,
            beat_type=self.aviso,
            title="Solo aviso",
            payload={},
        )
        beat = await sync_to_async(
            Beat.objects.select_related("system", "beat_type").get
        )(pk=beat.pk)
        await sync_to_async(notify_company_beat)(beat)

        assigned_msg = await assigned.receive_json_from()
        self.assertEqual(assigned_msg["type"], "beat")
        self.assertEqual(assigned_msg["beat"]["title"], "Solo aviso")
        admin_msg = await admin.receive_json_from()
        self.assertEqual(admin_msg["type"], "beat")
        self.assertEqual(admin_msg["beat"]["title"], "Solo aviso")
        self.assertTrue(await skipped.receive_nothing())

        await assigned.disconnect()
        await skipped.disconnect()
        await admin.disconnect()


class HubOperatorWebTests(CompanyFixtureTests):
    def setUp(self):
        super().setUp()
        self.aviso = BeatType.objects.create(
            company=self.company,
            name="Aviso",
            slug="aviso",
        )
        self.operator.set_password("OperatorClave99")
        self.operator.save(update_fields=["password_hash"])

    def _operator_hub_login(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "op@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "operator")
        return response

    def test_operator_cannot_access_admin_apis(self):
        self._operator_hub_login()
        forbidden = [
            ("/api/salud/", "get"),
            ("/api/companies/", "get"),
            ("/api/systems/", "get"),
            ("/api/operators/", "get"),
            ("/api/beat-types/", "get"),
            (f"/api/systems/{self.system.id}/jwt/", "post"),
        ]
        for path, method in forbidden:
            response = getattr(self.client, method)(path, {}, format="json")
            self.assertEqual(response.status_code, 403, path)
        ingest = self.client.post(
            "/api/ingest/beats/",
            {"type": "alerta", "title": "No"},
            format="json",
        )
        self.assertEqual(ingest.status_code, 401)

    def test_operator_beats_are_filtered_by_assignment(self):
        self.operator.assigned_beat_types.set([self.aviso])
        self.operator.receive_all_beat_types = False
        self.operator.save(update_fields=["receive_all_beat_types"])
        self._ingest()
        self._ingest(body={"type": "aviso", "title": "Disco lleno"})
        self._operator_hub_login()
        listed = self.client.get("/api/beats/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["title"] for item in listed.data], ["Disco lleno"])

    def test_admin_hub_nav_unchanged(self):
        self._hub_session()
        salud = self.client.get("/api/salud/")
        self.assertEqual(salud.status_code, 200)
        systems = self.client.get("/api/systems/")
        self.assertEqual(systems.status_code, 200)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.json()["role"], "admin")

    async def test_monitor_websocket_accepts_operator_hub_session(self):
        from asgiref.sync import sync_to_async
        from channels.testing import WebsocketCommunicator

        from config.asgi import application

        login = await sync_to_async(self.client.post)(
            "/api/auth/login/",
            {"email": "op@labbe.test", "password": "OperatorClave99"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        session_key = self.client.cookies["sessionid"].value
        communicator = WebsocketCommunicator(
            application,
            "/ws/monitor/",
            headers=[
                (b"cookie", f"sessionid={session_key}".encode()),
            ],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        hello = await communicator.receive_json_from()
        self.assertEqual(hello.get("type"), "ready")
        await communicator.disconnect()


class SeverityAndStatsTests(CompanyFixtureTests):
    def test_existing_type_defaults_to_aviso(self):
        self.assertEqual(self.beat_type.severity, BeatType.Severity.AVISO)
        self.assertEqual(self.beat_type.resolved_icon(), "alert")

    def test_create_and_patch_beat_type_severity_and_icon(self):
        self._hub_session()
        created = self.client.post(
            "/api/beat-types/",
            {"name": "Caída crítica", "severity": "critica", "icon": "error"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["severity"], "critica")
        self.assertEqual(created.data["icon"], "error")
        patched = self.client.patch(
            f"/api/beat-types/{created.data['id']}/",
            {"severity": "info", "icon": "pulse"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["severity"], "info")
        invalid = self.client.post(
            "/api/beat-types/",
            {"name": "Raro", "severity": "urgente"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_ingest_and_lists_include_severity(self):
        self.beat_type.severity = BeatType.Severity.CRITICA
        self.beat_type.icon = "error"
        self.beat_type.save(update_fields=["severity", "icon"])
        ingested = self._ingest()
        self.assertEqual(ingested.status_code, 201)
        self.assertEqual(ingested.data["severity"], "critica")
        self.assertEqual(ingested.data["beat_type_icon"], "error")
        self._hub_session()
        listed = self.client.get("/api/beats/")
        rows = listed.data if isinstance(listed.data, list) else listed.data["results"]
        self.assertEqual(rows[0]["severity"], "critica")
        token = self._operator_token()
        monitor = self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(monitor.data[0]["severity"], "critica")

    def test_salud_and_monitor_stats_are_tenant_and_assignment_scoped(self):
        other = Company.objects.create(name="Otra", slug="otra-stats")
        grant_demo(other)
        other_type = BeatType.objects.create(
            company=other, name="Error", slug="error", severity="critica"
        )
        other_system = System.objects.create(company=other, name="Job", slug="job")
        Beat.objects.create(
            company=other,
            system=other_system,
            beat_type=other_type,
            title="Ajeno",
        )
        aviso = BeatType.objects.create(
            company=self.company,
            name="Aviso",
            slug="aviso",
            severity="aviso",
            icon="bell",
        )
        self._ingest()
        Beat.objects.create(
            company=self.company,
            system=self.system,
            beat_type=aviso,
            title="Aviso propio",
        )
        self.operator.receive_all_beat_types = False
        self.operator.save(update_fields=["receive_all_beat_types"])
        self.operator.assigned_beat_types.set([aviso])
        self._hub_session()
        salud = self.client.get("/api/salud/")
        self.assertEqual(salud.status_code, 200)
        self.assertEqual(salud.data["beats_total"], 2)
        names = {row["name"] for row in salud.data["by_type"]}
        self.assertIn("Alerta", names)
        self.assertNotIn("Error", names)
        self.assertEqual(len(salud.data["by_day"]), 14)
        token = self._operator_token()
        monitor = self.client.get(
            "/api/monitor/stats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(monitor.status_code, 200)
        self.assertEqual(monitor.data["beats_total"], 1)
        self.assertEqual(monitor.data["by_type"][0]["name"], "Aviso")


class SeedDemoBeatsTests(CompanyFixtureTests):
    def test_seed_completes_types_and_beats_without_emptying_quota(self):
        from django.core.management import call_command

        self.beat_type.severity = BeatType.Severity.INFO
        self.beat_type.icon = "pulse"
        self.beat_type.save(update_fields=["severity", "icon"])
        remaining_before = self.company.beats_remaining()
        call_command("seed_demo_beats", company="labbe-2")
        self.beat_type.refresh_from_db()
        self.assertEqual(self.beat_type.severity, BeatType.Severity.INFO)
        self.assertEqual(self.beat_type.icon, "pulse")
        self.assertEqual(self.company.beat_types.count(), 10)
        self.assertEqual(self.company.beats.count(), 100)
        self.company.refresh_from_db()
        self.assertGreater(self.company.beats_remaining(), 0)
        self.assertGreaterEqual(self.company.beats_remaining(), remaining_before - 1)
        dates = {item.created_at.date() for item in self.company.beats.all()}
        self.assertGreater(len(dates), 5)
        call_command("seed_demo_beats", company="labbe-2")
        self.assertEqual(self.company.beats.count(), 100)
        self.assertEqual(self.company.beat_types.count(), 10)

