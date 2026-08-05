from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applications.comunicaciones.models import Comunicacion, Historial, Responsable


class RolDeComunicacionesTest(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Administrador")
        self.transaccion_group = Group.objects.create(name="Transaccion")
        self.operador_group = Group.objects.create(name="Operador")

        self.admin_user = User.objects.create_user(username="admin1", password="123456", email="admin@test.com")
        self.transaccion_user = User.objects.create_user(username="trans1", password="123456", email="transaccion@test.com")
        self.operador_user = User.objects.create_user(username="oper1", password="123456", email="funcionario@test.com")

        self.admin_user.groups.add(self.admin_group)
        self.transaccion_user.groups.add(self.transaccion_group)
        self.operador_user.groups.add(self.operador_group)

        self.responsable = Responsable.objects.create(
            nombre="Funcionario",
            correo=self.operador_user.email,
            cargo="Analista",
            dependencia="Transacción",
            activo=True,
        )

        self.comunicacion_admin = Comunicacion.objects.create(
            tipo="ENTRADA",
            fecha=timezone.now(),
            remitente="origen@test.com",
            asunto="Asunto de prueba",
            mensaje="Mensaje de prueba",
            destinatarios="destino@test.com",
        )

        self.comunicacion_remitida = Comunicacion.objects.create(
            tipo="ENTRADA",
            fecha=timezone.now(),
            remitente="origen2@test.com",
            asunto="Asunto remitido",
            mensaje="Mensaje remitido",
            destinatarios="destino@test.com",
        )

        self.comunicacion_delegada = Comunicacion.objects.create(
            tipo="SALIDA",
            fecha=timezone.now(),
            remitente="origen3@test.com",
            asunto="Asunto delegado",
            mensaje="Mensaje delegado",
            destinatarios="destino@test.com",
            responsable=self.responsable,
            estado="DELEGADO",
        )

        Historial.objects.create(
            comunicacion=self.comunicacion_remitida,
            usuario=self.admin_user,
            accion="Remitido a Transaccion",
            descripcion="Remitido por administrador",
        )

    def test_admin_puede_remitir_comunicaciones_a_transaccion(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("home:remitir_a_transaccion"),
            {"remitidos": [str(self.comunicacion_remitida.id)]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Historial.objects.filter(
            comunicacion=self.comunicacion_remitida,
            accion="Remitido a Transaccion",
        ).exists())

    def test_transaccion_ve_solo_los_correos_remitidos_por_admin(self):
        self.client.force_login(self.transaccion_user)
        response = self.client.get(reverse("home:entrada"))

        self.assertEqual(response.status_code, 200)
        comunicaciones = list(response.context["comunicaciones"])
        self.assertEqual(len(comunicaciones), 1)
        self.assertEqual(comunicaciones[0].id, self.comunicacion_remitida.id)

    def test_admin_ve_toda_la_sincronizacion_de_entradas_y_salidas(self):
        self.client.force_login(self.admin_user)

        entrada_response = self.client.get(reverse("home:entrada"))
        salida_response = self.client.get(reverse("home:salida"))

        self.assertEqual(entrada_response.status_code, 200)
        self.assertEqual(salida_response.status_code, 200)
        self.assertEqual(len(list(entrada_response.context["comunicaciones"])), 2)
        self.assertEqual(len(list(salida_response.context["comunicaciones"])), 1)

    def test_operador_ve_solo_los_correos_delegados_a_su_correo(self):
        self.client.force_login(self.operador_user)
        response = self.client.get(reverse("home:salida"))

        self.assertEqual(response.status_code, 200)
        comunicaciones = list(response.context["comunicaciones"])
        self.assertEqual(len(comunicaciones), 1)
        self.assertEqual(comunicaciones[0].id, self.comunicacion_delegada.id)
