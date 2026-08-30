from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("companies", views.CompanyViewSet, basename="company")
router.register("operators", views.OperatorViewSet, basename="operator")
router.register("beat-types", views.BeatTypeViewSet, basename="beat-type")
router.register("systems", views.SystemViewSet, basename="system")
router.register("beats", views.BeatViewSet, basename="beat")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/me/", views.me, name="auth-me"),
    path("auth/login/", views.login_view, name="auth-login"),
    path("auth/register/", views.register_start, name="auth-register"),
    path("auth/register/verify/", views.register_verify, name="auth-register-verify"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
    path("auth/password/", views.change_password, name="auth-password"),
    path("auth/profile/", views.update_profile, name="auth-profile"),
    path("auth/profile/verify/", views.verify_profile_email, name="auth-profile-verify"),
    path("auth/company/", views.select_company, name="auth-company"),
    path("salud/", views.salud, name="salud"),
    path("ingest/beats/", views.ingest_beat, name="ingest-beat"),
    path("monitor/auth/request-otp/", views.monitor_request_otp, name="monitor-request-otp"),
    path("monitor/auth/verify-otp/", views.monitor_verify_otp, name="monitor-verify-otp"),
    path("monitor/auth/login/", views.monitor_login, name="monitor-login"),
    path("monitor/auth/me/", views.monitor_me, name="monitor-me"),
    path("monitor/auth/verify-email/", views.monitor_verify_email, name="monitor-verify-email"),
    path("monitor/auth/password/", views.monitor_password, name="monitor-password"),
    path("monitor/beats/", views.monitor_beats, name="monitor-beats"),
    path("", include(router.urls)),
]
