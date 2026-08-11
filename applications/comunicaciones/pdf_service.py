from pathlib import Path

from django.utils import timezone
from django.conf import settings

from bs4 import BeautifulSoup

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .models import Comunicacion
from .drive_service import subir_pdf_a_drive


# ==========================================================
# RUTA TEMPORAL DE PDFs
# ==========================================================

BASE_DIR = Path(settings.MEDIA_ROOT)


# ==========================================================
# CARPETA TEMPORAL SEGÚN TIPO
# ==========================================================

def _carpeta(tipo):
    """
    Crea una carpeta temporal para generar el PDF.

    Estos archivos NO son el almacenamiento definitivo.

    media/
        SGDEA/
            radicados_pdf/
            consecutivos_pdf/

    Una vez subido correctamente a Google Drive,
    el PDF local será eliminado.
    """

    raiz = BASE_DIR / "SGDEA"

    if tipo == "ENTRADA":
        carpeta = raiz / "radicados_pdf"
    else:
        carpeta = raiz / "consecutivos_pdf"

    carpeta.mkdir(
        parents=True,
        exist_ok=True
    )

    return carpeta


# ==========================================================
# GENERAR PDF
# ==========================================================

def generar_pdf(comunicacion: Comunicacion):
    """
    Genera el PDF temporal, lo sube a Google Drive
    y elimina la copia local después de confirmar
    que la subida fue exitosa.

    Flujo:

        Comunicación
             ↓
        PDF temporal
             ↓
        Google Drive
             ↓
        guardar ID + URL en MySQL
             ↓
        eliminar PDF local

    Si Drive falla:

        PDF local se conserva para evitar pérdida de evidencia.
    """

    # ======================================================
    # CARPETA TEMPORAL
    # ======================================================

    carpeta = _carpeta(
        comunicacion.tipo
    )

    # ======================================================
    # NOMBRE DEL ARCHIVO
    # ======================================================

    nombre = (
        comunicacion.radicado
        or comunicacion.consecutivo
        or f"correo_{comunicacion.id}"
    )

    archivo = carpeta / f"{nombre}.pdf"

    # ======================================================
    # ESTILOS
    # ======================================================

    estilos = getSampleStyleSheet()

    titulo = estilos["Heading1"]
    titulo.alignment = TA_CENTER

    normal = estilos["BodyText"]

    # ======================================================
    # DOCUMENTO
    # ======================================================

    doc = SimpleDocTemplate(
        str(archivo)
    )

    contenido = []

    # ======================================================
    # ENCABEZADO
    # ======================================================

    contenido.append(
        Paragraph(
            "SGDEA",
            titulo
        )
    )

    contenido.append(
        Spacer(1, 15)
    )

    # ======================================================
    # DATOS SEGÚN TIPO
    # ======================================================

    if comunicacion.tipo == "ENTRADA":

        contenido.append(
            Paragraph(
                f"<b>RADICADO:</b> "
                f"{comunicacion.radicado or ''}",
                normal,
            )
        )

        contenido.append(
            Paragraph(
                f"<b>REMITENTE:</b> "
                f"{comunicacion.remitente}",
                normal,
            )
        )

    else:

        contenido.append(
            Paragraph(
                f"<b>CONSECUTIVO:</b> "
                f"{comunicacion.consecutivo or ''}",
                normal,
            )
        )

        contenido.append(
            Paragraph(
                f"<b>DESTINATARIOS:</b> "
                f"{comunicacion.destinatarios}",
                normal,
            )
        )

    # ======================================================
    # INFORMACIÓN GENERAL
    # ======================================================

    contenido.append(
        Paragraph(
            f"<b>FECHA:</b> "
            f"{comunicacion.fecha}",
            normal,
        )
    )

    contenido.append(
        Paragraph(
            f"<b>ASUNTO:</b> "
            f"{comunicacion.asunto}",
            normal,
        )
    )

    contenido.append(
        Spacer(1, 20)
    )

    # ======================================================
    # CUERPO
    # ======================================================

    contenido.append(
        Paragraph(
            "<b>CUERPO DEL CORREO</b>",
            titulo
        )
    )

    contenido.append(
        Spacer(1, 10)
    )

    # ======================================================
    # LIMPIAR HTML
    # ======================================================

    texto = comunicacion.mensaje or ""

    soup = BeautifulSoup(
        texto,
        "html.parser"
    )

    texto = soup.get_text(
        separator="\n"
    )

    texto = texto.replace(
        "\xa0",
        " "
    )

    texto = texto.replace(
        "\r",
        ""
    )

    lineas = [
        linea.strip()
        for linea in texto.split("\n")
        if linea.strip()
    ]

    # ======================================================
    # AGREGAR TEXTO
    # ======================================================

    for linea in lineas:

        contenido.append(
            Paragraph(
                linea,
                normal
            )
        )

    # ======================================================
    # GENERAR PDF TEMPORAL
    # ======================================================

    doc.build(
        contenido
    )

    print("=" * 60)
    print("PDF TEMPORAL GENERADO")
    print("Comunicación:", comunicacion.id)
    print("Tipo:", comunicacion.tipo)
    print("Archivo:", archivo)
    print("=" * 60)

    # ======================================================
    # VERIFICAR QUE REALMENTE EXISTE
    # ======================================================

    if not archivo.exists():

        raise FileNotFoundError(
            f"No se pudo generar el PDF: {archivo}"
        )

    # ======================================================
    # SUBIR A GOOGLE DRIVE
    # ======================================================

    try:

        tipo_drive = (
            "ENTRADA"
            if comunicacion.tipo == "ENTRADA"
            else "SALIDA"
        )

        print("=" * 60)
        print("SUBIENDO PDF A GOOGLE DRIVE")
        print("=" * 60)

        resultado_drive = subir_pdf_a_drive(
            archivo,
            tipo_drive,
        )

        # ==================================================
        # VALIDAR RESPUESTA DE GOOGLE DRIVE
        # ==================================================

        drive_file_id = resultado_drive.get("id")
        drive_url = resultado_drive.get("webViewLink")

        if not drive_file_id:

            raise RuntimeError(
                "Google Drive no devolvió un ID de archivo."
            )

        if not drive_url:

            raise RuntimeError(
                "Google Drive no devolvió la URL del archivo."
            )

        # ==================================================
        # GUARDAR INFORMACIÓN DE DRIVE EN MYSQL
        # ==================================================

        comunicacion.drive_file_id = drive_file_id

        comunicacion.drive_url = drive_url

        comunicacion.drive_fecha_subida = (
            timezone.now()
        )

        comunicacion.save(
            update_fields=[
                "drive_file_id",
                "drive_url",
                "drive_fecha_subida",
                "fecha_actualizacion",
            ]
        )

        # ==================================================
        # CONFIRMACIÓN
        # ==================================================

        print("=" * 60)
        print("PDF SUBIDO A GOOGLE DRIVE")
        print("Nombre:", resultado_drive.get("name"))
        print("ID:", drive_file_id)
        print("URL:", drive_url)
        print("=" * 60)

        # ==================================================
        # ELIMINAR PDF LOCAL
        # ==================================================

        try:

            archivo.unlink()

            print(
                "PDF LOCAL ELIMINADO CORRECTAMENTE"
            )

            print(
                "Archivo eliminado:",
                archivo
            )

        except Exception as error_eliminando:

            print(
                "ADVERTENCIA: "
                "El PDF fue subido a Drive, "
                "pero no se pudo eliminar la copia local."
            )

            print(
                "Error:",
                error_eliminando
            )

        print("=" * 60)

    # ======================================================
    # ERROR DE GOOGLE DRIVE
    # ======================================================

    except Exception as error:

        print("=" * 60)

        print(
            "ERROR AL SUBIR PDF A GOOGLE DRIVE"
        )

        print(
            "Error:",
            error
        )

        print(
            "IMPORTANTE: "
            "El PDF local NO será eliminado."
        )

        print(
            "Archivo conservado:",
            archivo
        )

        print("=" * 60)

        # ==================================================
        # NO eliminamos el archivo.
        #
        # Esto evita perder evidencia si Drive falla.
        # ==================================================

        raise

    # ======================================================
    # RETORNAR RUTA
    # ======================================================

    return archivo