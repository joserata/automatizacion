from django.urls import path

from . import views

app_name = "home"

urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "entrada/",
        views.entrada,
        name="entrada"
    ),

    path(
        "salida/",
        views.salida,
        name="salida"
    ),

    path(
        "reportes/",
        views.reportes,
        name="reportes"
    ),

    path(
        "reglas/",
        views.reglas,
        name="reglas"
    ),

]