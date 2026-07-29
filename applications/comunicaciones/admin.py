from django.contrib import admin
from .models import Adjunto, Comunicacion, Consecutivo, Historial, Regla, Responsable

admin.site.register(Responsable)
admin.site.register(Regla)
admin.site.register(Comunicacion)
admin.site.register(Adjunto)
admin.site.register(Historial)
admin.site.register(Consecutivo)