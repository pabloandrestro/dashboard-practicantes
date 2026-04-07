"""
Vistas del sistema.

En este archivo defino las vistas (views) que manejan:
- Inicio y perfil de practicantes
- Proyectos (listar, detalle, unirme/salir, reportes)
- Registro de horas (inicio, pausa, término, historial y exportación)
- Login personalizado (y redirecciones post-login)
- Panel de administración interno (practicantes, proyectos, horas, reportes, perfil admin)
- Exportación a Excel desde el panel

Cada vista se encarga de:
- Validar permisos (login_required / staff_member_required)
- Consultar la base de datos
- Procesar formularios o acciones POST
- Retornar un template con contexto o redirigir
"""

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q, Sum, Case, When, Value, IntegerField

from datetime import timedelta
import csv
import openpyxl

from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash

# Importo modelos que uso en las vistas
from .models import (
    Practicante,
    Proyecto,
    ParticipacionProyecto,
    ReporteAvance,
    RegistroJornada,
    PerfilAdmin,
    Sugerencia,
)

# Importo formularios que uso en las vistas
from .forms import (
    PracticanteForm,
    ReporteAvanceForm,
    ProyectoImagenForm,
    ProyectoForm,
    AdminCrearPracticanteUserForm,
    AdminEditarUsuarioForm,
    SugerenciaForm,
)

User = get_user_model()


# =========================================================
# HELPERS
# =========================================================

def _es_controller(user):
    """
    Determino si un usuario es controller consultando el Practicante asociado.
    """
    return Practicante.objects.filter(user=user, es_controller=True).exists()


def _duracion_a_hm(d):
    """
    Convierto una duración (timedelta) a un string tipo: '12h 30m'.
    """
    if not d:
        return "0h 0m"
    total_seg = int(d.total_seconds())
    horas = total_seg // 3600
    minutos = (total_seg % 3600) // 60
    return f"{horas}h {minutos}m"


def redirect_post_login(user):
    """
    Defino a qué vista redirigir después de login según el tipo de usuario.

    IMPORTANTE: aquí había un error en tu archivo original (lo marco abajo en mejoras).
    """
    # Si es superuser, lo mando al panel de practicantes
    if user.is_superuser:
        return redirect("admin_practicantes")

    # En caso normal, lo mando a inicio
    return redirect("inicio")


# =========================================================
# INICIO
# =========================================================

@login_required
def inicio(request):
    """
    Renderizo el dashboard de inicio del practicante.

    Si el usuario es superuser, lo redirijo al panel de practicantes.
    Si es practicante, calculo métricas:
    - horas totales (sumando horas_trabajadas)
    - días activos (cantidad de jornadas con entrada)
    - proyectos activos (participaciones en proyectos con estado 'Activo')
    """
    user = request.user

    if request.user.is_superuser:
        return redirect("admin_practicantes")

    # Obtengo el practicante asociado al usuario autenticado
    practicante = Practicante.objects.get(user=user)

    # Sumatoria de horas trabajadas (en segundos para sumar fácil)
    jornadas = RegistroJornada.objects.filter(usuario=user)

    total_segundos = 0
    for j in jornadas:
        if j.horas_trabajadas:
            total_segundos += j.horas_trabajadas.total_seconds()

    horas_totales = int(total_segundos // 3600)

    # Días activos: cuántos registros tienen hora_entrada
    dias_activos = jornadas.filter(hora_entrada__isnull=False).count()

    # Proyectos activos: participaciones en proyectos cuyo estado sea "Activo"
    proyectos_activos = (
        ParticipacionProyecto.objects
        .filter(usuario=request.user, proyecto__estado="Activo")
        .values("proyecto_id")
        .distinct()
        .count()
    )

    # Retorno el template con el contexto calculado
    return render(request, "inicio.html", {
        "practicante": practicante,
        "horas_totales": horas_totales,
        "dias_activos": dias_activos,
        "proyectos_activos": proyectos_activos,
    })


# =========================================================
# PERFIL PRACTICANTE
# =========================================================

@login_required
def perfil(request):
    """
    Muestro el perfil del practicante autenticado.
    """
    practicante = request.user.practicante
    return render(request, "perfil.html", {"practicante": practicante})


@login_required
def perfil_editar(request):
    """
    Permito que el practicante edite su perfil y sus datos básicos de User.

    Además, permito cambiar contraseña si se ingresan password1/password2.
    """
    practicante = request.user.practicante
    error = None

    if request.method == "POST":
        form = PracticanteForm(request.POST, request.FILES, instance=practicante)

        if form.is_valid():
            # Guardo datos del Practicante
            form.save()

            # Actualizo campos del User
            request.user.first_name = form.cleaned_data["first_name"]
            request.user.last_name = form.cleaned_data["last_name"]
            request.user.email = form.cleaned_data["email"]

            # Cambio de contraseña (opcional)
            password1 = (request.POST.get("password1") or "").strip()
            password2 = (request.POST.get("password2") or "").strip()

            if password1 or password2:
                if password1 != password2:
                    error = "Las contraseñas no coinciden."
                elif len(password1) < 6:
                    error = "La contraseña debe tener al menos 6 caracteres."
                else:
                    request.user.set_password(password1)

            # Si hay error, vuelvo a mostrar el formulario con mensaje
            if error:
                return render(request, "perfil_editar.html", {
                    "form": form,
                    "practicante": practicante,
                    "error": error
                })

            request.user.save()

            # Mantengo la sesión activa si cambié contraseña
            if password1 and password1 == password2:
                update_session_auth_hash(request, request.user)

            return redirect("perfil")
        else:
            # SEGURIDAD/UX (2026-03-17):
            # Si el formulario es inválido, NO guardo nada y muestro un error claro.
            # Antes quedaba silencioso (parecía que guardaba, pero no persistía).
            try:
                # Tomo el primer error del formulario para mostrarlo arriba.
                primer_error = next(iter(form.errors.values()))[0]
            except Exception:
                primer_error = "Revisa los campos: hay datos inválidos."
            return render(request, "perfil_editar.html", {
                "form": form,
                "practicante": practicante,
                "error": primer_error,
            })

    else:
        # Si es GET, precargo datos del User en el formulario
        form = PracticanteForm(
            instance=practicante,
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
        )

    return render(request, "perfil_editar.html", {
        "form": form,
        "practicante": practicante,
        "error": error
    })

@login_required
def sugerencias(request):
    """
    Permito que el practicante envíe sugerencias/comentarios.

    - En GET muestro el formulario precargado con los datos del usuario.
    - En POST valido que venga alguna sugerencia y, si todo está bien,
      muestro un mensaje de éxito y redirijo al perfil.

    (Si en el futuro quieres persistir estas sugerencias, aquí podrías
    guardarlas en un modelo o enviarlas por correo.)
    """
    usuario = request.user
    error = None
    # REFACTOR/UX (2026-03-17):
    # Lista de sugerencias activas para mostrar en la misma página.
    # Como no existe un campo "estado" en el modelo, interpretamos "activas"
    # como "existentes" en BD. Para no exponer datos, un practicante solo ve
    # sus propias sugerencias; el superuser ve todas.

    sugerencias_qs = Sugerencia.objects.all().order_by("-creado_en")
 

    if request.method == "POST":
        form = SugerenciaForm(request.POST, request.FILES)
        if form.is_valid():
            sugerencias_txt = form.cleaned_data["sugerencias"]
            archivo = request.FILES.get("archivo_adjunto")
            # Guardo la sugerencia en base de datos
            Sugerencia.objects.create(
                usuario=usuario,
                nombre=f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username,
                email=usuario.email,
                texto=sugerencias_txt,
                archivo_adjunto=archivo,
            )
            messages.success(request, "¡Gracias! Tu sugerencia fue enviada correctamente.")
            return redirect("sugerencias")
        else:
            # Muestro el primer error del campo para mantener tu template simple
            error = form.errors.get("sugerencias", ["Entrada inválida."])[0]
    else:
        form = SugerenciaForm()

    return render(request, "sugerencias.html", {
        "usuario": usuario,
        "error": error,
        "form": form,
        "sugerencias_list": sugerencias_qs,
    })


# =========================================================
# PROYECTOS
# =========================================================

@login_required
def proyectos(request):
    """
    Listo proyectos.

    Si viene ?all=1, muestro todos los proyectos.
    Si no, muestro solo los proyectos donde el usuario participa.
    """
    ver_todos = request.GET.get("all") == "1"

    if ver_todos:
        proyectos_qs = Proyecto.objects.all().order_by("-fecha_inicio")
        participaciones = None
    else:
        participaciones = (
            ParticipacionProyecto.objects
            .filter(usuario=request.user)
            .select_related("proyecto")
            .order_by("-proyecto__fecha_inicio")
        )
        proyectos_qs = None

    return render(request, "proyectos.html", {
        "ver_todos": ver_todos,
        "participaciones": participaciones,
        "proyectos": proyectos_qs,
    })


@login_required
def proyecto_detalle(request, proyecto_id):
    """
    Muestro el detalle de un proyecto:
    - participación del usuario (para permisos)
    - reportes
    - integrantes (y sus fotos si existen)
    - permite cambiar imagen si el usuario participa y envía POST con imagen
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    participacion = (
        ParticipacionProyecto.objects
        .filter(usuario=request.user, proyecto=proyecto)
        .first()
    )

    # Defino si el usuario puede editar (mínimo: participar)
    can_edit = participacion is not None

    # Cambio de imagen por POST (solo si participa)
    if request.method == "POST" and request.FILES.get("imagen"):
        if not can_edit:
            return redirect("proyecto_detalle", proyecto_id=proyecto.id)

        proyecto.imagen = request.FILES["imagen"]
        proyecto.save(update_fields=["imagen"])
        return redirect("proyecto_detalle", proyecto_id=proyecto.id)

    # Reportes del proyecto
    reportes = (
        ReporteAvance.objects
        .filter(proyecto=proyecto)
        .select_related("usuario")
        .order_by("-fecha")
    )

    # Integrantes del proyecto (participaciones)
    integrantes = (
        ParticipacionProyecto.objects
        .filter(proyecto=proyecto)
        .select_related("usuario")
    )

    # Para cada integrante, intento adjuntar la foto de perfil si existe
    for part in integrantes:
        pract = Practicante.objects.filter(user=part.usuario).only("foto_perfil").first()
        part.foto_perfil = pract.foto_perfil if pract and pract.foto_perfil else None

    return render(request, "proyecto_detalle.html", {
        "proyecto": proyecto,
        "participacion": participacion,
        "can_edit": can_edit,
        "reportes": reportes,
        "integrantes": integrantes
    })


@login_required
@require_POST
def proyecto_unirme(request, proyecto_id):
    """
    Permito al usuario unirse a un proyecto.
    Si ya existe la participación, no creo duplicados.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    ParticipacionProyecto.objects.get_or_create(
        usuario=request.user,
        proyecto=proyecto,
        defaults={"rol_en_proyecto": "Integrante"}
    )

    return redirect("proyecto_detalle", proyecto_id=proyecto.id)


@login_required
@require_POST
def proyecto_salir(request, proyecto_id):
    """
    Permito al usuario salir de un proyecto eliminando su participación.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    ParticipacionProyecto.objects.filter(
        usuario=request.user,
        proyecto=proyecto
    ).delete()

    return redirect("proyecto_detalle", proyecto_id=proyecto.id)


@login_required
def proyecto_cambiar_foto(request, proyecto_id):
    """
    Cambio la foto del proyecto usando ProyectoImagenForm.
    Solo permito el cambio si el usuario participa en el proyecto.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # Exijo que exista participación; si no, devuelve 404
    get_object_or_404(ParticipacionProyecto, usuario=request.user, proyecto=proyecto)

    if request.method == "POST":
        form = ProyectoImagenForm(request.POST, request.FILES, instance=proyecto)
        if form.is_valid():
            form.save()
            return redirect("proyecto_detalle", proyecto_id=proyecto.id)
    else:
        form = ProyectoImagenForm(instance=proyecto)

    return render(request, "proyecto_foto_form.html", {"proyecto": proyecto, "form": form})


@login_required
def proyecto_crear(request):
    """
    Creo un proyecto y automáticamente agrego al creador como participante con rol 'Lider'.
    """
    if request.method == "POST":
        form = ProyectoForm(request.POST, request.FILES)

        if form.is_valid():
            proyecto = form.save(commit=False)
            proyecto.creado_por = request.user
            proyecto.save()

            # Agrego al usuario como participante del proyecto
            ParticipacionProyecto.objects.create(
                usuario=request.user,
                proyecto=proyecto,
                rol_en_proyecto="Lider"
            )

            return redirect("proyecto_detalle", proyecto_id=proyecto.id)
    else:
        form = ProyectoForm()

    return render(request, "proyecto_crear.html", {"form": form})


@login_required
@require_POST
def cambiar_mi_rol(request, proyecto_id):
    """
    Permito al usuario cambiar su rol dentro de un proyecto (texto libre).
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    participacion = ParticipacionProyecto.objects.filter(
        usuario=request.user,
        proyecto=proyecto
    ).first()

    if participacion:
        nuevo_rol = request.POST.get("rol")
        if nuevo_rol:
            participacion.rol_en_proyecto = nuevo_rol
            participacion.save()

    return redirect("proyecto_detalle", proyecto_id=proyecto.id)


@login_required
def reporte_crear(request, proyecto_id):
    """
    Creo un reporte de avance para un proyecto.

    Reglas:
    - El usuario debe participar en el proyecto.
    - Si el formulario incluye estado, actualizo el estado del proyecto.
    - Si no se indica fecha, uso la fecha de hoy.
    - Si se indica porcentaje, lo actualizo en el proyecto.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    participacion = get_object_or_404(
        ParticipacionProyecto,
        usuario=request.user,
        proyecto=proyecto
    )

    if request.method == "POST":
        form = ReporteAvanceForm(request.POST)

        if form.is_valid():
            nuevo_estado = form.cleaned_data.get("estado")
            if nuevo_estado:
                proyecto.estado = nuevo_estado
                proyecto.save(update_fields=["estado"])

            reporte = form.save(commit=False)
            reporte.proyecto = proyecto
            reporte.usuario = request.user

            if not reporte.fecha:
                reporte.fecha = timezone.now().date()

            reporte.save()

            if reporte.porcentaje_avance is not None:
                proyecto.porcentaje_avance = reporte.porcentaje_avance
                proyecto.save(update_fields=["porcentaje_avance"])

            return redirect("proyecto_detalle", proyecto_id=proyecto.id)

    else:
        form = ReporteAvanceForm()

    return render(request, "reporte_form.html", {
        "proyecto": proyecto,
        "participacion": participacion,
        "form": form
    })


@login_required
def reporte_borrar(request, reporte_id):
    """
    Borro un reporte existente.

    Reglas:
    - El usuario debe participar en el proyecto.
    - Recalculo el porcentaje_avance del proyecto usando el último reporte.
    """
    reporte = get_object_or_404(ReporteAvance, id=reporte_id)

    get_object_or_404(
        ParticipacionProyecto,
        usuario=request.user,
        proyecto=reporte.proyecto
    )

    if request.method == "POST":
        proyecto = reporte.proyecto
        reporte.delete()

        ultimo = ReporteAvance.objects.filter(proyecto=proyecto).order_by("-fecha", "-id").first()
        proyecto.porcentaje_avance = ultimo.porcentaje_avance if ultimo and ultimo.porcentaje_avance is not None else 0
        proyecto.save(update_fields=["porcentaje_avance"])

        return redirect("proyecto_detalle", proyecto_id=proyecto.id)

    return redirect("proyecto_detalle", proyecto_id=reporte.proyecto.id)


# =========================================================
# HORAS
# =========================================================

@login_required
def horas(request):
    """
    Registro de horas del practicante.

    Manejo un flujo simple:
    - Inicio jornada (crea RegistroJornada del día)
    - Inicio pausa
    - Fin pausa
    - Término jornada (setea hora_salida)

    Además, calculo flags para habilitar/deshabilitar botones en el template.
    """
    usuario = request.user
    hoy = timezone.localdate()

    jornada = RegistroJornada.objects.filter(usuario=usuario, fecha=hoy).first()

    # Flags para habilitar botones
    can_inicio = jornada is None

    can_inicio_pausa = (
        jornada is not None
        and jornada.hora_entrada is not None
        and jornada.hora_salida is None
        and jornada.inicio_pausa is None
    )

    can_fin_pausa = (
        jornada is not None
        and jornada.inicio_pausa is not None
        and jornada.fin_pausa is None
    )

    can_termino = (
        jornada is not None
        and jornada.hora_entrada is not None
        and jornada.hora_salida is None
        and not (jornada.inicio_pausa is not None and jornada.fin_pausa is None)
    )

    # Acciones por POST
    if request.method == "POST":
        accion = request.POST.get("accion")
        ahora = timezone.localtime().time()

        if accion == "inicio" and can_inicio:
            RegistroJornada.objects.create(
                usuario=usuario,
                fecha=hoy,
                hora_entrada=ahora
            )

        elif accion == "inicio_pausa" and can_inicio_pausa:
            jornada.inicio_pausa = ahora
            jornada.save()

        elif accion == "fin_pausa" and can_fin_pausa:
            jornada.fin_pausa = ahora
            jornada.save()

        elif accion == "termino" and can_termino:
            jornada.hora_salida = ahora
            jornada.save()

        return redirect("horas")

    historial = RegistroJornada.objects.filter(usuario=usuario).order_by("-fecha")

    return render(request, "horas.html", {
        "jornada": jornada,
        "historial": historial,
        "can_inicio": can_inicio,
        "can_inicio_pausa": can_inicio_pausa,
        "can_fin_pausa": can_fin_pausa,
        "can_termino": can_termino,
    })


@login_required
def descargar_horas_csv(request):
    """
    Descargo el historial de horas en formato CSV para el usuario autenticado.
    """
    registros = RegistroJornada.objects.filter(usuario=request.user).order_by("-fecha")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registro_horas.csv"'

    writer = csv.writer(response)

    # Encabezados del CSV
    writer.writerow(["Fecha", "Inicio", "Inicio pausa", "Fin pausa", "Termino", "Horas trabajadas"])

    # Datos del CSV
    for r in registros:
        writer.writerow([
            r.fecha.strftime("%d-%m-%Y") if r.fecha else "-",
            r.hora_entrada.strftime("%H:%M:%S") if r.hora_entrada else "-",
            r.inicio_pausa.strftime("%H:%M:%S") if r.inicio_pausa else "-",
            r.fin_pausa.strftime("%H:%M:%S") if r.fin_pausa else "-",
            r.hora_salida.strftime("%H:%M:%S") if r.hora_salida else "-",
            str(r.horas_trabajadas) if r.horas_trabajadas else "-",
        ])

    return response


# =========================================================
# LOGIN PERSONALIZADO
# =========================================================

def login_view(request):
    """
    Implemento un login manual (en vez de usar LoginView genérico).

    Si el usuario ya está autenticado, lo redirijo según su rol.
    Si el login falla, retorno el template con un error.
    """
    if request.user.is_authenticated:
        return redirect_post_login(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_post_login(user)

        return render(request, "login.html", {"error": "Usuario o contraseña incorrectos"})

    return render(request, "login.html")


# =========================================================
# PANEL ADMIN: PRACTICANTES
# =========================================================

@staff_member_required
def admin_practicantes(request):
    """
    Listo practicantes en el panel admin interno, con buscador.

    Además, marco automáticamente como inactivos a quienes ya llegaron o pasaron
    su fecha_termino_practica.
    """
    q = (request.GET.get("q") or "").strip()
    hoy = timezone.localdate()

    # Paso practicantes a inactivos si ya venció la fecha de término
    Practicante.objects.filter(
        activo=True,
        fecha_termino_practica__isnull=False,
        fecha_termino_practica__lte=hoy
    ).update(activo=False)

    practicantes_qs = Practicante.objects.select_related("user").filter(
        user__is_superuser=False,
    )

    if q:
        filtro = (
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(rut__icontains=q) |
            Q(universidad__icontains=q) |
            Q(carrera__icontains=q)
        )

        if q.isdigit():
            filtro = filtro | Q(horas_requeridas=int(q))

        practicantes_qs = practicantes_qs.filter(filtro)

    practicantes = (
        practicantes_qs
        .annotate(
            orden_activo=Case(
                When(activo=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            orden_sin_fecha=Case(
                When(fecha_termino_practica__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .order_by("orden_activo", "orden_sin_fecha", "fecha_termino_practica", "user__first_name", "user__last_name")
    )

    total_activos = practicantes.filter(activo=True).count()

    return render(request, "admin_practicantes.html", {
        "practicantes": practicantes,
        "total_activos": total_activos,
    })


@staff_member_required
def admin_practicante_perfil(request, user_id):
    """
    Muestro el perfil completo de un practicante desde el panel admin:
    - horas totales
    - % completado según horas requeridas
    - proyectos en los que participa
    """
    usuario = get_object_or_404(User, id=user_id)
    practicante = get_object_or_404(Practicante, user=usuario)

    total_td = (
        RegistroJornada.objects
        .filter(usuario=usuario)
        .aggregate(total=Sum("horas_trabajadas"))
        .get("total")
    ) or timedelta()

    participaciones = (
        ParticipacionProyecto.objects
        .filter(usuario=usuario)
        .select_related("proyecto")
        .order_by("-proyecto__fecha_inicio")
    )

    pct_label = "-"
    if practicante.horas_requeridas and practicante.horas_requeridas > 0:
        total_horas = total_td.total_seconds() / 3600
        pct = int((total_horas / float(practicante.horas_requeridas)) * 100)
        pct_label = f"{pct}%"

    return render(request, "admin_practicante_perfil.html", {
        "usuario": usuario,
        "practicante": practicante,
        "horas_totales": _duracion_a_hm(total_td),
        "pct_label": pct_label,
        "participaciones": participaciones,
    })


# =========================================================
# PANEL ADMIN: PROYECTOS / HORAS / REPORTES / PERFIL
# =========================================================

@staff_member_required
def admin_proyectos(request):
    """
    Listo todos los proyectos con buscador simple.
    """
    proyectos = Proyecto.objects.all().order_by("-fecha_inicio")

    query = request.GET.get("q")
    if query:
        proyectos = proyectos.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(estado__icontains=query) |
            Q(numero_celula__icontains=query)
        )

    return render(request, "admin_proyectos.html", {"proyectos": proyectos})


@staff_member_required
def admin_proyecto_detalle(request, proyecto_id):
    """
    Muestro detalle del proyecto desde el panel admin interno.
    """
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    reportes = (
        ReporteAvance.objects
        .filter(proyecto=proyecto)
        .select_related("usuario")
        .order_by("-fecha")
    )

    integrantes = (
        ParticipacionProyecto.objects
        .filter(proyecto=proyecto)
        .select_related("usuario")
    )

    for part in integrantes:
        pract = Practicante.objects.filter(user=part.usuario).only("foto_perfil").first()
        part.foto_perfil = pract.foto_perfil if pract and pract.foto_perfil else None

    return render(request, "admin_proyecto_detalle.html", {
        "proyecto": proyecto,
        "reportes": reportes,
        "integrantes": integrantes,
        "can_edit": False,
    })


@staff_member_required
def admin_horas(request):
    """
    Dashboard de horas para practicantes activos.
    - permite buscar practicantes
    - calcula horas de la semana y totales
    - calcula % de cumplimiento según horas requeridas
    """
    q = (request.GET.get("q") or "").strip()

    practicantes_qs = Practicante.objects.filter(
        activo=True,
        user__is_superuser=False,
    ).select_related("user")

    if q:
        practicantes_qs = practicantes_qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(rut__icontains=q)
        )

    practicantes = list(practicantes_qs)
    user_ids = [p.user_id for p in practicantes]

    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    semana_por_usuario = (
        RegistroJornada.objects
        .filter(usuario_id__in=user_ids, fecha__gte=inicio_semana, fecha__lte=hoy)
        .values("usuario_id")
        .annotate(total=Sum("horas_trabajadas"))
    )
    semana_map = {x["usuario_id"]: x["total"] for x in semana_por_usuario}

    total_por_usuario = (
        RegistroJornada.objects
        .filter(usuario_id__in=user_ids)
        .values("usuario_id")
        .annotate(total=Sum("horas_trabajadas"))
    )
    total_map = {x["usuario_id"]: x["total"] for x in total_por_usuario}

    practicantes_activos = len(practicantes)

    horas_semana_total = sum(((semana_map.get(uid) or timedelta()) for uid in user_ids), timedelta())
    horas_totales_total = sum(((total_map.get(uid) or timedelta()) for uid in user_ids), timedelta())

    filas = []
    for p in practicantes:
        total_u = total_map.get(p.user_id) or timedelta()
        total_horas = total_u.total_seconds() / 3600

        req = p.horas_requeridas
        if req and req > 0:
            pct = int((total_horas / float(req)) * 100)
            pct_label = f"{pct}%"
        else:
            pct_label = "-"

        filas.append({
            "user_id": p.user.id,
            "nombre": f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username,
            "horas_requeridas": req if req is not None else "-",
            "horas_registradas": _duracion_a_hm(total_u),
            "pct_label": pct_label,
        })

    # OJO: aquí se ordena por un string ("10h 2m"), no por número. Es mejorable.
    filas.sort(key=lambda x: x["horas_registradas"], reverse=True)

    return render(request, "admin_horas.html", {
        "practicantes_activos": practicantes_activos,
        "horas_semana": _duracion_a_hm(horas_semana_total),
        "horas_totales": _duracion_a_hm(horas_totales_total),
        "filas": filas,
    })


@staff_member_required
def admin_reportes(request):
    """
    Listo reportes de avance con buscador.
    """
    q = (request.GET.get("q") or "").strip()

    reportes = (
        ReporteAvance.objects
        .select_related("usuario", "proyecto")
        .annotate(
            fecha_es_null=Case(
                When(fecha__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    )

    if q:
        reportes = reportes.filter(
            Q(descripcion__icontains=q) |
            Q(proyecto__nombre__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(usuario__username__icontains=q)
        )

    reportes = reportes.order_by("fecha_es_null", "-fecha", "-id")

    return render(request, "admin_reportes.html", {"reportes": reportes})


@staff_member_required
def admin_perfil(request):
    """
    Muestro el perfil del admin y creo PerfilAdmin si no existe.
    """
    perfil_admin, _ = PerfilAdmin.objects.get_or_create(user=request.user)
    return render(request, "admin_perfil.html", {
        "usuario": request.user,
        "perfil_admin": perfil_admin,
    })


@staff_member_required
def admin_practicante_crear(request):
    """
    Creo un usuario nuevo para un practicante desde el panel admin.
    """
    if request.method == "POST":
        form = AdminCrearPracticanteUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = False
            user.save()
            return redirect("admin_practicantes")
    else:
        form = AdminCrearPracticanteUserForm()

    return render(request, "admin_practicante_crear.html", {"form": form})


@staff_member_required
def admin_perfil_editar(request):
    """
    Edito el perfil del administrador (User + PerfilAdmin).
    Permito cambiar contraseña, y mantengo sesión activa si se cambia.
    """
    usuario = request.user
    perfil_admin, _ = PerfilAdmin.objects.get_or_create(user=usuario)

    error = None

    if request.method == "POST":
        usuario.username = (request.POST.get("username") or usuario.username).strip()
        usuario.first_name = (request.POST.get("first_name") or "").strip()
        usuario.last_name = (request.POST.get("last_name") or "").strip()
        usuario.email = (request.POST.get("email") or "").strip()

        password1 = (request.POST.get("password1") or "").strip()
        password2 = (request.POST.get("password2") or "").strip()

        if password1 or password2:
            if password1 != password2:
                error = "Las contraseñas no coinciden."
            elif len(password1) < 6:
                error = "La contraseña debe tener al menos 6 caracteres."
            else:
                usuario.set_password(password1)

        if error:
            return render(request, "admin_perfil_editar.html", {
                "usuario": usuario,
                "perfil_admin": perfil_admin,
                "error": error,
            })

        usuario.save()

        if request.FILES.get("foto_perfil"):
            perfil_admin.foto_perfil = request.FILES["foto_perfil"]
            perfil_admin.save(update_fields=["foto_perfil"])

        if password1 and password1 == password2:
            update_session_auth_hash(request, usuario)

        messages.success(request, "Perfil actualizado.")
        return redirect("admin_perfil")

    return render(request, "admin_perfil_editar.html", {
        "usuario": usuario,
        "perfil_admin": perfil_admin,
        "error": error,
    })


@login_required
def admin_practicante_editar(request, user_id):
    """
    Edito un practicante desde el panel.

    Nota: esta vista tiene @login_required, pero por seguridad debería ser
    @staff_member_required, ya que permite editar usuarios.
    """
    usuario = get_object_or_404(User, id=user_id)
    practicante = get_object_or_404(Practicante, user=usuario)

    def clean_str(name):
        """Devuelvo string limpio o None si viene vacío."""
        v = request.POST.get(name, "")
        v = v.strip()
        return v if v else None

    def clean_int(name):
        """Devuelvo int o None si viene vacío."""
        v = request.POST.get(name, "")
        v = v.strip()
        return int(v) if v else None

    def clean_date(name):
        """Devuelvo string YYYY-MM-DD o None si viene vacío (Django lo parsea)."""
        v = request.POST.get(name, "")
        v = v.strip()
        return v if v else None

    if request.method == "POST":
        # --------- USER ----------
        username = request.POST.get("username", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        if username:
            usuario.username = username
        if first_name:
            usuario.first_name = first_name
        if last_name:
            usuario.last_name = last_name
        usuario.email = email

        password = request.POST.get("password", "").strip()
        if password:
            usuario.set_password(password)

        usuario.save()

        # --------- PRACTICANTE ----------
        practicante.rut = clean_str("rut")
        practicante.celular = clean_str("celular")
        practicante.universidad = clean_str("universidad")
        practicante.carrera = clean_str("carrera")
        practicante.horas_requeridas = clean_int("horas_requeridas")

        practicante.fecha_nacimiento = clean_date("fecha_nacimiento")
        practicante.fecha_inicio_practica = clean_date("fecha_inicio_practica")
        practicante.fecha_termino_practica = clean_date("fecha_termino_practica")

        practicante.activo = ("activo" in request.POST)
        practicante.es_controller = ("es_controller" in request.POST)

        if request.FILES.get("foto_perfil"):
            practicante.foto_perfil = request.FILES["foto_perfil"]

        practicante.save()

        # Sincronizo is_staff según es_controller
        usuario.is_staff = bool(practicante.es_controller)
        usuario.save(update_fields=["is_staff"])

        return redirect("admin_practicantes")

    return render(request, "admin_practicante_editar.html", {
        "usuario": usuario,
        "practicante": practicante
    })


@staff_member_required
def admin_practicante_eliminar(request, user_id):
    """
    Elimino un practicante y su usuario (solo por POST).
    """
    if request.method != "POST":
        return redirect("admin_practicantes")

    usuario = get_object_or_404(User, id=user_id)

    practicante = Practicante.objects.filter(user=usuario).first()
    if practicante:
        practicante.delete()

    usuario.delete()
    return redirect("admin_practicantes")


@staff_member_required
def admin_practicantes_excel(request):
    """
    Exporto los practicantes a un archivo Excel descargable.
    Respeto el filtro de búsqueda 'q' si viene.
    """
    practicantes = Practicante.objects.select_related("user").all()

    query = request.GET.get("q")
    if query:
        practicantes = practicantes.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(rut__icontains=query) |
            Q(universidad__icontains=query) |
            Q(carrera__icontains=query)
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Practicantes"

    headers = [
        "Nombre",
        "Rut",
        "Universidad",
        "Carrera",
        "Inicio",
        "Término",
        "Horas requeridas",
        "Estado"
    ]
    ws.append(headers)

    for p in practicantes:
        ws.append([
            f"{p.user.first_name} {p.user.last_name}",
            p.rut or "",
            p.universidad or "",
            p.carrera or "",
            p.fecha_inicio_practica.strftime("%d-%m-%Y") if p.fecha_inicio_practica else "",
            p.fecha_termino_practica.strftime("%d-%m-%Y") if p.fecha_termino_practica else "",
            p.horas_requeridas or "",
            "Activo" if p.activo else "Inactivo"
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="practicantes.xlsx"'
    wb.save(response)
    return response