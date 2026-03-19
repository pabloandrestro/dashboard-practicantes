"""
Servicios relacionados a horas / jornadas.

REFACTOR (2026-03-17):
- Movemos funciones utilitarias fuera de `core/models.py` para mantener los modelos
  enfocados en estructura de datos y pequeñas reglas locales.
"""

from django.db.models import Sum

from core.models import RegistroJornada


def total_horas_usuario(usuario) -> str:
    """
    Calculo el total de horas trabajadas por un usuario sumando sus registros.

    Retorno un string legible tipo:
    - "0 horas"
    - "12 horas 30 minutos"
    """
    registros = RegistroJornada.objects.filter(usuario=usuario)
    total = registros.aggregate(Sum("horas_trabajadas"))["horas_trabajadas__sum"]

    if not total:
        return "0 horas"

    total_segundos = total.total_seconds()
    horas = int(total_segundos // 3600)
    minutos = int((total_segundos % 3600) // 60)

    return f"{horas} horas {minutos} minutos"