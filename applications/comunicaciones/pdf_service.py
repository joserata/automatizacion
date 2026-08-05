from pathlib import Path

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


BASE_DIR = Path(settings.MEDIA_ROOT)


def _carpeta(tipo):
    """
    Crea automáticamente:

    media/
        SGDEA/
            radicados_pdf/
            consecutivos_pdf/
    """

    raiz = BASE_DIR / "SGDEA"

    if tipo == "ENTRADA":
        carpeta = raiz / "radicados_pdf"
    else:
        carpeta = raiz / "consecutivos_pdf"

    carpeta.mkdir(parents=True, exist_ok=True)

    return carpeta


def generar_pdf(comunicacion: Comunicacion):
    """
    Genera un PDF de evidencia del correo.

    Retorna la ruta completa del archivo.
    """

    carpeta = _carpeta(comunicacion.tipo)

    nombre = (
        comunicacion.radicado
        or comunicacion.consecutivo
        or f"correo_{comunicacion.id}"
    )

    archivo = carpeta / f"{nombre}.pdf"

    estilos = getSampleStyleSheet()

    titulo = estilos["Heading1"]
    titulo.alignment = TA_CENTER

    normal = estilos["BodyText"]

    doc = SimpleDocTemplate(str(archivo))

    contenido = []

    # =====================================================
    # ENCABEZADO
    # =====================================================

    contenido.append(Paragraph("SGDEA", titulo))
    contenido.append(Spacer(1, 15))

    if comunicacion.tipo == "ENTRADA":

        contenido.append(
            Paragraph(
                f"<b>RADICADO:</b> {comunicacion.radicado or ''}",
                normal,
            )
        )

        contenido.append(
            Paragraph(
                f"<b>REMITENTE:</b> {comunicacion.remitente}",
                normal,
            )
        )

    else:

        contenido.append(
            Paragraph(
                f"<b>CONSECUTIVO:</b> {comunicacion.consecutivo or ''}",
                normal,
            )
        )

        contenido.append(
            Paragraph(
                f"<b>DESTINATARIOS:</b> {comunicacion.destinatarios}",
                normal,
            )
        )

    contenido.append(
        Paragraph(
            f"<b>FECHA:</b> {comunicacion.fecha}",
            normal,
        )
    )

    contenido.append(
        Paragraph(
            f"<b>ASUNTO:</b> {comunicacion.asunto}",
            normal,
        )
    )

    contenido.append(Spacer(1, 20))

    contenido.append(
        Paragraph("<b>CUERPO DEL CORREO</b>", titulo)
    )

    contenido.append(Spacer(1, 10))

    # =====================================================
    # LIMPIEZA DEL HTML DEL CORREO
    # =====================================================

    texto = comunicacion.mensaje or ""

    # Convierte siempre a texto plano
    soup = BeautifulSoup(texto, "html.parser")

    texto = soup.get_text(separator="\n")

    texto = texto.replace("\xa0", " ")

    texto = texto.replace("\r", "")

    # Elimina líneas vacías
    lineas = [
        linea.strip()
        for linea in texto.split("\n")
        if linea.strip()
    ]

    # ReportLab maneja mejor varios Paragraph
    for linea in lineas:

        contenido.append(
            Paragraph(linea, normal)
        )

    # =====================================================
    # GENERAR PDF
    # =====================================================

    doc.build(contenido)

    # =====================================================
    # GUARDAR RUTA EN LA BASE DE DATOS
    # =====================================================

    ruta_relativa = str(
        archivo.relative_to(BASE_DIR)
    ).replace("\\", "/")

    comunicacion.evidencia = ruta_relativa

    comunicacion.save(
        update_fields=[
            "evidencia",
            "fecha_actualizacion",
        ]
    )

    print(
        "PDF generado:",
        comunicacion.id,
        comunicacion.evidencia,
    )

    return archivo