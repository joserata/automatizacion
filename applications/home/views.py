from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from applications.comunicaciones.forms import ReglaForm, ResponsableForm
from applications.comunicaciones.models import Comunicacion, Historial, Regla, Responsable
from applications.comunicaciones.services import GmailSyncError, sincronizar_gmail
from .dashboard import Dashboard
from applications.usuarios.decorators import grupo_requerido
from django.views.decorators.http import require_POST

from django.utils import timezone
from applications.comunicaciones.forms_consecutivo import ConsecutivoForm
from applications.comunicaciones.models import Consecutivo

from django.contrib import messages
from django.shortcuts import render, redirect

from datetime import datetime


@grupo_requerido(
    "Administrador",
    "Transaccion",
    "Operador",
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

    if request.user.groups.filter(name="Transaccion").exists():
        comunicaciones = comunicaciones.filter(
            historial__accion="Remitido a Transaccion"
        ).distinct()

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
def remitir_a_transaccion(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "mensaje": "Método no permitido."}, status=405)

    remitidos = request.POST.getlist("remitidos")
    procesados = []

    for valor in remitidos:
        try:
            comunicacion_id = int(valor)
        except (TypeError, ValueError):
            continue

        comunicacion = get_object_or_404(Comunicacion, pk=comunicacion_id)
        Historial.objects.create(
            comunicacion=comunicacion,
            usuario=request.user,
            accion="Remitido a Transaccion",
            descripcion="Remitido por administrador",
        )
        procesados.append(comunicacion.id)

    return JsonResponse({
        "ok": True,
        "mensaje": f"Se remitieron {len(procesados)} comunicaciones a Transacción.",
    })


@login_required
def asignar_responsables(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "mensaje": "Método no permitido."}, status=405)

    asignaciones = request.POST.getlist("asignaciones")
    procesados = []

    for valor in asignaciones:
        if ":" not in valor:
            continue

        comunicacion_id_raw, responsable_id_raw = valor.split(":", 1)
        try:
            comunicacion_id = int(comunicacion_id_raw)
            responsable_id = int(responsable_id_raw)
        except (TypeError, ValueError):
            continue

        comunicacion = get_object_or_404(Comunicacion, pk=comunicacion_id)
        responsable = get_object_or_404(Responsable, pk=responsable_id)

        comunicacion.responsable = responsable
        comunicacion.estado = "DELEGADO"
        comunicacion.save(update_fields=["responsable", "estado"])

        Historial.objects.create(
            comunicacion=comunicacion,
            usuario=request.user,
            accion="Delegado a responsable",
            descripcion=f"Delegado a {responsable.nombre}",
        )
        procesados.append(comunicacion.id)

    return JsonResponse({
        "ok": True,
        "mensaje": f"Se asignaron {len(procesados)} comunicaciones.",
    })


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



@require_POST
@grupo_requerido("Administrador")
def remitir_transaccion(request):

    ids = request.POST.getlist("ids[]")

    cantidad = (
        Comunicacion.objects
        .filter(
            id__in=ids,
            tipo="ENTRADA"
        )
        .update(
            remitido_transaccion=True,
            fecha_remision=timezone.now()
        )
    )

    return JsonResponse({
        "ok": True,
        "cantidad": cantidad
    })

@grupo_requerido("Transaccion")
def entrada_tran(request):

    comunicaciones = (
        Comunicacion.objects
        .filter(
            tipo="ENTRADA",
            remitido_transaccion=True
        )
        .select_related("responsable")
        .order_by("-fecha")
    )

    responsables = (
        Responsable.objects
        .filter(activo=True)
        .order_by("nombre")
    )

    return render(
        request,
        "home/entrada_tran.html",
        {
            "comunicaciones": comunicaciones,
            "responsables": responsables,
        }
    )

def nuevo_consecutivo(request):

    anio = datetime.now().year

    ultimo = (
        Consecutivo.objects
        .filter(fecha__year=anio)
        .order_by("-id")
        .first()
    )

    if ultimo:

        ultimo_consecutivo = ultimo.consecutivo

        siguiente = (
            f"N.1.014-{Consecutivo.objects.filter(fecha__year=anio).count()+1:04d}-{str(anio)[2:]}"
        )

    else:

        ultimo_consecutivo = "No existe"

        siguiente = f"N.1.014-0001-{str(anio)[2:]}"

    if request.method == "POST":

        form = ConsecutivoForm(request.POST)

        if form.is_valid():

            consecutivo = form.save(commit=False)
            consecutivo.usuario = request.user
            consecutivo.save()

            return redirect("home:consecutivo_nuevo")

    else:

        form = ConsecutivoForm()

    return render(
        request,
        "home/consecutivo_nuevo.html",
        {
            "form": form,
            "ultimo_consecutivo": ultimo_consecutivo,
            "siguiente_consecutivo": siguiente,
        },
    )