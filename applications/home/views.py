from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from applications.comunicaciones.forms import (
    ReglaForm,
    ResponsableForm,
)
from applications.comunicaciones.forms_consecutivo import (
    ConsecutivoForm,
)
from applications.comunicaciones.models import (
    Comunicacion,
    Consecutivo,
    Historial,
    Regla,
    Responsable,
)
from applications.comunicaciones.services import (
    GmailSyncError,
    sincronizar_gmail,
)
from applications.usuarios.decorators import grupo_requerido

from .dashboard import Dashboard


# ==========================================================
# DASHBOARD
# ==========================================================

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


# ==========================================================
# ENTRADAS
# ==========================================================

@login_required
def entrada(request):

    comunicaciones = (
        Comunicacion.objects
        .filter(tipo="ENTRADA")
        .select_related("responsable")
        .order_by("-fecha")
    )

    # ======================================================
    # TRANSACCIÓN
    # ======================================================

    if request.user.groups.filter(name="Transaccion").exists():

        comunicaciones = comunicaciones.filter(
            remitido_transaccion=True
        )

    # ======================================================
    # OPERADOR
    # ======================================================

    elif request.user.groups.filter(name="Operador").exists():

        try:
            responsable = request.user.responsable
        except Responsable.DoesNotExist:
            responsable = None

        if responsable:
            comunicaciones = comunicaciones.filter(
                responsable=responsable
            )
        else:
            # Un operador sin Responsable asociado
            # no debe visualizar comunicaciones.
            comunicaciones = comunicaciones.none()

    # ======================================================
    # CONSULTOR
    # ======================================================

    elif request.user.groups.filter(name="Consultor").exists():

        # Por ahora puede consultar las entradas.
        pass

    # ======================================================
    # ADMINISTRADOR
    # ======================================================
    # El administrador puede ver todas las comunicaciones.

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
        },
    )


# ==========================================================
# SALIDAS
# ==========================================================

@login_required
def salida(request):

    comunicaciones = (
        Comunicacion.objects
        .filter(tipo="SALIDA")
        .order_by("-fecha")
    )

    return render(
        request,
        "home/salida.html",
        {
            "comunicaciones": comunicaciones,
        },
    )


# ==========================================================
# SINCRONIZAR GMAIL
# ==========================================================

@login_required
def sincronizar_correo(request):

    if request.method != "POST":
        return redirect("home:dashboard")

    try:
        creados, actualizados = sincronizar_gmail()

    except GmailSyncError as error:

        messages.error(
            request,
            str(error),
        )

    else:

        messages.success(
            request,
            (
                f"Sincronización terminada: "
                f"{creados} nuevos y "
                f"{actualizados} actualizados."
            ),
        )

    return redirect(
        request.POST.get("next") or "home:dashboard"
    )


# ==========================================================
# REMITIR A TRANSACCIÓN
# ==========================================================

@login_required
def remitir_a_transaccion(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Método no permitido.",
            },
            status=405,
        )

    remitidos = request.POST.getlist("remitidos")

    procesados = []

    for valor in remitidos:

        try:
            comunicacion_id = int(valor)

        except (TypeError, ValueError):
            continue

        comunicacion = get_object_or_404(
            Comunicacion,
            pk=comunicacion_id,
        )

        Historial.objects.create(
            comunicacion=comunicacion,
            usuario=request.user,
            accion="Remitido a Transaccion",
            descripcion="Remitido por administrador",
        )

        procesados.append(
            comunicacion.id
        )

    return JsonResponse(
        {
            "ok": True,
            "mensaje": (
                f"Se remitieron "
                f"{len(procesados)} "
                f"comunicaciones a Transacción."
            ),
        }
    )


# ==========================================================
# ASIGNAR RESPONSABLES
# ==========================================================

@login_required
def asignar_responsables(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Método no permitido.",
            },
            status=405,
        )

    asignaciones = request.POST.getlist(
        "asignaciones"
    )

    procesados = []

    for valor in asignaciones:

        if ":" not in valor:
            continue

        comunicacion_id_raw, responsable_id_raw = (
            valor.split(":", 1)
        )

        try:
            comunicacion_id = int(
                comunicacion_id_raw
            )

            responsable_id = int(
                responsable_id_raw
            )

        except (TypeError, ValueError):
            continue

        comunicacion = get_object_or_404(
            Comunicacion,
            pk=comunicacion_id,
        )

        responsable = get_object_or_404(
            Responsable,
            pk=responsable_id,
        )

        comunicacion.responsable = responsable
        comunicacion.estado = "DELEGADO"

        comunicacion.save(
            update_fields=[
                "responsable",
                "estado",
            ]
        )

        Historial.objects.create(
            comunicacion=comunicacion,
            usuario=request.user,
            accion="Delegado a responsable",
            descripcion=(
                f"Delegado a "
                f"{responsable.nombre}"
            ),
        )

        procesados.append(
            comunicacion.id
        )

    return JsonResponse(
        {
            "ok": True,
            "mensaje": (
                f"Se asignaron "
                f"{len(procesados)} "
                f"comunicaciones."
            ),
        }
    )


# ==========================================================
# REPORTES
# ==========================================================

@login_required
def reportes(request):

    return render(
        request,
        "home/reportes.html",
    )


# ==========================================================
# REGLAS
# ==========================================================

@login_required
def reglas(request):

    reglas = (
        Regla.objects
        .select_related("responsable")
        .order_by("palabra")
    )

    return render(
        request,
        "home/reglas.html",
        {
            "reglas": reglas,
        },
    )


# ==========================================================
# EDITAR / CREAR REGLA
# ==========================================================

@login_required
def editar_regla(request, regla_id=None):

    regla = (
        get_object_or_404(Regla, pk=regla_id)
        if regla_id
        else None
    )

    form = ReglaForm(
        request.POST or None,
        instance=regla
    )

    if request.method == "POST" and form.is_valid():

        regla_guardada = form.save()

        messages.success(
            request,
            "Regla guardada correctamente."
        )

        return redirect("home:reglas")

    return render(
        request,
        "home/formulario.html",
        {
            "form": form,
            "titulo": "Regla de delegación",
        }
    )
# ==========================================================
# EDITAR / CREAR RESPONSABLE
# ==========================================================

@login_required
def editar_responsable(
    request,
    responsable_id=None,
):

    responsable = (
        get_object_or_404(
            Responsable,
            pk=responsable_id,
        )
        if responsable_id
        else None
    )

    form = ResponsableForm(
        request.POST or None,
        instance=responsable,
    )

    if request.method == "POST" and form.is_valid():

        responsable_guardado = form.save()

        messages.success(
            request,
            (
                f"Responsable "
                f"{responsable_guardado.nombre} "
                "guardado correctamente."
            ),
        )

        return redirect(
            "home:reglas"
        )

    return render(
        request,
        "home/formulario.html",
        {
            "form": form,
            "titulo": "Responsable",
        },
    )


# ==========================================================
# REMITIR COMUNICACIONES A TRANSACCIÓN
# ==========================================================

@require_POST
@grupo_requerido("Administrador")
def remitir_transaccion(request):

    ids = request.POST.getlist(
        "ids[]"
    )

    cantidad = (
        Comunicacion.objects
        .filter(
            id__in=ids,
            tipo="ENTRADA",
        )
        .update(
            remitido_transaccion=True,
            fecha_remision=timezone.now(),
        )
    )

    return JsonResponse(
        {
            "ok": True,
            "cantidad": cantidad,
        }
    )


# ==========================================================
# ENTRADA DE TRANSACCIÓN
# ==========================================================

@grupo_requerido("Transaccion")
def entrada_tran(request):

    comunicaciones = (
        Comunicacion.objects
        .filter(
            tipo="ENTRADA",
            remitido_transaccion=True,
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
        },
    )


# ==========================================================
# NUEVO CONSECUTIVO
# ==========================================================

@login_required
def nuevo_consecutivo(request):

    anio = datetime.now().year

    ultimo = (
        Consecutivo.objects
        .filter(
            fecha__year=anio
        )
        .order_by("-id")
        .first()
    )

    if ultimo:

        ultimo_consecutivo = (
            ultimo.consecutivo
        )

        cantidad = (
            Consecutivo.objects
            .filter(
                fecha__year=anio
            )
            .count()
        )

        siguiente = (
            f"N.1.014-"
            f"{cantidad + 1:04d}-"
            f"{str(anio)[2:]}"
        )

    else:

        ultimo_consecutivo = (
            "No existe"
        )

        siguiente = (
            f"N.1.014-0001-"
            f"{str(anio)[2:]}"
        )

    if request.method == "POST":

        form = ConsecutivoForm(
            request.POST
        )

        if form.is_valid():

            consecutivo = form.save(
                commit=False
            )

            consecutivo.usuario = (
                request.user
            )

            consecutivo.save()

            messages.success(
                request,
                (
                    f"Consecutivo "
                    f"{consecutivo.consecutivo} "
                    "creado correctamente."
                ),
            )

            return redirect(
                "home:consecutivo_nuevo"
            )

    else:

        form = ConsecutivoForm()

    return render(
        request,
        "home/consecutivo_nuevo.html",
        {
            "form": form,
            "ultimo_consecutivo": (
                ultimo_consecutivo
            ),
            "siguiente_consecutivo": (
                siguiente
            ),
        },
    )