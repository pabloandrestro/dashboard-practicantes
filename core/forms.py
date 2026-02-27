"""
Formularios del proyecto.

En este archivo defino formularios basados en modelos (ModelForm)
y formularios de usuario para poder crear, editar y validar datos
desde las vistas y templates del sistema.

Mi objetivo con estos formularios es:
- Controlar qué campos se muestran
- Validar correctamente la información
- Personalizar widgets (por ejemplo inputs tipo date)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Practicante, ReporteAvance, Proyecto


# =========================================================
# FUNCIONES AUXILIARES PARA VALIDACIÓN DE RUT
# =========================================================

def _normalizar_rut(rut: str) -> str:
    """
    Normalizo el RUT eliminando puntos, guiones y espacios.
    También lo dejo en mayúscula.
    """
    rut = (rut or "").strip().upper()
    rut = rut.replace(".", "").replace("-", "").replace(" ", "")
    return rut


def _dv_rut(numero: int) -> str:
    """
    Calculo el dígito verificador (DV) del RUT chileno.
    """
    suma = 0
    multiplicador = 2
    n = numero

    while n > 0:
        suma += (n % 10) * multiplicador
        n //= 10
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = 11 - (suma % 11)

    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def _formatear_rut(numero: str, dv: str) -> str:
    """
    Retorno el RUT en formato estándar: XXXXXXXX-DV
    """
    return f"{numero}-{dv}"


# =========================================================
# FORMULARIO: PRACTICANTE
# =========================================================

class PracticanteForm(forms.ModelForm):
    """
    Formulario para crear o editar un Practicante.

    Además de los campos del modelo Practicante, agrego campos del modelo User
    (nombre, apellido, correo) para poder editarlos en el mismo formulario.
    """

    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    email = forms.EmailField(label="Correo")

    class Meta:
        model = Practicante

        # Defino explícitamente los campos que quiero mostrar
        fields = [
            "rut",
            "fecha_nacimiento",
            "universidad",
            "carrera",
            "celular",
            "fecha_inicio_practica",
            "fecha_termino_practica",
            "horas_requeridas",
            "foto_perfil",
        ]

        # Uso inputs tipo date en el navegador
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "fecha_inicio_practica": forms.DateInput(attrs={"type": "date"}),
            "fecha_termino_practica": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_rut(self):
        """
        Valido que el RUT sea correcto:
        - Formato válido
        - DV correcto
        - Devuelvo el RUT formateado
        """
        rut_raw = self.cleaned_data.get("rut", "")
        rut_norm = _normalizar_rut(rut_raw)

        if len(rut_norm) < 2:
            raise forms.ValidationError("El RUT está incompleto.")

        numero = rut_norm[:-1]
        dv = rut_norm[-1]

        if not numero.isdigit():
            raise forms.ValidationError("El RUT debe contener solo números antes del DV.")

        if dv not in "0123456789K":
            raise forms.ValidationError("El dígito verificador es inválido.")

        dv_calculado = _dv_rut(int(numero))

        if dv != dv_calculado:
            raise forms.ValidationError("El RUT no es válido.")

        return _formatear_rut(numero, dv)


# =========================================================
# FORMULARIO: REPORTE DE AVANCE
# =========================================================

class ReporteAvanceForm(forms.ModelForm):
    """
    Formulario para registrar un reporte de avance de un proyecto.

    Incluyo un campo adicional "estado" que no pertenece al modelo,
    pero lo uso para actualizar el estado del proyecto desde la vista.
    """

    estado = forms.CharField(
        required=False,
        label="Nuevo estado del proyecto",
        widget=forms.TextInput(attrs={"placeholder": "Ej: Activo, Pausado, Terminado"}),
    )

    class Meta:
        model = ReporteAvance
        fields = ["fecha", "descripcion", "porcentaje_avance"]

        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_porcentaje_avance(self):
        """
        Valido que el porcentaje esté entre 0 y 100.
        """
        valor = self.cleaned_data.get("porcentaje_avance")

        if valor is None:
            raise forms.ValidationError("Debo indicar el porcentaje de avance.")

        try:
            valor_num = float(valor)
        except:
            raise forms.ValidationError("El porcentaje debe ser numérico.")

        if valor_num < 0 or valor_num > 100:
            raise forms.ValidationError("El porcentaje debe estar entre 0 y 100.")

        return valor


# =========================================================
# FORMULARIOS DE PROYECTO
# =========================================================

class ProyectoImagenForm(forms.ModelForm):
    """
    Formulario para actualizar solo la imagen de un proyecto.
    """

    class Meta:
        model = Proyecto
        fields = ["imagen"]


class ProyectoForm(forms.ModelForm):
    """
    Formulario principal para crear o editar un proyecto.
    """

    class Meta:
        model = Proyecto
        fields = [
            "nombre",
            "descripcion",
            "numero_celula",
            "fecha_inicio",
            "fecha_termino",
            "estado",
            "porcentaje_avance",
            "imagen",
        ]

        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_termino": forms.DateInput(attrs={"type": "date"}),
        }


# =========================================================
# FORMULARIOS DE ADMIN PARA USUARIOS
# =========================================================

class AdminCrearPracticanteUserForm(UserCreationForm):
    """
    Formulario para que el admin cree un usuario.
    """

    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "password1", "password2"]
        labels = {"username": "Usuario"}


class AdminEditarUsuarioForm(forms.ModelForm):
    """
    Formulario para editar un usuario existente.

    Permite cambiar la contraseña solo si se escribe una nueva.
    """

    password = forms.CharField(
        label="Contraseña (opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Dejar vacío para no cambiarla"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "password"]

    def save(self, commit=True):
        user = super().save(commit=False)

        nueva_password = self.cleaned_data.get("password")
        if nueva_password:
            user.set_password(nueva_password)

        if commit:
            user.save()

        return user