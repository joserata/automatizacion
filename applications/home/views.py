from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from applications.comunicaciones.forms import ReglaForm, ResponsableForm
from applications.comunicaciones.models import Comunicacion, Regla, Responsable
from applications.comunicaciones.services import GmailSyncError, sincronizar_gmail
from .dashboard import Dashboard
from applications.usuarios.decorators import grupo_requerido

@grupo_requerido(
    "Administrador",
    "Transaccion",
    "Consultor",
)
def dashboard(request):
    return render(
        request,
        "home/dashboard.html",
        Dashboard.datos(),
    )


@login_required
def entrada(request):

    comunicaciones = (
        Comunicacion.objects
        .filter(tipo="ENTRADA")
        .select_related("responsable")
    )

    responsables = (
        Responsable.objects
        .filter(activo=True)
        .order_by("nombre")
    )

    return render(

        request,

        "home/entrada.html",

        {

            "comunicaciones": comunicaciones,

            "responsables": responsables,

        }

    )


@login_required
def salida(request):
    comunicaciones = Comunicacion.objects.filter(tipo="SALIDA")
    return render(request, "home/salida.html", {"comunicaciones": comunicaciones})


@login_required
def sincronizar_correo(request):
    if request.method != "POST":
        return redirect("home:dashboard")
    try:
        creados, actualizados = sincronizar_gmail()
    except GmailSyncError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Sincronizacion terminada: {creados} nuevos y {actualizados} actualizados.")
    return redirect(request.POST.get("next") or "home:dashboard")


@login_required
def reportes(request):
    return render(request, "home/reportes.html")


@login_required
def reglas(request):
    return render(request, "home/reglas.html", {"reglas": Regla.objects.select_related("responsable").all()})


@login_required
def editar_regla(request, regla_id=None):
    regla = get_object_or_404(Regla, pk=regla_id) if regla_id else None
    form = ReglaForm(request.POST or None, instance=regla)
    if request.method == "POST" and form.is_valid():
        regla_guardada = form.save(commit=False)
        # Cada palabra debe conservar su propio responsable, aunque inicialmente
        # se haya seleccionado uno usado por otra regla.
        if Regla.objects.exclude(pk=regla_guardada.pk).filter(responsable=regla_guardada.responsable).exists():
            responsable = regla_guardada.responsable
            responsable.pk = None
            responsable.save()
            regla_guardada.responsable = responsable
        regla_guardada.save()
        messages.success(request, "Regla guardada. Se aplicara en la proxima sincronizacion.")
        return redirect("home:reglas")
    return render(request, "home/formulario.html", {"form": form, "titulo": "Regla de delegacion"})


@login_required
def editar_responsable(request, responsable_id=None):
    responsable = get_object_or_404(Responsable, pk=responsable_id) if responsable_id else None
    form = ResponsableForm(request.POST or None, instance=responsable)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Responsable guardado.")
        return redirect("home:reglas")
    return render(request, "home/formulario.html", {"form": form, "titulo": "Responsable"})