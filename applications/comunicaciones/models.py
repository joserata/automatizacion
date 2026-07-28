from django.db import models
from django.contrib.auth.models import User


class Responsable(models.Model):
    nombre = models.CharField(max_length=200)
    correo = models.EmailField(unique=True)
    cargo = models.CharField(max_length=150, blank=True)
    dependencia = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

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

    class Meta:
        verbose_name = "Comunicación"
        verbose_name_plural = "Comunicaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.asunto}"


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

    anio = models.PositiveIntegerField(unique=True)

    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Consecutivo"
        verbose_name_plural = "Consecutivos"
        ordering = ["-anio"]

    def __str__(self):
        return str(self.anio)