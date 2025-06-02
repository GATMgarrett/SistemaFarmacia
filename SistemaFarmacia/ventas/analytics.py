import os
import sys
import django
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configurar Django antes de importar los modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaFarmacia.settings')
# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Ahora se pueden importar los modelos de Django
from ventas.models import DetalleVenta, Medicamentos

def main():
    # Cargar datos de ventas
    detalle_ventas = DetalleVenta.objects.all()
    print(f"Cargando {detalle_ventas.count()} registros de ventas...")
    
    detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values('venta__fecha_venta', 'cantidad', 'medicamento_id', 'medicamento__nombre')))
    
    if detalle_ventas_data.empty:
        print("No hay datos de ventas para analizar.")
        return
    
    # Preprocesar los datos
    detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])
    detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month
    detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year
    detalle_ventas_data['dia_semana'] = detalle_ventas_data['fecha_venta'].dt.dayofweek
    
    # Determinar el último mes de datos para comenzar las predicciones desde ahí
    ultima_fecha = detalle_ventas_data['fecha_venta'].max()
    print("\nResumen de datos cargados:")
    print(f"Periodo de datos: {detalle_ventas_data['fecha_venta'].min()} a {ultima_fecha}")
    print(f"Número de medicamentos diferentes: {detalle_ventas_data['medicamento_id'].nunique()}")
    
    # Calcular la fecha de inicio para las predicciones (primer día del mes siguiente al último dato)
    next_month = ultima_fecha.replace(day=1) + pd.DateOffset(months=1)
    
    # Agrupar datos por medicamento y por mes/año
    detalle_ventas_data_grouped = detalle_ventas_data.groupby(['medicamento_id', 'medicamento__nombre', 'año', 'mes']).agg({'cantidad': 'sum'}).reset_index()
    
    # Lista de medicamentos
    medicamentos = Medicamentos.objects.all()
    print(f"\nAnalizando {medicamentos.count()} medicamentos...")
    
    # Clase para la Red Bayesiana Dinámica
    class DynamicBayesianNetwork:
        def __init__(self, n_components=3):
            """
            Implementa una Red Bayesiana Dinámica para predicción de ventas.
            
            Parámetros:
            -----------
            n_components: int
                Número de componentes ocultos (estacionalidad, tendencia, aleatorio)
            """
            self.n_components = n_components
            
            # Parámetros del modelo
            self.level = 0.0            # Nivel base (intercepto)
            self.trend = 0.0            # Tendencia
            self.seasonality = {}       # Efectos estacionales por mes
            
            # Hiperparámetros para la actualización bayesiana
            self.alpha_level = 0.1      # Tasa de aprendizaje para el nivel
            self.alpha_trend = 0.01     # Tasa de aprendizaje para la tendencia
            self.alpha_season = 0.05    # Tasa de aprendizaje para la estacionalidad
            
            # Varianzas para los componentes estocásticos
            self.sigma_level = 1.0
            self.sigma_trend = 0.1
            self.sigma_season = 0.5
            self.sigma_obs = 5.0
            
            # Inicializar estacionalidad
            for m in range(1, 13):
                self.seasonality[m] = 0.0
            
            # Matriz de covarianza para el filtro de Kalman
            self.P = np.eye(2) * 10  # Matriz de covarianza inicial para [level, trend]
            
            # Historial para diagnóstico
            self.history = {
                'level': [],
                'trend': [],
                'forecast': [],
                'actual': []
            }
        
        def update(self, y, month, year):
            """
            Actualiza el modelo con una nueva observación utilizando inferencia bayesiana.
            """
            # Predicción actual
            forecast = self.predict(month, year)
            
            # Componente estacional para el mes actual
            s_t = self.seasonality[month]
            
            # Error de predicción (innovación)
            error = y - forecast
            
            # Matriz de transición de estado
            A = np.array([[1, 1], [0, 1]])
            
            # Matriz de observación
            H = np.array([1, 0])
            
            # Matrices de covarianza de ruido del proceso y observación
            Q = np.diag([self.sigma_level, self.sigma_trend])
            R = np.array([self.sigma_obs])
            
            # Paso de predicción del filtro de Kalman
            x_pred = A @ np.array([self.level, self.trend])
            P_pred = A @ self.P @ A.T + Q
            
            # Paso de actualización del filtro de Kalman
            K = P_pred @ H.T / (H @ P_pred @ H.T + R)
            
            # Actualizar estado
            x_update = x_pred + K * (y - (x_pred[0] + s_t))
            self.P = (np.eye(2) - np.outer(K, H)) @ P_pred
            
            # Extraer componentes actualizados
            self.level, self.trend = x_update
            
            # Actualizar estacionalidad con enfoque bayesiano
            prior_season = self.seasonality[month]
            posterior_precision = 1/self.sigma_season + 1/self.sigma_obs
            posterior_mean = (prior_season/self.sigma_season + error/self.sigma_obs) / posterior_precision
            
            # Actualizar el componente estacional
            self.seasonality[month] = posterior_mean
            
            # Registrar para diagnóstico
            self.history['level'].append(self.level)
            self.history['trend'].append(self.trend)
            self.history['forecast'].append(forecast)
            self.history['actual'].append(y)
            
            return forecast
        
        def predict(self, month, year, steps=1):
            """
            Realiza una predicción para un mes y año específicos.
            Opcionalmente predice múltiples pasos adelante.
            """
            forecasts = []
            current_level = self.level
            current_trend = self.trend
            current_month = month
            current_year = year
            
            for _ in range(steps):
                # Componente estacional
                season_component = self.seasonality[current_month]
                
                # Predecir con el modelo actual
                forecast = current_level + season_component
                forecasts.append(forecast)
                
                # Actualizar para el siguiente paso
                current_level += current_trend
                
                # Añadir algo de ruido estocástico para hacer las predicciones más realistas
                current_level += np.random.normal(0, np.sqrt(self.sigma_level))
                current_trend += np.random.normal(0, np.sqrt(self.sigma_trend))
                
                # Avanzar al siguiente mes
                current_month = (current_month % 12) + 1
                if current_month == 1:
                    current_year += 1
            
            if steps == 1:
                return forecasts[0]
            return forecasts
        
        def fit(self, y_values, months, years):
            """
            Entrena el modelo con datos históricos.
            """
            # Inicializar nivel con la media de los primeros datos
            if len(y_values) > 0:
                self.level = np.mean(y_values[:min(3, len(y_values))])
            
            # Inicializar tendencia si hay suficientes datos
            if len(y_values) >= 2:
                self.trend = (y_values[1] - y_values[0]) / 10  # Suavizado para evitar sobreajuste
            
            # Entrenar el modelo secuencialmente
            for i in range(len(y_values)):
                self.update(y_values[i], months[i], years[i])
            
            return self
    
    # Crear predicciones para cada medicamento
    predicciones_totales = []
    datos_historicos = {}
    
    for medicamento in medicamentos:
        # Filtrar datos de ventas de un solo medicamento
        medicamento_data = detalle_ventas_data_grouped[detalle_ventas_data_grouped['medicamento_id'] == medicamento.id]
        
        if medicamento_data.empty:
            print(f"No hay datos de ventas para el medicamento: {medicamento.nombre}")
            continue
        
        print(f"\nProcesando medicamento: {medicamento.nombre}")
        
        # Crear variables de entrada y salida
        meses = medicamento_data['mes'].values
        años = medicamento_data['año'].values
        ventas = medicamento_data['cantidad'].values
        
        if len(ventas) < 3:  # Necesitamos al menos 3 meses de datos
            print(f"  - Datos insuficientes para entrenamiento ({len(ventas)} registros)")
            continue
            
        print(f"  - Datos disponibles: {len(ventas)} meses")
        
        # Guardar datos históricos para graficarlos después
        datos_historicos[medicamento.id] = {
            'fechas': [datetime(int(años[i]), int(meses[i]), 15) for i in range(len(meses))],
            'ventas': ventas,
            'nombre': medicamento.nombre
        }
        
        # Crear y entrenar el modelo de red bayesiana dinámica
        dbn = DynamicBayesianNetwork()
        dbn.fit(ventas, meses, años)
        
        # Crear fechas futuras para predicción
        future_dates = pd.date_range(start=next_month, periods=6, freq='MS')
        future_months = future_dates.month.tolist()
        future_years = future_dates.year.tolist()
        
        # Realizar predicciones para cada mes futuro
        future_predictions = []
        current_dbn = DynamicBayesianNetwork()
        
        # Copiar el estado del modelo entrenado
        current_dbn.level = dbn.level
        current_dbn.trend = dbn.trend
        current_dbn.seasonality = dbn.seasonality.copy()
        current_dbn.P = dbn.P.copy()
        
        # Predicciones paso a paso para capturar la dinámica
        for i in range(len(future_months)):
            # Añadir variabilidad estocástica específica del medicamento
            # Los medicamentos más vendidos tienden a tener más variabilidad
            mean_sales = np.mean(ventas)
            variability = np.sqrt(mean_sales) * 0.2  # Factor de escala para la variabilidad
            
            # Generar predicción con componente estocástico
            prediction = current_dbn.predict(future_months[i], future_years[i])
            
            # Añadir variabilidad basada en las ventas históricas y estacionalidad
            month_factor = 1.0
            # Más ventas en invierno (meses 5-8 en hemisferio sur)
            if 5 <= future_months[i] <= 8:
                month_factor = 1.1
            # Menos ventas en verano (meses 11-2 en hemisferio sur)
            elif future_months[i] == 11 or future_months[i] == 12 or future_months[i] <= 2:
                month_factor = 0.9
                
            # Calcular variabilidad según el mes (más alta a fin de mes)
            noise = np.random.normal(0, variability * month_factor)
            
            # Asegurar que la predicción sea positiva
            final_prediction = max(0, prediction + noise)
            future_predictions.append(final_prediction)
            
            # Actualizar el modelo para la siguiente predicción (simulando datos futuros)
            current_dbn.update(final_prediction, future_months[i], future_years[i])
        
        # Crear DataFrame con las predicciones
        future_data = pd.DataFrame({
            'fecha_venta': future_dates,
            'medicamento_id': medicamento.id,
            'nombre_medicamento': medicamento.nombre,
            'predicted_sales': future_predictions
        })
        
        # Agregar las predicciones a la lista de resultados
        predicciones_totales.append(future_data)
    
    if not predicciones_totales:
        print("\nNo se pudieron generar predicciones para ningún medicamento.")
        return
        
    # Concatenar las predicciones de todos los medicamentos
    resultados_predicciones = pd.concat(predicciones_totales, ignore_index=True)
    
    # Mostrar resultados
    print("\nPredicciones de ventas para los próximos 6 meses:")
    print(f"Periodo de predicción: {next_month.strftime('%B %Y')} a {future_dates[-1].strftime('%B %Y')}")
    
    for medicamento_id in resultados_predicciones['medicamento_id'].unique():
        med_data = resultados_predicciones[resultados_predicciones['medicamento_id'] == medicamento_id]
        nombre = med_data['nombre_medicamento'].iloc[0]
        print(f"\n{nombre}:")
        for _, row in med_data.iterrows():
            print(f"  {row['fecha_venta'].strftime('%b %Y')}: {int(round(row['predicted_sales']))} unidades")
    
    # Graficar predicciones para todos los medicamentos
    plt.figure(figsize=(15, 8))
    
    # Agregar una línea vertical para separar datos históricos de predicciones
    plt.axvline(x=next_month, color='gray', linestyle='--', alpha=0.7, label='Inicio predicciones')
    
    # Colores para los diferentes medicamentos
    colors = plt.cm.tab10.colors
    
    # Graficar datos históricos y predicciones para cada medicamento
    for i, medicamento_id in enumerate(resultados_predicciones['medicamento_id'].unique()):
        color = colors[i % len(colors)]
        
        # Datos históricos
        if medicamento_id in datos_historicos:
            hist_data = datos_historicos[medicamento_id]
            plt.plot(hist_data['fechas'], hist_data['ventas'], 'o-', color=color, alpha=0.7, 
                    label=f"Histórico - {hist_data['nombre']}")
        
        # Predicciones
        pred_data = resultados_predicciones[resultados_predicciones['medicamento_id'] == medicamento_id]
        plt.plot(pred_data['fecha_venta'], pred_data['predicted_sales'], 's--', color=color, 
                label=f"Predicción - {pred_data['nombre_medicamento'].iloc[0]}")
    
    # Configurar el gráfico
    plt.xlabel("Fecha", fontsize=12)
    plt.ylabel("Unidades vendidas", fontsize=12)
    plt.title("Predicción de Ventas con Red Bayesiana Dinámica", fontsize=14)
    
    # Mejorar la visualización
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Configurar las fechas en el eje X para que se vean mejor
    plt.gcf().autofmt_xdate()
    
    # Añadir texto explicativo
    plt.figtext(0.5, 0.01, 
                "Líneas continuas: datos históricos | Líneas punteadas: predicciones", 
                ha='center', fontsize=10, bbox={"facecolor":"lightgray", "alpha":0.5, "pad":5})
    
    # Mostrar la leyenda en una ubicación óptima
    plt.legend(loc='best', fontsize=9)
    
    plt.show()

if __name__ == '__main__':
    main()
