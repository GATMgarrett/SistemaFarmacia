from django.contrib import admin
from django.contrib.auth.models import User
from .models import Laboratorios, Medicamentos, Roles, Proveedores, Compras, DetalleCompra, Ventas, DetalleVenta

@admin.register(Laboratorios)
class LaboratoriosAdmin(admin.ModelAdmin):
    list_display = ['nombre_laboratorio', 'telefono_lab', 'direccion', 'nit_lab']

@admin.register(Medicamentos)
class MedicamentosAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio', 'fecha_vencimiento', 'stock', 'laboratorio']

@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ['nombre_rol']

##Esto nos sive para manejar y controlar a los usuarios
admin.site.unregister(User)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')


@admin.register(Proveedores)
class ProveedoresAdmin(admin.ModelAdmin):
    list_display = ['nombre_empresa', 'contacto', 'correo_contacto', 'telefono_contacto']

@admin.register(Compras)
class ComprasAdmin(admin.ModelAdmin):
    list_display = ['medicamento', 'proveedor', 'fecha_compra', 'cantidad', 'precio_total']

@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ['compra', 'medicamento', 'precio', 'cantidad']

@admin.register(Ventas)
class VentasAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'fecha_venta', 'precio_total']

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['venta', 'medicamento', 'precio', 'cantidad']
