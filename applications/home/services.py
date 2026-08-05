from applications.comunicaciones.models import Comunicacion


class DashboardService:
    @staticmethod
    def obtener_indicadores():
        comunicaciones = Comunicacion.objects.all()
        return {
            "entrantes": comunicaciones.filter(tipo="ENTRADA").count(),
            "salientes": comunicaciones.filter(tipo="SALIDA").count(),
            "radicados": comunicaciones.exclude(radicado__isnull=True).exclude(radicado="").count(),
            "pendientes": comunicaciones.exclude(estado="FINALIZADO").count(),
            "delegados": comunicaciones.filter(estado="DELEGADO").count(),
            "en_proceso": comunicaciones.filter(estado="EN_PROCESO").count(),
            "finalizados": comunicaciones.filter(estado="FINALIZADO").count(),
        }