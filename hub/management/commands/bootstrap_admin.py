from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from hub.models import Company
from hub.quota import grant_demo
from hub.tenant import ensure_membership

User = get_user_model()


class Command(BaseCommand):
    help = "Crea el superusuario y la primera empresa si no existen."

    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            slug="nynusoft",
            defaults={"name": "NynuSoft"},
        )
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        password = None
        if created or not user.has_usable_password():
            password = get_random_string(20)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        ensure_membership(user, company)
        grant_demo(company)
        if password:
            dest = Path(settings.BASE_DIR) / ".bootstrap-admin"
            dest.write_text(
                f"username=admin\npassword={password}\ncompany={company.slug}\n",
                encoding="utf-8",
            )
            dest.chmod(0o600)
            self.stdout.write(self.style.WARNING(f"Admin creado. Credenciales en {dest}"))
        else:
            self.stdout.write("Admin ya existía; no se cambió la contraseña.")
