from pathlib import Path

from django.conf import settings

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

NOMBRE_CARPETA_PRINCIPAL = "SGDEA-PRUEBAS"
NOMBRE_CARPETA_RADICADOS = "RADICADOS"
NOMBRE_CARPETA_CONSECUTIVOS = "CONSECUTIVOS"


# ==========================================================
# RUTAS
# ==========================================================

BASE_DIR = Path(settings.BASE_DIR)

CONFIG_DIR = BASE_DIR / "config"

CREDENTIALS_FILE = (
    CONFIG_DIR / "google_client_secret.json"
)

TOKEN_FILE = (
    CONFIG_DIR / "google_drive_token.json"
)


# ==========================================================
# AUTENTICACIÓN GOOGLE DRIVE
# ==========================================================

def obtener_servicio_drive():
    """
    Obtiene un servicio autenticado de Google Drive.

    Utiliza:

        config/google_client_secret.json

    y guarda el token en:

        config/google_drive_token.json
    """

    creds = None

    # ------------------------------------------------------
    # Cargar token existente
    # ------------------------------------------------------

    if TOKEN_FILE.exists():

        print(
            "Cargando token de Google Drive..."
        )

        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # ------------------------------------------------------
    # Verificar credenciales
    # ------------------------------------------------------

    if not creds or not creds.valid:

        # --------------------------------------------------
        # Renovar token
        # --------------------------------------------------

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            print(
                "Renovando token de Google Drive..."
            )

            creds.refresh(Request())

        # --------------------------------------------------
        # Primera autorización
        # --------------------------------------------------

        else:

            if not CREDENTIALS_FILE.exists():

                raise FileNotFoundError(
                    "No se encontró el archivo:\n"
                    f"{CREDENTIALS_FILE}"
                )

            print(
                "No existe autorización de Google Drive."
            )

            print(
                "Se abrirá el navegador para "
                "autorizar la cuenta."
            )

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(CREDENTIALS_FILE),
                    SCOPES,
                )
            )

            creds = flow.run_local_server(
                port=0
            )

        # --------------------------------------------------
        # Guardar token
        # --------------------------------------------------

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

        print(
            f"Token guardado en: {TOKEN_FILE}"
        )

    # ------------------------------------------------------
    # Crear servicio
    # ------------------------------------------------------

    servicio = build(
        "drive",
        "v3",
        credentials=creds,
    )

    print(
        "Google Drive conectado correctamente."
    )

    return servicio


# ==========================================================
# BUSCAR O CREAR CARPETA
# ==========================================================

def buscar_o_crear_carpeta(
    servicio,
    nombre,
    carpeta_padre_id=None,
):
    """
    Busca una carpeta dentro de Google Drive.

    Si no existe, la crea.

    Retorna el ID.
    """

    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{nombre}' "
        "and trashed=false"
    )

    if carpeta_padre_id:

        query += (
            f" and '{carpeta_padre_id}' in parents"
        )

    resultado = (
        servicio.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=100,
        )
        .execute()
    )

    archivos = resultado.get(
        "files",
        []
    )

    # ------------------------------------------------------
    # Ya existe
    # ------------------------------------------------------

    if archivos:

        print(
            f"Carpeta encontrada: {nombre}"
        )

        return archivos[0]["id"]

    # ------------------------------------------------------
    # Crear
    # ------------------------------------------------------

    metadata = {
        "name": nombre,
        "mimeType": (
            "application/vnd.google-apps.folder"
        ),
    }

    if carpeta_padre_id:

        metadata["parents"] = [
            carpeta_padre_id
        ]

    carpeta = (
        servicio.files()
        .create(
            body=metadata,
            fields="id,name",
        )
        .execute()
    )

    print(
        f"Carpeta creada: {nombre}"
    )

    print(
        f"ID: {carpeta['id']}"
    )

    return carpeta["id"]


# ==========================================================
# CREAR ESTRUCTURA SGDEA
# ==========================================================

def obtener_carpeta_sgdea():
    """
    Garantiza la existencia de:

        SGDEA-PRUEBAS/
            RADICADOS/
            CONSECUTIVOS/
    """

    servicio = obtener_servicio_drive()

    # ------------------------------------------------------
    # SGDEA-PRUEBAS
    # ------------------------------------------------------

    sgdea_id = buscar_o_crear_carpeta(
        servicio,
        NOMBRE_CARPETA_PRINCIPAL,
    )

    # ------------------------------------------------------
    # RADICADOS
    # ------------------------------------------------------

    radicados_id = buscar_o_crear_carpeta(
        servicio,
        NOMBRE_CARPETA_RADICADOS,
        sgdea_id,
    )

    # ------------------------------------------------------
    # CONSECUTIVOS
    # ------------------------------------------------------

    consecutivos_id = buscar_o_crear_carpeta(
        servicio,
        NOMBRE_CARPETA_CONSECUTIVOS,
        sgdea_id,
    )

    return {
        "servicio": servicio,
        "sgdea": sgdea_id,
        "radicados": radicados_id,
        "consecutivos": consecutivos_id,
    }


# ==========================================================
# BUSCAR PDF EXISTENTE
# ==========================================================

def buscar_pdf_existente(
    servicio,
    nombre,
    carpeta_id,
):
    """
    Busca un PDF por nombre dentro de una carpeta
    específica de Google Drive.

    Retorna:

        {
            "id": "...",
            "name": "...",
            "webViewLink": "..."
        }

    si existe.

    Retorna None si no existe.
    """

    # ------------------------------------------------------
    # Escapar comillas simples del nombre
    # ------------------------------------------------------

    nombre_busqueda = nombre.replace(
        "'",
        "\\'"
    )

    query = (
        "trashed=false "
        f"and name='{nombre_busqueda}' "
        f"and '{carpeta_id}' in parents"
    )

    resultado = (
        servicio.files()
        .list(
            q=query,
            spaces="drive",
            fields=(
                "files("
                "id,"
                "name,"
                "webViewLink,"
                "mimeType"
                ")"
            ),
            pageSize=100,
        )
        .execute()
    )

    archivos = resultado.get(
        "files",
        []
    )

    # ------------------------------------------------------
    # No existe
    # ------------------------------------------------------

    if not archivos:

        return None

    # ------------------------------------------------------
    # Buscar específicamente PDF
    # ------------------------------------------------------

    for archivo in archivos:

        if archivo.get("mimeType") == "application/pdf":

            print(
                "PDF existente encontrado en Google Drive:"
            )

            print(
                f"Nombre: {archivo.get('name')}"
            )

            print(
                f"ID: {archivo.get('id')}"
            )

            print(
                f"URL: {archivo.get('webViewLink')}"
            )

            return archivo

    return None


# ==========================================================
# SUBIR PDF A DRIVE
# ==========================================================

def subir_pdf_a_drive(
    archivo,
    tipo,
):
    """
    Sube un PDF a Google Drive.

    ENTRADA:
        SGDEA-PRUEBAS/RADICADOS

    SALIDA:
        SGDEA-PRUEBAS/CONSECUTIVOS

    IMPORTANTE:

    Si ya existe un PDF con el mismo nombre dentro
    de la carpeta correspondiente, NO se crea otro.

    En ese caso se devuelve el archivo existente.
    """

    # ======================================================
    # VALIDAR TIPO
    # ======================================================

    if tipo not in (
        "ENTRADA",
        "SALIDA",
    ):

        raise ValueError(
            "El tipo debe ser ENTRADA o SALIDA."
        )

    # ======================================================
    # CONVERTIR A PATH
    # ======================================================

    archivo = Path(archivo)

    # ======================================================
    # VALIDAR ARCHIVO
    # ======================================================

    if not archivo.exists():

        raise FileNotFoundError(
            f"No existe el archivo: {archivo}"
        )

    # ======================================================
    # OBTENER ESTRUCTURA
    # ======================================================

    estructura = obtener_carpeta_sgdea()

    servicio = estructura["servicio"]

    # ======================================================
    # DETERMINAR CARPETA
    # ======================================================

    if tipo == "ENTRADA":

        carpeta_id = estructura["radicados"]

    else:

        carpeta_id = estructura["consecutivos"]

    # ======================================================
    # BUSCAR SI YA EXISTE
    # ======================================================

    archivo_existente = buscar_pdf_existente(
        servicio,
        archivo.name,
        carpeta_id,
    )

    # ======================================================
    # SI YA EXISTE
    # ======================================================

    if archivo_existente:

        print("=" * 60)

        print(
            "EL PDF YA EXISTE EN GOOGLE DRIVE"
        )

        print(
            "NO SE CREARÁ UN DUPLICADO"
        )

        print(
            "Nombre:",
            archivo_existente.get("name")
        )

        print(
            "ID:",
            archivo_existente.get("id")
        )

        print(
            "URL:",
            archivo_existente.get("webViewLink")
        )

        print("=" * 60)

        return archivo_existente

    # ======================================================
    # METADATA
    # ======================================================

    metadata = {
        "name": archivo.name,
        "parents": [
            carpeta_id
        ],
    }

    # ======================================================
    # ARCHIVO PDF
    # ======================================================

    media = MediaFileUpload(
        str(archivo),
        mimetype="application/pdf",
        resumable=True,
    )

    # ======================================================
    # SUBIR
    # ======================================================

    resultado = (
        servicio.files()
        .create(
            body=metadata,
            media_body=media,
            fields=(
                "id,"
                "name,"
                "webViewLink,"
                "mimeType"
            ),
        )
        .execute()
    )

    # ======================================================
    # RESULTADO
    # ======================================================

    print("=" * 60)

    print(
        "PDF SUBIDO CORRECTAMENTE"
    )

    print(
        f"Nombre: {resultado.get('name')}"
    )

    print(
        f"ID: {resultado.get('id')}"
    )

    print(
        f"URL: {resultado.get('webViewLink')}"
    )

    print("=" * 60)

    return resultado