from django.urls import path

from .views import UsuarioLogin
from .views import UsuarioLogout

urlpatterns = [

    path(
        "login/",
        UsuarioLogin.as_view(),
        name="login"
    ),

    path(
        "logout/",
        UsuarioLogout.as_view(),
        name="logout"
    ),

]