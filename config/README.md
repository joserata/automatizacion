# Configuración de Gmail

1. En Google Cloud, cree o seleccione un proyecto y habilite **Gmail API**.
2. Configure la pantalla de consentimiento OAuth y cree una credencial de tipo **Aplicación de escritorio**.
3. Descargue el JSON y guárdelo como `google_client_secret.json` en esta carpeta.
4. Ejecute `python manage.py sincronizar_gmail` o pulse **Sincronizar Gmail** desde la aplicación.
5. Autorice la cuenta `js.caballero1@gmail.com` en el navegador. Se creará aquí `google_token.json` para las siguientes sincronizaciones.

Los dos JSON contienen secretos o permisos de acceso, por lo que están excluidos de Git.
