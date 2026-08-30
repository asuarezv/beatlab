from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APITestCase

from .models import Beat, BeatPackage, BeatType, Company, Operator, System
from .quota import grant_demo
from .tenant import ensure_membership
from .tokens import issue_operator_jwt, issue_system_jwt

User = get_user_model()


class IngestAndMonitorTests(APITestCase):
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

    def _hub_session(self, user=None, company=None):
        self.client.force_login(user or self.staff)
        session = self.client.session
        session["company_id"] = (company or self.company).id
        session.save()

    def test_monitor_otp_login_and_list(self):
        self._ingest()
        unknown = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "nadie@labbe.test"},
            format="json",
        )
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        staff_email = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "hubadmin@labbe.test"},
            format="json",
        )
        self.assertEqual(staff_email.status_code, 200)
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
        gone = self.client.post(
            "/api/monitor/auth/login/",
            {"username": "opdemo", "password": "password12"},
            format="json",
        )
        self.assertEqual(gone.status_code, 404)

    def test_hub_operator_crud_is_tenant_scoped(self):
        other = Company.objects.create(name="Otra", slug="otra")
        grant_demo(other)
        other_staff = User.objects.create_user(
            username="otroadmin",
            password="password12",
            is_staff=True,
        )
        ensure_membership(other_staff, other)
        self._hub_session()
        created = self.client.post(
            "/api/operators/",
            {
                "first_name": "Luis",
                "last_name": "García",
                "email": "luis@labbe.test",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        operator_id = created.data["id"]
        self.assertEqual(created.data["email"], "luis@labbe.test")
        self.assertIsNone(created.data["last_login_at"])
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
        asked = self.client.post(
            "/api/monitor/auth/request-otp/",
            {"email": "luis@labbe.test"},
            format="json",
        )
        self.assertEqual(asked.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

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

    def test_operational_error_returns_json(self):
        from django.db.utils import OperationalError

        from .exceptions import api_exception_handler

        response = api_exception_handler(OperationalError("slots"), {})
        self.assertEqual(response.status_code, 503)
        self.assertIn("base de datos", response.data["detail"])
