import numpy as np
import pandas as pd
import plotly.express as px
from ventas.models import DetalleVenta, Ventas

# Obtener los detalles de ventas y la información de la venta
detalle_ventas = DetalleVenta.objects.all()

# Verificar si hay datos en la base de datos
if not detalle_ventas.exists():
    def obtener_grafico_predicciones():
        return "<h3>No hay datos disponibles para generar predicciones.</h3>"
else:
    # Crear un DataFrame con los datos obtenidos, incluyendo las fechas de venta
    detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values(
        'venta__fecha_venta', 'cantidad', 'medicamento_id', 'medicamento__nombre'
    )))

    # Convertir las fechas a formato datetime
    detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])
    detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month
    detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year

    # Agrupar por medicamento, año y mes
    detalle_ventas_data_grouped = detalle_ventas_data.groupby(
        ['medicamento_id', 'año', 'mes']
    ).agg({'cantidad': 'sum'}).reset_index()

    # Extraer variables para entrenamiento
    X = detalle_ventas_data_grouped[['mes', 'año']].values
    y = detalle_ventas_data_grouped['cantidad'].values

    # Limpiar los datos (reemplazar NaN por 0)
    X = np.nan_to_num(X)

    # Verificar si hay desviación estándar cero y evitar división por cero
    std_devs = np.std(X, axis=0)
    if np.any(std_devs == 0):
        print("Advertencia: La desviación estándar de alguna columna es cero.")
        # Reemplazar la desviación estándar cero por 1 para evitar la división por cero
        std_devs[std_devs == 0] = 1
    
    # Normalizar los datos
    X_normalized = (X - np.mean(X, axis=0)) / std_devs
    
    # Asegurarse de que X_normalized no tenga NaN ni inf
    X_normalized = np.nan_to_num(X_normalized)

    # Añadir una columna de 1 para el término independiente (sesgo)
    X_normalized = np.hstack([np.ones((X_normalized.shape[0], 1)), X_normalized])

    # Definir priors para la regresión lineal simple
    alpha = np.random.normal(0, 10, 1000)
    beta_mes = np.random.normal(0, 10, 1000)
    beta_año = np.random.normal(0, 10, 1000)

    # Modelo de predicción simple
    mu = alpha[:, None] + beta_mes[:, None] * X_normalized[:, 1] + beta_año[:, None] * X_normalized[:, 2]
    mu_mean = np.mean(mu, axis=0)

    # Obtener los nombres de los medicamentos
    medicamentos = detalle_ventas_data[['medicamento_id', 'medicamento__nombre']].drop_duplicates()
    medicamento_dict = dict(zip(medicamentos['medicamento_id'], medicamentos['medicamento__nombre']))

    # Predicciones por medicamento
    predicciones_por_medicamento = {}
    for medicamento_id in medicamentos['medicamento_id']:
        medicamento_data = detalle_ventas_data_grouped[detalle_ventas_data_grouped['medicamento_id'] == medicamento_id]
        X_medicamento = medicamento_data[['mes', 'año']].values
        # Normalizar para cada medicamento, evitando NaN e inf
        X_medicamento_normalized = (X_medicamento - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)
        X_medicamento_normalized = np.nan_to_num(X_medicamento_normalized)
        X_medicamento_normalized = np.hstack([np.ones((X_medicamento_normalized.shape[0], 1)), X_medicamento_normalized])

        # Realizar la predicción
        predicciones_medicamento = np.mean(alpha) + np.mean(beta_mes) * X_medicamento_normalized[:, 1] + np.mean(beta_año) * X_medicamento_normalized[:, 2]
        predicciones_por_medicamento[medicamento_dict[medicamento_id]] = predicciones_medicamento

    # Fechas futuras para las predicciones (predecir para los próximos 6 meses, por ejemplo)
    future_dates = pd.date_range(start='2024-12-01', periods=6, freq='MS')
    future_data = pd.DataFrame({'fecha_venta': future_dates})
    future_data['mes'] = future_data['fecha_venta'].dt.month
    future_data['año'] = future_data['fecha_venta'].dt.year

    # Normalizar fechas futuras
    future_X = future_data[['mes', 'año']].values
    future_X = (future_X - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)
    future_X = np.nan_to_num(future_X)  # Asegurarse de que no haya NaN

    future_X = np.hstack([np.ones((future_X.shape[0], 1)), future_X])

    # Predicciones futuras por medicamento
    future_predictions_por_medicamento = {}
    for medicamento_id in medicamentos['medicamento_id']:
        future_predictions = np.mean(alpha) + np.mean(beta_mes) * future_X[:, 1] + np.mean(beta_año) * future_X[:, 2]
        future_predictions_por_medicamento[medicamento_dict[medicamento_id]] = future_predictions

    # Generar gráfico de predicciones
    fig = px.line(
        future_data,
        x='fecha_venta',
        y=list(future_predictions_por_medicamento.values()),
        labels={'value': 'Ventas Predichas', 'fecha_venta': 'Fecha'},
        title="Predicción de Ventas Mensuales por Medicamento"
    )

    # Actualizar diseño del gráfico
    fig.update_layout(xaxis_title="Fecha", yaxis_title="Ventas Predichas")

    # Convertir gráfico a HTML
    grafico_html = fig.to_html(full_html=False)

    # Función para retornar el gráfico
    def obtener_grafico_predicciones():
        return grafico_html
