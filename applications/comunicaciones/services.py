"""Sincronizacion local de mensajes de Gmail con el modelo Comunicacion."""

import base64
import unicodedata
from email.header import decode_header
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Comunicacion, Consecutivo, Historial, Regla
from .pdf_service import generar_pdf
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailSyncError(Exception):
    """Error explicable para la interfaz y los comandos de Django."""


def _servicio_gmail():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as error:
        raise GmailSyncError("Faltan dependencias de Gmail. Instale requirements.txt.") from error

    token = settings.GMAIL_TOKEN_FILE
    credentials_file = settings.GMAIL_CREDENTIALS_FILE
    credentials = Credentials.from_authorized_user_file(token, SCOPES) if token.exists() else None
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        if not credentials_file.exists():
            raise GmailSyncError(
                "Falta config/google_client_secret.json. Descargue el cliente OAuth de Google Cloud y guardelo alli."
            )
        credentials = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES).run_local_server(port=0)
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _cabecera(headers, nombre):
    valor = next((h["value"] for h in headers if h["name"].lower() == nombre.lower()), "")
    return "".join(
        fragment.decode(charset or "utf-8", errors="replace") if isinstance(fragment, bytes) else fragment
        for fragment, charset in decode_header(valor)
    )


def _cuerpo(payload):
    partes = [payload]
    texto_plano = ""
    texto_html = ""
    tiene_adjuntos = False
    while partes:
        parte = partes.pop()
        if parte.get("filename"):
            tiene_adjuntos = True
        partes.extend(parte.get("parts", []))
        data = parte.get("body", {}).get("data")
        if not data:
            continue
        contenido = base64.urlsafe_b64decode(data + "=").decode("utf-8", errors="replace")
        if parte.get("mimeType") == "text/plain":
            texto_plano += contenido
        elif parte.get("mimeType") == "text/html":
            texto_html += contenido
    return texto_plano or texto_html or "(Mensaje sin contenido legible)", tiene_adjuntos


def _guardar_mensaje(servicio, resumen, tipo):
    """
    Descarga un mensaje de Gmail y lo guarda en la base de datos.
    """

    mensaje = (
        servicio.users()
        .messages()
        .get(
            userId="me",
            id=resumen["id"],
            format="full",
        )
        .execute()
    )

    payload = mensaje.get("payload", {})
    headers = payload.get("headers", [])

    fecha = parsedate_to_datetime(
        _cabecera(headers, "Date")
    )

    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)

    cuerpo, tiene_adjuntos = _cuerpo(payload)

    datos = {
        "tipo": tipo,
        "fecha": fecha,
        "remitente": _cabecera(headers, "From"),
        "destinatarios": _cabecera(headers, "To"),
        "copia": _cabecera(headers, "Cc"),
        "asunto": _cabecera(headers, "Subject")[:500],
        "mensaje": cuerpo,
        "gmail_id": mensaje["id"],
        "thread_id": mensaje.get("threadId", ""),
        "tiene_adjuntos": tiene_adjuntos,
        "es_leido": "UNREAD" not in mensaje.get("labelIds", []),
    }

    objeto, creado = Comunicacion.objects.update_or_create(
        gmail_id=mensaje["id"],
        defaults=datos,
    )

    return objeto, creado

def _mensajes(servicio, etiqueta):
    pagina = None
    while True:
        respuesta = servicio.users().messages().list(userId="me", labelIds=[etiqueta], q=f"after:{timezone.localdate().strftime('%Y/%m/%d')}", maxResults=100, pageToken=pagina).execute()
        yield from respuesta.get("messages", [])
        pagina = respuesta.get("nextPageToken")
        if not pagina:
            return



def _normalizar(texto):
    return "".join(
        caracter for caracter in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caracter) != "Mn"
    )


def _radicar_si_aplica(comunicacion):
    """Radica y delega un correo entrante segun la regla que coincida."""
    if comunicacion.tipo != "ENTRADA":
        return False
    contenido = _normalizar(f"{comunicacion.asunto}\n{comunicacion.mensaje}")
    regla = next(
        (regla for regla in Regla.objects.filter(activa=True).select_related("responsable")
         if _normalizar(regla.palabra) in contenido),
        None,
    )
    if not regla or not regla.responsable.activo:
        return False
    if comunicacion.radicado:
        if comunicacion.responsable_id != regla.responsable_id or comunicacion.estado != "DELEGADO":
            comunicacion.responsable = regla.responsable
            comunicacion.estado = "DELEGADO"
            comunicacion.etiqueta = regla.palabra
            comunicacion.save(update_fields=["responsable", "estado", "etiqueta", "fecha_actualizacion"])
            Historial.objects.create(
                comunicacion=comunicacion,
                accion="Delegacion automatica actualizada",
                descripcion=f"Regla: {regla.palabra}. Responsable: {regla.responsable.correo}.",
            )
            generar_pdf(comunicacion)
        return False
    with transaction.atomic():
        consecutivo, _ = Consecutivo.objects.select_for_update().get_or_create(anio=comunicacion.fecha.year)
        consecutivo.ultimo += 1
        consecutivo.save(update_fields=["ultimo"])
        numero = f"{consecutivo.anio}-{consecutivo.ultimo:06d}"

        comunicacion.radicado = numero
        comunicacion.responsable = regla.responsable
        comunicacion.estado = "DELEGADO"
        comunicacion.etiqueta = regla.palabra

        comunicacion.save(
            update_fields=[
                "radicado",
                "responsable",
                "estado",
                "etiqueta",
                "fecha_actualizacion",
            ]
        )
        

        generar_pdf(comunicacion)   

        Historial.objects.create(
            comunicacion=comunicacion,
            accion="Delegacion automatica",
            descripcion=f"Regla: {regla.palabra}. Responsable: {regla.responsable.correo}.",
        )
    # Generar evidencia PDF
        generar_pdf(comunicacion)    
        return True
def _generar_consecutivo_salida(comunicacion):
    """Genera el consecutivo para un correo de salida."""

    if comunicacion.tipo != "SALIDA":
        return False

    if comunicacion.consecutivo:
        generar_pdf(comunicacion)
        return False

    with transaction.atomic():
        consecutivo, _ = Consecutivo.objects.select_for_update().get_or_create(
            anio=comunicacion.fecha.year
        )

        consecutivo.ultimo += 1
        consecutivo.save(update_fields=["ultimo"])

        anio = str(consecutivo.anio)[2:]
        numero = f"N.1.014-{consecutivo.ultimo:04d}-{anio}"

        comunicacion.consecutivo = numero

        comunicacion.save(
            update_fields=[
                "consecutivo",
                "fecha_actualizacion",
            ]
        )
        

        generar_pdf(comunicacion)

        Historial.objects.create(
            comunicacion=comunicacion,
            accion="Consecutivo generado",
            descripcion=f"Consecutivo asignado: {numero}",
        )
        # Generar evidencia PDF
        generar_pdf(comunicacion)
        return True

def sincronizar_gmail():
    """
    Sincroniza los correos de Gmail y:
    - Radica automáticamente los correos de entrada.
    - Genera automáticamente el consecutivo para los correos de salida.
    """

    servicio = _servicio_gmail()

    inicio_hoy = timezone.localtime().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    creados = 0
    actualizados = 0

    for etiqueta, tipo in (
        ("INBOX", "ENTRADA"),
        ("SENT", "SALIDA"),
    ):

        for resumen in _mensajes(servicio, etiqueta):

            comunicacion = Comunicacion.objects.filter(
                gmail_id=resumen["id"]
            ).first()

            # ==========================
            # YA EXISTE EN LA BASE
            # ==========================
            if comunicacion:

                if timezone.localtime(comunicacion.fecha) < inicio_hoy:
                    comunicacion.delete()
                    continue

                if comunicacion.tipo == "ENTRADA":
                    _radicar_si_aplica(comunicacion)

                elif comunicacion.tipo == "SALIDA":
                    _generar_consecutivo_salida(comunicacion)

                actualizados += 1
                continue

            # ==========================
            # NO EXISTE → CREAR
            # ==========================

            comunicacion, creado = _guardar_mensaje(
                servicio,
                resumen,
                tipo,
            )

            if timezone.localtime(comunicacion.fecha) < inicio_hoy:
                comunicacion.delete()
                continue

            if comunicacion.tipo == "ENTRADA":
                _radicar_si_aplica(comunicacion)

            elif comunicacion.tipo == "SALIDA":
                _generar_consecutivo_salida(comunicacion)

            if creado:
                creados += 1
            else:
                actualizados += 1

    return creados, actualizados