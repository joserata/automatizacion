from django.core.management.base import BaseCommand, CommandError

from applications.comunicaciones.services import GmailSyncError, sincronizar_gmail


class Command(BaseCommand):
    help = "Importa correos entrantes y salientes desde Gmail."

    def handle(self, *args, **options):
        try:
            creados, actualizados = sincronizar_gmail()
        except GmailSyncError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Gmail sincronizado: {creados} nuevos, {actualizados} actualizados."))
