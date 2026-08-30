from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def operator_invite_url(token: str) -> str:
    return f"{settings.PUBLIC_SITE_URL}/invitar?token={quote(token)}"


def operator_recover_url(email: str = "") -> str:
    base = f"{settings.PUBLIC_SITE_URL}/recuperar"
    if email:
        return f"{base}?email={quote(email)}"
    return base


def _send_html_email(*, to_email, subject, template, context) -> None:
    text_body = render_to_string(f"hub/email/{template}.txt", context)
    html_body = render_to_string(f"hub/email/{template}.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def _email_context(**extra) -> dict:
    context = {
        "logo_url": settings.EMAIL_LOGO_URL,
        "site_url": settings.PUBLIC_SITE_URL,
        "year": timezone.now().year,
    }
    context.update(extra)
    return context


def send_register_otp(to_email: str, username: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    _send_html_email(
        to_email=to_email,
        subject="Tu código de BeatLab Hub",
        template="register_otp",
        context=_email_context(username=username, otp=otp, minutes=minutes),
    )


def send_operator_invite(
    to_email: str,
    *,
    name: str,
    inviter_name: str,
    company_name: str,
    otp: str,
    ttl_seconds: int,
    invite_url: str,
) -> None:
    minutes = max(1, ttl_seconds // 60)
    _send_html_email(
        to_email=to_email,
        subject="Te invitaron a Monitor",
        template="operator_invite",
        context=_email_context(
            name=name,
            inviter_name=inviter_name,
            company_name=company_name,
            otp=otp,
            minutes=minutes,
            invite_url=invite_url,
        ),
    )


def send_operator_recover(
    to_email: str,
    *,
    name: str,
    otp: str,
    ttl_seconds: int,
    recover_url: str,
) -> None:
    minutes = max(1, ttl_seconds // 60)
    _send_html_email(
        to_email=to_email,
        subject="Recupera tu cuenta Monitor",
        template="operator_recover",
        context=_email_context(
            name=name,
            otp=otp,
            minutes=minutes,
            recover_url=recover_url,
        ),
    )


def send_email_change_otp(to_email: str, name: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    _send_html_email(
        to_email=to_email,
        subject="Confirma tu nuevo correo",
        template="email_change_otp",
        context=_email_context(name=name, otp=otp, minutes=minutes),
    )


def send_monitor_otp(to_email: str, name: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    _send_html_email(
        to_email=to_email,
        subject="Tu código Monitor",
        template="monitor_otp",
        context=_email_context(name=name, otp=otp, minutes=minutes),
    )
