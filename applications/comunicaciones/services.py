"""
Sincronización local de mensajes de Gmail con el modelo Comunicacion.

FUNCIONES PRINCIPALES
---------------------
1. Sincronizar mensajes de Gmail.
2. Registrar entradas y salidas.
3. Radicar automáticamente las entradas.
4. Delegar automáticamente según las reglas activas.
5. Actualizar la delegación si cambia una regla.
6. Generar PDF para entradas.
7. Generar consecutivo para salidas.
8. Generar PDF para salidas.
"""

import base64
import re
import unicodedata

from email.header import decode_header
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Comunicacion, Historial, Regla
from .pdf_service import generar_pdf


# ==========================================================
# GMAIL
# ==========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


class GmailSyncError(Exception):
    """
    Error controlado para mostrar mensajes claros
    en la interfaz de Django.
    """
    pass


# ==========================================================
# SERVICIO GMAIL
# ==========================================================

def _servicio_gmail():
    """
    Crea y devuelve el servicio autenticado de Gmail.
    """

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

    except ImportError as error:

        raise GmailSyncError(
            "Faltan dependencias de Gmail. "
            "Instale las dependencias de requirements.txt."
        ) from error

    token = settings.GMAIL_TOKEN_FILE
    credentials_file = settings.GMAIL_CREDENTIALS_FILE

    credentials = None

    # ------------------------------------------------------
    # Cargar token existente
    # ------------------------------------------------------

    if token.exists():

        try:

            credentials = Credentials.from_authorized_user_file(
                token,
                SCOPES
            )

        except Exception:

            credentials = None

    # ------------------------------------------------------
    # Renovar token
    # ------------------------------------------------------

    if credentials and credentials.expired and credentials.refresh_token:

        try:

            credentials.refresh(Request())

        except Exception:

            credentials = None

    # ------------------------------------------------------
    # Solicitar autorización si no existe
    # ------------------------------------------------------

    if not credentials or not credentials.valid:

        if not credentials_file.exists():

            raise GmailSyncError(
                "Falta config/google_client_secret.json. "
                "Descargue el cliente OAuth de Google Cloud "
                "y guárdelo allí."
            )

        try:

            credentials = (
                InstalledAppFlow
                .from_client_secrets_file(
                    credentials_file,
                    SCOPES
                )
                .run_local_server(port=0)
            )

        except Exception as error:

            raise GmailSyncError(
                f"No fue posible autenticar Gmail: {error}"
            ) from error

    # ------------------------------------------------------
    # Guardar token
    # ------------------------------------------------------

    token.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    token.write_text(
        credentials.to_json(),
        encoding="utf-8"
    )

    # ------------------------------------------------------
    # Crear servicio
    # ------------------------------------------------------

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )


# ==========================================================
# CABECERAS GMAIL
# ==========================================================

def _cabecera(headers, nombre):
    """
    Obtiene una cabecera de Gmail y la decodifica correctamente.
    """

    valor = next(
        (
            h.get("value", "")
            for h in headers
            if h.get("name", "").lower() == nombre.lower()
        ),
        ""
    )

    partes = decode_header(valor)

    resultado = []

    for fragmento, charset in partes:

        if isinstance(fragmento, bytes):

            resultado.append(
                fragmento.decode(
                    charset or "utf-8",
                    errors="replace"
                )
            )

        else:

            resultado.append(fragmento)

    return "".join(resultado)


# ==========================================================
# CUERPO DEL MENSAJE
# ==========================================================

def _cuerpo(payload):
    """
    Extrae el contenido texto/plain o text/html del correo.

    Devuelve:
        contenido
        tiene_adjuntos
    """

    partes = [payload]

    texto_plano = ""
    texto_html = ""

    tiene_adjuntos = False

    while partes:

        parte = partes.pop()

        # --------------------------------------------------
        # Adjuntos
        # --------------------------------------------------

        if parte.get("filename"):

            tiene_adjuntos = True

        # --------------------------------------------------
        # Subpartes
        # --------------------------------------------------

        partes.extend(
            parte.get("parts", [])
        )

        # --------------------------------------------------
        # Datos
        # --------------------------------------------------

        data = (
            parte
            .get("body", {})
            .get("data")
        )

        if not data:
            continue

        try:

            padding = "=" * (
                (-len(data)) % 4
            )

            contenido = (
                base64.urlsafe_b64decode(
                    data + padding
                )
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

        except Exception:

            continue

        mime_type = parte.get(
            "mimeType",
            ""
        )

        if mime_type == "text/plain":

            texto_plano += contenido

        elif mime_type == "text/html":

            texto_html += contenido

    return (
        texto_plano
        or texto_html
        or "(Mensaje sin contenido legible)"
    ), tiene_adjuntos


# ==========================================================
# GUARDAR MENSAJE
# ==========================================================

def _guardar_mensaje(servicio, resumen, tipo):
    """
    Descarga un mensaje de Gmail y lo guarda en Comunicacion.
    """

    mensaje = (
        servicio
        .users()
        .messages()
        .get(
            userId="me",
            id=resumen["id"],
            format="full",
        )
        .execute()
    )

    payload = mensaje.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    # ------------------------------------------------------
    # Fecha
    # ------------------------------------------------------

    fecha_texto = _cabecera(
        headers,
        "Date"
    )

    try:

        fecha = parsedate_to_datetime(
            fecha_texto
        )

    except Exception:

        fecha = timezone.now()

    if timezone.is_naive(fecha):

        fecha = timezone.make_aware(
            fecha
        )

    # ------------------------------------------------------
    # Cuerpo
    # ------------------------------------------------------

    cuerpo, tiene_adjuntos = _cuerpo(
        payload
    )

    # ------------------------------------------------------
    # Datos
    # ------------------------------------------------------

    datos = {

        "tipo": tipo,

        "fecha": fecha,

        "remitente": _cabecera(
            headers,
            "From"
        ),

        "destinatarios": _cabecera(
            headers,
            "To"
        ),

        "copia": _cabecera(
            headers,
            "Cc"
        ),

        "asunto": _cabecera(
            headers,
            "Subject"
        )[:500],

        "mensaje": cuerpo,

        "gmail_id": mensaje["id"],

        "thread_id": mensaje.get(
            "threadId",
            ""
        ),

        "tiene_adjuntos": tiene_adjuntos,

        "es_leido": (
            "UNREAD"
            not in mensaje.get(
                "labelIds",
                []
            )
        ),
    }

    objeto, creado = (
        Comunicacion.objects
        .update_or_create(
            gmail_id=mensaje["id"],
            defaults=datos,
        )
    )

    return objeto, creado


# ==========================================================
# MENSAJES DE GMAIL
# ==========================================================

def _mensajes(servicio, etiqueta):
    """
    Obtiene los mensajes de Gmail correspondientes
    al día actual.

    etiqueta:
        INBOX
        SENT
    """

    pagina = None

    hoy = timezone.localdate()

    fecha_gmail = hoy.strftime(
        "%Y/%m/%d"
    )

    while True:

        parametros = {
            "userId": "me",
            "labelIds": [etiqueta],
            "q": f"after:{fecha_gmail}",
            "maxResults": 100,
        }

        if pagina:

            parametros["pageToken"] = pagina

        respuesta = (
            servicio
            .users()
            .messages()
            .list(**parametros)
            .execute()
        )

        yield from respuesta.get(
            "messages",
            []
        )

        pagina = respuesta.get(
            "nextPageToken"
        )

        if not pagina:

            return


# ==========================================================
# NORMALIZAR TEXTO
# ==========================================================

def _normalizar(texto):
    """
    Normaliza texto para comparar reglas.

    Ejemplo:

        Seguridad
        SEGURIDAD
        seguridad
        seguridád

    terminan siendo comparables.
    """

    if not texto:

        return ""

    texto = str(texto)

    return "".join(
        caracter
        for caracter in unicodedata.normalize(
            "NFD",
            texto.casefold()
        )
        if unicodedata.category(caracter) != "Mn"
    )


# ==========================================================
# BUSCAR REGLA
# ==========================================================

def _buscar_regla(comunicacion):
    """
    Busca la primera regla activa que aparezca
    en asunto o cuerpo del mensaje.

    Las reglas vienen directamente de la BD.

    Ejemplo:

        red       -> Responsable 1
        soporte   -> Responsable 1
        seguridad -> Responsable 1
        web       -> Responsable 2
    """

    contenido = _normalizar(
        f"{comunicacion.asunto}\n"
        f"{comunicacion.mensaje}"
    )

    reglas = (
        Regla.objects
        .filter(activa=True)
        .select_related("responsable")
        .order_by("id")
    )

    for regla in reglas:

        responsable = regla.responsable

        if not responsable:
            continue

        if not responsable.activo:
            continue

        palabra = _normalizar(
            regla.palabra
        )

        if not palabra:
            continue

        # --------------------------------------------------
        # La palabra debe aparecer en el contenido.
        #
        # Se usa "in" y no igualdad porque:
        #
        # red
        #
        # también debe encontrar:
        #
        # redes
        # redacción sobre redes
        # Microsoft y sus redes
        # --------------------------------------------------

        if palabra in contenido:

            return regla

    return None


# ==========================================================
# RADICAR Y DELEGAR ENTRADA
# ==========================================================

def _radicar_si_aplica(comunicacion):
    """
    Radica y delega automáticamente una comunicación
    de entrada según las reglas activas.

    Retorna:
        True  -> se creó un nuevo radicado
        False -> ya existía o no aplicó ninguna regla
    """

    # ------------------------------------------------------
    # Solo ENTRADA
    # ------------------------------------------------------

    if comunicacion.tipo != "ENTRADA":

        return False

    print("\n========================================")
    print("PROCESANDO ENTRADA")
    print("ID:", comunicacion.id)
    print("ASUNTO:", comunicacion.asunto)
    print("RADICADO:", comunicacion.radicado)
    print("========================================")

    # ------------------------------------------------------
    # Buscar regla
    # ------------------------------------------------------

    regla = _buscar_regla(
        comunicacion
    )

    if not regla:

        print(
            "NO SE ENCONTRO REGLA ACTIVA"
        )

        return False

    responsable = regla.responsable

    print(
        "REGLA:",
        regla.palabra
    )

    print(
        "RESPONSABLE:",
        responsable.id,
        responsable.nombre,
        responsable.correo
    )

    # ------------------------------------------------------
    # Seguridad adicional
    # ------------------------------------------------------

    if not responsable.activo:

        print(
            "RESPONSABLE INACTIVO"
        )

        return False

    # ------------------------------------------------------
    # COMUNICACIÓN YA RADICADA
    # ------------------------------------------------------

    if comunicacion.radicado:

        cambios = []

        # --------------------------------------------------
        # Actualizar responsable si cambió la regla
        # --------------------------------------------------

        if (
            comunicacion.responsable_id
            != responsable.id
        ):

            comunicacion.responsable = (
                responsable
            )

            cambios.append(
                "responsable"
            )

        # --------------------------------------------------
        # Asegurar estado
        # --------------------------------------------------

        if comunicacion.estado != "DELEGADO":

            comunicacion.estado = (
                "DELEGADO"
            )

            cambios.append(
                "estado"
            )

        # --------------------------------------------------
        # Guardar palabra usada
        # --------------------------------------------------

        if comunicacion.etiqueta != regla.palabra:

            comunicacion.etiqueta = (
                regla.palabra
            )

            cambios.append(
                "etiqueta"
            )

        # --------------------------------------------------
        # Guardar cambios
        # --------------------------------------------------

        if cambios:

            cambios.append(
                "fecha_actualizacion"
            )

            comunicacion.save(
                update_fields=cambios
            )

            Historial.objects.create(
                comunicacion=comunicacion,
                accion=(
                    "Delegacion automatica "
                    "actualizada"
                ),
                descripcion=(
                    f"Regla: {regla.palabra} | "
                    f"Responsable: {responsable.nombre}"
                ),
            )

            print(
                "DELEGACION ACTUALIZADA"
            )

        else:

            print(
                "SIN CAMBIOS DE DELEGACION"
            )

        # --------------------------------------------------
        # PDF
        # --------------------------------------------------

        print(
            "GENERANDO PDF ENTRADA"
        )

        generar_pdf(
            comunicacion
        )

        return False

    # ======================================================
    # NUEVO RADICADO
    # ======================================================

    with transaction.atomic():

        anio = comunicacion.fecha.year

        # --------------------------------------------------
        # Bloqueo para evitar duplicados
        # --------------------------------------------------

        ultimo = (
            Comunicacion.objects
            .select_for_update()
            .filter(
                tipo="ENTRADA",
                radicado__isnull=False,
                fecha__year=anio,
            )
            .order_by("-id")
            .first()
        )

        if ultimo and ultimo.radicado:

            coincidencia = re.search(
                r"(\d{6})$",
                ultimo.radicado
            )

            if coincidencia:

                ultimo_numero = int(
                    coincidencia.group(1)
                )

            else:

                ultimo_numero = (
                    Comunicacion.objects
                    .filter(
                        tipo="ENTRADA",
                        radicado__isnull=False,
                        fecha__year=anio,
                    )
                    .count()
                )

        else:

            ultimo_numero = 0

        nuevo_numero = (
            ultimo_numero + 1
        )

        radicado = (
            f"RAD-{anio}-{nuevo_numero:06d}"
        )

        # --------------------------------------------------
        # Asignación automática
        # --------------------------------------------------

        comunicacion.radicado = (
            radicado
        )

        comunicacion.responsable = (
            responsable
        )

        comunicacion.estado = (
            "DELEGADO"
        )

        comunicacion.etiqueta = (
            regla.palabra
        )

        comunicacion.save(
            update_fields=[
                "radicado",
                "responsable",
                "estado",
                "etiqueta",
                "fecha_actualizacion",
            ]
        )

    # ------------------------------------------------------
    # Historial
    # ------------------------------------------------------

    Historial.objects.create(
        comunicacion=comunicacion,
        accion="Delegacion automatica",
        descripcion=(
            f"Regla: {regla.palabra} | "
            f"Responsable: {responsable.nombre}"
        ),
    )

    print(
        "RADICADO GENERADO:",
        radicado
    )

    # ------------------------------------------------------
    # PDF
    # ------------------------------------------------------

    print(
        "GENERANDO PDF ENTRADA"
    )

    generar_pdf(
        comunicacion
    )

    return True


# ==========================================================
# CONSECUTIVO SALIDA
# ==========================================================

def _generar_consecutivo_salida(comunicacion):
    """
    Genera el consecutivo para una comunicación de salida.

    Formato:

        N.1.014-0001-26

        N.1.014-0002-26
        N.1.014-0003-26
        ...
    """

    # ------------------------------------------------------
    # Solo SALIDA
    # ------------------------------------------------------

    if comunicacion.tipo != "SALIDA":

        return False

    # ------------------------------------------------------
    # Ya tiene consecutivo
    # ------------------------------------------------------

    if comunicacion.consecutivo:

        print(
            "SALIDA YA TIENE CONSECUTIVO:",
            comunicacion.consecutivo
        )

        # El PDF debe seguir generándose.
        generar_pdf(
            comunicacion
        )

        return False

    anio = comunicacion.fecha.year

    # ======================================================
    # Generar número
    # ======================================================

    with transaction.atomic():

        ultimo = (
            Comunicacion.objects
            .select_for_update()
            .filter(
                tipo="SALIDA",
                consecutivo__isnull=False,
                fecha__year=anio,
            )
            .order_by("-id")
            .first()
        )

        ultimo_numero = 0

        if ultimo and ultimo.consecutivo:

            coincidencia = re.search(
                r"N\.1\.014-(\d+)-\d{2}$",
                ultimo.consecutivo
            )

            if coincidencia:

                ultimo_numero = int(
                    coincidencia.group(1)
                )

        numero = (
            f"N.1.014-"
            f"{ultimo_numero + 1:04d}-"
            f"{str(anio)[2:]}"
        )

        comunicacion.consecutivo = (
            numero
        )

        comunicacion.save(
            update_fields=[
                "consecutivo",
                "fecha_actualizacion",
            ]
        )

    # ------------------------------------------------------
    # Historial
    # ------------------------------------------------------

    Historial.objects.create(
        comunicacion=comunicacion,
        accion="Consecutivo generado",
        descripcion=(
            f"Consecutivo asignado: {numero}"
        ),
    )

    print(
        "CONSECUTIVO GENERADO:",
        numero
    )

    # ------------------------------------------------------
    # PDF
    # ------------------------------------------------------

    print(
        "GENERANDO PDF SALIDA"
    )

    generar_pdf(
        comunicacion
    )

    return True


# ==========================================================
# SINCRONIZAR GMAIL
# ==========================================================

def sincronizar_gmail():
    """
    Sincroniza Gmail con la base de datos.

    ENTRADA:
        Gmail INBOX
        ↓
        Comunicacion
        ↓
        Buscar Regla
        ↓
        Responsable
        ↓
        Radicado
        ↓
        Historial
        ↓
        PDF

    SALIDA:
        Gmail SENT
        ↓
        Comunicacion
        ↓
        Consecutivo
        ↓
        Historial
        ↓
        PDF

    Retorna:

        creados,
        actualizados
    """

    print("\n")
    print("==========================================")
    print("INICIANDO SINCRONIZACION GMAIL")
    print("==========================================")

    servicio = _servicio_gmail()

    inicio_hoy = (
        timezone.localtime()
        .replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    creados = 0
    actualizados = 0

    # ======================================================
    # ENTRADAS Y SALIDAS
    # ======================================================

    for etiqueta, tipo in (
        ("INBOX", "ENTRADA"),
        ("SENT", "SALIDA"),
    ):

        print("\n")
        print("------------------------------------------")
        print(
            "PROCESANDO:",
            tipo
        )
        print("------------------------------------------")

        for resumen in _mensajes(
            servicio,
            etiqueta
        ):

            gmail_id = resumen["id"]

            # --------------------------------------------------
            # Buscar existente
            # --------------------------------------------------

            comunicacion = (
                Comunicacion.objects
                .filter(
                    gmail_id=gmail_id
                )
                .first()
            )

            # ==================================================
            # YA EXISTE
            # ==================================================

            if comunicacion:

                # ----------------------------------------------
                # Solo procesamos mensajes del día actual.
                # ----------------------------------------------

                if (
                    timezone.localtime(
                        comunicacion.fecha
                    )
                    < inicio_hoy
                ):

                    continue

                # ----------------------------------------------
                # ENTRADA
                # ----------------------------------------------

                if comunicacion.tipo == "ENTRADA":

                    _radicar_si_aplica(
                        comunicacion
                    )

                # ----------------------------------------------
                # SALIDA
                # ----------------------------------------------

                elif comunicacion.tipo == "SALIDA":

                    _generar_consecutivo_salida(
                        comunicacion
                    )

                actualizados += 1

                continue

            # ==================================================
            # NO EXISTE → CREAR
            # ==================================================

            comunicacion, creado = (
                _guardar_mensaje(
                    servicio,
                    resumen,
                    tipo
                )
            )

            # --------------------------------------------------
            # Validar fecha
            # --------------------------------------------------

            if (
                timezone.localtime(
                    comunicacion.fecha
                )
                < inicio_hoy
            ):

                continue

            # ==================================================
            # ENTRADA
            # ==================================================

            if comunicacion.tipo == "ENTRADA":

                _radicar_si_aplica(
                    comunicacion
                )

            # ==================================================
            # SALIDA
            # ==================================================

            elif comunicacion.tipo == "SALIDA":

                _generar_consecutivo_salida(
                    comunicacion
                )

            # --------------------------------------------------
            # Contadores
            # --------------------------------------------------

            if creado:

                creados += 1

            else:

                actualizados += 1

    # ======================================================
    # FINAL
    # ======================================================

    print("\n")
    print("==========================================")
    print("SINCRONIZACION TERMINADA")
    print("CREADOS:", creados)
    print("ACTUALIZADOS:", actualizados)
    print("==========================================")

    return creados, actualizados