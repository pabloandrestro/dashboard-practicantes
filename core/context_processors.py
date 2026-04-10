"""
Context processors del proyecto.

En este archivo defino funciones que agregan variables globales
al contexto de todos los templates automáticamente.

Mi objetivo es:
- Exponer el avatar del usuario en la navbar.
- Indicar si el usuario autenticado es controller.
- Detectar si estoy navegando dentro del panel interno (/panel/).
"""

from .models import Practicante, PerfilAdmin
from .models import Sugerencia

def _get_practicante(request):
    """
    Helper interno: obtengo el Practicante asociado al usuario autenticado.

    Lo centralizo aquí para evitar repetir consultas a la base de datos
    en múltiples context processors.
    """
    if not request.user.is_authenticated or request.user.is_superuser:
        return None

    # Uso .first() para no lanzar excepción si no existe registro.
    return Practicante.objects.filter(user=request.user).first()


def _get_perfil_admin(request):
    """
    Helper interno: obtengo el PerfilAdmin del superuser autenticado.

    Lo centralizo aquí para evitar duplicación de lógica.
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        return None

    return PerfilAdmin.objects.filter(user=request.user).first()


def navbar_avatar(request):
    """
    Agrego la URL del avatar del usuario autenticado para mostrarla
    en la barra de navegación (navbar).

    Lógica:
    - Si es superuser, busco PerfilAdmin y su foto.
    - Si no es superuser, busco Practicante y su foto.
    - Si no hay foto, retorno None.
    """

    avatar_url = None

    if request.user.is_authenticated:

        if request.user.is_superuser:
            perfil = _get_perfil_admin(request)
            if perfil and getattr(perfil, "foto_perfil", None):
                avatar_url = perfil.foto_perfil.url

        else:
            pract = _get_practicante(request)
            if pract and getattr(pract, "foto_perfil", None):
                avatar_url = pract.foto_perfil.url

    return {"navbar_avatar_url": avatar_url}


def es_controller(request):
    """
    Indico si el usuario autenticado tiene rol de controller.

    Retorno True si:
    - Existe el registro Practicante asociado al usuario.
    - Y su atributo es_controller es True.
    """

    pract = _get_practicante(request)
    es_ctrl = bool(pract and pract.es_controller)

    return {"es_controller": es_ctrl}


def es_admin_path(request):
    """
    Detecto si la URL actual pertenece al panel interno.

    Considero como panel admin:
    - rutas que empiezan con /panel/
    """

    path_actual = request.path or ""
    return {"es_admin_path": path_actual.startswith("/panel/")}

def sugerencias_pendientes(request):
    """
    Inyecta el contador de sugerencias nuevas ('enviada') 
    solo si el usuario es administrador.
    """
    if request.user.is_authenticated and request.user.is_staff:
        # Filtramos por el estado 'enviada' según tu migración 0013_sugerencia_estado.py
        count = Sugerencia.objects.filter(estado='enviada').count()
        return {'nuevas_sugerencias_count': count}
    
    # Para los practicantes normales, el conteo siempre es 0
    return {'nuevas_sugerencias_count': 0}