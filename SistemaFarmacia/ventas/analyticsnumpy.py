import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ventas.models import DetalleVenta  # Asegúrate de importar el modelo adecuado

detalle_ventas = DetalleVenta.objects.all()
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values('venta__fecha_venta', 'cantidad', 'medicamento_id', 'medicamento__nombre')))

detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])  # Convertir a tipo datetime
detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month  # Extraer mes
detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year  # Extraer año

# Agrupar datos por medicamento y por mes/año
detalle_ventas_data_grouped = detalle_ventas_data.groupby(['medicamento_id', 'año', 'mes']).agg({'cantidad': 'sum'}).reset_index()

# Crear matrices de entrada (X) y salida (y)
X = detalle_ventas_data_grouped[['mes', 'año']].values
y = detalle_ventas_data_grouped['cantidad'].values

X = (X - np.mean(X, axis=0)) / np.std(X, axis=0)  # Estandarizar (muy común en regresión lineal)

X = np.hstack([np.ones((X.shape[0], 1)), X])  # Añadimos una columna de unos para el intercepto
# Matriz de covarianza de los parámetros
alpha = np.random.normal(0, 10, 1000)  # Prior para alpha
beta_mes = np.random.normal(0, 10, 1000)  # Prior para beta_mes
beta_año = np.random.normal(0, 10, 1000)  # Prior para beta_año
sigma = np.abs(np.random.normal(1, 0.1, 1000))  # Prior para sigma

mu = alpha[:, None] + beta_mes[:, None] * X[:, 1] + beta_año[:, None] * X[:, 2]
mu_mean = np.mean(mu, axis=0)

# Obtener nombres de medicamentos de la base de datos
medicamentos = detalle_ventas_data[['medicamento_id', 'medicamento__nombre']].drop_duplicates()

# Crear un diccionario que mapea el ID del medicamento con su nombre
medicamento_dict = dict(zip(medicamentos['medicamento_id'], medicamentos['medicamento__nombre']))

predicciones_por_medicamento = {}

for medicamento_id in medicamentos['medicamento_id']:
    # Filtrar los datos por medicamento
    medicamento_data = detalle_ventas_data_grouped[detalle_ventas_data_grouped['medicamento_id'] == medicamento_id]
    X_medicamento = medicamento_data[['mes', 'año']].values
    y_medicamento = medicamento_data['cantidad'].values
    X_medicamento = (X_medicamento - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)  # Usar la media y std global
    X_medicamento = np.hstack([np.ones((X_medicamento.shape[0], 1)), X_medicamento])

    # Predicción con los parámetros medios de la muestra para este medicamento
    predicciones_medicamento = np.mean(alpha) + np.mean(beta_mes) * X_medicamento[:, 1] + np.mean(beta_año) * X_medicamento[:, 2]
    
    # Guardar las predicciones, usando el nombre del medicamento en lugar del ID
    predicciones_por_medicamento[medicamento_dict[medicamento_id]] = predicciones_medicamento

# Solicitar al usuario un rango de fechas futuras (por ejemplo, 6 meses más)
# Esto puede ser parte de un formulario o input manual.
future_dates = pd.date_range(start='2024-12-01', periods=6, freq='MS')  # 6 meses
future_data = pd.DataFrame({'fecha_venta': future_dates})
future_data['mes'] = future_data['fecha_venta'].dt.month
future_data['año'] = future_data['fecha_venta'].dt.year

# Normalizar las fechas futuras (usando la misma media y desviación estándar de los datos anteriores)
future_X = future_data[['mes', 'año']].values
future_X = (future_X - np.mean(X[:, 1:], axis=0)) / np.std(X[:, 1:], axis=0)
future_X = np.hstack([np.ones((future_X.shape[0], 1)), future_X])  # Añadimos la columna de unos

# Realizar la predicción para cada medicamento
future_predictions_por_medicamento = {}

for medicamento_id in medicamentos['medicamento_id']:
    future_predictions = np.mean(alpha) + np.mean(beta_mes) * future_X[:, 1] + np.mean(beta_año) * future_X[:, 2]
    future_predictions_por_medicamento[medicamento_dict[medicamento_id]] = future_predictions

# Mostrar las predicciones futuras para cada medicamento
for medicamento, predicciones in future_predictions_por_medicamento.items():
    print(f"Predicciones para el medicamento {medicamento}:")
    print(future_data[['fecha_venta']].assign(predicted_sales=predicciones))

# Graficar las predicciones para cada medicamento
plt.figure(figsize=(12, 6))
for medicamento, predicciones in future_predictions_por_medicamento.items():
    plt.plot(future_data['fecha_venta'], predicciones, label=f"{medicamento}")

plt.xlabel("Fecha")
plt.ylabel("Ventas Predichas")
plt.title("Predicción de Ventas Mensuales por Medicamento con Regresión Bayesiana Dinámica")
plt.legend()
plt.grid(True)
plt.show()
