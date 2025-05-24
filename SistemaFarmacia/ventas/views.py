from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from datetime import datetime, timedelta
from django.db.models import Sum, F, Count
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from django.utils import timezone
from django.utils.timezone import now
from .models import *
from django.http import Http404
import plotly.io as pio
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
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

from datetime import datetime, timedelta
from .models import Laboratorios, Proveedores, Medicamentos, Ventas, DetalleVenta, LoteMedicamento, Compras, DetalleCompra, Categorias, User, Cliente, Factura
from .forms import UsuarioForm, LaboratorioForm, ProveedorForm, MedicamentoForm, VentaForm, DetalleVentaForm

from openpyxl import Workbook

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required



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
        'grupos': grupos_usuario,  # Pasar los grupos del usuario a la plantilla

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

# Vista para la edición de los usuarios
@login_required
def update_user_view(request, id):
    usuario = get_object_or_404(User, pk=id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            user = form.save()  # Usará el método save personalizado
            messages.success(request, 'Usuario actualizado correctamente')
            return redirect('Usuarios')
    else:
        form = UsuarioForm(instance=usuario)
        # Limpiar el campo de contraseña en el GET
        form.fields['password'].initial = ''
    
    return render(request, 'usuariosCRUD/update_user.html', {
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
def obtener_datos_ventas(fecha_inicio=None, fecha_fin=None):
    # Obtiene los datos de ventas y realiza las transformaciones necesarias
    ventas_query = DetalleVenta.objects.filter(activo=True)
    
    # Aplicar filtros de fecha si se proporcionan
    if fecha_inicio and fecha_fin:
        ventas_query = ventas_query.filter(venta__fecha_venta__range=[fecha_inicio, fecha_fin])
    
    ventas = ventas_query.values(
        'medicamento__nombre',
        'medicamento__categoria__nombre_categoria',
        'venta__fecha_venta',
        'cantidad',
        'precio'
    )
    
    # Si no hay datos, devolver un DataFrame vacío pero con la estructura correcta
    if not ventas.exists():
        return pd.DataFrame(columns=['medicamento', 'categoria', 'fecha', 'cantidad', 'precio_total'])
    
    df = pd.DataFrame(ventas)
    df['venta__fecha_venta'] = pd.to_datetime(df['venta__fecha_venta'], errors='coerce')
    
    # Calcular el total de ventas (precio * cantidad)
    df['precio_total'] = df['precio'] * df['cantidad']
    
    # Agrupar por mes
    df['mes'] = df['venta__fecha_venta'].dt.to_period('M')
    df['fecha'] = df['mes'].dt.to_timestamp()
    
    # Agrupar por medicamento, categoría y fecha
    df_agrupado = df.groupby(['medicamento__nombre', 'medicamento__categoria__nombre_categoria', 'fecha']).agg({
        'cantidad': 'sum',
        'precio_total': 'sum'
    }).reset_index()

    # Renombramos las columnas para mayor claridad
    df_agrupado.rename(columns={
        'medicamento__nombre': 'medicamento',
        'medicamento__categoria__nombre_categoria': 'categoria',
    }, inplace=True)
    
    return df_agrupado


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
    top_productos = DetalleVenta.objects.filter(
        activo=True,
        venta__fecha_venta__gte=fecha_inicio,
        venta__fecha_venta__lte=fecha_fin
    ).values(
        'medicamento__nombre',
        'medicamento__categoria__nombre_categoria'
    ).annotate(
        total_unidades=Sum('cantidad'),
        total_ventas=Sum(F('precio') * F('cantidad'))
    ).order_by('-total_unidades')[:limite]
    
    return top_productos

# Nueva función para generar el gráfico de barras con Plotly
def generar_grafico_barras(df):
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
    
    # Crear el gráfico de barras mejorado
    fig = px.bar(
        df_tops,
        x='medicamento',
        y='cantidad',
        color='categoria',
        barmode='group',
        labels={
            'cantidad': '<b>Unidades Vendidas</b>',
            'medicamento': '<b>Medicamento</b>',
            'categoria': '<b>Categoría</b>'
        },
        title='<b>Top 5 Medicamentos por Categoría</b>',
        template='plotly_white',
        height=500,
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    
    # Mejorar el diseño del gráfico
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
        legend={
            'title': '<b>Categorías</b>',
            'font': {'size': 13, 'family': 'Arial, sans-serif'},

            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1,
            'bgcolor': 'rgba(255, 255, 255, 0.8)',
            'bordercolor': '#e1e5eb',
            'borderwidth': 1
        },
        plot_bgcolor='white',
        margin=dict(l=50, r=20, t=100, b=150, pad=5),
        bargap=0.3,
        bargroupgap=0.1,
        hovermode='closest',
        hoverlabel={
            'bgcolor': 'white',
            'bordercolor': '#ddd'
        }
    )
    
    # Mejorar las barras
    fig.update_traces(
        hovertemplate=
        '<b>%{x}</b><br>' +
        'Cantidad: <b>%{y}</b><br>' +
        '<extra></extra>',
        marker=dict(
            line=dict(width=0.5, color='DarkSlateGrey'),
            opacity=0.9
        )
    )
    
    # Crear botones para filtrar por categoría
    botones_categorias = []
    
    # Botón para mostrar todos los medicamentos top
    botones_categorias.append(dict(
        label="<b>Todos</b>",
        method="update",
        args=[{"x": [df_tops['medicamento']], 
               "y": [df_tops['cantidad']]}, 
              {"title": "<b>Top 5 Medicamentos por Categoría</b>"}]
    ))
    
    # Botones para cada categoría
    for categoria, df_cat in top_por_categoria.items():
        botones_categorias.append(dict(
            label=f"<b>{categoria[:15]}{'...' if len(categoria) > 15 else ''}</b>",
            method="update",
            args=[{"x": [df_cat['medicamento']], 
                   "y": [df_cat['cantidad']]}, 
                  {"title": f"<b>Top 5 Medicamentos: {categoria}</b>"}]
        ))
    
    # Añadir menú de filtros
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=botones_categorias,
                direction="down",
                pad={"r": 10, "t": 10, "b": 10},
                showactive=True,
                x=0.02,
                xanchor="left",
                y=1.15,
                yanchor="top",
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(0, 0, 0, 0.1)',
                borderwidth=1,
                font=dict(size=12, color='#2c3e50')
            )
        ],
        autosize=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    # Configuración simplificada
    config = {
        'responsive': True,
        'displaylogo': False
    }
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)

# Grafico de las ventas de medicamentos graficado de manera lineal
def generar_grafico_con_plotly(df):
    fig = go.Figure()
    
    # Obtener categorías y medicamentos únicos
    categorias = df['categoria'].unique()
    medicamentos = df['medicamento'].unique()
    
    # Crear un colormap para que cada medicamento tenga un color consistente
    import plotly.colors as colors
    colores = colors.qualitative.Plotly + colors.qualitative.D3 + colors.qualitative.G10
    color_map = {}
    for i, med in enumerate(medicamentos):
        color_map[med] = colores[i % len(colores)]
    
    # Agregar líneas para cada medicamento, pero limitar a 5 medicamentos por categoría inicialmente
    for categoria in categorias:
        # Filtrar medicamentos de esta categoría
        meds_en_categoria = df[df['categoria'] == categoria]['medicamento'].unique()
        
        # Tomar solo los primeros 5 medicamentos o menos si hay menos
        meds_a_mostrar = meds_en_categoria[:min(5, len(meds_en_categoria))]
        
        for medicamento in meds_a_mostrar:
            # Filtrar datos por medicamento y categoría
            datos_filtrados = df[(df['medicamento'] == medicamento) & 
                               (df['categoria'] == categoria)]
            
            if not datos_filtrados.empty:
                fig.add_trace(go.Scatter(
                    x=datos_filtrados['fecha'],
                    y=datos_filtrados['cantidad'],
                    mode='lines+markers',
                    name=f"{medicamento} ({categoria})",
                    line=dict(color=color_map[medicamento], width=2.5),
                    marker=dict(
                        size=7,
                        line=dict(width=1, color='DarkSlateGrey')
                    ),
                    hovertemplate=
                    '<b>%{x|%d-%m-%Y}</b><br>' +
                    'Cantidad: <b>%{y}</b><br>' +
                    '<extra></extra>',
                    visible=True if categoria == categorias[0] else 'legendonly',
                ))

    # Crear botones para categorías
    botones_categorias = []
    
    # Agregar botón para "Todas las categorías"
    botones_categorias.append(dict(
        label="<b>Todas</b>",
        method="update",
        args=[{"visible": [True] * len(fig.data)}, 
              {"title": "<b>Todas las categorías</b>",
               "showlegend": True}]
    ))
    
    # Agregar botones para cada categoría
    for categoria in categorias:
        # Configurar visibilidad para mostrar solo medicamentos de la categoría seleccionada
        visibilidad = [categoria in trace.name for trace in fig.data]
        
        botones_categorias.append(dict(
            label=f"<b>{categoria[:15]}{'...' if len(categoria) > 15 else ''}</b>",
            method="update",
            args=[{"visible": visibilidad}, 
                  {"title": f"<b>Categoría: {categoria}</b>",
                   "showlegend": True}]
        ))
    
    # Agregar un botón para mostrar top 10 medicamentos más vendidos
    if 'total_vendido' in df.columns:
        # Obtener los 10 medicamentos más vendidos
        top_medicamentos = df.groupby('medicamento')['total_vendido'].sum().nlargest(10).index.tolist()
        visibilidad_top = [trace.name.split(' (')[0] in top_medicamentos for trace in fig.data]
        
        botones_categorias.append(dict(
            label="<b>Top 10</b>",
            method="update",
            args=[{"visible": visibilidad_top}, 
                  {"title": "<b>Top 10 medicamentos más vendidos</b>",
                   "showlegend": True}]
        ))
    
    # Configurar el diseño
    fig.update_layout(
        title="<b>Histórico de Ventas por Categoría</b>",

        xaxis={
            'title': "<b>Fecha</b>",
            'tickfont': {'size': 12},
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': True,
            'showline': True,
            'linewidth': 1,
            'linecolor': 'lightgray',
            'zeroline': False
        },
        yaxis={
            'title': "<b>Cantidad Vendida</b>",
            'tickfont': {'size': 12},
            'gridcolor': 'rgba(220, 220, 220, 0.3)',
            'showgrid': True,
            'showline': True,
            'linewidth': 1,
            'linecolor': 'lightgray',
            'zeroline': False
        },
        legend={
            'title': '<b>Medicamentos</b>',
            'font': {'size': 13, 'family': 'Arial, sans-serif'},

            'orientation': 'v',
            'y': 1,
            'x': 1.02,
            'xanchor': 'left',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.8)',
            'bordercolor': '#e1e5eb',
            'borderwidth': 1,
            'itemclick': 'toggleothers',
            'itemdoubleclick': 'toggle'
        },
        margin=dict(l=50, r=20, t=100, b=80, pad=5),
        template="plotly_white",
        hovermode="closest",
        hoverlabel={
            'bgcolor': 'white',
            'bordercolor': '#ddd'
        },
        updatemenus=[
            dict(
                active=0,
                buttons=botones_categorias,
                direction="down",
                pad={"r": 10, "t": 10, "b": 10},
                showactive=True,
                x=0.02,
                xanchor="left",
                y=1.15,
                yanchor="top",
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(0, 0, 0, 0.1)',
                borderwidth=1,
                font=dict(size=12, color='#2c3e50')
            )
        ],
        height=500,
        autosize=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Configuración simplificada
    config = {
        'responsive': True,
        'displaylogo': False
    }
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)

# Actualizamos la vista para incluir el gráfico interactivo
@login_required
def dashboard_view_ventas(request):
    # Procesar parámetros de filtro de fechas si existen
    fecha_inicio = request.GET.get('fecha_inicio', None)
    fecha_fin = request.GET.get('fecha_fin', None)
    
    # Si no hay filtros, usar rango por defecto (último mes)
    if not fecha_inicio or not fecha_fin:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=30)
    else:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            fecha_fin = timezone.now().date()
            fecha_inicio = fecha_fin - timedelta(days=30)
    
    # Obtener datos de ventas históricos con los filtros aplicados
    df_ventas = obtener_datos_ventas(fecha_inicio, fecha_fin)
    
    # Obtener los datos para las tarjetas del dashboard
    ventas_mes = obtener_ventas_mes()
    ventas_anual = obtener_ventas_anual()
    productos_vendidos = obtener_productos_vendidos(fecha_inicio, fecha_fin)
    clientes_nuevos = obtener_clientes_nuevos(fecha_inicio, fecha_fin)
    
    # Obtener los datos para la tabla de top productos vendidos
    top_productos = obtener_top_productos(fecha_inicio, fecha_fin)

    # Generar gráficos interactivos
    grafico_lineas_html = generar_grafico_con_plotly(df_ventas)
    grafico_barras_html = generar_grafico_barras(df_ventas)

    # Obtener grupos del usuario
    grupos_usuario = request.user.groups.values_list('name', flat=True)

    # Pasar los datos y gráficos al contexto
    contexto = {
        'df_ventas': df_ventas.to_dict(orient='records'),  # Datos históricos de ventas
        'grafico_lineas_html': grafico_lineas_html,  # Gráfico de líneas
        'grafico_barras_html': grafico_barras_html,  # Gráfico de barras
        'grupos': grupos_usuario,  # Grupos del usuario
        
        # Datos para las tarjetas del dashboard
        'ventas_mes': ventas_mes,
        'ventas_anual': ventas_anual,
        'productos_vendidos': productos_vendidos,
        'clientes_nuevos': clientes_nuevos,
        'top_productos': top_productos,
        
        # Fechas para los filtros
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
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

    # Obtener las alertas de stock mínimo
    alertas_stock_minimo = obtener_alertas_stock_minimo()

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
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
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
@login_required
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
    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    # Contexto para el template
    contexto = {
        'grafico_proveedores_html': grafico_proveedores_html,
        'grafico_medicamentos_cantidad_html': grafico_medicamentos_cantidad_html,
        'grafico_medicamentos_costo_html': grafico_medicamentos_costo_html,
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
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

@login_required
def dashboard_view_usuarios(request):
    # Cargar datos
    ventas_df = cargar_datos_ventas()

    # Análisis
    frecuencia_ventas = analizar_frecuencia_ventas(ventas_df)
    contribucion_ingresos = analizar_contribucion_ingresos(ventas_df)

    # Generar gráficos
    grafico_frecuencia_html = grafico_frecuencia_ventas(frecuencia_ventas)
    grafico_contribucion_html = grafico_contribucion_ingresos(contribucion_ingresos)

    grupos_usuario = request.user.groups.values_list('name', flat=True)  # Obtén los grupos del usuario

    # Contexto para el template
    contexto = {
        'grafico_frecuencia_html': grafico_frecuencia_html,
        'grafico_contribucion_html': grafico_contribucion_html,
        'grupos': grupos_usuario  # Pasar los grupos del usuario a la plantilla
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
    
    # Obtener el carrito de la sesión
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
    
    return redirect('Ventas')