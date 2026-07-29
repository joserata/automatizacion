from django import forms

from .models import Regla, Responsable


class ResponsableForm(forms.ModelForm):
    class Meta:
        model = Responsable
        fields = ("nombre", "correo", "cargo", "dependencia", "activo")
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "dependencia": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ReglaForm(forms.ModelForm):
    class Meta:
        model = Regla
        fields = ("palabra", "responsable", "activa")
        widgets = {
            "palabra": forms.TextInput(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
