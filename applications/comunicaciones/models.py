from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Responsable(models.Model):

    nombre = models.CharField(
        max_length=200
    )

    correo = models.EmailField()

    cargo = models.CharField(
        max_length=150,
        blank=True
    )

    dependencia = models.CharField(
        max_length=150
    )

    activo = models.BooleanField(
        default=True
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsables"
    )

    class Meta:
        verbose_name = "Responsable"
        verbose_name_plural = "Responsables"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} - {self.dependencia}"
    
    
class Regla(models.Model):
    palabra = models.CharField(max_length=100, unique=True)
    responsable = models.ForeignKey(
        Responsable,
        on_delete=models.CASCADE
    )
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Regla"
        verbose_name_plural = "Reglas"
        ordering = ["palabra"]

    def __str__(self):
        return self.palabra


class Comunicacion(models.Model):

    TIPO = (
        ("ENTRADA", "Entrada"),
        ("SALIDA", "Salida"),
    )

    ESTADO = (
        ("NUEVO", "Nuevo"),
        ("RADICADO", "Radicado"),
        ("DELEGADO", "Delegado"),
        ("EN_PROCESO", "En Proceso"),
        ("FINALIZADO", "Finalizado"),
    )

    PRIORIDAD = (
        ("BAJA", "Baja"),
        ("NORMAL", "Normal"),
        ("ALTA", "Alta"),
        ("URGENTE", "Urgente"),
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO
    )

    radicado = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        db_index=True
    )

    consecutivo = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        db_index=True
    )

    fecha = models.DateTimeField(
        verbose_name="Fecha del correo"
    )

    fecha_recepcion = models.DateTimeField(
        auto_now_add=True
    )

    remitente = models.CharField(max_length=250)

    destinatarios = models.TextField(blank=True)

    copia = models.TextField(blank=True)

    asunto = models.CharField(max_length=500)

    mensaje = models.TextField()

    referencia = models.CharField(
        max_length=100,
        blank=True
    )

    responsable = models.ForeignKey(
        Responsable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO,
        default="NUEVO",
        db_index=True
    )

    remitido_transaccion = models.BooleanField(
    default=False
)

    fecha_remision = models.DateTimeField(
    null=True,
    blank=True
)

    prioridad = models.CharField(
    max_length=20,
    choices=PRIORIDAD,
    default="NORMAL"
)

    ESTADO_FLUJO = (
        ("ADMIN", "Administrador"),
        ("TRANSACCION", "Transacción"),
        ("FUNCIONARIO", "Funcionario"),
        ("FINALIZADO", "Finalizado"),
    )

    estado_flujo = models.CharField(
        max_length=20,
        choices=ESTADO_FLUJO,
        default="ADMIN",
        db_index=True,
    )

    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDAD,
        default="NORMAL"
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    observaciones = models.TextField(blank=True)

    gmail_id = models.CharField(
        max_length=200,
        blank=True,
        db_index=True
    )

    thread_id = models.CharField(
        max_length=200,
        blank=True,
        db_index=True
    )

    tiene_adjuntos = models.BooleanField(default=False)

    es_leido = models.BooleanField(default=False)

    es_archivado = models.BooleanField(default=False)

    etiqueta = models.CharField(
        max_length=100,
        blank=True
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    fecha_actualizacion = models.DateTimeField(auto_now=True)
    evidencia = models.FileField(
    upload_to="evidencias/",
    blank=True,
    null=True,
    verbose_name="PDF Evidencia"
)
    drive_file_id = models.CharField(
    max_length=200,
    blank=True,
    null=True,
    db_index=True,
    verbose_name="ID archivo Google Drive"
)

    drive_url = models.URLField(
    max_length=200,
    blank=True,
    null=True,
    verbose_name="URL Google Drive"
)

    drive_fecha_subida = models.DateTimeField(
    blank=True,
    null=True,
    verbose_name="Fecha subida a Drive"
)
    class Meta:
        verbose_name = "Comunicación"
        verbose_name_plural = "Comunicaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.asunto}"

    def estado_logico_display(self):
        historial = self.historial_set.order_by("-fecha").first()
        if historial and historial.accion == "Remitido a Transaccion":
            return "Remitido a Transacción"
        if self.responsable_id and self.estado == "DELEGADO":
            return "Delegado a responsable"
        return self.get_estado_display()


class Adjunto(models.Model):

    comunicacion = models.ForeignKey(
        Comunicacion,
        on_delete=models.CASCADE,
        related_name="adjuntos"
    )

    nombre = models.CharField(max_length=250)

    archivo = models.FileField(
        upload_to="adjuntos/"
    )

    tamano = models.PositiveIntegerField()

    tipo = models.CharField(max_length=100)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto"
        verbose_name_plural = "Adjuntos"

    def __str__(self):
        return self.nombre


class Historial(models.Model):

    comunicacion = models.ForeignKey(
        Comunicacion,
        on_delete=models.CASCADE
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    accion = models.CharField(max_length=200)

    descripcion = models.TextField(blank=True)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial"
        verbose_name_plural = "Historial"
        ordering = ["-fecha"]

    def __str__(self):
        return self.accion

class Consecutivo(models.Model):

    ARCHIVADO = (
        ("SI", "SI"),
        ("NO", "NO"),
    )

    consecutivo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Consecutivo"
    )

    fecha = models.DateField(
        verbose_name="Fecha"
    )

    dirigido_a = models.CharField(
        max_length=300,
        verbose_name="Dirigido a"
    )

    asunto = models.CharField(
        max_length=500
    )

    funcionario_responsable = models.CharField(
        max_length=200
    )

    caso_aranda = models.CharField(
        max_length=200,
        blank=True
    )

    observaciones = models.TextField(
        blank=True
    )

    fecha_envio = models.DateField(
        null=True,
        blank=True
    )

    tipo_archivo = models.CharField(
        max_length=150,
        verbose_name="Tipo Archivo / TRD"
    )

    ubicacion = models.CharField(
        max_length=300,
        verbose_name="Ubicación (Carpeta Archivo)"
    )

    archivado = models.CharField(
        max_length=2,
        choices=ARCHIVADO,
        default="NO"
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        verbose_name = "Consecutivo"
        verbose_name_plural = "Consecutivos"

        ordering = [
            "-fecha",
            "-id"
        ]

    def __str__(self):

        return self.consecutivo

    

    def save(self, *args, **kwargs):

        if not self.consecutivo:

            anio = datetime.now().year

            consecutivos = Consecutivo.objects.filter(
                fecha__year=anio
            ).count() + 1

            self.consecutivo = (
                f"N.1.014-{consecutivos:04d}-{str(anio)[2:]}"
            )

        super().save(*args, **kwargs)