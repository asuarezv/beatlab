from django.contrib.auth import get_user_model
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
            password="password12",
        )
        self.operator = Operator.objects.create(company=self.company, user=self.op_user)

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

    def test_monitor_login_and_list(self):
        self._ingest()
        denied = self.client.post(
            "/api/monitor/auth/login/",
            {"username": "hubadmin", "password": "password12"},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(denied.data["detail"], "No hay Operator con ese usuario.")
        wrong = self.client.post(
            "/api/monitor/auth/login/",
            {"username": "opdemo", "password": "noesesta"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.data["detail"], "Usuario o contraseña incorrectos")
        login = self.client.post(
            "/api/monitor/auth/login/",
            {"username": "opdemo", "password": "password12"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        token = login.data["token"]
        beats = self.client.get(
            "/api/monitor/beats/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(beats.status_code, 200)
        self.assertEqual(len(beats.data), 1)
        self.assertEqual(beats.data[0]["title"], "Cola recuperada")

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
