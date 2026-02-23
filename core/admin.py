from django.contrib import admin
from .models import Proyecto

admin.site.register(Proyecto)

from .models import Proyecto, ParticipacionProyecto

admin.site.register(ParticipacionProyecto)

from .models import Proyecto, ParticipacionProyecto, RegistroJornada

admin.site.register(RegistroJornada)

from django.contrib import admin
from .models import Practicante

admin.site.register(Practicante)

from .models import ReporteAvance

admin.site.register(ReporteAvance)