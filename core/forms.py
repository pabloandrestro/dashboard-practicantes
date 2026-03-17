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

import re
import unicodedata

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils.html import strip_tags

from .models import Practicante, ReporteAvance, Proyecto

"""
REFACTOR/SEGURIDAD (2026-03-17):
- Se agregan validaciones y sanitización robusta contra datos basura / XSS.
- Nota: Django ORM ya protege contra SQL injection en consultas típicas, pero
  aquí protegemos principalmente:
  - inputs con HTML/script (XSS almacenado/reflejado)
  - caracteres de control invisibles
  - tamaños/largos excesivos
  - formatos inválidos (teléfono, username, etc.)
"""


# =========================================================
# HELPERS DE VALIDACIÓN / SANITIZACIÓN
# =========================================================

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MULTISPACE_RE = re.compile(r"\s+")
_SAFE_NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]{1,150}$")
_SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")


def _sanitize_text(value: str, *, max_len: int, allow_newlines: bool = True) -> str:
    """
    Sanitizo texto para evitar basura y XSS:
    - strip + colapso espacios
    - remuevo caracteres de control
    - elimino tags HTML (strip_tags)
    - limito longitud
    """
    value = (value or "").strip()
    # Remuevo control chars y normalizo unicode para evitar caracteres "raros"
    value = unicodedata.normalize("NFKC", value)
    value = _CONTROL_CHARS_RE.sub("", value)

    # Quito HTML (evita XSS almacenado si alguien intenta <script>...</script>)
    value = strip_tags(value)

    if not allow_newlines:
        value = value.replace("\r", " ").replace("\n", " ")

    # Colapso espacios para evitar textos con padding gigante
    value = _MULTISPACE_RE.sub(" ", value).strip()

    if len(value) > max_len:
        value = value[:max_len].strip()

    return value


def _validate_not_empty(value: str, message: str):
    if not value:
        raise forms.ValidationError(message)


def _validate_safe_name(value: str, field_label: str):
    if value and not _SAFE_NAME_RE.match(value):
        raise forms.ValidationError(f"{field_label} contiene caracteres inválidos.")


def _validate_phone(value: str):
    """
    Valido teléfono chileno/latam simple:
    - permite + al inicio
    - luego solo dígitos
    - largo razonable
    """
    if not value:
        return
    v = value.replace(" ", "")
    if v.startswith("+"):
        v_body = v[1:]
    else:
        v_body = v
    if not v_body.isdigit():
        raise forms.ValidationError("El celular solo puede contener números (y opcionalmente '+' al inicio).")
    if len(v) < 8 or len(v) > 16:
        raise forms.ValidationError("El celular tiene un largo inválido.")


def _validate_image_file(file):
    """
    Validación de archivo de imagen:
    - extensión permitida
    - tamaño máximo
    """
    if not file:
        return
    max_mb = 5
    if getattr(file, "size", 0) > max_mb * 1024 * 1024:
        raise forms.ValidationError(f"La imagen es demasiado grande (máx {max_mb}MB).")



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

    def clean_first_name(self):
        v = _sanitize_text(self.cleaned_data.get("first_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el nombre.")
        _validate_safe_name(v, "Nombre")
        return v

    def clean_last_name(self):
        v = _sanitize_text(self.cleaned_data.get("last_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el apellido.")
        _validate_safe_name(v, "Apellido")
        return v

    def clean_email(self):
        # EmailField ya valida formato; aquí solo limpio y limito.
        v = _sanitize_text(self.cleaned_data.get("email"), max_len=254, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el correo.")
        return v

    def clean_universidad(self):
        return _sanitize_text(self.cleaned_data.get("universidad"), max_len=255, allow_newlines=False)

    def clean_carrera(self):
        return _sanitize_text(self.cleaned_data.get("carrera"), max_len=255, allow_newlines=False)

    def clean_celular(self):
        v = _sanitize_text(self.cleaned_data.get("celular"), max_len=16, allow_newlines=False)
        _validate_phone(v)
        return v


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

    def clean_descripcion(self):
        v = _sanitize_text(self.cleaned_data.get("descripcion"), max_len=2000, allow_newlines=True)
        _validate_not_empty(v, "Debo indicar una descripción.")
        return v

    def clean_estado(self):
        # Campo "virtual" (no es del modelo), pero igual lo sanitizo.
        v = _sanitize_text(self.cleaned_data.get("estado"), max_len=50, allow_newlines=False)
        return v


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

    imagen = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )

    def clean_imagen(self):
        img = self.cleaned_data.get("imagen")
        _validate_image_file(img)
        return img


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

    imagen = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )

    def clean_nombre(self):
        v = _sanitize_text(self.cleaned_data.get("nombre"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el nombre del proyecto.")
        return v

    def clean_descripcion(self):
        v = _sanitize_text(self.cleaned_data.get("descripcion"), max_len=5000, allow_newlines=True)
        _validate_not_empty(v, "Debo indicar una descripción.")
        return v

    def clean_estado(self):
        v = _sanitize_text(self.cleaned_data.get("estado"), max_len=50, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el estado del proyecto.")
        return v

    def clean_numero_celula(self):
        n = self.cleaned_data.get("numero_celula")
        if n is None:
            raise forms.ValidationError("Debo indicar el número de célula.")
        if int(n) <= 0 or int(n) > 9999:
            raise forms.ValidationError("El número de célula es inválido.")
        return n

    def clean_porcentaje_avance(self):
        v = self.cleaned_data.get("porcentaje_avance")
        if v is None:
            return 0
        try:
            v_num = int(v)
        except:
            raise forms.ValidationError("El porcentaje de avance debe ser numérico.")
        if v_num < 0 or v_num > 100:
            raise forms.ValidationError("El porcentaje debe estar entre 0 y 100.")
        return v_num

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get("fecha_inicio")
        ter = cleaned.get("fecha_termino")
        if ini and ter and ter < ini:
            self.add_error("fecha_termino", "La fecha de término no puede ser anterior a la fecha de inicio.")
        return cleaned

    def clean_imagen(self):
        img = self.cleaned_data.get("imagen")
        _validate_image_file(img)
        return img


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

    def clean_username(self):
        v = _sanitize_text(self.cleaned_data.get("username"), max_len=30, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar un usuario.")
        if not _SAFE_USERNAME_RE.match(v):
            raise forms.ValidationError("El usuario debe tener 3-30 caracteres y solo usar letras, números, '.', '_' o '-'.")
        return v

    def clean_first_name(self):
        v = _sanitize_text(self.cleaned_data.get("first_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el nombre.")
        _validate_safe_name(v, "Nombre")
        return v

    def clean_last_name(self):
        v = _sanitize_text(self.cleaned_data.get("last_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el apellido.")
        _validate_safe_name(v, "Apellido")
        return v


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

    def clean_username(self):
        v = _sanitize_text(self.cleaned_data.get("username"), max_len=30, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar un usuario.")
        if not _SAFE_USERNAME_RE.match(v):
            raise forms.ValidationError("El usuario debe tener 3-30 caracteres y solo usar letras, números, '.', '_' o '-'.")
        return v

    def clean_first_name(self):
        v = _sanitize_text(self.cleaned_data.get("first_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el nombre.")
        _validate_safe_name(v, "Nombre")
        return v

    def clean_last_name(self):
        v = _sanitize_text(self.cleaned_data.get("last_name"), max_len=150, allow_newlines=False)
        _validate_not_empty(v, "Debo indicar el apellido.")
        _validate_safe_name(v, "Apellido")
        return v

    def save(self, commit=True):
        user = super().save(commit=False)

        nueva_password = self.cleaned_data.get("password")
        if nueva_password:
            user.set_password(nueva_password)

        if commit:
            user.save()

        return user


# =========================================================
# FORMULARIO: SUGERENCIAS
# =========================================================
class SugerenciaForm(forms.Form):
    """
    REFACTOR/SEGURIDAD (2026-03-17):
    Este form valida el input de sugerencias para evitar XSS/datos basura.
    La identidad del usuario (username/nombre/email) se toma desde `request.user`
    en la vista; no se confía en lo que venga por POST para esos campos.
    """

    sugerencias = forms.CharField(
        label="Sugerencias",
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=2000,
        required=True,
    )

    def clean_sugerencias(self):
        v = _sanitize_text(self.cleaned_data.get("sugerencias"), max_len=2000, allow_newlines=True)
        _validate_not_empty(v, "Por favor escribe tu sugerencia antes de enviar.")
        if len(v) < 3:
            raise forms.ValidationError("La sugerencia es demasiado corta.")
        return v