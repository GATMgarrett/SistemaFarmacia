from ventas.models import Compras, DetalleCompra, LoteMedicamento, Ventas, DetalleVenta

# Limpiar datos de las tablas relacionadas con compras y ventas
DetalleCompra.objects.all().delete()
DetalleVenta.objects.all().delete()
LoteMedicamento.objects.all().delete()
Compras.objects.all().delete()
Ventas.objects.all().delete()

print("Datos de compras y ventas eliminados.")


#//////////////////////////////////////////////////////////////////////////////////////////
"""
import matplotlib.pyplot as plt
import pandas as pd
from ventas.models import DetalleVenta, Ventas

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

# Crear un gráfico de barras para las ventas diarias por medicamento
plt.figure(figsize=(10, 6))  # Tamaño de la figura
for medicamento in ventas_diarias['medicamento'].unique():
    # Filtrar los datos del medicamento
    data = ventas_diarias[ventas_diarias['medicamento'] == medicamento]
    plt.plot(data['fecha_venta'], data['cantidad_vendida'], label=medicamento)

# Personalizar el gráfico
plt.title('Ventas Diarias por Medicamento')
plt.xlabel('Fecha')
plt.ylabel('Cantidad Vendida')
plt.xticks(rotation=45)  # Rotar las fechas para que no se superpongan
plt.legend(title='Medicamentos')

# Mostrar el gráfico
plt.tight_layout()
plt.show()
"""