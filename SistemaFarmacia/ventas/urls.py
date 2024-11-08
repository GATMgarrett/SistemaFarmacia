from django.urls import path
#con esto vamos a importar las vistas (ventas\views.py)
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    
    # urls para la creacion o registracion de  ventas y otros etc etc
    path('', views.ventas_view, name='Ventas'),
    path('venta/detalle/<int:id>/', views.detalle_venta, name='detalle_venta'),  # Nueva URL para el detalle de la venta
    path('venta/create/', views.create_venta_view, name='CreateVenta'),
    path('venta/add_to_cart/<int:medicamento_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:medicamento_id>/', views.remove_from_cart, name='remove_from_cart'),

    # urls for the
    path('compras/', views.compras_view, name='Compras'),
    
    # urls for the views of the users
    path('usuario/', views.usuarios_view, name='Usuarios'),
    path('usuario/create/', views.create_user_view, name='CreateUsuarios'),
    path('deleteUsuario/<int:id>', views.delete_user_view, name='DeleteUsuarios'),
    path('usuario/update/<int:id>', views.update_user_view, name='UpdateUsuarios'),
    path('activateUsuario/<int:id>', views.activate_user_view, name='ActivateUsuarios'),
    
    # urls for the views of the suppliers (proveedores)
    path('proveedores/', views.proveedores_view, name='Proveedores'),
    path('proveedores/create', views.create_proveedor_view, name='CreateProveedores'),
    path('proveedores/update/<int:id>', views.update_proveedor_view, name='UpdateProveedores'),
    path('deleteProveedores/<int:id>', views.delete_proveedor_view, name='DeleteProveedores'),
    
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
    
    # dashboard
    path('Dashboard/', views.dashboard_view, name='Dashboard'),
    
    # Vista para el login
    path('login/', views.login_view, name='login'),
    #path('logout/', views.logout_view, name='logout'),
    
    
    

]