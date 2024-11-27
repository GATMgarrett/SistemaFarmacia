import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from ventas.models import DetalleVenta, Ventas
from datetime import timedelta

# Obtener los detalles de las ventas junto con la fecha de la venta
detalle_ventas = DetalleVenta.objects.all().select_related('venta', 'medicamento')

# Crear un DataFrame a partir de los detalles de ventas
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values(
    'venta__fecha_venta', 'medicamento_id', 'medicamento__nombre', 'cantidad'
)))

# Convertir la fecha de venta a formato datetime
detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])

# Agrupar por fecha y medicamento, sumando la cantidad de ventas de cada medicamento en ese día
ventas_diarias = detalle_ventas_data.groupby(['fecha_venta', 'medicamento__nombre']).agg({'cantidad': 'sum'}).reset_index()

# Renombrar las columnas para mayor claridad
ventas_diarias = ventas_diarias.rename(columns={'medicamento__nombre': 'medicamento', 'cantidad': 'cantidad_vendida'})

# Crear un gráfico de ventas diarias por medicamento
plt.figure(figsize=(10, 6))  # Tamaño de la figura

for medicamento in ventas_diarias['medicamento'].unique():
    # Filtrar los datos del medicamento
    data = ventas_diarias[ventas_diarias['medicamento'] == medicamento]
    
    # Convertir las fechas a un formato numérico (el número de días desde la fecha más temprana)
    min_date = data['fecha_venta'].min()
    data['dias'] = (data['fecha_venta'] - min_date).dt.days
    
    # Usar una regresión polinómica para predecir las ventas
    X = data['dias'].values  # Días desde la fecha mínima
    y = data['cantidad_vendida'].values  # Cantidad vendida
    
    # Ajuste polinómico de grado 2 (puedes probar con otro grado si lo deseas)
    degree = 2  
    poly_coeffs = np.polyfit(X, y, degree)  # Ajuste polinómico
    
    # Crear una función polinómica a partir de los coeficientes
    poly_func = np.poly1d(poly_coeffs)
    
    # Generar las predicciones para los días futuros
    future_days = np.arange(X[-1] + 1, X[-1] + 181)  # 180 días adicionales para predicción (6 meses)
    predictions = poly_func(future_days)
    
    # Convertir los días predichos a fechas
    future_dates = pd.to_datetime(min_date + pd.to_timedelta(future_days, unit='D'))
    
    # Añadir ruido a las predicciones para simular fluctuaciones reales
    noise = np.random.normal(loc=0, scale=0.5, size=len(predictions))  # Aumenta el valor de scale para mayor variabilidad
    noisy_predictions = predictions + noise * predictions  # Aumentamos el ruido proporcionalmente a la predicción
    
    # Eliminar valores negativos de las predicciones (hacer que sean cero)
    noisy_predictions = np.maximum(noisy_predictions, 0)  # Asegurarse de que no haya valores negativos
    
    # Suavizar las predicciones con una media móvil de 7 días (puedes ajustar el valor de la ventana si lo deseas)
    smoothed_predictions = pd.Series(noisy_predictions).rolling(window=3).mean().to_numpy()  # Ventana de 3 días para menos suavizado

    # Graficar las ventas actuales y las predicciones
    plt.plot(data['fecha_venta'], data['cantidad_vendida'], label=f'{medicamento} - Ventas Reales')
    plt.plot(future_dates, smoothed_predictions, label=f'{medicamento} - Predicción con Variabilidad', linestyle='--')

# Personalizar el gráfico
plt.title('Ventas Diarias y Predicciones por Medicamento (6 meses adelante) con Variabilidad')
plt.xlabel('Fecha')
plt.ylabel('Cantidad Vendida')
plt.xticks(rotation=45)  # Rotar las fechas para que no se superpongan
plt.legend(title='Medicamentos')

# Mostrar el gráfico
plt.tight_layout()
plt.show()
