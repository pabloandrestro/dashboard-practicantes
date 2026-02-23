from django.db import models
from django.contrib.auth.models import User


class Proyecto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    numero_celula = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=50)
    porcentaje_avance = models.IntegerField(default=0)
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(upload_to="proyectos/", null=True, blank=True)

    def __str__(self):
        return self.nombre

class ParticipacionProyecto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    rol_en_proyecto = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.usuario.username} - {self.proyecto.nombre}"

from datetime import datetime, timedelta

class RegistroJornada(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateField()
    
    hora_entrada = models.TimeField()
    inicio_pausa = models.TimeField(null=True, blank=True)
    fin_pausa = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)

    horas_trabajadas = models.DurationField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.hora_salida:
            entrada = datetime.combine(self.fecha, self.hora_entrada)
            salida = datetime.combine(self.fecha, self.hora_salida)

            tiempo_total = salida - entrada

            if self.inicio_pausa and self.fin_pausa:
                pausa_inicio = datetime.combine(self.fecha, self.inicio_pausa)
                pausa_fin = datetime.combine(self.fecha, self.fin_pausa)
                tiempo_total -= (pausa_fin - pausa_inicio)

            self.horas_trabajadas = tiempo_total

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha}"
    
from django.db.models import Sum

def total_horas_usuario(usuario):
    registros = RegistroJornada.objects.filter(usuario=usuario)
    total = registros.aggregate(Sum('horas_trabajadas'))['horas_trabajadas__sum']
    
    if not total:
        return "0 horas"

    total_segundos = total.total_seconds()
    horas = int(total_segundos // 3600)
    minutos = int((total_segundos % 3600) // 60)

    return f"{horas} horas {minutos} minutos"


import uuid


class Practicante(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    rut = models.CharField(
    max_length=12,
    unique=True,
    null=True,
    blank=True
)
    universidad = models.CharField(max_length=255, null=True, blank=True)
    carrera = models.CharField(max_length=255, null=True, blank=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)

    fecha_inicio_practica = models.DateField(null=True, blank=True)
    fecha_termino_practica = models.DateField(null=True, blank=True)
    horas_requeridas = models.IntegerField(null=True, blank=True)
    celular = models.CharField(max_length=15, blank=True, null=True)

    es_controller = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    foto_perfil = models.ImageField(upload_to="perfiles/", null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def crear_practicante(sender, instance, created, **kwargs):
    if created:
        Practicante.objects.create(user=instance)
    
class ReporteAvance(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    fecha = models.DateField(null=True, blank=True)
    descripcion = models.TextField()

    porcentaje_avance = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.fecha}"
    
