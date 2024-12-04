import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ventas.models import DetalleVenta
from datetime import timedelta

def obtener_grafico_predicciones():
    # Obtener los detalles de las ventas junto con la fecha de la venta
    detalle_ventas = DetalleVenta.objects.all().select_related('venta', 'medicamento')

    # Verificar si hay datos disponibles
    if not detalle_ventas.exists():
        return "<h3>No hay datos disponibles para generar predicciones.</h3>"

    # Crear un DataFrame a partir de los detalles de ventas
    detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values(
        'venta__fecha_venta', 'medicamento__nombre', 'cantidad', 'medicamento__categoria__nombre_categoria'
    )))

    # Convertir la fecha de venta a formato datetime
    detalle_ventas_data['venta__fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])

    # Renombrar las columnas para mayor claridad
    detalle_ventas_data.rename(columns={
        'venta__fecha_venta': 'fecha_venta',
        'medicamento__nombre': 'medicamento',
        'cantidad': 'cantidad_vendida',
        'medicamento__categoria__nombre_categoria': 'categoria'
    }, inplace=True)

    # Agrupar por mes, medicamento y categoría, sumando la cantidad de ventas
    detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.to_period('M')
    ventas_mensuales = detalle_ventas_data.groupby(['mes', 'medicamento', 'categoria']).agg({'cantidad_vendida': 'sum'}).reset_index()

    # Convertir el período del mes a una fecha de inicio para graficar
    ventas_mensuales['fecha_mes'] = ventas_mensuales['mes'].dt.to_timestamp()

    # Crear figura inicial
    fig = go.Figure()

    # Obtener categorías y medicamentos únicos
    categorias = ventas_mensuales['categoria'].unique()
    medicamentos = ventas_mensuales['medicamento'].unique()

    for categoria in categorias:
        for medicamento in medicamentos:
            # Filtrar datos del medicamento y la categoría
            datos_filtrados = ventas_mensuales[(ventas_mensuales['categoria'] == categoria) & (ventas_mensuales['medicamento'] == medicamento)]
            if datos_filtrados.empty:
                continue

            # Predicción
            min_date = datos_filtrados['fecha_mes'].min()
            datos_filtrados['meses'] = ((datos_filtrados['fecha_mes'].dt.year - min_date.year) * 12 + 
                                        (datos_filtrados['fecha_mes'].dt.month - min_date.month))

            X = datos_filtrados['meses'].values
            y = datos_filtrados['cantidad_vendida'].values

            degree = 2
            poly_coeffs = np.polyfit(X, y, degree)
            poly_func = np.poly1d(poly_coeffs)

            # Generar meses futuros
            future_months = np.arange(X[-1] + 1, X[-1] + 7)  # Predicción para los próximos 6 meses
            predictions = poly_func(future_months)

            # Añadir ruido
            noise = np.random.normal(loc=0, scale=0.5, size=len(predictions))
            noisy_predictions = np.maximum(predictions + noise * predictions, 0)

            # Crear fechas futuras
            future_dates = [min_date + pd.DateOffset(months=int(m)) for m in future_months]

            # Añadir la línea al gráfico
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=noisy_predictions,
                mode='lines',
                name=f'{medicamento} ({categoria}) - Predicción',
                visible=False
            ))

    # Activar solo las líneas de la primera categoría inicialmente
    for i, trace in enumerate(fig.data):
        if categorias[0] in trace.name:
            fig.data[i].visible = True

    # Crear botones para categorías
    botones = []
    for categoria in categorias:
        visibilidad = [categoria in trace.name for trace in fig.data]
        botones.append(dict(
            label=categoria,
            method="update",
            args=[{"visible": visibilidad}, {"title": f"Categoría: {categoria}"}]
        ))

    # Añadir menú de botones
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=botones,
                direction="down",
                showactive=True,
                x=0.5,
                xanchor="center",
                y=1.2,
                yanchor="top"
            )
        ]
    )

    # Configuración general del gráfico
    fig.update_layout(
        title="Predicciones (Mensuales)",
        xaxis_title="Mes",
        yaxis_title="Cantidad Vendida (Predicha)",
        legend_title="Medicamentos",
        template="plotly_white"
    )

    # Retornar el gráfico en formato HTML
    return fig.to_html(full_html=False)
