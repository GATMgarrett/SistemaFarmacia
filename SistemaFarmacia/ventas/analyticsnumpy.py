import numpy as np
import pandas as pd
import plotly.express as px
from ventas.models import DetalleVenta  # Asegúrate de importar el modelo adecuado

# Obtener los datos de ventas
detalle_ventas = DetalleVenta.objects.all()
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values('venta__fecha_venta', 'cantidad', 'medicamento_id', 'medicamento__nombre')))

# Convertir las fechas a formato datetime y extraer el mes y el año
detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])  
detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month  
detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year  

# Agrupar los datos por medicamento, año y mes
detalle_ventas_data_grouped = detalle_ventas_data.groupby(['medicamento_id', 'año', 'mes']).agg({'cantidad': 'sum'}).reset_index()

# Crear matrices de entrada (X) y salida (y)
X = detalle_ventas_data_grouped[['mes', 'año']].values
y = detalle_ventas_data_grouped['cantidad'].values

# Estandarizar X
X = (X - np.mean(X, axis=0)) / np.std(X, axis=0)

# Añadir una columna de unos para el intercepto en la regresión
X = np.hstack([np.ones((X.shape[0], 1)), X])

# Definir priors para la regresión bayesiana
alpha = np.random.normal(0, 10, 1000)
beta_mes = np.random.normal(0, 10, 1000)
beta_año = np.random.normal(0, 10, 1000)
sigma = np.abs(np.random.normal(1, 0.1, 1000))

# Modelo de predicción (mu)
mu = alpha[:, None] + beta_mes[:, None] * X[:, 1] + beta_año[:, None] * X[:, 2]
mu_mean = np.mean(mu, axis=0)

# Obtener los nombres de los medicamentos
medicamentos = detalle_ventas_data[['medicamento_id', 'medicamento__nombre']].drop_duplicates()

# Crear un diccionario de mapeo de ID a nombre de medicamento
medicamento_dict = dict(zip(medicamentos['medicamento_id'], medicamentos['medicamento__nombre']))

# Diccionario para almacenar las predicciones por medicamento
predicciones_por_medicamento = {}

# Generar predicciones por cada medicamento
for medicamento_id in medicamentos['medicamento_id']:
    medicamento_data = detalle_ventas_data_grouped[detalle_ventas_data_grouped['medicamento_id'] == medicamento_id]
    X_medicamento = medicamento_data[['mes', 'año']].values
    y_medicamento = medicamento_data['cantidad'].values
    X_medicamento = (X_medicamento - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)
    X_medicamento = np.hstack([np.ones((X_medicamento.shape[0], 1)), X_medicamento])

    # Realizar la predicción para este medicamento
    predicciones_medicamento = np.mean(alpha) + np.mean(beta_mes) * X_medicamento[:, 1] + np.mean(beta_año) * X_medicamento[:, 2]
    predicciones_por_medicamento[medicamento_dict[medicamento_id]] = predicciones_medicamento

# Generar fechas futuras para las predicciones
future_dates = pd.date_range(start='2024-12-01', periods=6, freq='MS')  # 6 meses de predicción
future_data = pd.DataFrame({'fecha_venta': future_dates})
future_data['mes'] = future_data['fecha_venta'].dt.month
future_data['año'] = future_data['fecha_venta'].dt.year

# Normalizar las fechas futuras
future_X = future_data[['mes', 'año']].values
future_X = (future_X - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)
future_X = np.hstack([np.ones((future_X.shape[0], 1)), future_X])

# Realizar predicciones para cada medicamento en el rango de fechas futuras
future_predictions_por_medicamento = {}

for medicamento_id in medicamentos['medicamento_id']:
    future_predictions = np.mean(alpha) + np.mean(beta_mes) * future_X[:, 1] + np.mean(beta_año) * future_X[:, 2]
    future_predictions_por_medicamento[medicamento_dict[medicamento_id]] = future_predictions

# Generar gráfico de predicciones usando Plotly
fig = px.line(future_data, 
              x='fecha_venta', 
              y=list(future_predictions_por_medicamento.values()),  # Convertir a lista para pasar a Plotly
              labels={'value': 'Ventas Predichas', 'fecha_venta': 'Fecha'},
              title="Predicción de Ventas Mensuales por Medicamento")

# Actualizar el diseño del gráfico
fig.update_layout(xaxis_title="Fecha", yaxis_title="Ventas Predichas")

# Convertir el gráfico a HTML para insertarlo en la plantilla
grafico_html = fig.to_html(full_html=False)

# Función que devuelve el gráfico en formato HTML
def obtener_grafico_predicciones():
    return grafico_html
