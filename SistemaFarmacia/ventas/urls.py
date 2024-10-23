from django.urls import path
#con esto vamos a importar las vistas (ventas\views.py)
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    
    # urls para la creacion o registracion de  ventas y otros etc etc
    path('', views.ventas_view, name='Ventas'),
    path('ventas/create/', views.registrar_venta, name='CreateVenta'),

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
    
    # urls for the views of the (laboratorios)
    path('laboratorios/', views.laboratorios_view, name='Laboratorios'),
    path('laboratorio/create/', views.create_laboratorios_view, name='CreateLaboratorios'),
    path('laboratorio/update/<int:id>', views.update_laboratorios_view, name='UpdateLaboratorios'),
    path('deleteLaboratorio/<int:id>', views.delete_laboratorio_view, name='DeleteLaboratorios'),
    
    # urls for the views of the (medicamentos)
    path('inventario/', views.medicamentos_view, name='Medicamentos'),
    path('inventario/create/', views.create_medicamento_view, name='CreateMedicamentos'),
    path('inventario/update/<int:id>', views.update_medicamento_view, name='UpdateMedicamentos'),
    path('deleteInventario/<int:id>', views.delete_medicamento_view, name='DeleteMedicamentos'),
    
    # dashboard
    path('Dashboard/', views.dashboard_view, name='Dashboard'),
    
    # Vista para el login
    path('login/', views.login_view, name='login'),
    #path('logout/', views.logout_view, name='logout'),
    
    
    

]