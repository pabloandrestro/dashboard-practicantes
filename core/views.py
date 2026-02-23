from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required
from .models import Practicante
from .forms import PracticanteForm
from .models import Proyecto, ParticipacionProyecto
from django.utils import timezone
from datetime import date

from .models import Proyecto, ParticipacionProyecto, ReporteAvance
from .forms import ReporteAvanceForm
from .forms import ProyectoImagenForm
from .forms import ProyectoForm
from .models import RegistroJornada
from django.views.decorators.http import require_POST

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required




@login_required
def inicio(request):
    user = request.user

    # datos del practicante
    practicante = Practicante.objects.get(user=user)

    # 🔹 HORAS TRABAJADAS (sumatoria)
    jornadas = RegistroJornada.objects.filter(usuario=user)

    total_segundos = 0
    for j in jornadas:
        if j.horas_trabajadas:
            total_segundos += j.horas_trabajadas.total_seconds()

    horas_totales = int(total_segundos // 3600)

    # 🔹 DIAS ACTIVOS
    dias_activos = jornadas.filter(hora_entrada__isnull=False).count()

    # 🔹 PROYECTOS ACTIVOS
    
    proyectos_activos = (
        ParticipacionProyecto.objects
        .filter(usuario=request.user, proyecto__estado="Activo")
        .values("proyecto_id")
        .distinct()
        .count()
    )

    context = {
        "practicante": practicante,
        "horas_totales": horas_totales,
        "dias_activos": dias_activos,
        "proyectos_activos": proyectos_activos,
    }

    return render(request, "inicio.html", {
        "practicante": practicante,
        "horas_totales": horas_totales,
        "dias_activos": dias_activos,
        "proyectos_activos": proyectos_activos,
    })



@login_required
def perfil(request):
    practicante = request.user.practicante
    return render(request, "perfil.html", {"practicante": practicante})



@login_required
def perfil_editar(request):
    practicante = request.user.practicante

    if request.method == "POST":
        form = PracticanteForm(request.POST, request.FILES, instance=practicante)
        if form.is_valid():
            form.save()

            request.user.first_name = form.cleaned_data["first_name"]
            request.user.last_name = form.cleaned_data["last_name"]
            request.user.email = form.cleaned_data["email"]
            request.user.save()

            return redirect("perfil")
    else:
        form = PracticanteForm(
            instance=practicante,
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
        )

    return render(request, "perfil_editar.html", {"form": form, "practicante": practicante})



def proyectos(request):
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

    return render(
        request,
        "proyectos.html",
        {
            "ver_todos": ver_todos,
            "participaciones": participaciones,
            "proyectos": proyectos_qs,
        }
    )

@login_required
def proyecto_detalle(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    participacion = (
        ParticipacionProyecto.objects
        .filter(usuario=request.user, proyecto=proyecto)
        .first()
    )

    can_edit = participacion is not None  

    if request.method == "POST" and request.FILES.get("imagen"):
        if not can_edit:
            # opcional: devolver forbidden o simplemente ignorar
            return redirect("proyecto_detalle", proyecto_id=proyecto.id)

        proyecto.imagen = request.FILES["imagen"]
        proyecto.save(update_fields=["imagen"])
        return redirect("proyecto_detalle", proyecto_id=proyecto.id)

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
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    #if not proyecto.activo: 
      #  return redirect("proyecto_detalle", proyecto_id=proyecto.id)

    
    ParticipacionProyecto.objects.get_or_create(
        usuario=request.user,
        proyecto=proyecto,
        defaults={"rol_en_proyecto": "Integrante"}  
    )

    return redirect("proyecto_detalle", proyecto_id=proyecto.id)

@login_required
@require_POST
def proyecto_salir(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # eliminar la participación del usuario en ese proyecto
    ParticipacionProyecto.objects.filter(
        usuario=request.user,
        proyecto=proyecto
    ).delete()

    return redirect("proyecto_detalle", proyecto_id=proyecto.id)


def proyecto_cambiar_foto(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

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
    if request.method == "POST":
        form = ProyectoForm(request.POST, request.FILES)
        if form.is_valid():
            proyecto = form.save(commit=False)
            proyecto.creado_por = request.user
            proyecto.save()

            # agregar al usuario como participante automáticamente
            from .models import ParticipacionProyecto
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

            # Si la fecha viene vacía, usa hoy
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



@login_required
def horas(request):
    usuario = request.user
    hoy = timezone.localdate()

    jornada = RegistroJornada.objects.filter(usuario=usuario, fecha=hoy).first()

    # --------- FLAGS PARA BLOQUEAR BOTONES ----------
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
        and not (jornada.inicio_pausa is not None and jornada.fin_pausa is None)  # no terminar “en pausa”
    )

    # --------- ACCIONES ----------
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
    registros = RegistroJornada.objects.filter(usuario=request.user).order_by("-fecha")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registro_horas.csv"'

    writer = csv.writer(response)

    # encabezados
    writer.writerow([
        "Fecha",
        "Inicio",
        "Inicio pausa",
        "Fin pausa",
        "Termino",
        "Horas trabajadas"
    ])

    # datos
    for r in registros:
        writer.writerow([
            r.fecha.strftime("%d-%m-%Y") if r.fecha else "-",
            r.hora_entrada.strftime("%H:%M:%S") if r.hora_entrada else "-",
            r.inicio_pausa.strftime("%H:%M:%S") if r.inicio_pausa else "-",
            r.fin_pausa.strftime("%H:%M:%S") if r.fin_pausa else "-",
            r.hora_salida.strftime("%H:%M:%S") if r.hora_salida else "-",
            str(r.horas_trabajadas) if r.horas_trabajadas else "-"
        ])

    return response