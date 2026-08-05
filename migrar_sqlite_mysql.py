import os
import sqlite3

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "automatiza.settings"
)

import django
django.setup()

from django.contrib.auth.models import User, Group

from applications.comunicaciones.models import (
    Responsable,
    Regla,
    Comunicacion,
    Adjunto,
    Historial,
    Consecutivo,
)

# =====================================================
# CONEXIÓN A SQLITE
# =====================================================

sqlite = sqlite3.connect("db_sqlite_respaldo.sqlite3")
sqlite.row_factory = sqlite3.Row

cursor = sqlite.cursor()

print("=" * 60)
print("CONECTADO A SQLITE")
print("=" * 60)

# =====================================================
# MIGRAR USUARIOS
# =====================================================

print("\nMigrando usuarios...")

cursor.execute("""
SELECT *
FROM auth_user
ORDER BY id
""")

usuarios = cursor.fetchall()

for fila in usuarios:

    User.objects.update_or_create(

        id=fila["id"],

        defaults={

            "password": fila["password"],
            "last_login": fila["last_login"],
            "is_superuser": bool(fila["is_superuser"]),
            "username": fila["username"],
            "first_name": fila["first_name"],
            "last_name": fila["last_name"],
            "email": fila["email"],
            "is_staff": bool(fila["is_staff"]),
            "is_active": bool(fila["is_active"]),
            "date_joined": fila["date_joined"],

        }

    )

print(f"Usuarios migrados: {len(usuarios)}")

print("=" * 60)
print("FINALIZADO")
print("=" * 60)

# =====================================================
# MIGRAR RESPONSABLES
# =====================================================

print("\nMigrando responsables...")

cursor.execute("""
SELECT *
FROM comunicaciones_responsable
ORDER BY id
""")

responsables = cursor.fetchall()

for fila in responsables:

    Responsable.objects.update_or_create(

        id=fila["id"],

        defaults={

            "nombre": fila["nombre"],
            "correo": fila["correo"],
            "cargo": fila["cargo"],
            "dependencia": fila["dependencia"],
            "activo": bool(fila["activo"]),

        }

    )

print(f"Responsables migrados: {len(responsables)}")

# =====================================================
# MIGRAR REGLAS
# =====================================================

print("\nMigrando reglas...")

cursor.execute("""
SELECT *
FROM comunicaciones_regla
ORDER BY id
""")

reglas = cursor.fetchall()

for fila in reglas:

    responsable = Responsable.objects.get(
        id=fila["responsable_id"]
    )

    Regla.objects.update_or_create(

        id=fila["id"],

        defaults={

            "palabra": fila["palabra"],
            "responsable": responsable,
            "activa": bool(fila["activa"]),

        }

    )

print(f"Reglas migradas: {len(reglas)}")

# =====================================================
# MIGRAR COMUNICACIONES
# =====================================================

print("\nMigrando comunicaciones...")

cursor.execute("""
SELECT *
FROM comunicaciones_comunicacion
ORDER BY id
""")

comunicaciones = cursor.fetchall()

for fila in comunicaciones:

    responsable = None
    usuario = None

    if fila["responsable_id"]:
        responsable = Responsable.objects.filter(
            id=fila["responsable_id"]
        ).first()

    if fila["usuario_id"]:
        usuario = User.objects.filter(
            id=fila["usuario_id"]
        ).first()

    Comunicacion.objects.update_or_create(

        id=fila["id"],

        defaults={

            "tipo": fila["tipo"],
            "radicado": fila["radicado"],
            "consecutivo": fila["consecutivo"],
            "fecha": fila["fecha"],
            "fecha_recepcion": fila["fecha_recepcion"],
            "remitente": fila["remitente"],
            "destinatarios": fila["destinatarios"],
            "copia": fila["copia"],
            "asunto": fila["asunto"],
            "mensaje": fila["mensaje"],
            "referencia": fila["referencia"],
            "responsable": responsable,
            "estado": fila["estado"],
            "remitido_transaccion": bool(fila["remitido_transaccion"]),
            "fecha_remision": fila["fecha_remision"],
            "prioridad": fila["prioridad"],
            "estado_flujo": fila["estado_flujo"],
            "usuario": usuario,
            "observaciones": fila["observaciones"],
            "gmail_id": fila["gmail_id"],
            "thread_id": fila["thread_id"],
            "tiene_adjuntos": bool(fila["tiene_adjuntos"]),
            "es_leido": bool(fila["es_leido"]),
            "es_archivado": bool(fila["es_archivado"]),
            "etiqueta": fila["etiqueta"],
            "fecha_creacion": fila["fecha_creacion"],
            "fecha_actualizacion": fila["fecha_actualizacion"],
            "evidencia": fila["evidencia"],

        }

    )

print(f"Comunicaciones migradas: {len(comunicaciones)}")
cursor.execute("""
SELECT COUNT(*)
FROM comunicaciones_adjunto
""")

print(
    "Adjuntos en SQLite:",
    cursor.fetchone()[0]
)
# =====================================================
# MIGRAR ADJUNTOS
# =====================================================

print("\nMigrando adjuntos...")

cursor.execute("""
SELECT *
FROM comunicaciones_adjunto
ORDER BY id
""")

adjuntos = cursor.fetchall()

for fila in adjuntos:

    comunicacion = Comunicacion.objects.get(
        id=fila["comunicacion_id"]
    )

    Adjunto.objects.update_or_create(

        id=fila["id"],

        defaults={

            "comunicacion": comunicacion,
            "nombre": fila["nombre"],
            "archivo": fila["archivo"],
            "tamano": fila["tamano"],
            "tipo": fila["tipo"],
            "fecha": fila["fecha"],

        }

    )

print(f"Adjuntos migrados: {len(adjuntos)}")