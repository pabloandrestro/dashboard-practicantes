"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from core.views import inicio, proyectos, horas, perfil, perfil_editar
from core.views import proyecto_detalle, reporte_crear
from core.views import proyecto_cambiar_foto
from core.views import reporte_borrar
from core.views import proyecto_crear
from core.views import proyecto_unirme, proyecto_salir, cambiar_mi_rol, descargar_horas_csv, inicio

urlpatterns = [
    path('admin/', admin.site.urls),

    path("perfil/", perfil, name="perfil"),
    path("perfil/editar/", perfil_editar, name="perfil_editar"),

     # LOGIN / LOGOUT
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),


    path('', inicio, name='inicio'),
    path("proyectos/", proyectos, name="proyectos"),
    path('horas/', horas, name='horas'),
    path("proyectos/<int:proyecto_id>/", proyecto_detalle, name="proyecto_detalle"),
    path("proyectos/<int:proyecto_id>/reporte/nuevo/", reporte_crear, name="reporte_crear"),
    path("proyectos/<int:proyecto_id>/foto/", proyecto_cambiar_foto, name="proyecto_cambiar_foto"),
    path("reportes/<int:reporte_id>/borrar/", reporte_borrar, name="reporte_borrar"),
    path('proyectos/nuevo/', proyecto_crear, name='proyecto_crear'),
    path("proyectos/<int:proyecto_id>/unirme/", proyecto_unirme, name="proyecto_unirme"),
    path("proyectos/<int:proyecto_id>/salir/", proyecto_salir, name="proyecto_salir"),
    path("proyectos/<int:proyecto_id>/cambiar-rol/", cambiar_mi_rol, name="cambiar_mi_rol"),
    path("horas/descargar-csv/", descargar_horas_csv, name="descargar_horas_csv"),
    path("", inicio, name="inicio"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


