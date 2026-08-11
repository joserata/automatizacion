from django import forms

from .models import Regla, Responsable


# ==========================================================
# RESPONSABLE
# ==========================================================

class ResponsableForm(forms.ModelForm):

    class Meta:
        model = Responsable

        fields = (
            "nombre",
            "correo",
            "cargo",
            "dependencia",
            "activo",
        )

        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "correo": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "cargo": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "dependencia": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


# ==========================================================
# REGLA
# ==========================================================

class ReglaForm(forms.ModelForm):

    class Meta:
        model = Regla

        fields = (
            "palabra",
            "responsable",
            "activa",
        )

        widgets = {
            "palabra": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: redes",
                }
            ),

            "responsable": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "activa": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["responsable"].queryset = (
            Responsable.objects
            .filter(activo=True)
            .order_by("nombre", "correo")
        )

        self.fields["responsable"].label_from_instance = (
            lambda responsable:
            f"{responsable.nombre} - {responsable.correo}"
        )