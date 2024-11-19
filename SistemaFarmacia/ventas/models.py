from django.db import models
from django.contrib.auth.models import User

class Laboratorios(models.Model):
    nombre_laboratorio = models.CharField(max_length=100)
    telefono_lab = models.IntegerField()
    direccion = models.CharField(max_length=255, null=True, blank=True)
    abreviatura_lab = models.CharField(max_length=10, null=True, blank=True)
    nit_lab = models.IntegerField()
    activo = models.BooleanField(default=True)  # Campo para la eliminación lógica

    def __str__(self):
        return self.nombre_laboratorio  # Muestra el nombre del laboratorio en el select
    
class Categorias(models.Model):
    nombre_categoria = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_categoria

class Tipos(models.Model):
    nombre_tipo = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)  # Campo de descripción para el tipo
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_tipo

class Medicamentos(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    stock = models.IntegerField(default=0)
    laboratorio = models.ForeignKey(Laboratorios, on_delete=models.SET_NULL, null=True)
    categoria = models.ForeignKey(
        Categorias,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicamentos'
    )
    tipo = models.ForeignKey(
        Tipos,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicamentos'
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Roles(models.Model):
    nombre_rol = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class Proveedores(models.Model):
    nombre_empresa = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, null=True, blank=True)
    correo_contacto = models.EmailField(null=True, blank=True)
    telefono_contacto = models.CharField(max_length=20, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)  # Nuevo campo descripción
    direccion = models.CharField(max_length=255, null=True, blank=True)  # Nuevo campo dirección
    activo = models.BooleanField(default=True)  # Establecer por defecto como activo
    
    def __str__(self):
        return self.nombre_empresa

class Compras(models.Model):
    proveedor = models.ForeignKey(Proveedores, on_delete=models.CASCADE)
    fecha_compra = models.DateField()
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compras, on_delete=models.CASCADE)
    medicamento = models.ForeignKey(Medicamentos, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica
    
    def save(self, *args, **kwargs):
        # Obtener el primer lote de medicamento activo con precio
        lote = LoteMedicamento.objects.filter(medicamento=self.medicamento, activo=True).first()
        if lote:
            self.precio = lote.precio_compra  # Establecer el precio de compra del lote
        super().save(*args, **kwargs)

class LoteMedicamento(models.Model):
    medicamento = models.ForeignKey('Medicamentos', on_delete=models.CASCADE, related_name='lotes')
    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_compra = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_produccion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Lote {self.id} - {self.medicamento.nombre}"

class Ventas(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_venta = models.DateField(null=True, blank=True)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, related_name="detalles")
    medicamento = models.ForeignKey(Medicamentos, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Almacena y reduce el stock de cada lote en función del FIFO
        cantidad_requerida = self.cantidad
        lotes = LoteMedicamento.objects.filter(
            medicamento=self.medicamento,
            activo=True
        ).order_by('fecha_compra')

        for lote in lotes:
            if lote.cantidad >= cantidad_requerida:
                lote.cantidad -= cantidad_requerida
                lote.save()
                break
            else:
                cantidad_requerida -= lote.cantidad
                lote.cantidad = 0
                lote.activo = False  # Desactiva el lote si ya no tiene stock
                lote.save()

        super().save(*args, **kwargs)
