from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        REFACTOR (2026-03-17):
        Registramos signals de la app en un módulo dedicado (`core/signals.py`).
        Esto evita mezclar señales con la definición de modelos y mantiene
        `models.py` enfocado en estructura de datos.
        """
        from . import signals  # noqa: F401

    