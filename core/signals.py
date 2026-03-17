from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Practicante


"""
REFACTOR (2026-03-17):
- Movimos los signals fuera de `core/models.py` hacia este módulo dedicado.
- La importación de este archivo se gatilla desde `core/apps.py` (CoreConfig.ready).
"""


@receiver(post_save, sender=User)
def crear_practicante(sender, instance, created, **kwargs):
    """
    Cuando se crea un User nuevo, creo automáticamente su registro Practicante
    si no es staff ni superuser.

    Uso get_or_create() para evitar duplicados si el registro ya existe
    por alguna razón (por ejemplo, creación manual o procesos paralelos).
    """
    if created and (not instance.is_staff) and (not instance.is_superuser):
        Practicante.objects.get_or_create(user=instance)


