from .models import Company, Membership


def companies_for(user):
    if user.is_superuser:
        return Company.objects.all()
    return Company.objects.filter(memberships__user=user).distinct()


def current_company(request):
    qs = companies_for(request.user)
    company_id = request.session.get("company_id")
    if company_id:
        company = qs.filter(pk=company_id).first()
        if company:
            return company
    company = qs.first()
    if company:
        request.session["company_id"] = company.id
    return company


def ensure_membership(user, company):
    Membership.objects.get_or_create(user=user, company=company)
