"""
Configuración de URLs del proyecto config.

En este archivo defino todas las rutas (endpoints) del sistema
y las vinculo con las vistas correspondientes.
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Vistas de autenticación de Django
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

# Vistas propias (core)
from core.views import (
    # Inicio / secciones principales
    inicio, proyectos, horas,

    # Perfil practicante
    perfil, perfil_editar,

    # Proyectos / reportes / horas
    proyecto_crear, proyecto_detalle, proyecto_cambiar_foto,
    proyecto_unirme, proyecto_salir, cambiar_mi_rol,
    reporte_crear, reporte_borrar,
    descargar_horas_csv,

    # Panel de administración interno (mi panel, no el admin de Django)
    admin_practicantes, admin_practicante_crear, admin_practicante_editar,
    admin_practicante_eliminar, admin_practicantes_excel, admin_practicante_perfil,
    admin_proyectos, admin_proyecto_detalle,
    admin_horas,
    admin_reportes,
    admin_perfil, admin_perfil_editar,
)


urlpatterns = [
    # =========================
    # ADMIN DJANGO (por defecto)
    # =========================
    path("admin/", admin.site.urls),

    # =========================
    # AUTENTICACIÓN
    # =========================
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),

    # =========================
    # INICIO
    # =========================
    # Dejo la raíz como "home" para evitar duplicar el name="inicio"
    path("", inicio, name="home"),
    path("inicio/", inicio, name="inicio"),

    # =========================
    # PERFIL PRACTICANTE
    # =========================
    path("perfil/", perfil, name="perfil"),
    path("perfil/editar/", perfil_editar, name="perfil_editar"),

    # =========================
    # SECCIONES PRINCIPALES
    # =========================
    path("proyectos/", proyectos, name="proyectos"),
    path("horas/", horas, name="horas"),

    # =========================
    # PROYECTOS
    # =========================
    path("proyectos/nuevo/", proyecto_crear, name="proyecto_crear"),
    path("proyectos/<int:proyecto_id>/", proyecto_detalle, name="proyecto_detalle"),
    path("proyectos/<int:proyecto_id>/foto/", proyecto_cambiar_foto, name="proyecto_cambiar_foto"),

    # Acciones dentro del proyecto
    path("proyectos/<int:proyecto_id>/unirme/", proyecto_unirme, name="proyecto_unirme"),
    path("proyectos/<int:proyecto_id>/salir/", proyecto_salir, name="proyecto_salir"),
    path("proyectos/<int:proyecto_id>/cambiar-rol/", cambiar_mi_rol, name="cambiar_mi_rol"),

    # =========================
    # REPORTES
    # =========================
    path("proyectos/<int:proyecto_id>/reporte/nuevo/", reporte_crear, name="reporte_crear"),
    path("reportes/<int:reporte_id>/borrar/", reporte_borrar, name="reporte_borrar"),

    # =========================
    # HORAS
    # =========================
    path("horas/descargar-csv/", descargar_horas_csv, name="descargar_horas_csv"),

    # =========================
    # PANEL (ADMIN INTERNO)
    # Recomiendo estandarizar con prefijo "panel/"
    # =========================

    # Practicantes
    path("panel/practicantes/", admin_practicantes, name="admin_practicantes"),
    path("panel/practicantes/crear/", admin_practicante_crear, name="admin_practicante_crear"),
    path("panel/practicantes/<int:user_id>/editar/", admin_practicante_editar, name="admin_practicante_editar"),
    path("panel/practicantes/<int:user_id>/eliminar/", admin_practicante_eliminar, name="admin_practicante_eliminar"),
    path("panel/practicantes/excel/", admin_practicantes_excel, name="admin_practicantes_excel"),
    path("panel/practicante/<int:user_id>/", admin_practicante_perfil, name="admin_practicante_perfil"),

    # Proyectos
    path("panel/proyectos/", admin_proyectos, name="admin_proyectos"),
    path("panel/proyectos/<int:proyecto_id>/", admin_proyecto_detalle, name="admin_proyecto_detalle"),

    # Horas
    path("panel/horas/", admin_horas, name="admin_horas"),

    # Reportes (ojo: aquí dejo un solo endpoint y un solo name)
    path("panel/reportes/", admin_reportes, name="admin_reportes"),

    # Perfil admin
    path("panel/perfil/", admin_perfil, name="admin_perfil"),
    path("panel/perfil/editar/", admin_perfil_editar, name="admin_perfil_editar"),
]


# =========================
# MEDIA (solo en desarrollo)
# =========================
# Esto permite servir archivos subidos (por ejemplo fotos) mientras DEBUG=True.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)