from django import forms
from .models import Practicante
from .models import ReporteAvance
from .models import Proyecto

class PracticanteForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    email = forms.EmailField(label="Correo")

    class Meta:
        model = Practicante
        fields = [
            'rut',
            'fecha_nacimiento',
            'universidad',
            'carrera',
            'celular',
            'fecha_inicio_practica',
            'fecha_termino_practica',
            'horas_requeridas',
            'foto_perfil'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_inicio_practica': forms.DateInput(attrs={'type': 'date'}),
            'fecha_termino_practica': forms.DateInput(attrs={'type': 'date'}),
        }



class ReporteAvanceForm(forms.ModelForm):
    estado = forms.CharField(
        required=False,
        label="Nuevo estado del proyecto",
        widget=forms.TextInput(attrs={"placeholder": "Ej: Activo, Pausado, Terminado"})
    )

    class Meta:
        model = ReporteAvance
        fields = ["fecha", "descripcion", "porcentaje_avance"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

class ProyectoImagenForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ["imagen"]


class ProyectoForm(forms.ModelForm):
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