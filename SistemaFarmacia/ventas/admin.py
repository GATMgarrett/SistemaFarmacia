from django.contrib import admin
from django.contrib.auth.models import User
from .models import Laboratorios, Medicamentos, Roles, Proveedores, Compras, DetalleCompra, Ventas, DetalleVenta, Categorias, Tipos

@admin.register(Laboratorios)
class LaboratoriosAdmin(admin.ModelAdmin):
    list_display = ['nombre_laboratorio', 'telefono_lab', 'direccion', 'nit_lab']

@admin.register(Medicamentos)
class MedicamentosAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'laboratorio']  # Se eliminó 'stock' ya que ahora se maneja en LoteMedicamento

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
    list_display = ['proveedor', 'fecha_compra', 'precio_total']

@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ['compra', 'medicamento', 'precio', 'cantidad']

@admin.register(Ventas)
class VentasAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'fecha_venta', 'precio_total']

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['venta', 'medicamento', 'precio', 'cantidad']

@admin.register(Categorias)
class CategoriasAdmin(admin.ModelAdmin):
    list_display = ['nombre_categoria', 'descripcion']

@admin.register(Tipos)
class TiposAdmin(admin.ModelAdmin):
    list_display = ['nombre_tipo', 'descripcion']