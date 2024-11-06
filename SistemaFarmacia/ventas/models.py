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

class Medicamentos(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField()
    stock = models.IntegerField()
    laboratorio = models.ForeignKey(Laboratorios, on_delete=models.SET_NULL, null=True)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class Roles(models.Model):
    nombre_rol = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class Proveedores(models.Model):
    nombre_empresa = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, null=True, blank=True)
    correo_contacto = models.EmailField(null=True, blank=True)
    telefono_contacto = models.CharField(max_length=20, null=True, blank=True)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class Compras(models.Model):
    medicamento = models.ForeignKey(Medicamentos, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedores, on_delete=models.CASCADE)
    fecha_compra = models.DateField()
    cantidad = models.IntegerField()
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compras, on_delete=models.CASCADE)
    medicamento = models.ForeignKey(Medicamentos, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class Ventas(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_venta = models.DateField(null=True, blank=True)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE)
    medicamento = models.ForeignKey(Medicamentos, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    activo = models.BooleanField(default=True)  # Nuevo campo para la eliminación lógica
