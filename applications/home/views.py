from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
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


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from applications.comunicaciones.models import Consecutivo
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from applications.comunicaciones.forms_consecutivo import ConsecutivoForm

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
        .select_related("responsable", "usuario")
        .order_by("-fecha")
    )

    # ======================================================
    # ADMINISTRADOR
    # ======================================================
    # Ve absolutamente todas las entradas.
    if request.user.is_superuser or request.user.groups.filter(
        name="Administrador"
    ).exists():

        pass

    # ======================================================
    # TRANSACCION
    # ======================================================
    elif request.user.groups.filter(name="Transaccion").exists():

        comunicaciones = comunicaciones.filter(
            remitido_transaccion=True
        )

    # ======================================================
    # OPERADOR
    # ======================================================
    elif request.user.groups.filter(name="Operador").exists():

        responsable = (
            Responsable.objects
            .filter(
                usuario=request.user,
                activo=True
            )
            .first()
        )

        if responsable:
            comunicaciones = comunicaciones.filter(
                responsable=responsable,
                estado="DELEGADO"
            )
        else:
            comunicaciones = comunicaciones.none()

    # ======================================================
    # CONSULTOR
    # ======================================================
    elif request.user.groups.filter(name="Consultor").exists():

        # El consultor puede consultar las entradas.
        pass

    # ======================================================
    # CUALQUIER OTRO USUARIO
    # ======================================================
    else:

        comunicaciones = comunicaciones.none()

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
        .select_related("usuario")
        .order_by("-fecha")
    )

    # ======================================================
    # ADMINISTRADOR
    # ======================================================

    if request.user.is_superuser or request.user.groups.filter(
        name="Administrador"
    ).exists():

        # Administrador puede ver todas.
        pass

    # ======================================================
    # CUALQUIER OTRO USUARIO
    # ======================================================

    else:

        # Cada usuario solamente ve sus propias salidas.
        comunicaciones = comunicaciones.filter(
            usuario=request.user
        )

    return render(
        request,
        "home/salida.html",
        {
            "comunicaciones": comunicaciones,
        },
    )

    # ======================================================
    # ADMINISTRADOR
    # ======================================================
    if request.user.groups.filter(name="Administrador").exists():

        # El administrador puede ver todas.
        pass

    # ======================================================
    # DEMÁS USUARIOS
    # ======================================================
    else:

        comunicaciones = comunicaciones.filter(
            usuario=request.user
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

# ==========================================================
# NUEVO CONSECUTIVO
# ==========================================================

@login_required
def nuevo_consecutivo(request):

    anio = timezone.now().year

    # ======================================================
    # BUSCAR ÚLTIMO CONSECUTIVO DEL AÑO
    # ======================================================

    ultimo = (
        Consecutivo.objects
        .filter(fecha__year=anio)
        .order_by("-id")
        .first()
    )

    ultimo_numero = 0

    if ultimo and ultimo.consecutivo:

        try:
            partes = ultimo.consecutivo.split("-")

            # N.1.014-0003-26
            ultimo_numero = int(partes[1])

        except (ValueError, IndexError):
            ultimo_numero = 0

    # ======================================================
    # SIGUIENTE CONSECUTIVO
    # ======================================================

    siguiente_numero = ultimo_numero + 1

    siguiente_consecutivo = (
        f"N.1.014-"
        f"{siguiente_numero:04d}-"
        f"{str(anio)[2:]}"
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        form = ConsecutivoForm(request.POST)

        if form.is_valid():

            try:

                with transaction.atomic():

                    # Volvemos a consultar dentro de la
                    # transacción para evitar duplicados.

                    ultimo = (
                        Consecutivo.objects
                        .select_for_update()
                        .filter(fecha__year=anio)
                        .order_by("-id")
                        .first()
                    )

                    ultimo_numero = 0

                    if ultimo and ultimo.consecutivo:

                        try:

                            partes = ultimo.consecutivo.split("-")

                            ultimo_numero = int(partes[1])

                        except (ValueError, IndexError):

                            ultimo_numero = 0

                    # ======================================
                    # GENERAR CONSECUTIVO GLOBAL
                    # ======================================

                    siguiente_numero = ultimo_numero + 1

                    numero = (
                        f"N.1.014-"
                        f"{siguiente_numero:04d}-"
                        f"{str(anio)[2:]}"
                    )

                    # ======================================
                    # GUARDAR
                    # ======================================

                    consecutivo = form.save(commit=False)

                    consecutivo.consecutivo = numero
                    consecutivo.usuario = request.user

                    consecutivo.save()

                messages.success(
                    request,
                    f"Consecutivo {numero} generado correctamente."
                )

                return redirect("home:salida")

            except Exception as e:

                messages.error(
                    request,
                    f"No fue posible generar el consecutivo: {e}"
                )

    else:

        form = ConsecutivoForm()

    # ======================================================
    # MOSTRAR ÚLTIMO Y SIGUIENTE
    # ======================================================

    contexto = {
        "form": form,
        "titulo": "Nuevo consecutivo",
        "ultimo_consecutivo": (
            ultimo.consecutivo
            if ultimo
            else "No existen consecutivos"
        ),
        "siguiente_consecutivo": siguiente_consecutivo,
    }

    return render(
        request,
        "home/consecutivo_nuevo.html",
        contexto
    )

from django.core.exceptions import PermissionDenied    

# ==========================================================
# CONSULTA DE CONSECUTIVOS DEL USUARIO
# ==========================================================

@login_required
def consulta_consecutivos(request):

    consecutivos = (
        Consecutivo.objects
        .filter(usuario=request.user)
        .select_related("usuario")
        .order_by("-fecha_creacion", "-id")
    )

    return render(
        request,
        "home/consulta_consecutivos.html",
        {
            "consecutivos": consecutivos,
            "usuario_actual": request.user,
        },
    )


# ==========================================================
# CONSULTA DE CONSECUTIVOS - ADMINISTRADOR
# ==========================================================

@login_required
def consecutivos_admin(request):

    es_administrador = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    if not es_administrador:
        raise PermissionDenied(
            "No tiene permisos para consultar todos los consecutivos."
        )

    consecutivos = (
        Consecutivo.objects
        .select_related("usuario")
        .order_by("-fecha_creacion", "-id")
    )

    return render(
        request,
        "home/consecutivos_admin.html",
        {
            "consecutivos": consecutivos,
            "usuario_actual": request.user,
        },
    )
    

    
    