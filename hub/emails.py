from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def send_register_otp(to_email: str, username: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    subject = "Tu código de BeatLab Hub"
    context = {
        "username": username,
        "otp": otp,
        "minutes": minutes,
        "logo_url": settings.EMAIL_LOGO_URL,
        "site_url": settings.PUBLIC_SITE_URL,
        "year": timezone.now().year,
    }
    text_body = render_to_string("hub/email/register_otp.txt", context)
    html_body = render_to_string("hub/email/register_otp.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def send_operator_invite_otp(to_email: str, name: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    subject = "Confirma tu alta como Operator"
    context = {
        "name": name,
        "otp": otp,
        "minutes": minutes,
        "logo_url": settings.EMAIL_LOGO_URL,
        "site_url": settings.PUBLIC_SITE_URL,
        "year": timezone.now().year,
    }
    text_body = render_to_string("hub/email/operator_invite_otp.txt", context)
    html_body = render_to_string("hub/email/operator_invite_otp.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def send_email_change_otp(to_email: str, name: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    subject = "Confirma tu nuevo correo"
    context = {
        "name": name,
        "otp": otp,
        "minutes": minutes,
        "logo_url": settings.EMAIL_LOGO_URL,
        "site_url": settings.PUBLIC_SITE_URL,
        "year": timezone.now().year,
    }
    text_body = render_to_string("hub/email/email_change_otp.txt", context)
    html_body = render_to_string("hub/email/email_change_otp.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def send_monitor_otp(to_email: str, name: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    subject = "Tu código Monitor"
    context = {
        "name": name,
        "otp": otp,
        "minutes": minutes,
        "logo_url": settings.EMAIL_LOGO_URL,
        "site_url": settings.PUBLIC_SITE_URL,
        "year": timezone.now().year,
    }
    text_body = render_to_string("hub/email/monitor_otp.txt", context)
    html_body = render_to_string("hub/email/monitor_otp.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
