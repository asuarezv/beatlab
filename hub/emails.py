from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_register_otp(to_email: str, username: str, otp: str, ttl_seconds: int) -> None:
    minutes = max(1, ttl_seconds // 60)
    subject = "Tu código de BeatLab Hub"
    text_body = (
        f"Hola {username},\n\n"
        f"Tu código para crear el Hub es:\n\n"
        f"  {otp}\n\n"
        f"Caduca en {minutes} minutos.\n"
        "Si no solicitaste este registro, ignora este correo.\n\n"
        "— BeatLab\n"
    )
    html_body = (
        f"<p>Hola {username},</p>"
        f"<p>Tu código para crear el Hub es:</p>"
        f"<p style=\"font-size:28px;letter-spacing:0.2em;font-weight:700\">{otp}</p>"
        f"<p>Caduca en {minutes} minutos. Si no solicitaste este registro, ignora este correo.</p>"
        f"<p>— BeatLab</p>"
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
