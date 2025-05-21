from django.urls import path
#con esto vamos a importar las vistas (ventas\views.py)
from . import views
from .auth_views import login_view, verify_code_view, resend_code_view

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import user_passes_test

def is_admin(user):
    # Verifica si el usuario tiene el grupo 'Administrador'
    return user.groups.filter(name='Administrador').exists()

urlpatterns = [
    
    # urls para la creacion o registracion de  ventas y otros etc etc
    path('', views.ventas_view, name='Ventas'),
    path('', views.ventas_view, name='index'),  # Alias para que funcione la redirección del 2FA
    path('venta/detalle/<int:id>/', views.detalle_venta, name='detalle_venta'),  # Nueva URL para el detalle de la venta
    path('venta/create/', views.create_venta_view, name='CreateVenta'),
    path('venta/add_to_cart/<int:lote_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:lote_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('venta/confirmar/', views.confirmar_venta, name='confirmar_venta'),
    path('buscar-cliente/', views.buscar_cliente_view, name='buscar_cliente_view'),

    # urls for the compra
    path('compras/', views.compras_view, name='Compras'),
    path('compras/<int:compra_id>/detalle/', views.detalle_compra_view, name='detalle_compra'),
    path('compras/create/', views.create_compra_view, name='CreateCompra'),
    path('Compras/add_to_cart_compra/<int:medicamento_id>/', views.add_to_cart_compra, name='add_to_cart_compra'),
    path('remove_from_cart_compra/<int:medicamento_id>/', views.remove_from_cart_compra, name='remove_from_cart_compra'),
    path('compras/export/', views.export_compras_to_excel, name='export_compras_excel'),  # Ruta para exportar a Excel
    
    # urls for the views of the users
    path('usuario/', user_passes_test(is_admin)(views.usuarios_view), name='Usuarios'),
    #path('usuario/', views.usuarios_view, name='Usuarios'),
    #path('usuario/create/', views.create_user_view, name='CreateUsuarios'),
    path('usuario/create/', user_passes_test(is_admin)(views.create_user_view), name='CreateUsuarios'),
    path('deleteUsuario/<int:id>', views.delete_user_view, name='DeleteUsuarios'),
    path('usuario/update/<int:id>', views.update_user_view, name='UpdateUsuarios'),
    path('activateUsuario/<int:id>', views.activate_user_view, name='ActivateUsuarios'),
    
    # urls for the views of the suppliers (proveedores)
    path('proveedores/', views.proveedores_view, name='Proveedores'),
    path('proveedores/create', views.create_proveedor_view, name='CreateProveedores'),
    path('proveedores/update/<int:id>', views.update_proveedor_view, name='UpdateProveedores'),
    path('deleteProveedores/<int:id>', views.delete_proveedor_view, name='DeleteProveedores'),
    path('activate/<int:id>/', views.activate_proveedor_view, name='ActivateProveedores'),
    
    # URLs for the views of (laboratorios)
    path('laboratorios/', views.laboratorios_view, name='Laboratorios'),
    path('laboratorio/create/', views.create_laboratorio_view, name='CreateLaboratorio'),
    path('laboratorio/update/<int:id>/', views.update_laboratorio_view, name='UpdateLaboratorio'),
    path('laboratorio/delete/<int:id>/', views.delete_laboratorio_view, name='DeleteLaboratorio'),
    path('laboratorio/activate/<int:id>/', views.activate_laboratorio_view, name='ActivateLaboratorio'),
    
    # URLs para las vistas de los medicamentos
    path('inventario/', views.medicamentos_view, name='Medicamentos'),
    path('inventario/create/', views.create_medicamento_view, name='CreateMedicamentos'),
    path('inventario/update/<int:id>/', views.update_medicamento_view, name='UpdateMedicamentos'),
    path('inventario/delete/<int:id>/', views.delete_medicamento_view, name='DeleteMedicamentos'),  # Cambiado para reflejar la estructura
    path('inventario/activate/<int:id>/', views.activate_medicamento_view, name='ActivateMedicamentos'),  # Nueva ruta para activar medicamentos
    
    # dashboard Analisis BA
    path('Dashboard/ventas/', views.dashboard_view_ventas, name='Dashboard_ventas'),
    path('Dashboard/Inventario/', views.dashboard_view_inventario, name='Dashboard_inventario'),
    path('Dashboard/Proveedores/', views.dashboard_view_proveedores, name='Dashboard_proveedores'),
    path('Dashboard/Usuarios/', views.dashboard_view_usuarios, name='Dashboard_usuarios'),
    
    # Vistas para el login con 2FA
    path('login/', login_view, name='login'),  # Mantener esta URL para compatibilidad
    path('verify-code/', verify_code_view, name='verify_code'),
    path('resend-code/', resend_code_view, name='resend_code'),
    #path('logout/', views.logout_view, name='logout'),
    
    # Vista para la Facturación
    path('facturas/', views.facturas_view, name='facturas'),
    path('facturas/generar/<int:venta_id>/', views.generar_factura_view, name='generar_factura'),
    path('facturas/detalle/<int:factura_id>/', views.detalle_factura_view, name='detalle_factura'),
    path('facturas/imprimir/<int:factura_id>/', views.imprimir_factura_view, name='imprimir_factura'),
    path('facturas/anular/<int:factura_id>/', views.anular_factura_view, name='anular_factura'),
    
    # Vista para buscar clientes por NIT/CI (AJAX)
    #path('buscar-cliente/', views.buscar_cliente_view, name='buscar_cliente'),
]