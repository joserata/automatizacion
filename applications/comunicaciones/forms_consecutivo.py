from django import forms

from .models import Consecutivo


class ConsecutivoForm(forms.ModelForm):

    class Meta:

        model = Consecutivo

        exclude = (
            "consecutivo",
            "usuario",
            "fecha_creacion",
            "fecha_actualizacion",
        )

        widgets = {

            "fecha": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "fecha_envio": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "dirigido_a": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "asunto": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "funcionario_responsable": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "caso_aranda": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "tipo_archivo": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "ubicacion": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "archivado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),

        }