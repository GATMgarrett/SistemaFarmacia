import pandas as pd
from pgmpy.models import BayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator
from pgmpy.inference import VariableElimination
from ventas.models import DetalleVenta

# Obtener los datos de ventas
detalle_ventas = DetalleVenta.objects.all().select_related('venta', 'medicamento')

# Verificar si hay datos
if not detalle_ventas.exists():
    print("No hay datos disponibles.")
    exit()

# Crear un DataFrame
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values(
    'venta__fecha_venta', 'medicamento__nombre', 'cantidad'
)))

# Preprocesar los datos
detalle_ventas_data['fecha'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])
detalle_ventas_data['mes'] = detalle_ventas_data['fecha'].dt.to_period('M')  # Agrupar por mes
detalle_ventas_data = detalle_ventas_data.groupby(['mes', 'medicamento__nombre']).agg({'cantidad': 'sum'}).reset_index()
detalle_ventas_data = detalle_ventas_data.rename(columns={'medicamento__nombre': 'medicamento', 'cantidad': 'cantidad_vendida'})

# Convertir columnas categóricas
detalle_ventas_data['mes'] = detalle_ventas_data['mes'].astype(str)  # Convertir Period a string
detalle_ventas_data['medicamento'] = detalle_ventas_data['medicamento'].astype(str)

# Definir la estructura de la red
model = BayesianNetwork([('mes', 'medicamento'), ('medicamento', 'cantidad_vendida')])

# Entrenar la red con estimador de máxima verosimilitud
model.fit(detalle_ventas_data, estimator=MaximumLikelihoodEstimator)

# Realizar inferencias
inferencia = VariableElimination(model)

# Predicción para un medicamento específico en un mes
consulta = inferencia.map_query(variables=['cantidad_vendida'], evidence={'mes': '2024-12', 'medicamento': 'Paracetamol'})

print(f"Predicción para Paracetamol en diciembre de 2024: {consulta['cantidad_vendida']}")
