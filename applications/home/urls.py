from django.urls import path
from . import views

app_name = "home"


urlpatterns = [

    # ======================================================
    # DASHBOARD
    # ======================================================

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # ======================================================
    # ENTRADAS
    # ======================================================

    path(
        "entrada/",
        views.entrada,
        name="entrada",
    ),

    # ======================================================
    # SALIDAS
    # ======================================================

    path(
        "salida/",
        views.salida,
        name="salida",
    ),

    # ======================================================
    # REPORTES
    # ======================================================

    path(
        "reportes/",
        views.reportes,
        name="reportes",
    ),

    # ======================================================
    # REGLAS
    # ======================================================

    path(
        "reglas/",
        views.reglas,
        name="reglas",
    ),

    path(
        "reglas/nueva/",
        views.editar_regla,
        name="nueva_regla",
    ),

    path(
        "reglas/<int:regla_id>/",
        views.editar_regla,
        name="editar_regla",
    ),

    # ======================================================
    # RESPONSABLES
    # ======================================================

    path(
        "responsables/nuevo/",
        views.editar_responsable,
        name="nuevo_responsable",
    ),

    path(
        "responsables/<int:responsable_id>/",
        views.editar_responsable,
        name="editar_responsable",
    ),

    # ======================================================
    # GMAIL
    # ======================================================

    path(
        "sincronizar-correo/",
        views.sincronizar_correo,
        name="sincronizar_correo",
    ),

    # ======================================================
    # DELEGACIÓN
    # ======================================================

    path(
        "remitir-a-transaccion/",
        views.remitir_a_transaccion,
        name="remitir_a_transaccion",
    ),

    path(
        "asignar-responsables/",
        views.asignar_responsables,
        name="asignar_responsables",
    ),

    # ======================================================
    # TRANSACCIÓN
    # ======================================================

    path(
        "remitir-transaccion/",
        views.remitir_transaccion,
        name="remitir_transaccion",
    ),

    path(
        "entrada-transaccion/",
        views.entrada_tran,
        name="entrada_tran",
    ),

    # ======================================================
    # CONSECUTIVOS
    # ======================================================

    path(
        "consecutivos/nuevo/",
        views.nuevo_consecutivo,
        name="consecutivo_nuevo",
    ),

    # ======================================================
# CONSULTA DE CONSECUTIVOS
# ======================================================

path(
    "consecutivos/",
    views.consulta_consecutivos,
    name="consulta_consecutivos",
),

# ======================================================
# CONSECUTIVOS - ADMINISTRADOR
# ======================================================

path(
    "consecutivos/admin/",
    views.consecutivos_admin,
    name="consecutivos_admin",
),
# ======================================================
# RADICADOS
# ======================================================

path(
    "consolidado-radicados/",
    views.consolidado_radicados,
    name="consolidado_radicados",
),

# ======================================================
# EXPORTACIONES EXCEL
# ======================================================

path(
    "reportes/exportar-radicados/",
    views.exportar_radicados_excel,
    name="exportar_radicados_excel",
),

path(
    "reportes/exportar-consecutivos/",
    views.exportar_consecutivos_excel,
    name="exportar_consecutivos_excel",
),
# ======================================================
# TABLERO DE CONTROL - CONSULTOR
# ======================================================
path(
    "tablero-control/",
    views.tablero_control,
    name="tablero_control",
),

]