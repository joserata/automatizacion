from django.contrib.auth.models import Group


def grupos(request):

    if not request.user.is_authenticated:
        return {}

    grupos = list(request.user.groups.values_list("name", flat=True))

    return {
        "es_administrador": request.user.is_superuser or "Administrador" in grupos,
        "es_transaccion": "Transaccion" in grupos,
        "es_operador": "Operador" in grupos,
        "es_consultor": "Consultor" in grupos,
    }