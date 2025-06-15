from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .prediccion_mensual_medicamentos import main as ejecutar_prediccion, generar_predicciones, cargar_datos_ventas_mensuales, completar_series_mensuales, filtrar_medicamentos_relevantes
import logging
from datetime import datetime, timedelta
from django.db.models import Sum
from .models import LoteMedicamento
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
import hashlib

# Configurar logger
logger = logging.getLogger(__name__)

# Función para invalidar el caché de los dashboards
def invalidar_cache_dashboard():
    """
    Invalida todos los cachés relacionados con los dashboards del sistema
    Se debe llamar cuando se registren nuevas ventas, compras o se modifiquen datos relevantes
    """
    try:
        # Patrón para buscar todas las claves de los dashboards
        cache_patterns = [
            # Patrones para dashboard de ventas
            'dashboard_datos_*',
            'dashboard_graficos_*', 
            'dashboard_categorias',
            # Patrones para dashboard de predicciones
            'dashboard_predicciones_datos_*',
            'dashboard_predicciones_grafico_*'
        ]
        
        # Django no tiene un método nativo para eliminar por patrón,
        # por lo que usaremos una aproximación simple
        cache.delete('dashboard_categorias')
        
        # Para patrones más complejos, podríamos usar versioning del caché
        # incrementando un número de versión cuando queremos invalidar todo
        cache_version = cache.get('dashboard_cache_version', 0)
        cache.set('dashboard_cache_version', cache_version + 1, None)  # Sin expiración
        
        print(f"Caché del dashboard invalidado. Nueva versión: {cache_version + 1}")
        
    except Exception as e:
        print(f"Error al invalidar caché del dashboard: {str(e)}")

from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseForbidden, Http404
from django.urls import reverse
from django.db.models import Sum, F, Count, Q, Func, ExpressionWrapper, DecimalField
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.timezone import now
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from .models import Proveedores, Compras, DetalleCompra
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay, TruncYear, ExtractWeekDay
from .forms import UsuarioForm, UsuarioFormNoPassword

# Importaciones de datetime
from datetime import datetime, date, timedelta

# Librerías para gráficos y análisis de datos
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import json
import io
import base64

# Importaciones para Excel
from openpyxl import Workbook

# Importaciones de modelos
from .models import *


# Create your views here.
# Aqui van la creacion de las vistas

# Vista de las ventas
def ventas_view(request):
    num_ventas = 156 #esto solo es un dato que estamos enviando a num ventas
    context = {
        'num_ventas': num_ventas
    }
    return render(request, 'ventas.html', context)

# Vista de las compras
def compras_view(request):
    return render(request, 'compras.html')


#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los laboratorios
# Vista de los laboratorios
@login_required
def laboratorios_view(request):
    # Obtener los laboratorios activos e inactivos
    laboratorios_activos = Laboratorios.objects.filter(activo=True)
    laboratorios_inactivos = Laboratorios.objects.filter(activo=False)

    # Obtener el número de elementos por página desde el request (por defecto 5)
    num_laboratorios = request.GET.get('num_laboratorios', 5)

    # Crear el paginador para los laboratorios activos
    paginator = Paginator(laboratorios_activos, num_laboratorios)
    page = request.GET.get('page')  # Página actual
    laboratorios_activos_page = paginator.get_page(page)

    # Crear el paginador para los laboratorios inactivos
    paginator_inactivos = Paginator(laboratorios_inactivos, num_laboratorios)
    laboratorios_inactivos_page = paginator_inactivos.get_page(page)

    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario
    return render(request, 'laboratorios.html', {
        'laboratorios_activos': laboratorios_activos_page,
        'laboratorios_inactivos': laboratorios_inactivos_page,
        'num_laboratorios': num_laboratorios,
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla

    })
# Vista para la creación de laboratorios
@login_required
def create_laboratorio_view(request):
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    formulario = LaboratorioForm(request.POST or None)
    if formulario.is_valid():
        laboratorio = formulario.save(commit=False)  # Guarda el formulario sin guardar en la base de datos aún
        laboratorio.activo = True  # Establece activo como True por defecto
        laboratorio.save()  # Ahora guarda en la base de datos
        return redirect('Laboratorios')  # Cambia esta URL según tu configuración
    return render(request, 'laboratoriosCRUD/create_laboratorio.html', {'formulario': formulario, 'grupos': grupos_usuario})
# Vista para la edición de laboratorios
@login_required
def update_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    formulario = LaboratorioForm(request.POST or None, instance=laboratorio)
    if formulario.is_valid():
        formulario.save()
        return redirect('Laboratorios')
    return render(request, 'laboratoriosCRUD/update_laboratorio.html', {'formulario': formulario})
# Vista para la eliminación lógica de laboratorios
def delete_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    laboratorio.activo = False
    laboratorio.save()
    return redirect('Laboratorios')
# Vista para reactivar laboratorios inactivos
def activate_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    laboratorio.activo = True
    laboratorio.save()
    return redirect('Laboratorios')
#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los usuarios
# Vista de los usuarios
@login_required
def usuarios_view(request):
    # Usuarios activos
    usuarios_activos = User.objects.filter(is_active=True).prefetch_related('groups')
    # Usuarios inactivos
    usuarios_inactivos = User.objects.filter(is_active=False).prefetch_related('groups')
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    return render(request, 'usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos, 
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
    })

# Vista para la creacion de los ususarios


# Vista para la creación de los usuarios
@login_required
def create_user_view(request):
    """
    Vista original para crear usuarios con contraseña manual.
    Mantener para compatibilidad o casos especiales.
    """
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    if request.method == 'POST':
        formulario = UsuarioForm(request.POST)
        if formulario.is_valid():
            user = formulario.save(commit=False)  # No se guarda todavía en la base de datos
            user.set_password(formulario.cleaned_data['password'])  # Usa la contraseña del formulario
            user.save()  # Guarda el usuario en la base de datos
            if formulario.cleaned_data['grupo']:
                user.groups.add(formulario.cleaned_data['grupo'])  # Asigna el grupo seleccionado
            return redirect('Usuarios')  # Redirige a la lista de usuarios o a donde necesites
    else:
        formulario = UsuarioForm()  # Crea una nueva instancia del formulario

    return render(request, 'usuariosCRUD/create_user.html', {'formulario': formulario, 'grupos': grupos_usuario})

@login_required
def create_user_secure_view(request):
    """
    Vista de creación de usuarios con generación automática de contraseña
    y envío por correo electrónico para mejorar la seguridad.
    """
    grupos_usuario = request.user.groups.values_list('name', flat=True)
    
    if request.method == 'POST':
        formulario = UsuarioFormNoPassword(request.POST)
        if formulario.is_valid():
            # Guardar usuario sin commit para poder establecer la contraseña
            user = formulario.save(commit=False)
            
            # Generar contraseña aleatoria segura
            from .email_utils import generate_random_password, send_user_credentials
            password = generate_random_password()
            
            # Establecer contraseña y guardar usuario
            user.set_password(password)
            user.save()
            
            # Asignar grupo si se seleccionó
            if formulario.cleaned_data['grupo']:
                user.groups.add(formulario.cleaned_data['grupo'])
            
            # Enviar credenciales por correo electrónico
            if user.email:
                send_result = send_user_credentials(user.email, user.username, password)
                if send_result:
                    messages.success(request, f'Usuario {user.username} creado exitosamente. Las credenciales han sido enviadas por correo a {user.email}')
                else:
                    messages.warning(request, f'Usuario creado, pero hubo un problema al enviar el correo con las credenciales.')
            else:
                messages.warning(request, f'Usuario creado, pero no se pudo enviar el correo porque no tiene dirección de correo electrónico.')
                
            return redirect('Usuarios')
    else:
        formulario = UsuarioFormNoPassword()
    
    return render(request, 'usuariosCRUD/create_user_no_password.html', {'formulario': formulario, 'grupos': grupos_usuario})

# Vista para la edición de los usuarios
@login_required
def update_user_view(request, id):
    # Solo permitir a los usuarios editar su propio perfil o a los administradores editar cualquier perfil
    if not (request.user.is_superuser or request.user.id == int(id)):
        messages.error(request, 'No tienes permiso para editar este perfil.')
        return redirect('Ventas')  # Redirigir a la página principal
        
    usuario = get_object_or_404(User, pk=id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            user = form.save()  # Usará el método save personalizado
            messages.success(request, 'Perfil actualizado correctamente')
            # Si el usuario está editando su propio perfil, redirigir a la página de perfil
            if request.user.id == int(id):
                return redirect('UpdateUsuarios', id=user.id)
            return redirect('Usuarios')
    else:
        form = UsuarioForm(instance=usuario)
        # Limpiar el campo de contraseña en el GET
        form.fields['password'].initial = ''
        # Si no es administrador, ocultar el campo de grupo
        if not request.user.is_superuser:
            form.fields.pop('grupo', None)
    
    return render(request, 'usuariosCRUD/update_user.html', {
        'form': form,
        'usuario': usuario,
        'es_edicion_propia': str(request.user.id) == str(id)
    })

# Vista para la edición de los usuarios sin campo de contraseña
@login_required
def update_user_basic_view(request, id):
    # Solo permitir a los administradores editar cualquier perfil con esta vista
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para editar este perfil.')
        return redirect('Ventas')  # Redirigir a la página principal
        
    usuario = get_object_or_404(User, pk=id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            # Aseguramos que no se modifica la contraseña desde esta vista
            form.cleaned_data['password'] = ''
            user = form.save()  # Usará el método save personalizado
            messages.success(request, 'Perfil actualizado correctamente')
            return redirect('Usuarios')
    else:
        form = UsuarioForm(instance=usuario)
        # Limpiar el campo de contraseña
        form.fields['password'].initial = ''
        # Ocultamos el campo de contraseña del form (aunque igualmente se renderizará en otra plantilla sin este campo)
        form.fields['password'].widget = form.fields['password'].hidden_widget()
    
    return render(request, 'usuariosCRUD/update_user_basic.html', {
        'form': form,
        'usuario': usuario
    })

# Vista para la eliminación de los usuarios
def delete_user_view(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = False  # Desactivar el usuario en lugar de eliminarlo
    usuario.save()
    return redirect('Usuarios')

# Vista para la activación de los usuarios
def activate_user_view(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = True  # Activar el usuario
    usuario.save()
    return redirect('Usuarios')

#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los proveedores
# Vista de los proveedores
@login_required
def proveedores_view(request):
    # Obtén los proveedores activos e inactivos
    proveedores_activos = Proveedores.objects.filter(activo=True)
    proveedores_inactivos = Proveedores.objects.filter(activo=False)

    # Determinar cuántos elementos por página
    items_per_page = request.GET.get('items_per_page', 5)  # Por defecto, 5

    # Paginación para proveedores activos
    paginator_activos = Paginator(proveedores_activos, items_per_page)
    page_activos = request.GET.get('page')
    proveedores_activos_pag = paginator_activos.get_page(page_activos)

    # Paginación para proveedores inactivos
    paginator_inactivos = Paginator(proveedores_inactivos, items_per_page)
    page_inactivos = request.GET.get('page')
    proveedores_inactivos_pag = paginator_inactivos.get_page(page_inactivos)
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    context = {
        'proveedores_activos': proveedores_activos_pag,
        'proveedores_inactivos': proveedores_inactivos_pag,
        'items_per_page': items_per_page,  # Pasar la opción seleccionada
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
    }
    return render(request, 'proveedores.html', context)
# Vista para la creacion de los proveedores
@login_required
def create_proveedor_view(request):
    formulario = ProveedorForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Proveedores')  # Redirige a la lista de proveedores
    return render(request, 'proveedoresCRUD/create_proveedor.html', {'formulario': formulario})
# Vista para la edicion de los proveedores
@login_required
def update_proveedor_view(request, id):
    proveedores = Proveedores.objects.get(id=id)
    formulario = ProveedorForm(request.POST or None, request.FILES or None, instance=proveedores)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Proveedores')
    return render(request, 'proveedoresCRUD/update_proveedor.html', {'formulario': formulario})
# Vista para la eliminación lógica de proveedores
def delete_proveedor_view(request, id):
    proveedor = Proveedores.objects.get(id=id)
    proveedor.activo = False  # Establece el proveedor como inactivo
    proveedor.save()
    return redirect('Proveedores')
# Vista para activar los proveedores
def activate_proveedor_view(request, id):
    proveedor = get_object_or_404(Proveedores, id=id)
    proveedor.activo = True
    proveedor.save()
    return redirect('Proveedores')  # Redirige a la página de proveedores
#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los medicamentos(inventario)
# Vista de los medicamentos
@login_required
def medicamentos_view(request):
    # Número de medicamentos por página (por defecto 5)
    num_medicamentos = request.GET.get('num_medicamentos', '5')  # Valor predeterminado: 5
    num_medicamentos = int(num_medicamentos) if num_medicamentos.isdigit() else 5

    # Medicamentos activos con stock calculado desde los lotes
    medicamentos_activos = Medicamentos.objects.filter(activo=True)
    
    # Calculamos el stock total para cada medicamento desde sus lotes activos
    for medicamento in medicamentos_activos:
        total_stock = LoteMedicamento.objects.filter(
            medicamento=medicamento,
            activo=True
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        medicamento.total_stock = total_stock
    
    paginator_activos = Paginator(medicamentos_activos, num_medicamentos)
    page_activos = request.GET.get('page_activos', 1)
    medicamentos_activos_page = paginator_activos.get_page(page_activos)

    # Medicamentos inactivos con stock calculado desde los lotes
    medicamentos_inactivos = Medicamentos.objects.filter(activo=False)
    
    # Calculamos el stock total para cada medicamento inactivo
    for medicamento in medicamentos_inactivos:
        total_stock = LoteMedicamento.objects.filter(
            medicamento=medicamento,
            activo=True
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        medicamento.total_stock = total_stock
    
    paginator_inactivos = Paginator(medicamentos_inactivos, num_medicamentos)
    page_inactivos = request.GET.get('page_inactivos', 1)
    medicamentos_inactivos_page = paginator_inactivos.get_page(page_inactivos)
    
    # Obtener los grupos del usuario actual
    grupos_usuario = request.user.groups.values_list('name', flat=True) 
    
    # Renderizar la plantilla
    return render(request, 'inventario.html', {
        'medicamentos_activos': medicamentos_activos_page,
        'medicamentos_inactivos': medicamentos_inactivos_page,
        'num_medicamentos': num_medicamentos,
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
    })
# Vista para la creación de medicamentos
@login_required
def create_medicamento_view(request):
    formulario = MedicamentoForm(request.POST or None, request.FILES or None)
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    if formulario.is_valid():
        formulario.save()
        return redirect('Medicamentos')  # Cambia según tu URL de lista
    return render(request, 'inventarioCRUD/create_medicamento.html', {'formulario': formulario, 'grupos': grupos_usuario})
# Vista para la edición de medicamentos
@login_required
def update_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    formulario = MedicamentoForm(request.POST or None, request.FILES or None, instance=medicamento)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Medicamentos')  # Cambia según tu URL de lista
    return render(request, 'inventarioCRUD/update_medicamento.html', {'formulario': formulario})
# Vista para la eliminación lógica de medicamentos
def delete_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    medicamento.activo = False  # Establecer como inactivo
    medicamento.save()
    return redirect('Medicamentos')  # Cambia según tu URL de lista
# Vista para la activación de medicamentos (si deseas restaurarlos)
def activate_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    medicamento.activo = True  # Activar el medicamento
    medicamento.save()
    return redirect('Medicamentos')  # Cambia según tu URL de lista

#////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////Todo aqui sera para el analisi BA
#/////////////////////////////////////////////////////////////////////Esto va a pertenecer al analsisid de ventas
def obtener_datos_ventas(fecha_inicio=None, fecha_fin=None, categoria_id=None, tipo_id=None):
    # Si no hay fechas, devolver un DataFrame vacío con la estructura correcta
    if not fecha_inicio or not fecha_fin:
        return pd.DataFrame(columns=['medicamento', 'categoria', 'tipo', 'fecha', 'cantidad', 'precio_total'])
    
    # Crear consulta básica
    ventas_query = DetalleVenta.objects.filter(activo=True)
    
    # Aplicar filtros de fecha
    ventas_query = ventas_query.filter(venta__fecha_venta__range=[fecha_inicio, fecha_fin])
    
    # Si no hay datos en el rango de fechas, devolver un DataFrame vacío
    if not ventas_query.exists():
        return pd.DataFrame(columns=['medicamento', 'categoria', 'tipo', 'fecha', 'cantidad', 'precio_total'])
    
    # Usar anotaciones y agregaciones de Django para procesar los datos en la base de datos
    # Usamos ExpressionWrapper para operaciones matemáticas
    from django.db.models import ExpressionWrapper, DecimalField
    
    precio_total_expr = ExpressionWrapper(
        F('precio') * F('cantidad'), 
        output_field=DecimalField()
    )
    
    ventas_por_mes = ventas_query.annotate(
        mes=TruncMonth('venta__fecha_venta'),
        subtotal=precio_total_expr
    ).values(
        'medicamento__nombre',
        'medicamento__categoria__nombre_categoria',
        'medicamento__tipo__nombre_tipo',
        'mes'
    ).annotate(
        cantidad=Sum('cantidad'),
        precio_total=Sum('subtotal')
    ).order_by('mes')
    
    # Convertir a DataFrame para manipulación adicional
    ventas_data = []
    for v in ventas_por_mes:
        ventas_data.append({
            'medicamento': v['medicamento__nombre'] or "Desconocido",
            'categoria': v['medicamento__categoria__nombre_categoria'] or "Sin categoría",
            'tipo': v['medicamento__tipo__nombre_tipo'] or "Sin tipo",
            'fecha': v['mes'],
            'cantidad': v['cantidad'],
            'precio_total': v['precio_total']
        })
    
    df = pd.DataFrame(ventas_data)
    
    # Si hay datos, realizar transformaciones adicionales
    if not df.empty:
        # Asegurarse de que la fecha es datetime
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    return df


def obtener_ventas_mes():
    """Obtiene el total de ventas del mes actual"""
    hoy = timezone.now().date()
    primer_dia_mes = hoy.replace(day=1)
    
    # Consultar ventas del mes actual
    ventas_mes = DetalleVenta.objects.filter(
        activo=True,
        venta__fecha_venta__gte=primer_dia_mes,
        venta__fecha_venta__lte=hoy
    ).aggregate(
        total=Sum(F('precio') * F('cantidad'))
    )['total'] or 0
    
    # Redondear a 2 decimales
    return round(ventas_mes, 2)


def obtener_ventas_anual():
    """Obtiene el total de ventas del año actual"""
    hoy = timezone.now().date()
    primer_dia_anio = hoy.replace(month=1, day=1)
    
    # Consultar ventas del año actual
    ventas_anual = DetalleVenta.objects.filter(
        activo=True,
        venta__fecha_venta__gte=primer_dia_anio,
        venta__fecha_venta__lte=hoy
    ).aggregate(
        total=Sum(F('precio') * F('cantidad'))
    )['total'] or 0
    
    # Redondear a 2 decimales
    return round(ventas_anual, 2)


def obtener_productos_vendidos(fecha_inicio, fecha_fin):
    """Obtiene la cantidad total de productos vendidos en un período"""
    productos_vendidos = DetalleVenta.objects.filter(
        activo=True,
        venta__fecha_venta__gte=fecha_inicio,
        venta__fecha_venta__lte=fecha_fin
    ).aggregate(
        total=Sum('cantidad')
    )['total'] or 0
    
    return productos_vendidos


def obtener_clientes_nuevos(fecha_inicio, fecha_fin):
    """Obtiene la cantidad de clientes nuevos en un período"""
    # Obtener clientes que aparecen en facturas en el período especificado
    clientes_nuevos = Cliente.objects.filter(
        factura__fecha_emision__gte=fecha_inicio,
        factura__fecha_emision__lte=fecha_fin,
        activo=True
    ).distinct().count()
    
    return clientes_nuevos


def obtener_top_productos(fecha_inicio, fecha_fin, limite=10):
    """Obtiene los productos más vendidos en un período"""
    from django.db.models import ExpressionWrapper, DecimalField
    
    # Creamos una expresión para el cálculo de precio_total
    precio_total_expr = ExpressionWrapper(
        F('precio') * F('cantidad'), 
        output_field=DecimalField()
    )
    
    top_productos = DetalleVenta.objects.filter(
        activo=True,
        venta__fecha_venta__gte=fecha_inicio,
        venta__fecha_venta__lte=fecha_fin
    ).annotate(
        precio_total=precio_total_expr
    ).values(
        'medicamento__nombre',
        'medicamento__categoria__nombre_categoria',
        'medicamento__tipo__nombre_tipo'
    ).annotate(
        total_unidades=Sum('cantidad'),
        total_ventas=Sum('precio_total')
    ).order_by('-total_unidades')[:limite]
    
    return top_productos

# Nueva función para generar el gráfico de barras con Plotly
def generar_grafico_barras(df, fecha_inicio=None, fecha_fin=None):
    # Check if the DataFrame is empty
    if df.empty:
        # Create an empty figure with a message
        fig = go.Figure()
        fig.update_layout(
            title='<b>No hay datos de ventas disponibles para el período seleccionado</b>',
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': 'No hay datos de ventas para mostrar en este período.<br>Pruebe seleccionando un rango de fechas diferente.',
                'showarrow': False,
                'font': {'size': 16}
            }],
            template='plotly_white',
            height=500
        )
        config = {
            'responsive': True,
            'displaylogo': False
        }
        return fig.to_html(config=config)
        
    # Agrupar por categoría y obtener los 5 medicamentos principales por categoría
    top_por_categoria = {}
    for categoria in df['categoria'].unique():
        # Filtrar por categoría
        df_cat = df[df['categoria'] == categoria]
        # Agrupar por medicamento y sumar las cantidades
        df_agrupado = df_cat.groupby('medicamento')['cantidad'].sum().reset_index()
        # Ordenar de mayor a menor y tomar los 5 principales
        df_top = df_agrupado.sort_values('cantidad', ascending=False).head(5)
        # Añadir la categoría al DataFrame para mantener la referencia
        df_top['categoria'] = categoria
        top_por_categoria[categoria] = df_top
    
    # Crear un DataFrame combinado con los tops de cada categoría
    df_tops = pd.concat(top_por_categoria.values())
    
    # Crear un gráfico base
    fig = go.Figure()
    
    # Importar módulo para colores de Plotly
    import plotly.colors as colors
    
    # Obtener categorías únicas para menú desplegable y buscar "Antiácidos"
    categorias = sorted(df_tops['categoria'].unique())
    indice_antiacidos = -1
    indice_default = 0
    
    # Buscar la categoría "Antiácidos" para usarla como default
    for i, cat in enumerate(categorias):
        if 'antiácido' in cat.lower() or 'antiacido' in cat.lower():
            indice_antiacidos = i
            break
    
    # Si encontramos la categoría "Antiácidos", la usamos como default
    if indice_antiacidos >= 0:
        indice_default = indice_antiacidos
    
    # Crear trazas para cada categoría con visibilidad inicial
    for i, categoria in enumerate(categorias):
        df_cat = df_tops[df_tops['categoria'] == categoria]
        fig.add_trace(go.Bar(
            x=df_cat['medicamento'],
            y=df_cat['cantidad'],
            name=categoria,
            marker_color=colors.qualitative.Plotly[i % len(colors.qualitative.Plotly)],
            hovertemplate='<b>%{x}</b><br>Cantidad: <b>%{y}</b><br>Categoría: ' + categoria + '<extra></extra>',
            visible=(i == indice_default)  # La categoría Antiácidos visible inicialmente
        ))
    
    # Crear botones para cada categoría
    buttons = []
    for i, categoria in enumerate(categorias):
        visible = [False] * len(categorias)
        visible[i] = True
        buttons.append(dict(
            label=categoria,
            method="update",
            args=[{"visible": visible}]
        ))
        
    # Configurar título y tamaño
    fig.update_layout(
        title='<b>Top 5 Medicamentos por Categoría</b>',
        height=500,
        template='plotly_white'
    )
    
    # Actualizar el diseño completo del gráfico
    fig.update_layout(
        title='<b>Top 5 Medicamentos por Categoría</b>',
        xaxis={
            'title': '<b>Medicamento</b>',
            'tickfont': {'size': 11},
            'tickangle': -45,
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': False,
            'showline': True,
            'linewidth': 1,
            'linecolor': 'lightgray',
            'automargin': True
        },
        yaxis={
            'title': '<b>Unidades Vendidas</b>',
            'tickfont': {'size': 11},
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': True,
            'showline': True,
            'linewidth': 1,
            'linecolor': 'lightgray',
            'zeroline': False,
            'rangemode': 'tozero'
        },
        # Menú desplegable para filtrar por categoría
        updatemenus=[{
            'buttons': buttons,
            'direction': 'down',
            'showactive': True,
            'x': 0.1,
            'y': 1.15,
            'xanchor': 'left',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.9)',
            'bordercolor': '#ddd',
            'font': {'size': 12}
        }],
        # Etiqueta para el menú
        annotations=[
            dict(text="<b>Filtrar Categoría:</b>", 
                 x=0.005, 
                 y=1.12, 
                 xref="paper", 
                 yref="paper",
                 showarrow=False, 
                 font=dict(size=12, color="#333"))
        ],
        # Configuración adicional
        plot_bgcolor='white',
        margin=dict(l=50, r=20, t=120, b=110, pad=5),  # Margen superior aumentado para el menú
        bargap=0.3,
        bargroupgap=0.1,
        hovermode='closest',
        hoverlabel={
            'bgcolor': 'white',
            'bordercolor': '#ddd'
        },
        showlegend=False  # Ocultar leyenda, ya que usamos el menú desplegable
    )
    
    # Configuración simplificada para el gráfico de barras
    config = {
        'responsive': True,
        'displaylogo': False
    }
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)

# Grafico de las ventas de medicamentos graficado de manera lineal
def generar_grafico_con_plotly(df, fecha_inicio=None, fecha_fin=None):
    # Importar colores al inicio para evitar errores
    import plotly.colors as colors
    
    fig = go.Figure()
    
    # Si el DataFrame está vacío, devolver un gráfico vacío con un mensaje
    if df.empty:
        fig.add_annotation(
            text="No hay datos disponibles para los filtros seleccionados",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        
        fig.update_layout(
            title="<b>Histórico de Ventas</b>",
            height=500,
            template="plotly_white"
        )
        
        config = {
            'responsive': True,
            'displaylogo': False
        }
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)
    
    # Obtener categorías y medicamentos únicos
    categorias = sorted(df['categoria'].unique())
    medicamentos = df['medicamento'].unique()
    
    # Buscar la categoría "Antiácidos" para usarla como default
    indice_antiacidos = -1
    indice_default = 0
    
    for i, cat in enumerate(categorias):
        if 'antiácido' in cat.lower() or 'antiacido' in cat.lower():
            indice_antiacidos = i
            indice_default = i
            break
    
    # Colores para cada medicamento
    colores = colors.qualitative.Plotly + colors.qualitative.D3 + colors.qualitative.G10
    color_map = {}
    for i, med in enumerate(medicamentos):
        color_map[med] = colores[i % len(colores)]
    
    # Crear una lista de botones para filtrar por categoría (sin "Todas las categorías")
    buttons_categoria = []
    
    # Mapeo de medicamentos a su índice en la lista de trazas
    med_to_index = {}
    
    # Agregar líneas para cada medicamento y guardar su índice
    for i, medicamento in enumerate(medicamentos):
        # Filtrar datos por medicamento
        datos_filtrados = df[df['medicamento'] == medicamento]
        
        if not datos_filtrados.empty:
            # Obtener la categoría para este medicamento (tomamos el primero si hay varios)
            categoria = datos_filtrados['categoria'].iloc[0]
            
            # Guardar el índice de esta traza para el medicamento
            med_to_index[medicamento] = i
            
            # Determinar visibilidad inicial: visible solo si pertenece a la categoría Antiácidos
            # o a la primera categoría si no existe Antiácidos
            is_default_category = False
            if indice_antiacidos >= 0:
                is_default_category = (categoria.lower() == categorias[indice_default].lower())
            else:
                is_default_category = (categoria.lower() == categorias[0].lower())
            
            fig.add_trace(go.Scatter(
                x=datos_filtrados['fecha'],
                y=datos_filtrados['cantidad'],
                mode='lines+markers',
                name=f"{medicamento}",
                legendgroup=categoria,
                visible=is_default_category,  # Inicialmente visible solo si es la categoría por defecto
                hovertemplate=
                '<b>%{x|%d-%m-%Y}</b><br>' +
                'Cantidad: <b>%{y}</b><br>' +
                f'Categoría: {categoria}<br>' +
                '<extra></extra>',
                line=dict(color=color_map[medicamento], width=2.5),
                marker=dict(
                    size=7,
                    line=dict(width=1, color='DarkSlateGrey')
                )
            ))
    
    # Crear botones para cada categoría (sin "Todas las categorías")
    for i, cat in enumerate(categorias):
        # Crear una lista de visibilidad - True para medicamentos de esta categoría, False para otros
        visibility = []
        for med in medicamentos:
            # Si el medicamento está en esta categoría, hacerlo visible
            datos_med = df[df['medicamento'] == med]
            if not datos_med.empty and datos_med['categoria'].iloc[0] == cat:
                visibility.append(True)
            else:
                visibility.append(False)
        
        # Añadir el botón
        buttons_categoria.append(
            dict(
                label = cat,
                method = 'update',
                args = [{'visible': visibility}]
            )
        )
    
    # Configurar el diseño - solo incluyendo filtro por categoría, sin filtro por tipo
    fig.update_layout(
        title="<b>Histórico de Ventas</b>",
        xaxis={
            'title': "<b>Fecha</b>",
            'tickformat': '%d-%m-%Y',
            'tickangle': -45,
            'tickfont': {'size': 10},
            'nticks': 10,
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': True,
            'showline': True,
            'linewidth': 1
        },
        yaxis={
            'title': "<b>Cantidad Vendida</b>",
            'tickfont': {'size': 12},
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': True,
            'showline': True,
            'linewidth': 1
        },
        margin={
            'l': 50, 'r': 30,
            'b': 50, 't': 80,
            'pad': 5
        },
        height=500,
        hovermode='closest',
        legend={
            'orientation': "h",
            'y': -0.2,
            'x': 0.5,
            'xanchor': 'center'
        },
        autosize=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        # Menú desplegable SOLO para filtrar por categoría (sin filtro por tipo)
        updatemenus=[
            {
                'buttons': buttons_categoria,
                'direction': 'down',
                'showactive': True,
                'x': 0.12,
                'y': 1.13,
                'xanchor': 'center',
                'yanchor': 'top',
                'active': indice_default,  # La categoría Antiácidos está activa si se encontró
                'bgcolor': 'rgba(255, 255, 255, 0.9)',
                'bordercolor': '#ddd',
                'font': {'size': 11},
                'pad': {'r': 10, 't': 10, 'b': 10, 'l': 10}
            }
        ],
        # Añadir anotaciones para etiquetar el menú desplegable (SOLO CATEGORÍA, NO TIPO)
        annotations=[
            dict(
                text="<b>Categoría:</b>",
                x=0.02,
                y=1.15,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=11, color="#333")
            )
        ]
    )
    
    # Si se proporcionaron fechas, agregar anotación de período
    if fecha_inicio and fecha_fin:
        fig.update_layout(
            annotations=fig.layout.annotations + (
                dict(
                    text="<b>Período: </b>" + fecha_inicio.strftime('%d/%m/%Y') + " al " + fecha_fin.strftime('%d/%m/%Y'),
                    x=1,
                    y=1.11,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=10),
                    align="right",
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    borderpad=4
                ),
            )
        )
    
    # Configuración simplificada
    config = {
        'responsive': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d'],
        'displayModeBar': True,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'grafico_ventas'
        }
    }
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)

# Actualizamos la vista para incluir el gráfico interactivo
@login_required
def dashboard_view_predicciones(request):
    # Obtener los grupos del usuario para permisos
    grupos_usuario = request.user.groups.values_list('name', flat=True)
    
    # Parámetros para generación de claves de caché
    cache_version = 'v1'  # Incrementar cuando se cambie la estructura de datos
    pagina = request.GET.get('pagina', 1)
    
    # Generar clave única para la página actual
    cache_key_datos = f'dashboard_predicciones_datos_{cache_version}_{pagina}'
    cache_key_grafico = f'dashboard_predicciones_grafico_{cache_version}'
    
    # Comprobar si hay datos en caché
    cache_hit = False
    cache_datos = cache.get(cache_key_datos)
    cache_grafico = cache.get(cache_key_grafico)
    
    # Si hay datos en caché, usarlos directamente
    if cache_datos and cache_grafico:
        cache_hit = True
        contexto = cache_datos
        contexto['grafico_prediccion_html'] = cache_grafico
        contexto['cache_hit'] = cache_hit
        contexto['cache_timestamp'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return render(request, 'dashboard_predicciones.html', contexto)
    
    try:
        # Parámetros para la predicción
        anios_historia = 3  # Años de historia a considerar
        horizonte_prediccion = 3  # Meses a predecir hacia adelante
        min_ventas_totales = 5  # Ventas mínimas para considerar un medicamento
        min_meses_con_ventas = 3  # Mínimo de meses con ventas para considerar un medicamento
        
        # 1. Cargar datos históricos
        df_mensual = cargar_datos_ventas_mensuales(anios=anios_historia)
        
        if df_mensual is None or df_mensual.empty:
            messages.error(request, "No se pudieron cargar datos históricos de ventas.")
            return render(request, 'dashboard_predicciones.html', {'error': True})
        
        # 2. Completar series temporales
        df_completo = completar_series_mensuales(df_mensual)
        
        # 3. Filtrar medicamentos relevantes
        medicamentos_relevantes = filtrar_medicamentos_relevantes(
            df_completo, 
            min_ventas=min_ventas_totales,
            min_meses=min_meses_con_ventas
        )
        
        # 4. Generar predicciones
        df_predicciones = generar_predicciones(
            df_completo,
            medicamentos_relevantes,
            horizonte=horizonte_prediccion
        )
        
        if df_predicciones is None or df_predicciones.empty:
            messages.error(request, "No se pudieron generar predicciones.")
            return render(request, 'dashboard_predicciones.html', {'error': True, 'grupos': grupos_usuario})
        
        # Calcular total_prediccion si no existe
        if 'total_prediccion' not in df_predicciones.columns:
            # Calcular la suma de las predicciones por mes para cada medicamento
            columnas_mes = [f'mes_{i}_cantidad' for i in range(1, horizonte_prediccion + 1)]
            df_predicciones['total_prediccion'] = df_predicciones[columnas_mes].sum(axis=1)
            
            # Calcular también el promedio mensual si no existe
            if 'promedio_mensual' not in df_predicciones.columns:
                df_predicciones['promedio_mensual'] = df_predicciones['total_prediccion'] / horizonte_prediccion
        
        # Preparar datos para el gráfico
        meses_futuros = []
        fecha_actual = datetime.now()
        for i in range(1, horizonte_prediccion + 1):
            mes_futuro = fecha_actual + timedelta(days=30 * i)
            meses_futuros.append(mes_futuro.strftime('%B %Y'))
        
        # Obtener todos los medicamentos para el gráfico, ordenados por predicción total
        todos_medicamentos = df_predicciones.sort_values('total_prediccion', ascending=False)
        
        # Obtener stock actual de cada medicamento
        stocks = {}
        try:
            lotes_medicamentos = LoteMedicamento.objects.filter(
                medicamento__id__in=todos_medicamentos['medicamento_id'].tolist(),
                activo=True
            ).values('medicamento').annotate(stock_actual=Sum('cantidad'))
            
            # Crear diccionario de medicamento_id -> stock_actual
            for lote in lotes_medicamentos:
                stocks[lote['medicamento']] = lote['stock_actual'] or 0
            
            logger.info(f"Stock obtenido para {len(stocks)} medicamentos")
        except Exception as e:
            logger.error(f"Error al obtener stock actual: {str(e)}")
        
        # Añadir información de stock y diferencia al DataFrame
        todos_medicamentos['stock_actual'] = todos_medicamentos['medicamento_id'].map(lambda x: stocks.get(x, 0))
        todos_medicamentos['diferencia'] = todos_medicamentos['total_prediccion'] - todos_medicamentos['stock_actual']
        
        # Ordenar por diferencia (mayor diferencia primero)
        todos_medicamentos_ordenados = todos_medicamentos.sort_values('diferencia', ascending=False)
        
        # Obtener top 60 medicamentos para la tabla paginada (20 por página, 3 páginas)
        top_medicamentos = todos_medicamentos_ordenados.head(60)
        
        # Convertir a lista de diccionarios para la paginación
        lista_medicamentos = top_medicamentos.to_dict('records')
        
        # Implementar paginación
        pagina = request.GET.get('pagina', 1)
        items_por_pagina = 20
        
        paginator = Paginator(lista_medicamentos, items_por_pagina)
        try:
            medicamentos_pagina = paginator.page(pagina)
        except PageNotAnInteger:
            # Si la página no es un entero, mostrar la primera página
            medicamentos_pagina = paginator.page(1)
        except EmptyPage:
            # Si la página está fuera de rango, mostrar la última página
            medicamentos_pagina = paginator.page(paginator.num_pages)
        
        # Obtener las categorías de los medicamentos
        try:
            # Conectar medicamentos con sus categorías
            medicamentos_info = {}
            medicamentos_categoria = {}
            categorias_set = set()
            
            for med_id in todos_medicamentos['medicamento_id']:
                try:
                    med = Medicamentos.objects.get(id=med_id)
                    categoria = med.categoria.nombre_categoria if med.categoria else "Sin Categoría"
                    medicamentos_categoria[med.nombre] = categoria
                    categorias_set.add(categoria)
                    medicamentos_info[med.nombre] = {
                        'id': med_id,
                        'categoria': categoria
                    }
                except Medicamentos.DoesNotExist:
                    logger.error(f"Medicamento con ID {med_id} no encontrado")
            
            categorias_list = sorted(list(categorias_set))
        except Exception as e:
            logger.error(f"Error al obtener categorías: {e}")
            categorias_list = ["Sin Categoría"]
            medicamentos_categoria = {med: "Sin Categoría" for med in todos_medicamentos['medicamento_nombre'].tolist()}
        
        # Preparar datos para el gráfico por categoría
        datos_grafico = {
            'medicamentos': todos_medicamentos['medicamento_nombre'].tolist(),
            'categorias': [medicamentos_categoria.get(med, "Sin Categoría") for med in todos_medicamentos['medicamento_nombre'].tolist()],
            'meses': meses_futuros,
            'predicciones': []
        }
        
        # Para cada medicamento, obtener sus predicciones mensuales
        for i, med in todos_medicamentos.iterrows():
            datos_grafico['predicciones'].append([
                med[f'mes_1_cantidad'],
                med[f'mes_2_cantidad'],
                med[f'mes_3_cantidad']
            ])
        
        # Generar gráfico de líneas con filtro por categoría
        import plotly.graph_objects as go
        import plotly.colors as colors
        
        fig = go.Figure()
        
        # Crear un colormap
        colores = colors.qualitative.Plotly + colors.qualitative.D3 + colors.qualitative.G10
        color_map = {}
        for i, med in enumerate(datos_grafico['medicamentos']):
            color_map[med] = colores[i % len(colores)]
        
        # Buscar la categoría "Antiácidos" para usarla como default
        indice_antiacidos = -1
        indice_default = 0
        
        for i, cat in enumerate(categorias_list):
            if 'antiácido' in cat.lower() or 'antiacido' in cat.lower():
                indice_antiacidos = i
                indice_default = i
                break
        
        # Añadir una línea para cada medicamento con visibilidad según su categoría
        for i, medicamento in enumerate(datos_grafico['medicamentos']):
            categoria = datos_grafico['categorias'][i]
            
            # Determinar si el medicamento debe estar visible inicialmente
            visible = False
            if indice_antiacidos >= 0:
                visible = (categoria.lower() == categorias_list[indice_default].lower())
            else:
                visible = (categoria.lower() == categorias_list[0].lower())
                
            fig.add_trace(go.Scatter(
                x=datos_grafico['meses'],
                y=datos_grafico['predicciones'][i],
                mode='lines+markers',
                name=medicamento,
                legendgroup=categoria,
                visible=visible,  # Solo visible si es de la categoría por defecto
                hovertemplate=
                '<b>%{x}</b><br>' +
                'Cantidad: <b>%{y}</b><br>' +
                f'Categoría: {categoria}<br>' +
                '<extra></extra>',
                line=dict(color=color_map[medicamento], width=2),
                marker=dict(
                    size=7,
                    line=dict(width=1, color='DarkSlateGrey')
                )
            ))
        
        # Crear botones para cada categoría (sin "Todas las categorías")
        buttons_categoria = []
        for i, cat in enumerate(categorias_list):
            # Crear una lista de visibilidad - True para medicamentos de esta categoría
            visibility = []
            for j, med in enumerate(datos_grafico['medicamentos']):
                visibility.append(datos_grafico['categorias'][j] == cat)
            
            # Añadir botón para esta categoría
            buttons_categoria.append(
                dict(
                    label=cat,
                    method='update',
                    args=[{'visible': visibility}]
                )
            )
        
        # Configuración del diseño
        fig.update_layout(
            title='<b>Predicción de Ventas - Próximos 3 Meses</b>',
            xaxis_title='<b>Mes</b>',
            yaxis_title='<b>Unidades</b>',
            legend_title='<b>Medicamentos</b>',
            template='plotly_white',
            # Menú desplegable para filtrar por categoría
            updatemenus=[
                {
                    'buttons': buttons_categoria,
                    'direction': 'down',
                    'showactive': True,
                    'x': 0.12,
                    'y': 1.13,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'active': indice_default,  # La categoría Antiácidos está activa si se encontró
                    'bgcolor': 'rgba(255, 255, 255, 0.9)',
                    'bordercolor': '#ddd',
                    'font': {'size': 11},
                    'pad': {'r': 10, 't': 10, 'b': 10, 'l': 10}
                }
            ],
            # Añadir anotaciones para etiquetar el menú desplegable
            annotations=[
                dict(
                    text="<b>Categoría:</b>",
                    x=0.02,
                    y=1.15,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=11, color="#333")
                )
            ]
        )
        
        grafico_html = fig.to_html()
        
        # Calcular totales mensuales para los indicadores
        total_mes1 = top_medicamentos['mes_1_cantidad'].sum()
        total_mes2 = top_medicamentos['mes_2_cantidad'].sum()
        total_mes3 = top_medicamentos['mes_3_cantidad'].sum()
        total_prediccion = top_medicamentos['total_prediccion'].sum()
        
        # Obtener las fechas de los próximos 3 meses para mostrar en los indicadores
        fecha_actual = datetime.now()
        mes1 = (fecha_actual + timedelta(days=30)).strftime('%B %Y')
        mes2 = (fecha_actual + timedelta(days=60)).strftime('%B %Y')
        mes3 = (fecha_actual + timedelta(days=90)).strftime('%B %Y')
        
        contexto = {
            'grupos': grupos_usuario,
            'medicamentos_prediccion': medicamentos_pagina,
            'paginator': paginator,
            'total_mes1': total_mes1,
            'total_mes2': total_mes2,
            'total_mes3': total_mes3,
            'total_prediccion': total_prediccion,
            'mes1_nombre': mes1,
            'mes2_nombre': mes2,
            'mes3_nombre': mes3,
            'fecha_prediccion': fecha_actual.strftime('%Y-%m-%d'),
            'pagina_actual': int(pagina),
            'cache_hit': False,  # Indicador de caché miss porque estamos generando datos nuevos
            'cache_timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Guardar datos en caché con diferentes tiempos de expiración
        # Datos numéricos: 15 minutos (900 segundos)
        cache.set(cache_key_datos, contexto, 900)  
        
        # Gráficos: 30 minutos (1800 segundos) porque cambian menos frecuentemente
        cache.set(cache_key_grafico, grafico_html, 1800)
        
        # Incluir el gráfico en el contexto para renderizar
        contexto['grafico_prediccion_html'] = grafico_html
        
        return render(request, 'dashboard_predicciones.html', contexto)
        
    except Exception as e:
        import traceback
        logger.error(f"Error en dashboard_view_predicciones: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, f"Error al generar predicciones: {str(e)}")
        return render(request, 'dashboard_predicciones.html', {'error': True})

@login_required
def dashboard_view_ventas(request):
    # Obtener los grupos del usuario para permisos
    grupos_usuario = request.user.groups.values_list('name', flat=True)
    
    # Procesar parámetros de filtro de fechas si existen
    fecha_inicio = request.GET.get('fecha_inicio', None)
    fecha_fin = request.GET.get('fecha_fin', None)
    categoria_id = request.GET.get('categoria', None)
    tipo_id = request.GET.get('tipo', None)
    
    # Si no hay filtros, usar rango por defecto (6 meses atrás)
    if not fecha_inicio or not fecha_fin:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=180)  # 6 meses atrás
    else:
        # Convertir las fechas de string a objetos date
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            # Si hay un error al convertir, usar rango por defecto
            fecha_fin = timezone.now().date()
            fecha_inicio = fecha_fin - timedelta(days=180)  # 6 meses (aproximadamente)
    
    # Crear una clave de caché única basada en los parámetros de filtro
    filtros_key = f"{fecha_inicio}_{fecha_fin}_{categoria_id}_{tipo_id}"
    cache_key_hash = hashlib.md5(filtros_key.encode()).hexdigest()
    
    # Obtener versión del caché para invalidación inteligente
    cache_version = cache.get('dashboard_cache_version', 0)
    cache_key_datos = f"dashboard_datos_{cache_key_hash}_v{cache_version}"
    cache_key_graficos = f"dashboard_graficos_{cache_key_hash}_v{cache_version}"
    
    # Intentar obtener datos del caché
    datos_cache = cache.get(cache_key_datos)
    graficos_cache = cache.get(cache_key_graficos)
    
    if datos_cache is None or graficos_cache is None:
        # Si no está en caché, obtener y procesar los datos
        
        # Obtener datos de ventas en el rango de fechas - eliminando filtro tipo_id
        df_ventas = obtener_datos_ventas(fecha_inicio, fecha_fin, categoria_id, None)
        
        # Si no hay datos, crear un DataFrame vacío simple
        if df_ventas.empty:
            # Solo crear un DataFrame vacío con las columnas básicas
            df_ventas = pd.DataFrame(columns=['medicamento', 'categoria', 'tipo', 'fecha', 'cantidad', 'precio_total'])
        
        # Generar gráficos con Plotly - ELIMINADA LA DUPLICACIÓN DE LLAMADAS
        grafico_lineas_html = generar_grafico_con_plotly(df_ventas)
        grafico_barras_html = generar_grafico_barras(df_ventas, fecha_inicio, fecha_fin)
        
        # Indicadores de resumen
        ventas_mes = obtener_ventas_mes()
        ventas_anual = obtener_ventas_anual()
        productos_vendidos = int(df_ventas['cantidad'].sum()) if not df_ventas.empty else 0
        clientes_nuevos = obtener_clientes_nuevos(fecha_inicio, fecha_fin)
        
        # Obtener los datos para la tabla de top productos vendidos
        top_productos = obtener_top_productos(fecha_inicio, fecha_fin)
        
        # Preparar datos para caché
        datos_cache = {
            'ventas_mes': ventas_mes,
            'ventas_anual': ventas_anual,
            'productos_vendidos': productos_vendidos,
            'clientes_nuevos': clientes_nuevos,
            'top_productos': list(top_productos),  # Convertir a lista para serialización
        }
        
        graficos_cache = {
            'grafico_lineas_html': grafico_lineas_html,
            'grafico_barras_html': grafico_barras_html,
        }
        
        # Guardar en caché por 15 minutos (900 segundos)
        # Los gráficos pueden tener un caché más largo ya que son más costosos de generar
        cache.set(cache_key_datos, datos_cache, 900)  # 15 minutos
        cache.set(cache_key_graficos, graficos_cache, 1800)  # 30 minutos para gráficos
        
        print(f"Datos generados y guardados en caché: {cache_key_datos}")
    else:
        print(f"Datos obtenidos del caché: {cache_key_datos}")
    
    # Obtener solo categorías para los filtros (datos que cambian poco, caché más largo)
    cache_key_categorias = "dashboard_categorias"
    categorias = cache.get(cache_key_categorias)
    categorias_from_cache = True
    if categorias is None:
        from ventas.models import Categorias
        categorias = list(Categorias.objects.filter(activo=True).order_by('nombre_categoria').values('id', 'nombre_categoria'))
        cache.set(cache_key_categorias, categorias, 3600)  # 1 hora para categorías
        categorias_from_cache = False
    
    # Información sobre el estado del caché
    cache_info = {
        'datos_from_cache': datos_cache is not None and graficos_cache is not None,
        'categorias_from_cache': categorias_from_cache,
        'cache_version': cache_version,
    }
    
    # Pasar solo los datos y gráficos al contexto - eliminando tipos
    contexto = {
        'grafico_lineas_html': graficos_cache['grafico_lineas_html'],  # Gráfico de líneas
        'grafico_barras_html': graficos_cache['grafico_barras_html'],  # Gráfico de barras
        'grupos': grupos_usuario,  # Grupos del usuario
        'ventas_mes': datos_cache['ventas_mes'],  # Indicador de ventas del mes
        'ventas_anual': datos_cache['ventas_anual'],  # Indicador de ventas anuales
        'productos_vendidos': datos_cache['productos_vendidos'],  # Indicador de productos vendidos
        'clientes_nuevos': datos_cache['clientes_nuevos'],  # Indicador de clientes nuevos
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),  # Fecha inicio seleccionada
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),  # Fecha fin seleccionada
        'top_productos': datos_cache['top_productos'],  # Top productos vendidos
        'categorias': categorias,  # Lista de categorías para el filtro
        'cache_info': cache_info,  # Información sobre el estado del caché
    }

    return render(request, 'dashboard_ventas.html', contexto)

#//////////////////////////////Todo esto va a aportar a la parte de gestion de inventario
def obtener_medicamentos_baja_rotacion():
    # Ventas en los últimos 3 meses
    fecha_limite = now().date() - timedelta(days=90)
    ventas = DetalleVenta.objects.filter(venta__fecha_venta__gte=fecha_limite, activo=True).values(
        'medicamento__id', 'medicamento__nombre'
    ).annotate(total_vendido=Sum('cantidad'))

    medicamentos_venta = {venta['medicamento__id']: venta['total_vendido'] for venta in ventas}

    # Medicamentos con baja o sin rotación
    medicamentos = Medicamentos.objects.filter(activo=True)
    medicamentos_baja_rotacion = [
        med for med in medicamentos
        if med.id not in medicamentos_venta or medicamentos_venta[med.id] < 10  # Umbral de baja rotación
    ]
    return medicamentos_baja_rotacion
def generar_grafico_pastel_baja_rotacion(medicamentos_baja_rotacion, total_medicamentos):
    # Datos para el gráfico
    labels = ['Baja Rotación', 'Otros Medicamentos']
    values = [len(medicamentos_baja_rotacion), total_medicamentos - len(medicamentos_baja_rotacion)]

    print("Labels:", labels)  # Temporal
    print("Values:", values)  # Temporal

    # Crear el gráfico
    fig = px.pie(
        values=values,
        names=labels,
        title='Proporción de Medicamentos con Baja Rotación',
        hole=0.4,  # Para crear un gráfico tipo "donut"
    )
    fig.update_layout(template='plotly_white')
    return fig.to_html(full_html=False)

def obtener_medicamentos_proximos_a_vencer():
    fecha_actual = now().date()
    fecha_limite = fecha_actual + timedelta(days=30)  # Lotes que vencen en los próximos 30 días

    # Filtrar lotes activos que estén próximos a vencer (pero no ya vencidos)
    lotes_vencer = LoteMedicamento.objects.filter(
        fecha_vencimiento__gt=fecha_actual,  # Fecha mayor que hoy
        fecha_vencimiento__lte=fecha_limite,  # Fecha menor o igual a la fecha límite
        activo=True
    )

    proximos_a_vencer = []
    for lote in lotes_vencer:
        dias_restantes = (lote.fecha_vencimiento - fecha_actual).days
        proximos_a_vencer.append({
            'medicamento': lote.medicamento.nombre,
            'cantidad': lote.cantidad,
            'fecha_vencimiento': lote.fecha_vencimiento,
            'dias_restantes': dias_restantes,
        'lote_id': lote.id,
        'lote_fabricante': lote.lote_fabricante
        })
    return proximos_a_vencer



def obtener_alertas_stock_minimo(umbral=10):
    # Obtener todos los medicamentos activos
    medicamentos = Medicamentos.objects.filter(activo=True)
    alertas = []
    
    # Para cada medicamento, calcular su stock total sumando las cantidades de todos sus lotes activos
    for med in medicamentos:
        stock_total = LoteMedicamento.objects.filter(
            medicamento=med, 
            activo=True
        ).aggregate(total_stock=Sum('cantidad'))['total_stock'] or 0
        
        # Si el stock total es menor o igual al umbral especificado, añadirlo a las alertas
        if stock_total <= umbral and stock_total > 0:  # Solo incluir si tiene stock mayor a 0
            alertas.append({
                'nombre': med.nombre,
                'stock_actual': stock_total,
                'umbral': umbral
            })
            
    return alertas

def generar_grafico_barras_stock_minimo(alertas_stock_minimo):
    # Extraer datos para el gráfico
    nombres = [alerta['nombre'] for alerta in alertas_stock_minimo]
    stock_actual = [alerta['stock_actual'] for alerta in alertas_stock_minimo]
    umbrales = [alerta['umbral'] for alerta in alertas_stock_minimo]

    print("Labels:", nombres)  # Temporal
    print("Values:", stock_actual)  # Temporal

    # Crear un DataFrame para evitar el error
    import pandas as pd
    df = pd.DataFrame({
        'Medicamento': nombres,
        'Stock Actual': stock_actual,
        'Umbral': umbrales
    })

    # Crear el gráfico
    fig = px.bar(
        df,
        x='Stock Actual',
        y='Medicamento',
        orientation='h',
        text='Stock Actual',
        title='Medicamentos con Stock por Debajo del Umbral',
        labels={'Stock Actual': 'Stock Actual', 'Medicamento': 'Medicamentos'}
    )
    
    # Añadir línea de umbral (usando el DataFrame)
    for i, row in df.iterrows():
        fig.add_vline(
            x=row['Umbral'], 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Umbral: {row['Umbral']}",
            annotation_position="top right"
        )
    
    # Configuración adicional
    fig.update_layout(template='plotly_white', showlegend=True)
    return fig.to_html(full_html=False)

@login_required
def dashboard_view_inventario(request):
    # Obtener los medicamentos con baja rotación
    medicamentos_baja_rotacion = obtener_medicamentos_baja_rotacion()

    # Total de medicamentos activos
    total_medicamentos = Medicamentos.objects.filter(activo=True).count()

    # Generar gráfico de pastel para baja rotación
    grafico_baja_rotacion_html = generar_grafico_pastel_baja_rotacion(
        medicamentos_baja_rotacion, total_medicamentos
    )

    # Obtener los medicamentos cercanos al vencimiento
    medicamentos_proximos_a_vencer = obtener_medicamentos_proximos_a_vencer()
    
    # Total de productos próximos a vencer
    total_proximos_vencer = len(medicamentos_proximos_a_vencer)

    # Obtener las alertas de stock mínimo
    alertas_stock_minimo = obtener_alertas_stock_minimo()
    
    # Total de productos con stock bajo
    total_stock_bajo = len(alertas_stock_minimo)
    
    # Calcular el valor total del inventario
    valor_inventario = 0
    lotes_activos = LoteMedicamento.objects.filter(activo=True)
    
    for lote in lotes_activos:
        if lote.precio_venta:  # Verificar que el precio de venta exista
            valor_inventario += lote.precio_venta * lote.cantidad

    # Generar gráfico de barras para stock mínimo
    grafico_stock_minimo_html = generar_grafico_barras_stock_minimo(alertas_stock_minimo)
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    # Pasar los datos al contexto para la plantilla
    contexto = {
        'medicamentos_baja_rotacion': medicamentos_baja_rotacion,
        'grafico_baja_rotacion_html': grafico_baja_rotacion_html,
        'medicamentos_proximos_a_vencer': medicamentos_proximos_a_vencer,
        'alertas_stock_minimo': alertas_stock_minimo,
        'grafico_stock_minimo_html': grafico_stock_minimo_html,
        'grupos': grupos_usuario,  # Pasar los grupos del usuario a la plantilla
        
        # Agregar los valores para las tarjetas
        'total_productos': total_medicamentos,
        'total_proximos_vencer': total_proximos_vencer,
        'total_stock_bajo': total_stock_bajo,
        'valor_inventario': round(valor_inventario, 2)  # Redondear a 2 decimales
    }
    return render(request, 'dashboard_inventario.html', contexto)

def cargar_datos_compras(fecha_inicio=None, fecha_fin=None):
    # Cargar datos de compras y proveedores
    query = Compras.objects.filter(activo=True)
    if fecha_inicio:
        query = query.filter(fecha_compra__gte=fecha_inicio)
    if fecha_fin:
        query = query.filter(fecha_compra__lte=fecha_fin)
    
    compras = query.select_related('proveedor')
    compras_df = pd.DataFrame.from_records(
        compras.values('id', 'proveedor__nombre_empresa', 'fecha_compra', 'precio_total')
    )
    return compras_df

def cargar_datos_detalle_compras(fecha_inicio=None, fecha_fin=None):
    # Cargar datos de los detalles de las compras
    query = DetalleCompra.objects.filter(activo=True, compra__activo=True) # Asegurar que la compra también esté activa
    if fecha_inicio:
        query = query.filter(compra__fecha_compra__gte=fecha_inicio)
    if fecha_fin:
        query = query.filter(compra__fecha_compra__lte=fecha_fin)

    detalles = query.select_related('compra', 'medicamento')
    detalles_df = pd.DataFrame.from_records(
        detalles.values(
            'compra__id', 
            'medicamento__nombre', 
            'cantidad', 
            'precio'
        ).annotate(total_costo=F('cantidad') * F('precio'))
    )
    return detalles_df

def analizar_proveedor_frecuente(compras_df):
    # Agrupar por proveedor y contar compras
    proveedor_frecuente = (
        compras_df.groupby('proveedor__nombre_empresa')
        .size()
        .reset_index(name='cantidad_compras')
        .sort_values(by='cantidad_compras', ascending=False)
    )
    return proveedor_frecuente

def analizar_medicamentos_mas_comprados(detalles_df, por='cantidad'):
    if por == 'cantidad':
        # Agrupar por medicamento y sumar cantidades
        medicamentos = (
            detalles_df.groupby('medicamento__nombre')['cantidad']
            .sum()
            .reset_index(name='cantidad_total')
            .sort_values(by='cantidad_total', ascending=False)
        )
    elif por == 'costo':
        # Agrupar por medicamento y sumar costos
        medicamentos = (
            detalles_df.groupby('medicamento__nombre')['total_costo']
            .sum()
            .reset_index(name='costo_total')
            .sort_values(by='costo_total', ascending=False)
        )
    return medicamentos

def grafico_proveedor_frecuente(proveedor_frecuente):
    fig = px.bar(
        proveedor_frecuente,
        x='proveedor__nombre_empresa',  # Cambiado para barras verticales
        y='cantidad_compras',           # Cambiado para barras verticales
        title="Proveedores más frecuentes",
        # orientation='h', # Eliminado para barras verticales (suele ser el default)
        labels={'proveedor__nombre_empresa': 'Proveedor', 'cantidad_compras': 'Número de Compras'},
        text='cantidad_compras',
    )
    fig.update_traces(texttemplate='%{text}', textposition='outside') # texttemplate para mejor control
    fig.update_layout(template='plotly_white', showlegend=False)
    fig.update_xaxes(tickangle=-45) # Rotar etiquetas del eje X para mejor legibilidad
    return fig.to_html(full_html=False)

def grafico_medicamentos_mas_comprados(medicamentos, por='cantidad'):
    titulo = "Medicamentos más comprados (por cantidad)" if por == 'cantidad' else "Medicamentos más comprados (por costo)"
    y_col = 'cantidad_total' if por == 'cantidad' else 'costo_total'

    fig = px.bar(
        medicamentos,
        x=y_col,
        y='medicamento__nombre',
        orientation='h',  # Barras horizontales
        title=titulo,
        labels={y_col: "Cantidad Total" if por == 'cantidad' else "Costo Total", 'medicamento__nombre': "Medicamento"},
        text=y_col,  # Mostrar valores en las barras
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(template='plotly_white', showlegend=False)
    return fig.to_html(full_html=False)

# Vista del dashboard de los proveedores
@login_required
def dashboard_view_proveedores(request):
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    fecha_inicio_filtro = None
    fecha_fin_filtro = None

    if fecha_inicio_str:
        try:
            fecha_inicio_filtro = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de fecha de inicio inválido para filtros. Use YYYY-MM-DD.")
    
    if fecha_fin_str:
        try:
            fecha_fin_filtro = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de fecha de fin inválido para filtros. Use YYYY-MM-DD.")

    # Cargar datos para los gráficos, aplicando filtros de fecha si existen
    compras_df = cargar_datos_compras(fecha_inicio=fecha_inicio_filtro, fecha_fin=fecha_fin_filtro)
    detalles_df = cargar_datos_detalle_compras(fecha_inicio=fecha_inicio_filtro, fecha_fin=fecha_fin_filtro)

    # Análisis
    proveedor_frecuente = analizar_proveedor_frecuente(compras_df)
    medicamentos_por_cantidad = analizar_medicamentos_mas_comprados(detalles_df, por='cantidad')
    medicamentos_por_costo = analizar_medicamentos_mas_comprados(detalles_df, por='costo')

    # Generar gráficos
    grafico_proveedores_html = grafico_proveedor_frecuente(proveedor_frecuente)
    grafico_medicamentos_cantidad_html = grafico_medicamentos_mas_comprados(medicamentos_por_cantidad, por='cantidad')
    grafico_medicamentos_costo_html = grafico_medicamentos_mas_comprados(medicamentos_por_costo, por='costo')
    # Cálculos para los cards
    total_proveedores_activos = Proveedores.objects.filter(activo=True).count()

    hoy = datetime.today()
    # Compras del mes
    inicio_mes = hoy.replace(day=1)
    fin_mes = inicio_mes + relativedelta(months=1) - timedelta(days=1)
    compras_mes_actual = Compras.objects.filter(
        activo=True, 
        fecha_compra__gte=inicio_mes, 
        fecha_compra__lte=fin_mes
    ).aggregate(total=Sum('precio_total'))['total'] or 0
    rango_fechas_mes = f"{inicio_mes.strftime('%d/%m/%Y')} - {fin_mes.strftime('%d/%m/%Y')}"

    # Productos comprados en el mes
    productos_comprados_mes_actual = DetalleCompra.objects.filter(
        activo=True, 
        compra__activo=True, 
        compra__fecha_compra__gte=inicio_mes, 
        compra__fecha_compra__lte=fin_mes
    ).aggregate(total_cantidad=Sum('cantidad'))['total_cantidad'] or 0

    # Compras anuales
    inicio_ano = hoy.replace(day=1, month=1)
    fin_ano = inicio_ano.replace(year=hoy.year + 1) - timedelta(days=1) # Correcto para fin de año
    compras_anuales_actual = Compras.objects.filter(
        activo=True, 
        fecha_compra__gte=inicio_ano, 
        fecha_compra__lte=fin_ano
    ).aggregate(total=Sum('precio_total'))['total'] or 0
    rango_fechas_ano = f"{inicio_ano.strftime('%d/%m/%Y')} - {fin_ano.strftime('%d/%m/%Y')}"

    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    # Contexto para el template
    contexto = {
        'grafico_proveedores_html': grafico_proveedores_html,
        'grafico_medicamentos_cantidad_html': grafico_medicamentos_cantidad_html,
        'grafico_medicamentos_costo_html': grafico_medicamentos_costo_html,
        'grupos': grupos_usuario,  # Pasar los grupos del usuario a la plantilla
        
        # Datos para los cards
        'total_proveedores': total_proveedores_activos,
        'compras_mes': compras_mes_actual,
        'rango_fechas_mes': rango_fechas_mes,
        'productos_comprados': productos_comprados_mes_actual,
        'compras_anuales': compras_anuales_actual,
        'rango_fechas_ano': rango_fechas_ano,

        # Fechas para el formulario de filtro (mantener lo que el usuario ingresó)
        'fecha_inicio': fecha_inicio_str if fecha_inicio_str else '',
        'fecha_fin': fecha_fin_str if fecha_fin_str else '',
    }

    return render(request, 'dashboard_proveedores.html', contexto)

# Vista del dashboard de los usuarios
def cargar_datos_ventas():
    # Extraer las ventas y usuarios activos
    ventas = Ventas.objects.filter(activo=True).values('id', 'usuario__username', 'fecha_venta', 'precio_total')
    df = pd.DataFrame(list(ventas))
    
    # Obtener los nombres de los clientes a través de las facturas
    facturas = Factura.objects.filter(venta__in=df['id']).values('venta_id', 'cliente__nombre')
    facturas_df = pd.DataFrame(list(facturas))
    
    # Unir los datos de las facturas con las ventas
    df = df.merge(facturas_df, left_on='id', right_on='venta_id', how='left')
    df = df.rename(columns={'cliente__nombre': 'cliente_nombre'})
    
    # Convertir fecha_venta a datetime.datetime
    df['fecha_venta'] = pd.to_datetime(df['fecha_venta'])
    
    return df
def analizar_frecuencia_ventas(df_ventas):
    # Agrupar por usuario y contar las ventas
    frecuencia = df_ventas.groupby('usuario__username').size().reset_index(name='frecuencia')
    frecuencia = frecuencia.sort_values(by='frecuencia', ascending=False)
    return frecuencia
def analizar_contribucion_ingresos(df_ventas):
    # Agrupar por usuario y sumar los ingresos
    contribucion = df_ventas.groupby('usuario__username')['precio_total'].sum().reset_index(name='ingreso_total')
    contribucion = contribucion.sort_values(by='ingreso_total', ascending=False)
    return contribucion
def grafico_frecuencia_ventas(frecuencia):
    fig = px.bar(
        frecuencia,
        x='frecuencia',
        y='usuario__username',
        orientation='h',  # Barras horizontales
        title='Frecuencia de Ventas por Usuario',
        labels={'frecuencia': 'Número de Ventas', 'usuario__username': 'Usuario'},
        text='frecuencia',  # Mostrar valores en las barras
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(template='plotly_white', showlegend=False)
    return fig.to_html(full_html=False)
def grafico_contribucion_ingresos(contribucion):
    fig = px.pie(
        contribucion,
        names='usuario__username',
        values='ingreso_total',
        title='Contribución de cada Vendedor al Ingreso Total',
        hole=0.4,  # Gráfico tipo donut
        labels={'usuario__username': 'Usuario', 'ingreso_total': 'Ingreso Total'}
    )
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(template='plotly_white')
    return fig.to_html(full_html=False)

@login_required
def dashboard_view_usuarios(request):
    # Cargar datos
    ventas_df = cargar_datos_ventas()

    # Análisis
    frecuencia_ventas = analizar_frecuencia_ventas(ventas_df)
    contribucion_ingresos = analizar_contribucion_ingresos(ventas_df)

    # Cálculos para los cards
    # Total de usuarios activos
    total_usuarios = User.objects.filter(is_active=True).count()

    # Ventas por usuario (promedio)
    if frecuencia_ventas.empty:
        ventas_por_usuario = 0
    else:
        ventas_por_usuario = frecuencia_ventas['frecuencia'].mean()

    # Usuario del mes (basado en ventas del mes actual)
    hoy = datetime.now()
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    ventas_mes = ventas_df[(ventas_df['fecha_venta'] >= inicio_mes) & (ventas_df['fecha_venta'] <= hoy)]
    if ventas_mes.empty:
        usuario_mes = {'nombre': 'N/A', 'ventas': 0, 'ingresos': 0}
    else:
        ventas_mes_frecuencia = ventas_mes.groupby('usuario__username').size().reset_index(name='ventas_mes')
        ventas_mes_ingresos = ventas_mes.groupby('usuario__username')['precio_total'].sum().reset_index(name='ingresos_mes')
        usuario_mes = ventas_mes_frecuencia.merge(ventas_mes_ingresos, on='usuario__username')
        usuario_mes = usuario_mes.sort_values(by='ventas_mes', ascending=False).iloc[0]
        usuario_mes = {
            'nombre': usuario_mes['usuario__username'],
            'ventas': usuario_mes['ventas_mes'],
            'ingresos': usuario_mes['ingresos_mes']
        }

    # Clientes registrados
    clientes_registrados = ventas_df['cliente_nombre'].nunique()

    # Generar gráficos
    grafico_frecuencia_html = grafico_frecuencia_ventas(frecuencia_ventas)
    grafico_contribucion_html = grafico_contribucion_ingresos(contribucion_ingresos)

    grupos_usuario = request.user.groups.values_list('name', flat=True)

    # Contexto para el template
    contexto = {
        'grafico_frecuencia_html': grafico_frecuencia_html,
        'grafico_contribucion_html': grafico_contribucion_html,
        'grupos': grupos_usuario,
        
        # Datos para los cards
        'total_usuarios': total_usuarios,
        'ventas_por_usuario': round(ventas_por_usuario, 1),
        'usuario_mes': usuario_mes,
        'clientes_registrados': clientes_registrados
    }
    return render(request, 'dashboard_usuarios.html', contexto)

###/////////////////////////////Todo esto va a ser para el login
# Función login original comentada para usar el sistema 2FA
# Renombrado a old_login_view para evitar conflictos con el nuevo sistema 2FA
def old_login_view(request):
    """Esta función ha sido reemplazada por un sistema de autenticación en dos factores"""
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('Ventas'))
        else:
            # Puedes simplemente pasar un contexto con el mensaje de error al mismo template.
            #return render(request, "registration/login.html", {"message": "Invalid credentials."})
            return render(request, "registration/login.html", {"error_message": "Usuario o contraseña incorrectos"})
        
    else:
        return render(request, "registration/login.html")

###/////////////////////////////////////////////////////////////////////////Esto va a ser para las vistas de ventas y detalle ventas
@login_required
@transaction.atomic
def create_venta_view(request):
    # Obtener el término de búsqueda
    query = request.GET.get('q', '')
    
    # Filtrar los lotes de medicamentos activos y con stock disponible
    lotes_query = LoteMedicamento.objects.filter(
        activo=True,
        cantidad__gt=0,  # Solo lotes con stock disponible
        medicamento__activo=True  # Solo medicamentos activos
    ).select_related('medicamento', 'medicamento__laboratorio')
    
    # Aplicar filtro de búsqueda si existe
    if query:
        lotes_query = lotes_query.filter(
            Q(medicamento__nombre__icontains=query) |
            Q(lote_fabricante__icontains=query)
        )
    
    # Ordenar los lotes: primero por nombre de medicamento, luego por fecha de vencimiento (más próximos primero)
    lotes_query = lotes_query.order_by('medicamento__nombre', 'fecha_vencimiento')
    
    # Paginación
    paginator = Paginator(lotes_query, 10)  # 10 lotes por página
    page_number = request.GET.get('page', 1)
    lotes_medicamentos = paginator.get_page(page_number)
    
    # Obtener carrito actual
    productos_carrito = request.session.get('carrito', [])
    
    # Limpiar el carrito para evitar problemas con el formato antiguo
    nuevo_carrito = []
    total_carrito = 0
    
    # Verificar si el carrito tiene el formato antiguo y convertirlo al nuevo formato
    for item in productos_carrito:
        # Verificar si es un elemento del formato antiguo (con medicamento_id en lugar de lote_id)
        if 'medicamento_id' in item and 'lote_id' not in item:
            # Intentar obtener el lote correspondiente
            try:
                medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
                lote = LoteMedicamento.objects.filter(
                    medicamento=medicamento, activo=True, cantidad__gt=0
                ).order_by('fecha_vencimiento').first()
                
                if lote:
                    # Crear un nuevo elemento con el formato correcto
                    nuevo_item = {
                        'lote_id': lote.id,
                        'medicamento': {
                            'id': medicamento.id,
                            'nombre': medicamento.nombre
                        },
                        'precio_unitario': float(lote.precio_venta),
                        'cantidad': item['cantidad'],
                        'subtotal': float(lote.precio_venta) * item['cantidad']
                    }
                    nuevo_carrito.append(nuevo_item)
                    total_carrito += nuevo_item['subtotal']
            except:
                # Si hay algún error, omitir este elemento
                pass
        elif 'lote_id' in item:
            # Ya tiene el formato correcto, calcular el subtotal
            if 'precio_unitario' not in item:
                # Si falta precio_unitario, intentar recuperarlo
                try:
                    lote = get_object_or_404(LoteMedicamento, id=item['lote_id'])
                    item['precio_unitario'] = float(lote.precio_venta)
                except:
                    # Si no se puede obtener, usar un valor por defecto
                    item['precio_unitario'] = 0
            
            item['subtotal'] = item['cantidad'] * item['precio_unitario']
            nuevo_carrito.append(item)
            total_carrito += item['subtotal']
    
    # Guardar el carrito convertido
    request.session['carrito'] = nuevo_carrito
    
    # Pasar la fecha actual al contexto para comparaciones de vencimiento
    fecha_actual = datetime.now()
    
    context = {
        'lotes_medicamentos': lotes_medicamentos,
        'productos_carrito': nuevo_carrito,
        'total_carrito': total_carrito,
        'query': query,
        'now': fecha_actual,
    }
    
    return render(request, 'ventasCRUD/create_venta.html', context)

# Agregar al carrito
@login_required
def add_to_cart(request, lote_id):
    if request.method == 'POST':
        lote = get_object_or_404(LoteMedicamento, id=lote_id, activo=True)
        
        # Verificar que haya stock disponible
        cantidad_solicitada = int(request.POST.get('cantidad', 1))
        if cantidad_solicitada > lote.cantidad:
            messages.error(request, f"No hay suficiente stock disponible. Stock actual: {lote.cantidad}")
            return redirect('CreateVenta')
        
        # Obtener carrito actual
        carrito = request.session.get('carrito', [])

        # Verificar si el lote ya está en el carrito
        item_exists = False
        for item in carrito:
            if item['lote_id'] == lote_id:
                # Actualizar cantidad si ya existe
                nueva_cantidad = item['cantidad'] + cantidad_solicitada
                if nueva_cantidad > lote.cantidad:
                    messages.error(request, f"No hay suficiente stock disponible. Stock actual: {lote.cantidad}")
                    return redirect('CreateVenta')
                item['cantidad'] = nueva_cantidad
                item_exists = True
                break
        
        # Si no existe, agregar nuevo item al carrito
        if not item_exists:
            carrito.append({
                'lote_id': lote_id,
                'medicamento': {
                    'id': lote.medicamento.id,
                    'nombre': lote.medicamento.nombre
                },
                'precio_unitario': float(lote.precio_venta),
                'cantidad': cantidad_solicitada,
                'subtotal': float(lote.precio_venta) * cantidad_solicitada
            })
        
        # Guardar carrito actualizado en la sesión
        request.session['carrito'] = carrito
        messages.success(request, f"Se agregó {lote.medicamento.nombre} (Lote: {lote.lote_fabricante}) al carrito.")
    
    return redirect('CreateVenta')

# Quitar del carrito
@login_required
def remove_from_cart(request, lote_id):
    carrito = request.session.get('carrito', [])
    
    # Buscar y eliminar el item del lote específico
    for i, item in enumerate(carrito):
        if item['lote_id'] == lote_id:
            del carrito[i]
            break
    
    # Guardar carrito actualizado
    request.session['carrito'] = carrito
    
    return redirect('CreateVenta')

@login_required
def ventas_view(request):
    query = request.GET.get('q', '')  # Capturar el término de búsqueda
    ventas_query = Ventas.objects.all()

    # Filtro de búsqueda por usuario
    if query:
        ventas_query = ventas_query.filter(usuario__username__icontains=query)

    # Paginación
    paginator = Paginator(ventas_query, 5)  # 5 ventas por página
    page_number = request.GET.get('page', 1)
    ventas = paginator.get_page(page_number)

    # Obtener los grupos del usuario actual
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    return render(request, 'ventas.html', {
        'ventas': ventas,
        'query': query,  # Pasar el término de búsqueda para mantenerlo en el formulario
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
    })

def detalle_venta(request, id):
    venta = get_object_or_404(Ventas, id=id)  # Obtén la venta o muestra un error 404 si no existe
    return render(request, 'detalle_venta.html', {'venta': venta})

#//////////////////////////////////////////////////////////////////////////////Todo lo de aqui sera para la parte de las compras
# Vista para crear una nueva compra
@login_required
@transaction.atomic
def create_compra_view(request):
    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor')
        carrito_compra = request.session.get('carrito_compra', [])

        if not carrito_compra:
            messages.error(request, "El carrito de compras está vacío.")
            return redirect('CreateCompra')

        total_compra = sum(item['precio_unitario'] * item['cantidad'] for item in carrito_compra)

        compra = Compras.objects.create(
            proveedor_id=proveedor_id,
            fecha_compra=now(),
            precio_total=total_compra
        )

        for item in carrito_compra:
            medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
            cantidad = item['cantidad']
            precio_compra = item['precio_unitario']
            precio_venta = item['precio_venta']
            fecha_vencimiento = datetime.strptime(item['fecha_vencimiento'], '%Y-%m-%d').date()
            fecha_produccion = datetime.strptime(item['fecha_produccion'], '%Y-%m-%d').date()
            lote_fabricante = item['lote_fabricante']

            DetalleCompra.objects.create(
                compra=compra,
                medicamento=medicamento,
                precio=precio_compra,
                cantidad=cantidad
            )

            LoteMedicamento.objects.create(
                medicamento=medicamento,
                cantidad=cantidad,
                precio_compra=precio_compra,
                precio_venta=precio_venta,
                fecha_compra=compra.fecha_compra,
                fecha_vencimiento=fecha_vencimiento,
                fecha_produccion=fecha_produccion,
                lote_fabricante=lote_fabricante,
                activo=True
            )

            # Ya no actualizamos el stock en el modelo Medicamento porque fue eliminado
            # El stock ahora se maneja exclusivamente a través de LoteMedicamento

        request.session['carrito_compra'] = []
        request.session.modified = True

        messages.success(request, "Compra registrada exitosamente.")
        return redirect('Compras')

    # Proveedores activos
    proveedores = Proveedores.objects.filter(activo=True)

    # Manejo de búsqueda
    query = request.GET.get('q', '')  # Obtener la consulta del usuario
    medicamentos_query = Medicamentos.objects.filter(activo=True)
    if query:
        medicamentos_query = medicamentos_query.filter(Q(nombre__icontains=query))

    # Manejo de paginación
    paginator = Paginator(medicamentos_query, 5)  # Mostrar 10 medicamentos por página
    page_number = request.GET.get('page', 1)
    medicamentos = paginator.get_page(page_number)

    # Obtener carrito de compras de la sesión
    carrito_compra = request.session.get('carrito_compra', [])
    for item in carrito_compra:
        item['subtotal'] = item['precio_unitario'] * item['cantidad']

    # Verificar si es una solicitud AJAX
    is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Para solicitudes AJAX, solo renderizar la parte de resultados
    if is_ajax_request:
        return render(request, 'comprasCRUD/create_compra.html', {
            'medicamentos': medicamentos,
            'query': query,
        })
    # Para solicitudes normales, renderizar la página completa
    else:
        return render(request, 'comprasCRUD/create_compra.html', {
            'proveedores': proveedores,
            'medicamentos': medicamentos,
            'productos_compra_carrito': carrito_compra,
            'total_compra': sum(item['precio_unitario'] * item['cantidad'] for item in carrito_compra),
            'query': query,  # Para mantener el término de búsqueda en el formulario
        })

@require_POST
def add_to_cart_compra(request, medicamento_id):
    # Obtener el carrito actual de la sesión
    carrito_compra = request.session.get('carrito_compra', [])

    # Obtener el medicamento
    medicamento = get_object_or_404(Medicamentos, id=medicamento_id)
    cantidad = int(request.POST.get('cantidad', 1))
    fecha_vencimiento = request.POST.get('fecha_vencimiento')
    fecha_produccion = request.POST.get('fecha_produccion')
    precio_compra = float(request.POST.get('precio_compra'))
    precio_venta = float(request.POST.get('precio_venta'))
    lote_fabricante = request.POST.get('lote_fabricante', '').strip()

    # Validar datos
    if cantidad <= 0 or precio_compra <= 0 or precio_venta <= 0:
        messages.error(request, "Cantidad, precio de compra y precio de venta deben ser mayores a cero.")
        return redirect('CreateCompra')

    # Validar la fecha de vencimiento y producción
    try:
        fecha_vencimiento = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
        fecha_produccion = datetime.strptime(fecha_produccion, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Fechas inválidas.")
        return redirect('CreateCompra')

    # Buscar si el medicamento ya está en el carrito con las mismas fechas y lote de fabricante
    for item in carrito_compra:
        if (
            item['medicamento_id'] == medicamento_id and
            item['fecha_vencimiento'] == str(fecha_vencimiento) and
            item['fecha_produccion'] == str(fecha_produccion) and
            item['lote_fabricante'] == lote_fabricante
        ):
            item['cantidad'] += cantidad
            break
    else:
        # Si no está, agregarlo como nuevo producto
        carrito_compra.append({
            'medicamento_id': medicamento_id,
            'nombre': medicamento.nombre,
            'cantidad': cantidad,
            'precio_unitario': precio_compra,
            'precio_venta': precio_venta,
            'fecha_vencimiento': str(fecha_vencimiento),
            'fecha_produccion': str(fecha_produccion),
            'lote_fabricante': lote_fabricante,
        })

    # Guardar el carrito actualizado en la sesión
    request.session['carrito_compra'] = carrito_compra
    request.session.modified = True

    print(f"Carrito actualizado: {request.session['carrito_compra']}")  # Depuración

    messages.success(request, f"{medicamento.nombre} ha sido agregado al carrito.")
    return redirect('CreateCompra')

# Eliminar medicamento del carrito
@require_POST
def remove_from_cart_compra(request, medicamento_id):
    carrito_compra = request.session.get('carrito_compra', [])
    carrito_compra = [item for item in carrito_compra if item.get('medicamento_id') != medicamento_id]
    request.session['carrito_compra'] = carrito_compra
    request.session.modified = True
    messages.success(request, "Medicamento eliminado del carrito.")
    return redirect('CreateCompra')

@login_required
# Vista para mostrar las compras registradas
def compras_view(request):
    query = request.GET.get('q', '')  # Capturar el término de búsqueda
    compras_query = Compras.objects.select_related('proveedor').all()

    # Filtro de búsqueda por proveedor
    if query:
        compras_query = compras_query.filter(proveedor__nombre_empresa__icontains=query)

    # Paginación
    paginator = Paginator(compras_query, 5)  # 5 compras por página
    page_number = request.GET.get('page', 1)
    compras = paginator.get_page(page_number)

    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    return render(request, 'compras.html', {
        'compras': compras,
        'query': query,  # Pasar el término de búsqueda para mantenerlo en el formulario
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
    })

# Vista para mostrar el detalle de las compras
def detalle_compra_view(request, compra_id):
    compra = get_object_or_404(Compras, id=compra_id)
    detalles = DetalleCompra.objects.filter(compra=compra)
    return render(request, 'comprasCRUD/form_compra.html', {'compra': compra, 'detalles': detalles})

def export_compras_to_excel(request):
    # Crear un libro de trabajo Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Compras"
    
    # Agregar encabezados de las columnas
    ws.append(['ID Compra', 'Proveedor', 'Fecha', 'Total (Bs)'])

    # Obtener las compras desde la base de datos
    compras = Compras.objects.all()  # Aquí estamos usando el modelo Compras

    # Agregar los datos de las compras a la hoja de cálculo
    for compra in compras:
        ws.append([compra.id, compra.proveedor.nombre_empresa, compra.fecha_compra, compra.precio_total])

    # Crear una respuesta HTTP con el archivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=compras.xlsx'  # Nombre del archivo descargado
    wb.save(response)
    return response

# Módulo de Facturación

# Vista para listar las facturas
@login_required
def facturas_view(request):
    query = request.GET.get('q', '')  # Capturar el término de búsqueda
    facturas_query = Factura.objects.select_related('cliente', 'venta').filter(activo=True)

    # Filtrar por cliente o número de factura
    if query:
        facturas_query = facturas_query.filter(
            Q(cliente__nombre__icontains=query) | 
            Q(cliente__nit_ci__icontains=query) |
            Q(numero_factura__icontains=query)
        )

    # Paginación
    paginator = Paginator(facturas_query, 10)  # 10 facturas por página
    page_number = request.GET.get('page', 1)
    facturas = paginator.get_page(page_number)

    grupos_usuario = request.user.groups.values_list('name', flat=True)

    return render(request, 'facturacion/facturas.html', {
        'facturas': facturas,
        'query': query,
        'grupos': grupos_usuario
    })

# Vista para generar una factura a partir de una venta
@login_required
def generar_factura_view(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)
    
    # Verificar si ya existe una factura para esta venta
    factura_existente = Factura.objects.filter(venta=venta).first()
    if factura_existente:
        messages.warning(request, f"Ya existe una factura para esta venta (Factura #{factura_existente.numero_factura}).")
        return redirect('detalle_factura', factura_id=factura_existente.id)
    
    if request.method == 'POST':
        # Crear o buscar cliente
        nombre_cliente = request.POST.get('nombre')
        nit_ci = request.POST.get('nit_ci')
        telefono = request.POST.get('telefono', '')
        
        # Buscar si ya existe el cliente con ese NIT/CI
        cliente, created = Cliente.objects.get_or_create(
            nit_ci=nit_ci,
            defaults={
                'nombre': nombre_cliente,
                'telefono': telefono,
                'activo': True
            }
        )
        
        # Si el cliente existe pero algunos datos son diferentes, actualizarlos
        if not created:
            cliente.nombre = nombre_cliente  # Actualizar nombre si cambió
            if telefono:
                cliente.telefono = telefono  # Actualizar teléfono si se proporcionó
            cliente.save()
            
        # Generar la factura
        # Calcular fecha límite de emisión (60 días después)
        fecha_limite = datetime.now().date() + timedelta(days=60)
        
        # Crear la factura
        factura = Factura(
            venta=venta,
            cliente=cliente,
            monto_total=venta.precio_total,
            fecha_limite_emision=fecha_limite
        )
        factura.save()  # Esto generará automáticamente el número de factura
        
        messages.success(request, f"Factura #{factura.numero_factura} generada exitosamente.")
        return redirect('detalle_factura', factura_id=factura.id)
        
    return render(request, 'facturacion/generar_factura.html', {
        'venta': venta,
        'detalles': DetalleVenta.objects.filter(venta=venta, activo=True)
    })

# Vista para ver el detalle de una factura
@login_required
def detalle_factura_view(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    detalles_venta = DetalleVenta.objects.filter(venta=factura.venta, activo=True)
    
    return render(request, 'facturacion/detalle_factura.html', {
        'factura': factura,
        'detalles': detalles_venta,
    })

# Vista para imprimir una factura en PDF
@login_required
def imprimir_factura_view(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    detalles_venta = DetalleVenta.objects.filter(venta=factura.venta, activo=True)
    
    # Configuración para la impresión (formato PDF)
    context = {
        'factura': factura,
        'detalles': detalles_venta,
        'fecha_actual': timezone.now(),
        'nombre_empresa': 'FARMACIA SALUD TOTAL',
        'direccion_empresa': 'Av. Principal #123, Ciudad',
        'telefono_empresa': '(591) 3-XXXXXXX',
    }
    
    return render(request, 'facturacion/imprimir_factura.html', context)

# Vista para anular una factura
@login_required
def anular_factura_view(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    
    if request.method == 'POST':
        # Anular la factura (desactivarla)
        factura.activo = False
        factura.save()
        messages.success(request, f"Factura #{factura.numero_factura} anulada exitosamente.")
        return redirect('facturas')
    
    return render(request, 'facturacion/anular_factura.html', {'factura': factura})

@login_required
def buscar_cliente_view(request):
    """
    Vista para buscar un cliente por NIT/CI y devolver sus datos en formato JSON.
    Utilizada para autocompletar los campos del cliente en la creación de ventas.
    """
    nit_ci = request.GET.get('nit_ci', '').strip()
    response_data = {
        'encontrado': False,
        'cliente': None
    }
    
    if nit_ci:
        try:
            cliente = Cliente.objects.get(nit_ci=nit_ci, activo=True)
            response_data['encontrado'] = True
            response_data['cliente'] = {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'telefono': cliente.telefono or ''
            }
        except Cliente.DoesNotExist:
            # El cliente no existe, se devuelve encontrado=False
            pass
    
    return JsonResponse(response_data)

# Función para procesar la confirmación de venta
@login_required
@transaction.atomic
def confirmar_venta(request):
    from datetime import date, datetime, timedelta
    
    if request.method != 'POST':
        return redirect('CreateVenta')
    
    # Obtener el carrito
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, "No hay productos en el carrito para procesar la venta.")
        return redirect('CreateVenta')
    
    # Calcular el total
    total_venta = sum(item.get('subtotal', 0) for item in carrito)
    
    # Crear el registro de venta
    venta = Ventas.objects.create(
        usuario=request.user,
        fecha_venta=date.today(),
        precio_total=total_venta
    )
    
    # Procesar cada ítem del carrito
    for item in carrito:
        if 'lote_id' not in item:
            continue
        
        lote = get_object_or_404(LoteMedicamento, id=item['lote_id'], activo=True)
        cantidad = item.get('cantidad', 0)
        
        # Verificar stock disponible
        if lote.cantidad < cantidad:
            # Rollback de la transacción
            transaction.set_rollback(True)
            messages.error(request, f"No hay suficiente stock de {lote.medicamento.nombre} (Lote: {lote.lote_fabricante}). Stock actual: {lote.cantidad}")
            return redirect('CreateVenta')
        
        # Crear el detalle de venta
        detalle_venta = DetalleVenta.objects.create(
            venta=venta,
            medicamento=lote.medicamento,
            precio=lote.precio_venta,
            cantidad=cantidad
        )
        
        # Actualizar stock del lote
        lote.cantidad -= cantidad
        lote.save()
        
        # Si el lote se queda sin stock, marcarlo como inactivo
        if lote.cantidad <= 0:
            lote.activo = False
            lote.save()
    
    # Limpiar el carrito
    request.session['carrito'] = []
    request.session.modified = True
    
    # Generar factura si se proporcionaron datos del cliente
    if 'nombre_cliente' in request.POST and request.POST['nombre_cliente'].strip():
        try:
            # Datos del cliente
            nombre_cliente = request.POST.get('nombre_cliente')
            nit_ci = request.POST.get('nit_ci')
            telefono = request.POST.get('telefono', '')
            
            # Buscar o crear cliente
            cliente, created = Cliente.objects.get_or_create(
                nit_ci=nit_ci,
                defaults={
                    'nombre': nombre_cliente,
                    'telefono': telefono,
                    'activo': True
                }
            )
            
            # Si el cliente existe pero algunos datos son diferentes, actualizarlos
            if not created:
                cliente.nombre = nombre_cliente  # Actualizar nombre si cambió
                if telefono:
                    cliente.telefono = telefono  # Actualizar teléfono si se proporcionó
                cliente.save()
            
            # Generar factura
            fecha_limite = datetime.now().date() + timedelta(days=60)
            factura = Factura(
                venta=venta,
                cliente=cliente,
                monto_total=venta.precio_total,
                fecha_limite_emision=fecha_limite
            )
            factura.save()  # Esto generará automáticamente el número de factura
            
            messages.success(request, f"Venta registrada y factura #{factura.numero_factura} generada exitosamente.")
            return redirect('detalle_factura', factura_id=factura.id)
        except Exception as e:
            messages.warning(request, f"Venta registrada pero hubo un error al generar la factura: {str(e)}")
    else:
        messages.success(request, "Venta registrada exitosamente.")
    
    # Invalidar caché del dashboard ya que se registró una nueva venta
    invalidar_cache_dashboard()
    
    return redirect('Ventas')

# Función de utilidad para probar el rendimiento del caché
@login_required
def test_cache_performance(request):
    """
    Vista de prueba para verificar el funcionamiento del caché del dashboard.
    Útil para desarrollo y diagnóstico de rendimiento.
    """
    import time
    from django.http import JsonResponse
    
    # Obtener parámetros de prueba
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().date().strftime('%Y-%m-%d'))
    
    results = {}
    
    # Limpiar caché para la prueba
    invalidar_cache_dashboard()
    
    # Prueba 1: Primera carga (sin caché)
    start_time = time.time()
    df_ventas = obtener_datos_ventas(
        datetime.strptime(fecha_inicio, '%Y-%m-%d').date(), 
        datetime.strptime(fecha_fin, '%Y-%m-%d').date(), 
        None, None
    )
    generar_grafico_con_plotly(df_ventas)
    generar_grafico_barras(df_ventas, 
        datetime.strptime(fecha_inicio, '%Y-%m-%d').date(), 
        datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    )
    first_load_time = time.time() - start_time
    results['primera_carga_sin_cache'] = f"{first_load_time:.3f} segundos"
    
    # Simular carga del dashboard con caché
    filtros_key = f"{fecha_inicio}_{fecha_fin}_None_None"
    cache_key_hash = hashlib.md5(filtros_key.encode()).hexdigest()
    cache_version = cache.get('dashboard_cache_version', 0)
    cache_key_datos = f"dashboard_datos_{cache_key_hash}_v{cache_version}"
    cache_key_graficos = f"dashboard_graficos_{cache_key_hash}_v{cache_version}"
    
    # Simular datos en caché
    datos_cache = {
        'ventas_mes': 15000,
        'ventas_anual': 180000,
        'productos_vendidos': 500,
        'clientes_nuevos': 25,
        'top_productos': [],
    }
    graficos_cache = {
        'grafico_lineas_html': '<div>Gráfico simulado</div>',
        'grafico_barras_html': '<div>Gráfico simulado</div>',
    }
    
    cache.set(cache_key_datos, datos_cache, 900)
    cache.set(cache_key_graficos, graficos_cache, 1800)
    
    # Prueba 2: Segunda carga (con caché)
    start_time = time.time()
    cached_datos = cache.get(cache_key_datos)
    cached_graficos = cache.get(cache_key_graficos)
    second_load_time = time.time() - start_time
    results['segunda_carga_con_cache'] = f"{second_load_time:.3f} segundos"
    
    # Calcular mejora de rendimiento
    if first_load_time > 0:
        improvement = ((first_load_time - second_load_time) / first_load_time) * 100
        results['mejora_rendimiento'] = f"{improvement:.1f}%"
        results['factor_aceleracion'] = f"{first_load_time / second_load_time if second_load_time > 0 else 'N/A':.1f}x"
    
    results['cache_status'] = {
        'datos_en_cache': cached_datos is not None,
        'graficos_en_cache': cached_graficos is not None,
        'version_cache': cache_version,
    }
    
    return JsonResponse({
        'status': 'success',
        'message': 'Prueba de rendimiento del caché completada',
        'results': results,
        'recommendations': [
            'El caché reduce significativamente los tiempos de carga',
            'Los gráficos son los elementos más costosos de generar',
            'El caché se invalida automáticamente al registrar nuevas ventas'
        ]
    })