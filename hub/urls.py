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
    path("auth/company/", views.select_company, name="auth-company"),
    path("salud/", views.salud, name="salud"),
    path("", include(router.urls)),
]
