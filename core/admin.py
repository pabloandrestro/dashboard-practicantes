"""
Configuración del panel de administración de Django.

En este archivo registro mis modelos para que aparezcan en /admin
y pueda gestionarlos desde el panel de Django sin crear vistas propias.
"""

from django.contrib import admin

# Importo todos los modelos que quiero administrar desde el panel de Django.
# Evito repetir imports para mantener el archivo ordenado y fácil de mantener.
from .models import (
    Proyecto,
    ParticipacionProyecto,
    RegistroJornada,
    Practicante,
    ReporteAvance,
)

# Registro los modelos en el admin para que se muestren en el panel.
# Con esto puedo crear, editar y eliminar registros desde /admin.
admin.site.register(Proyecto)
admin.site.register(ParticipacionProyecto)
admin.site.register(RegistroJornada)
admin.site.register(Practicante)
admin.site.register(ReporteAvance)