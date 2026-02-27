"""
Modelos del sistema.

En este archivo defino la estructura de datos principal de mi proyecto usando Django ORM.
Cada clase representa una tabla en la base de datos.

También incluyo:
- Cálculo automático de horas trabajadas en RegistroJornada.
- Una función utilitaria para sumar horas trabajadas por usuario.
- Creación automática del registro Practicante cuando se crea un User normal.
"""

import uuid
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver


# =========================================================
# MODELO: PROYECTO
# =========================================================
class Proyecto(models.Model):
    """
    Represento un proyecto del portal.

    Guardo información general del proyecto, su estado, porcentaje de avance
    y el usuario que lo creó. También permito una imagen opcional.
    """

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()

    # Según mi lógica interna, esto representa la célula/equipo del proyecto.
    numero_celula = models.IntegerField()

    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)

    estado = models.CharField(max_length=50)

    # Porcentaje simple 0-100 (lo valido en forms.py para asegurar rango).
    porcentaje_avance = models.IntegerField(default=0)

    # Usuario creador del proyecto.
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)

    # Fecha automática de creación del proyecto.
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Imagen opcional del proyecto.
    imagen = models.ImageField(upload_to="proyectos/", null=True, blank=True)

    def __str__(self):
        return self.nombre


# =========================================================
# MODELO: PARTICIPACIÓN EN PROYECTO
# =========================================================
class ParticipacionProyecto(models.Model):
    """
    Represento la relación entre un usuario y un proyecto.

    Esto me permite saber qué usuario participa en qué proyecto y cuál es su rol.
    """

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)

    # Rol textual dentro del proyecto (por ejemplo: "Practicante", "Líder", etc.)
    rol_en_proyecto = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.usuario.username} - {self.proyecto.nombre}"


# =========================================================
# MODELO: REGISTRO DE JORNADA
# =========================================================
class RegistroJornada(models.Model):
    """
    Represento un registro diario de jornada laboral.

    Guardo:
    - hora_entrada
    - inicio/fin de pausa (opcional)
    - hora_salida (opcional)
    - horas_trabajadas (duración calculada automáticamente)

    Defensas incluidas:
    - Si hora_salida <= hora_entrada, no guardo una duración negativa.
    - Solo descuento pausa si está completa y es válida (fin > inicio).
    """

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateField()

    hora_entrada = models.TimeField()
    inicio_pausa = models.TimeField(null=True, blank=True)
    fin_pausa = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)

    # DurationField guarda una duración (timedelta).
    horas_trabajadas = models.DurationField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Antes de guardar, calculo automáticamente las horas trabajadas.

        Reglas:
        - Solo calculo si existe hora_salida.
        - Evito negativos si salida <= entrada.
        - Descuento pausa solo si inicio y fin existen y fin > inicio.
        """
        self.horas_trabajadas = None  # Por defecto lo dejo vacío

        if self.hora_salida:
            entrada = datetime.combine(self.fecha, self.hora_entrada)
            salida = datetime.combine(self.fecha, self.hora_salida)

            # Evito guardar resultados negativos o 0 si la salida es inválida.
            if salida <= entrada:
                super().save(*args, **kwargs)
                return

            tiempo_total = salida - entrada

            # Descuento pausa solo si es válida.
            if self.inicio_pausa and self.fin_pausa:
                pausa_inicio = datetime.combine(self.fecha, self.inicio_pausa)
                pausa_fin = datetime.combine(self.fecha, self.fin_pausa)

                if pausa_fin > pausa_inicio:
                    tiempo_total -= (pausa_fin - pausa_inicio)

            # Si por cualquier motivo queda <= 0, no guardo una duración inválida.
            if tiempo_total.total_seconds() > 0:
                self.horas_trabajadas = tiempo_total

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha}"


# =========================================================
# FUNCIÓN UTILITARIA: TOTAL DE HORAS POR USUARIO
# =========================================================
def total_horas_usuario(usuario):
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


# =========================================================
# MODELO: PRACTICANTE
# =========================================================
class Practicante(models.Model):
    """
    Represento a un practicante asociado 1 a 1 con un User.

    Uso UUID como PK para evitar IDs predecibles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relación 1 a 1 con el usuario de Django.
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # RUT opcional (si se llena, debe ser único).
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)

    universidad = models.CharField(max_length=255, null=True, blank=True)
    carrera = models.CharField(max_length=255, null=True, blank=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)

    fecha_inicio_practica = models.DateField(null=True, blank=True)
    fecha_termino_practica = models.DateField(null=True, blank=True)
    horas_requeridas = models.IntegerField(null=True, blank=True)
    celular = models.CharField(max_length=15, blank=True, null=True)

    # Flags para lógica de negocio.
    es_controller = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    foto_perfil = models.ImageField(upload_to="perfiles/", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


# =========================================================
# SIGNAL: CREACIÓN AUTOMÁTICA DE PRACTICANTE
# =========================================================
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


# =========================================================
# MODELO: REPORTE DE AVANCE
# =========================================================
class ReporteAvance(models.Model):
    """
    Represento un reporte de avance asociado a un proyecto y al usuario que lo crea.
    """

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    fecha = models.DateField(null=True, blank=True)
    descripcion = models.TextField()
    porcentaje_avance = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.fecha}"


# =========================================================
# MODELO: PERFIL ADMIN
# =========================================================
class PerfilAdmin(models.Model):
    """
    Perfil extendido para el administrador (superuser).
    Lo uso principalmente para almacenar foto de perfil.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto_perfil = models.ImageField(upload_to="perfiles_admin/", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PerfilAdmin: {self.user.username}"