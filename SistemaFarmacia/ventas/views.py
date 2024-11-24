from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import date
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q, Sum, Count, F, Func
from django.db.models.functions import TruncMonth, TruncWeek

import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import io
import base64
import pandas as pd
import numpy as np

from datetime import datetime, timedelta
from .models import Laboratorios, Proveedores, Medicamentos, Ventas, DetalleVenta, LoteMedicamento, Compras, DetalleCompra, Categorias
from .forms import UsuarioForm, LaboratorioForm, ProveedorForm, MedicamentoForm, VentaForm, DetalleVentaForm
from pgmpy.models import DynamicBayesianNetwork as DBN
from pgmpy.estimators import MaximumLikelihoodEstimator
from pgmpy.inference import DBNInference

import firebase_admin
from firebase_admin import credentials, messaging

# Ruta al archivo JSON de la clave privada descargado desde la consola de Firebase
cred = credentials.Certificate('C:\ProyectoGrado\SistemaFarmacia\SistemaFarmacia\secrets/sistemafarmacia-87e60-firebase-adminsdk-ar1j6-480ea9d19a.json')
firebase_admin.initialize_app(cred)



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

    return render(request, 'laboratorios.html', {
        'laboratorios_activos': laboratorios_activos_page,
        'laboratorios_inactivos': laboratorios_inactivos_page,
        'num_laboratorios': num_laboratorios,
    })
# Vista para la creación de laboratorios
def create_laboratorio_view(request):
    formulario = LaboratorioForm(request.POST or None)
    if formulario.is_valid():
        laboratorio = formulario.save(commit=False)  # Guarda el formulario sin guardar en la base de datos aún
        laboratorio.activo = True  # Establece activo como True por defecto
        laboratorio.save()  # Ahora guarda en la base de datos
        return redirect('ListaLaboratorios')  # Cambia esta URL según tu configuración
    return render(request, 'laboratoriosCRUD/create_laboratorio.html', {'formulario': formulario})
# Vista para la edición de laboratorios
def update_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    formulario = LaboratorioForm(request.POST or None, request.FILES or None, instance=laboratorio)
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
def usuarios_view(request):
    # Usuarios activos
    usuarios_activos = User.objects.filter(is_active=True).prefetch_related('groups')
    # Usuarios inactivos
    usuarios_inactivos = User.objects.filter(is_active=False).prefetch_related('groups')
    
    return render(request, 'usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos
    })

# Vista para la creacion de los ususarios

# Vista de los usuarios
def usuarios_view(request):
    # Usuarios activos
    usuarios_activos = User.objects.filter(is_active=True).prefetch_related('groups')
    # Usuarios inactivos
    usuarios_inactivos = User.objects.filter(is_active=False).prefetch_related('groups')
    
    return render(request, 'usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos
    })

# Vista para la creación de los usuarios
def create_user_view(request):
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

    return render(request, 'usuariosCRUD/create_user.html', {'formulario': formulario})

# Vista para la edición de los usuarios
def update_user_view(request, id):
    usuario = User.objects.get(id=id)
    formulario = UsuarioForm(request.POST or None, request.FILES or None, instance=usuario)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Usuarios')
    return render(request, 'usuariosCRUD/update_user.html', {'formulario': formulario})

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

    context = {
        'proveedores_activos': proveedores_activos_pag,
        'proveedores_inactivos': proveedores_inactivos_pag,
        'items_per_page': items_per_page  # Pasar la opción seleccionada
    }
    return render(request, 'proveedores.html', context)
# Vista para la creacion de los proveedores
def create_proveedor_view(request):
    formulario = ProveedorForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Proveedores')  # Redirige a la lista de proveedores
    return render(request, 'proveedoresCRUD/create_proveedor.html', {'formulario': formulario})
# Vista para la edicion de los proveedores
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
def medicamentos_view(request):
    # Número de medicamentos por página (por defecto 5)
    num_medicamentos = request.GET.get('num_medicamentos', '5')  # Valor predeterminado: 5
    num_medicamentos = int(num_medicamentos) if num_medicamentos.isdigit() else 5

    # Medicamentos activos
    medicamentos_activos = Medicamentos.objects.filter(activo=True)
    paginator_activos = Paginator(medicamentos_activos, num_medicamentos)
    page_activos = request.GET.get('page_activos', 1)
    medicamentos_activos_page = paginator_activos.get_page(page_activos)

    # Medicamentos inactivos
    medicamentos_inactivos = Medicamentos.objects.filter(activo=False)
    paginator_inactivos = Paginator(medicamentos_inactivos, num_medicamentos)
    page_inactivos = request.GET.get('page_inactivos', 1)
    medicamentos_inactivos_page = paginator_inactivos.get_page(page_inactivos)

    # Renderizar la plantilla
    return render(request, 'inventario.html', {
        'medicamentos_activos': medicamentos_activos_page,
        'medicamentos_inactivos': medicamentos_inactivos_page,
        'num_medicamentos': num_medicamentos,
    })
# Vista para la creación de medicamentos
def create_medicamento_view(request):
    formulario = MedicamentoForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Medicamentos')  # Cambia según tu URL de lista
    return render(request, 'inventarioCRUD/create_medicamento.html', {'formulario': formulario})
# Vista para la edición de medicamentos
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
def obtener_datos_ventas():
    # Obtiene los datos de ventas y realiza las transformaciones necesarias
    ventas = DetalleVenta.objects.filter(activo=True).values(
        'medicamento__nombre',
        'medicamento__categoria__nombre_categoria',
        'venta__fecha_venta',
        'cantidad'
    )
    df = pd.DataFrame(ventas)
    df['venta__fecha_venta'] = pd.to_datetime(df['venta__fecha_venta'], errors='coerce')
    df['mes'] = df['venta__fecha_venta'].dt.to_period('M')
    df['fecha'] = df['mes'].dt.to_timestamp()
    df = df.groupby(['medicamento__nombre', 'medicamento__categoria__nombre_categoria', 'fecha'])['cantidad'].sum().reset_index()

    # Renombramos las columnas para mayor claridad
    df.rename(columns={
        'medicamento__nombre': 'medicamento',
        'medicamento__categoria__nombre_categoria': 'categoria',
    }, inplace=True)
    
    return df

# Nueva función para generar el gráfico de barras con Plotly
def generar_grafico_barras(df):
    fig = px.bar(
        df,
        x='medicamento',
        y='cantidad',
        color='categoria',
        title='Cantidad de ventas por categoria y medicamento',
        labels={'cantidad': 'Cantidad Vendida', 'medicamento': 'Medicamento'}
    )
    fig.update_layout(template='plotly_white')
    return fig.to_html(full_html=False)

def generar_grafico_con_plotly(df):
    fig = px.line(
        df,
        x='fecha',
        y='cantidad',
        color='medicamento',
        title='Cantidad vendida por medicamento',
        labels={
            'fecha': 'Fecha',
            'cantidad': 'Cantidad Vendida',
            'medicamento': 'Medicamento'
        }
    )
    fig.update_traces(mode='lines+markers')
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Cantidad Vendida",
        legend_title="Medicamento",
        template="plotly_white"
    )
    return fig.to_html(full_html=False)

# Actualizamos la vista para incluir el gráfico interactivo
def dashboard_view_ventas(request):
    # Obtener datos de ventas históricos
    df_ventas = obtener_datos_ventas()

    # Generar gráficos interactivos
    grafico_lineas_html = generar_grafico_con_plotly(df_ventas)
    grafico_barras_html = generar_grafico_barras(df_ventas)

    # Pasar los datos y gráficos al contexto
    contexto = {
        'df_ventas': df_ventas.to_dict(orient='records'),  # Datos históricos de ventas
        'grafico_lineas_html': grafico_lineas_html,  # Gráfico de líneas
        'grafico_barras_html': grafico_barras_html,  # Gráfico de barras
    }
    return render(request, 'dashboard_ventas.html', contexto)
#////////////////////////////Esto va a aportar a la parte de gestion de inventario
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
"""
def enviar_notificacion_push(token, title, body):
    try:
        # Crear el mensaje
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token,  # Token del dispositivo móvil al que se enviará la notificación
        )

        # Enviar el mensaje
        response = messaging.send(message)
        print('Mensaje enviado con éxito:', response)
    except Exception as e:
        print('Error al enviar la notificación:', e)
"""
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
        proximos_a_vencer.append({
            'medicamento': lote.medicamento.nombre,
            'cantidad': lote.cantidad,
            'fecha_vencimiento': lote.fecha_vencimiento
        })
    """
        # Enviar notificaciones a los dispositivos móviles
    for lote in proximos_a_vencer:
        mensaje = f"El medicamento {lote['medicamento']} está por vencer. Vencimiento: {lote['fecha_vencimiento']}"
        
        # Obtener los tokens de los usuarios registrados
        usuarios = User.objects.all()  # O filtra según lo que necesites
        for usuario in usuarios:
            token = usuario.profile.fcm_token  # Asume que has guardado el token en el perfil del usuario
            if token:
                # Enviar la notificación
                enviar_notificacion_push(token, "Medicamento próximo a vencer", mensaje)
    """
    return proximos_a_vencer

def obtener_alertas_stock_minimo(umbral=10):
    medicamentos_bajo_stock = Medicamentos.objects.filter(stock__lte=umbral, activo=True)
    alertas = []
    for med in medicamentos_bajo_stock:
        alertas.append({
            'nombre': med.nombre,
            'stock_actual': med.stock,
            'umbral': umbral
        })
    return alertas

def generar_grafico_barras_stock_minimo(alertas_stock_minimo):
    # Extraer datos para el gráfico
    nombres = [alerta['nombre'] for alerta in alertas_stock_minimo]
    stock_actual = [alerta['stock_actual'] for alerta in alertas_stock_minimo]
    umbrales = [alerta['umbral'] for alerta in alertas_stock_minimo]

    # Crear el gráfico
    fig = px.bar(
        x=stock_actual,
        y=nombres,
        orientation='h',  # Barras horizontales
        text=stock_actual,  # Mostrar valores sobre las barras
        title='Medicamentos con Stock por Debajo del Umbral',
        labels={'x': 'Stock Actual', 'y': 'Medicamentos'}
    )
    
    # Añadir línea de umbral
    fig.add_scatter(
        x=umbrales,
        y=nombres,
        mode='lines',
        name='Umbral',
        line=dict(color='red', dash='dash')
    )
    
    # Configuración adicional
    fig.update_layout(template='plotly_white', showlegend=True)
    return fig.to_html(full_html=False)

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

    # Obtener las alertas de stock mínimo
    alertas_stock_minimo = obtener_alertas_stock_minimo()

    # Generar gráfico de barras para stock mínimo
    grafico_stock_minimo_html = generar_grafico_barras_stock_minimo(alertas_stock_minimo)

    # Pasar los datos al contexto para la plantilla
    contexto = {
        'medicamentos_baja_rotacion': medicamentos_baja_rotacion,
        'grafico_baja_rotacion_html': grafico_baja_rotacion_html,
        'medicamentos_proximos_a_vencer': medicamentos_proximos_a_vencer,
        'alertas_stock_minimo': alertas_stock_minimo,
        'grafico_stock_minimo_html': grafico_stock_minimo_html,
    }
    return render(request, 'dashboard_inventario.html', contexto)

def cargar_datos_compras():
    # Cargar datos de compras y proveedores
    compras = Compras.objects.filter(activo=True).select_related('proveedor')
    compras_df = pd.DataFrame.from_records(
        compras.values('id', 'proveedor__nombre_empresa', 'fecha_compra', 'precio_total')
    )
    return compras_df

def cargar_datos_detalle_compras():
    # Cargar datos de los detalles de las compras
    detalles = DetalleCompra.objects.filter(activo=True).select_related('compra', 'medicamento')
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
        x='cantidad_compras',
        y='proveedor__nombre_empresa',
        title="Proveedores más frecuentes",
        orientation='h',  # Barras horizontales
        labels={'cantidad_compras': 'Número de Compras', 'proveedor__nombre_empresa': 'Proveedor'},
        text='cantidad_compras',  # Mostrar valores en las barras
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(template='plotly_white', showlegend=False)
    return fig.to_html(full_html=False)

def grafico_medicamentos_mas_comprados(medicamentos, por='cantidad'):
    titulo = "Medicamentos más comprados (por cantidad)" if por == 'cantidad' else "Medicamentos más comprados (por costo)"
    y_col = 'cantidad_total' if por == 'cantidad' else 'costo_total'

    fig = px.bar(
        medicamentos,
        x=y_col,
        y='medicamento__nombre',
        title=titulo,
        orientation='h',  # Barras horizontales
        labels={y_col: "Cantidad Total" if por == 'cantidad' else "Costo Total", 'medicamento__nombre': "Medicamento"},
        text=y_col,  # Mostrar valores en las barras
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(template='plotly_white', showlegend=False)
    return fig.to_html(full_html=False)

# Vista del dashboard de los proveedores
def dashboard_view_proveedores(request):
    # Cargar datos
    compras_df = cargar_datos_compras()
    detalles_df = cargar_datos_detalle_compras()

    # Análisis
    proveedor_frecuente = analizar_proveedor_frecuente(compras_df)
    medicamentos_por_cantidad = analizar_medicamentos_mas_comprados(detalles_df, por='cantidad')
    medicamentos_por_costo = analizar_medicamentos_mas_comprados(detalles_df, por='costo')

    # Generar gráficos
    grafico_proveedores_html = grafico_proveedor_frecuente(proveedor_frecuente)
    grafico_medicamentos_cantidad_html = grafico_medicamentos_mas_comprados(medicamentos_por_cantidad, por='cantidad')
    grafico_medicamentos_costo_html = grafico_medicamentos_mas_comprados(medicamentos_por_costo, por='costo')

    # Contexto para el template
    contexto = {
        'grafico_proveedores_html': grafico_proveedores_html,
        'grafico_medicamentos_cantidad_html': grafico_medicamentos_cantidad_html,
        'grafico_medicamentos_costo_html': grafico_medicamentos_costo_html,
    }

    return render(request, 'dashboard_proveedores.html', contexto)

# Vista del dashboard de los usuarios
def cargar_datos_ventas():
    # Extraer las ventas y usuarios activos
    ventas = Ventas.objects.filter(activo=True).values('id', 'usuario__username', 'fecha_venta', 'precio_total')
    return pd.DataFrame(list(ventas))
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
def dashboard_view_usuarios(request):
    # Cargar datos
    ventas_df = cargar_datos_ventas()

    # Análisis
    frecuencia_ventas = analizar_frecuencia_ventas(ventas_df)
    contribucion_ingresos = analizar_contribucion_ingresos(ventas_df)

    # Generar gráficos
    grafico_frecuencia_html = grafico_frecuencia_ventas(frecuencia_ventas)
    grafico_contribucion_html = grafico_contribucion_ingresos(contribucion_ingresos)

    # Contexto para el template
    contexto = {
        'grafico_frecuencia_html': grafico_frecuencia_html,
        'grafico_contribucion_html': grafico_contribucion_html,
    }

    return render(request, 'dashboard_usuarios.html', contexto)

###/////////////////////////////Todo esto va a ser para el login
def login_view(request):
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
    # Obtener el término de búsqueda desde el GET request
    query = request.GET.get('q', '').strip()
    
    # Filtrar medicamentos activos y, si hay una búsqueda, aplicar filtro adicional
    medicamentos = Medicamentos.objects.filter(activo=True)
    if query:
        medicamentos = medicamentos.filter(Q(nombre__icontains=query))

    # Paginación: mostrar 5 medicamentos por página
    paginator = Paginator(medicamentos, 5)  # 5 medicamentos por página
    page_number = request.GET.get('page')
    medicamentos_paginados = paginator.get_page(page_number)

    # Obtener el carrito actual de la sesión
    carrito = request.session.get('carrito', [])
    productos_carrito = []
    total_carrito = 0

    # Procesar el carrito
    for item in carrito:
        if 'medicamento_id' not in item:
            continue
        medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
        cantidad = item['cantidad']
        subtotal = medicamento.precio * cantidad
        productos_carrito.append({
            'medicamento': medicamento,
            'cantidad': cantidad,
            'subtotal': subtotal
        })
        total_carrito += subtotal

    # Chequear si hay suficiente stock en los lotes antes de procesar la venta
    for item in carrito:
        medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
        cantidad_requerida = item['cantidad']
        lotes = LoteMedicamento.objects.filter(medicamento=medicamento, activo=True)
        stock_total = sum(lote.cantidad for lote in lotes)

        if stock_total < cantidad_requerida:
            messages.error(request, f"No hay suficiente stock para {medicamento.nombre}. Stock disponible: {stock_total}")
            return redirect('CreateVenta')

    # Procesar la confirmación de venta
    if request.method == 'POST' and carrito:
        venta = Ventas.objects.create(
            usuario=request.user,
            fecha_venta=date.today(),
            precio_total=total_carrito
        )

        for item in carrito:
            if 'medicamento_id' not in item:
                continue
            medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
            cantidad = item['cantidad']
            lotes = LoteMedicamento.objects.filter(
                medicamento=medicamento,
                activo=True
            ).order_by('fecha_compra')

            cantidad_requerida = cantidad
            for lote in lotes:
                if lote.cantidad >= cantidad_requerida:
                    lote.cantidad -= cantidad_requerida
                    if lote.cantidad == 0:
                        lote.activo = False
                    lote.save()
                    break
                else:
                    cantidad_requerida -= lote.cantidad
                    lote.cantidad = 0
                    lote.activo = False
                    lote.save()

            DetalleVenta.objects.create(
                venta=venta,
                medicamento=medicamento,
                precio=medicamento.precio,
                cantidad=cantidad
            )

        request.session['carrito'] = []
        messages.success(request, "La venta se ha registrado exitosamente.")
        return redirect('Ventas')

    return render(request, 'ventasCRUD/create_venta.html', {
        'medicamentos': medicamentos_paginados,
        'productos_carrito': productos_carrito,
        'total_carrito': total_carrito,
        'query': query
    })

@require_POST
def add_to_cart(request, medicamento_id):
    # Obtener el carrito de la sesión o inicializarlo como una lista vacía
    carrito = request.session.get('carrito', [])

    # Obtener el valor de cantidad desde el formulario
    cantidad_str = request.POST.get('cantidad', '').strip()

    # Validar si el campo de cantidad está vacío
    if not cantidad_str:
        messages.error(request, "El campo de cantidad está vacío. Por favor, ingrese una cantidad.")
        return redirect('CreateVenta')

    try:
        # Convertir cantidad a entero
        cantidad = int(cantidad_str)
        if cantidad < 1:
            raise ValueError("La cantidad debe ser al menos 1.")
    except ValueError:
        messages.error(request, "Por favor, ingrese una cantidad válida.")
        return redirect('CreateVenta')

    # Obtener el medicamento
    medicamento = get_object_or_404(Medicamentos, id=medicamento_id)

    # Verificar el stock disponible en todos los lotes activos
    lotes = LoteMedicamento.objects.filter(medicamento=medicamento, activo=True)
    stock_total = sum(lote.cantidad for lote in lotes)

    if cantidad > stock_total:
        # Si la cantidad solicitada excede el stock total, mostrar un mensaje de error y redirigir
        messages.error(request, f"No hay suficiente stock para {medicamento.nombre}. Stock disponible: {stock_total}")
        return redirect('CreateVenta')

    # Verificar si el medicamento ya está en el carrito
    for item in carrito:
        if item.get('medicamento_id') == medicamento_id:
            # Si ya está en el carrito, verificar que la suma de cantidades no exceda el stock total
            nueva_cantidad = item['cantidad'] + cantidad
            if nueva_cantidad > stock_total:
                # Si la cantidad total en el carrito excede el stock disponible, no agregar y redirigir
                messages.error(request, f"No puedes agregar más de {stock_total} unidades de {medicamento.nombre}.")
                return redirect('CreateVenta')
            item['cantidad'] = nueva_cantidad  # Actualiza la cantidad si no excede el stock total
            break
    else:
        # Si no está en el carrito, agregarlo como un nuevo producto
        carrito.append({'medicamento_id': medicamento_id, 'cantidad': cantidad})

    # Guardar el carrito actualizado en la sesión
    request.session['carrito'] = carrito
    request.session.modified = True  # Fuerza la actualización de la sesión

    # Redirige con un mensaje de éxito (opcional)
    # messages.success(request, "Producto agregado al carrito.")
    return redirect('CreateVenta')

def remove_from_cart(request, medicamento_id):
    # Obtén el carrito de la sesión
    carrito = request.session.get('carrito', [])
    print("Carrito antes de eliminar:", carrito)  # Depuración

    # Filtra el carrito para eliminar el medicamento de manera segura
    carrito = [item for item in carrito if item.get('medicamento_id') != medicamento_id]
    
    # Actualiza el carrito en la sesión
    request.session['carrito'] = carrito
    request.session.modified = True

    print("Carrito después de eliminar:", request.session.get('carrito', {}))  # Depuración
    #messages.success(request, "Producto eliminado del carrito.")
    return redirect('CreateVenta')


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

    return render(request, 'ventas.html', {
        'ventas': ventas,
        'query': query  # Pasar el término de búsqueda para mantenerlo en el formulario
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
                activo=True
            )

            medicamento.stock += cantidad
            medicamento.save()

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

    # Buscar si el medicamento ya está en el carrito con las mismas fechas
    for item in carrito_compra:
        if (
            item['medicamento_id'] == medicamento_id and
            item['fecha_vencimiento'] == str(fecha_vencimiento) and
            item['fecha_produccion'] == str(fecha_produccion)
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

    return render(request, 'compras.html', {
        'compras': compras,
        'query': query  # Pasar el término de búsqueda para mantenerlo en el formulario
    })

# Vista para mostrar el detalle de las compras
def detalle_compra_view(request, compra_id):
    compra = get_object_or_404(Compras, id=compra_id)
    detalles = DetalleCompra.objects.filter(compra=compra)
    return render(request, 'comprasCRUD/form_compra.html', {'compra': compra, 'detalles': detalles})