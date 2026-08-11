import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "automatiza.settings"
)

import django

django.setup()

from applications.comunicaciones.drive_service import (
    obtener_carpeta_sgdea,
)


print("=" * 60)
print("PRUEBA GOOGLE DRIVE - SGDEA")
print("=" * 60)

try:

    estructura = obtener_carpeta_sgdea()

    print()
    print("CONEXIÓN EXITOSA")
    print()

    print(
        "SGDEA-PRUEBAS:",
        estructura["sgdea"],
    )

    print(
        "RADICADOS:",
        estructura["radicados"],
    )

    print(
        "CONSECUTIVOS:",
        estructura["consecutivos"],
    )

    print()
    print("=" * 60)
    print("PRUEBA FINALIZADA CORRECTAMENTE")
    print("=" * 60)

except Exception as e:

    print()
    print("=" * 60)
    print("ERROR")
    print("=" * 60)

    print(
        type(e).__name__,
        str(e),
    )

    raise