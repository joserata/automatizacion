from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import LoginForm


class UsuarioLogin(LoginView):

    template_name = "usuarios/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UsuarioLogout(LogoutView):

    next_page = reverse_lazy("login")