import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ventas.models import DetalleVenta, Medicamentos

# Cargar datos de ventas
detalle_ventas = DetalleVenta.objects.all()
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values('venta__fecha_venta', 'cantidad', 'medicamento_id')))

# Preprocesar los datos
detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])
detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month
detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year

# Agrupar datos por medicamento y por mes/año
detalle_ventas_data_grouped = detalle_ventas_data.groupby(['medicamento_id', 'año', 'mes']).agg({'cantidad': 'sum'}).reset_index()

# Crear un modelo bayesiano dinámico
class BayesianDynamicModel:
    def __init__(self, initial_alpha=0, initial_beta=0, sigma_alpha=1, sigma_beta=1, sigma_obs=5):
        # Parámetros iniciales del modelo
        self.alpha = initial_alpha  # Intercepto inicial
        self.beta = initial_beta    # Pendiente inicial (una para mes, otra para año)
        self.sigma_alpha = sigma_alpha  # Varianza del intercepto
        self.sigma_beta = sigma_beta    # Varianza de los coeficientes
        self.sigma_obs = sigma_obs      # Varianza del ruido observacional

    def predict(self, X):
        return self.alpha + np.dot(X, self.beta)

    def update(self, X, y):
        """
        Actualiza los parámetros del modelo basándose en los datos observados.
        """
        # Predicciones actuales
        y_pred = self.predict(X)

        # Residuos
        residuals = y - y_pred

        # Actualización bayesiana para alpha y beta
        self.alpha += np.mean(residuals) / (1 + self.sigma_alpha)
        self.beta += np.dot(residuals, X) / (1 + self.sigma_beta)

# Lista de medicamentos
medicamentos = Medicamentos.objects.all()

# Crear predicciones para cada medicamento
predicciones_totales = []
for medicamento in medicamentos:
    # Filtrar datos de ventas de un solo medicamento
    medicamento_data = detalle_ventas_data_grouped[detalle_ventas_data_grouped['medicamento_id'] == medicamento.id]

    # Crear variables de entrada (mes y año) y salida (cantidad vendida)
    X = medicamento_data[['mes', 'año']].values
    y = medicamento_data['cantidad'].values

    # Iniciar el modelo bayesiano dinámico
    bdm = BayesianDynamicModel(initial_alpha=np.mean(y), initial_beta=np.array([0, 0]))

    # Ajustar el modelo iterativamente
    for t in range(len(y)):
        bdm.update(X[t:t+1], y[t:t+1])

    # Crear datos futuros para predicción
    future_dates = pd.date_range(start='2024-12-01', periods=6, freq='MS')  # 6 meses
    future_data = pd.DataFrame({'fecha_venta': future_dates})
    future_data['mes'] = future_data['fecha_venta'].dt.month
    future_data['año'] = future_data['fecha_venta'].dt.year
    future_X = future_data[['mes', 'año']].values

    # Realizar predicciones
    future_data['medicamento_id'] = medicamento.id
    future_data['predicted_sales'] = bdm.predict(future_X).clip(min=0)  # Asegurar que no haya valores negativos

    # Agregar las predicciones a la lista de resultados
    predicciones_totales.append(future_data[['medicamento_id', 'fecha_venta', 'predicted_sales']])

# Concatenar las predicciones de todos los medicamentos
resultados_predicciones = pd.concat(predicciones_totales, ignore_index=True)

# Mostrar resultados
print(resultados_predicciones)

# Graficar predicciones para todos los medicamentos
plt.figure(figsize=(12, 6))
for medicamento in medicamentos:
    # Filtrar las predicciones por medicamento
    pred_data = resultados_predicciones[resultados_predicciones['medicamento_id'] == medicamento.id]
    plt.plot(pred_data['fecha_venta'], pred_data['predicted_sales'], label=f"Predicción - {medicamento.nombre}")

plt.xlabel("Fecha")
plt.ylabel("Ventas Predichas")
plt.title("Predicción de Ventas Mensuales por Medicamento")
plt.legend()
plt.grid()
plt.show()
