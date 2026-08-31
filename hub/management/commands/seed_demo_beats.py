from django.core.management.base import BaseCommand, CommandError

from hub.models import Company
from hub.seed import companies_for_seed, seed_company


class Command(BaseCommand):
    help = "Completa ~10 tipos de Beat y hasta 100 Beats de demo, sin dejar la cuota en 0."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company",
            dest="slug",
            default="",
            help="Slug de la empresa. Si se omite, siembra todas las que tengan System.",
        )

    def handle(self, *args, **options):
        slug = (options.get("slug") or "").strip()
        companies = companies_for_seed(slug or None)
        if slug and not companies:
            if not Company.objects.filter(slug=slug).exists():
                raise CommandError(f"No existe la empresa {slug}.")
            raise CommandError(f"La empresa {slug} no tiene Systems.")
        if not companies:
            raise CommandError("No hay empresas con System para sembrar.")
        for company in companies:
            result = seed_company(company)
            self.stdout.write(
                f"{result['company']} · {result['types']} tipos · "
                f"+{result['beats_created']} Beats ({result['beats_total']} total) · "
                f"{result['beats_remaining']} restantes · System {result['system']}"
            )
