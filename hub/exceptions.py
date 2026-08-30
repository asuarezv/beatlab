from django.db.utils import OperationalError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    if isinstance(exc, OperationalError):
        return Response(
            {
                "detail": "El Hub no pudo conectar a la base de datos. Intenta de nuevo.",
            },
            status=503,
        )
    return None
