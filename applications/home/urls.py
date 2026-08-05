from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("entrada/", views.entrada, name="entrada"),
    path("salida/", views.salida, name="salida"),
    path("reportes/", views.reportes, name="reportes"),
    path("reglas/", views.reglas, name="reglas"),
    path("reglas/nueva/", views.editar_regla, name="nueva_regla"),
    path("reglas/<int:regla_id>/", views.editar_regla, name="editar_regla"),
    path("responsables/nuevo/", views.editar_responsable, name="nuevo_responsable"),
    path("responsables/<int:responsable_id>/", views.editar_responsable, name="editar_responsable"),
    path("sincronizar-correo/", views.sincronizar_correo, name="sincronizar_correo"),
    path("remitir-a-transaccion/", views.remitir_a_transaccion, name="remitir_a_transaccion"),
    path("asignar-responsables/", views.asignar_responsables, name="asignar_responsables"),
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
    path(
    "consecutivos/nuevo/",
    views.nuevo_consecutivo,
    name="consecutivo_nuevo",
),
]