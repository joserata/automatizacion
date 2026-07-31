from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def grupo_requerido(*grupos):

    def decorator(view):

        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):

            if request.user.is_superuser:
                return view(request, *args, **kwargs)

            if request.user.groups.filter(name__in=grupos).exists():
                return view(request, *args, **kwargs)

            return HttpResponseForbidden(
                "No tiene permisos para acceder a esta página."
            )

        return wrapper

    return decorator