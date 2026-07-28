from .services import DashboardService


class Dashboard:

    @staticmethod
    def datos():

        return DashboardService.obtener_indicadores()