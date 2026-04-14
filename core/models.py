"""
Modelos del sistema.

En este archivo defino la estructura de datos principal de mi proyecto usando Django ORM.
Cada clase representa una tabla en la base de datos.

También incluyo:
- Cálculo automático de horas trabajadas en RegistroJornada.

REFACTOR (2026-03-17):
- La función utilitaria agregada `total_horas_usuario` fue movida a `core/services/horas.py`.
- La creación automática de `Practicante` vía signal fue movida a `core/signals.py`
  y se registra desde `core/apps.py` (CoreConfig.ready).
"""

import uuid
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User

# REFACTOR (2026-03-17):
# - Se removieron los signals y funciones de cálculo agregadas desde este archivo.
# - Signals ahora viven en `core/signals.py`
# - Cálculos agregados (ej: total de horas por usuario) viven en `core/services/horas.py`


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

    def calcular_horas_trabajadas(self):
        """
        REFACTOR (2026-03-17):
        Extraigo el cálculo a un método dedicado para que `save()` quede más limpio
        y la lógica sea reutilizable (tests, servicios, etc.).

        Retorno:
        - timedelta si puedo calcular
        - None si no corresponde (por ejemplo, no hay hora_salida o hay datos inválidos)
        """
        if not self.hora_salida:
            return None

        entrada = datetime.combine(self.fecha, self.hora_entrada)
        salida = datetime.combine(self.fecha, self.hora_salida)

        # Evito duraciones negativas o 0 si la salida es inválida.
        if salida <= entrada:
            return None

        tiempo_total = salida - entrada

        # Descuento pausa solo si es válida.
        if self.inicio_pausa and self.fin_pausa:
            pausa_inicio = datetime.combine(self.fecha, self.inicio_pausa)
            pausa_fin = datetime.combine(self.fecha, self.fin_pausa)

            if pausa_fin > pausa_inicio:
                tiempo_total -= (pausa_fin - pausa_inicio)

        return tiempo_total if tiempo_total.total_seconds() > 0 else None

    def save(self, *args, **kwargs):
        """
        Antes de guardar, calculo automáticamente las horas trabajadas.

        Reglas:
        - Solo calculo si existe hora_salida.
        - Evito negativos si salida <= entrada.
        - Descuento pausa solo si inicio y fin existen y fin > inicio.
        """
        # REFACTOR (2026-03-17): delego el cálculo a `calcular_horas_trabajadas()`.
        self.horas_trabajadas = self.calcular_horas_trabajadas()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha}"


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


# =========================================================
# MODELO: SUGERENCIA
# =========================================================
class Sugerencia(models.Model):
    """
    Represento una sugerencia enviada por un usuario.

    Guardo:
    - nombre de usuario (FK a User)
    - nombre y email al momento de enviar (por si cambian después)
    - el texto de la sugerencia
    - la fecha y hora de envío
    """

    ESTADO_CHOICES = [
        ("enviada", "Enviada"),
        ("leida", "Leida"),
        ("finalizada", "Finalizada"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255)
    email = models.EmailField()
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="enviada",
    )
    archivo_adjunto = models.FileField(
        upload_to="sugerencias_multimedia/",
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Sugerencia de {self.usuario.username} ({self.creado_en.strftime('%d/%m/%y %H:%M')})"


# =========================================================
# MODELO: TAREA SCRUM
# =========================================================
class TareaScrum(models.Model):
    """
    Represento una tarea dentro del tablero Scrum de un proyecto.

    Cada tarea pertenece a un proyecto, puede estar asignada a un integrante,
    y tiene un estado que define en qué columna del tablero aparece.

    Estados disponibles (en orden de flujo):
    1. backlog      → Tarea creada, sin asignar aún.
    2. asignado     → Tarea asignada a un integrante.
    3. en_proceso   → El integrante está trabajando en ella.
    4. verificacion → Lista para revisión.
    5. completado   → Tarea terminada y verificada.
    """

    ESTADO_CHOICES = [
        ("backlog",      "Backlog"),
        ("asignado",     "Asignado"),
        ("en_proceso",   "En Proceso"),
        ("verificacion", "Verificación"),
        ("completado",   "Completado"),
    ]

    # Proyecto al que pertenece la tarea
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="tareas_scrum"
    )

    # Título breve de la tarea
    titulo = models.CharField(max_length=200)

    # Descripción opcional con más detalle
    descripcion = models.TextField(blank=True, default="")

    # Estado actual de la tarea dentro del flujo Scrum
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="backlog",
    )

    # Usuario al que está asignada (puede no estar asignada aún)
    asignado_a = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas"
    )

    # Usuario que creó la tarea
    creado_por = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tareas_creadas"
    )

    # Fecha de creación automática
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_estado_display()}] {self.titulo} — {self.proyecto.nombre}"