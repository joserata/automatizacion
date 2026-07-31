from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import LoginForm


class UsuarioLogin(LoginView):

    template_name = "usuarios/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):

        usuario = self.request.user

        if usuario.groups.filter(name="Administrador").exists():
            return reverse_lazy("home:dashboard")

        elif usuario.groups.filter(name="Transaccion").exists():
            return reverse_lazy("home:entrada")

        elif usuario.groups.filter(name="Operador").exists():
            return reverse_lazy("home:salida")

        elif usuario.groups.filter(name="Consultor").exists():
            return reverse_lazy("home:dashboard")

        return reverse_lazy("home:dashboard")


class UsuarioLogout(LogoutView):

    next_page = "login"