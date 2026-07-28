from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .dashboard import Dashboard


@login_required
def dashboard(request):

    contexto = Dashboard.datos()

    return render(
        request,
        "home/dashboard.html",
        contexto
    )


@login_required
def entrada(request):

    return render(
        request,
        "home/entrada.html"
    )


@login_required
def salida(request):

    return render(
        request,
        "home/salida.html"
    )


@login_required
def reportes(request):

    return render(
        request,
        "home/reportes.html"
    )


@login_required
def reglas(request):

    return render(
        request,
        "home/reglas.html"
    )