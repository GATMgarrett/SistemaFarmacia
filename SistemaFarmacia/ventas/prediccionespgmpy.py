import os
import sys
from pathlib import Path
import django

# 1. Configuración para Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaFarmacia.settings')

# Inicialización de Django
django.setup()

# 2. Importaciones
import pandas as pd
import numpy as np
from pgmpy.models import DynamicBayesianNetwork as DBN
from pgmpy.inference import DBNInference
from django.utils import timezone
import logging

# 3. Configurar logging para mensajes informativos y errores
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 4. Importar modelos Django
from ventas.models import Ventas, DetalleVenta

def cargar_datos():
    """
    Carga datos históricos de ventas de los últimos 6 meses y los prepara
    para el entrenamiento de la red bayesiana dinámica.
    """
    try:
        # Consulta a la base de datos
        fecha_inicio = timezone.now() - timezone.timedelta(days=180)
        logger.info(f"Consultando ventas desde {fecha_inicio.strftime('%Y-%m-%d')}")
        
        ventas_qs = Ventas.objects.filter(
            fecha_venta__gte=fecha_inicio,
            activo=True
        ).values('fecha_venta', 'precio_total')
        
        # Verificar si hay datos
        if not ventas_qs.exists():
            logger.warning("No se encontraron datos de ventas en los últimos 6 meses.")
            return None
            
        # Convertir a DataFrame
        df = pd.DataFrame(list(ventas_qs))
        logger.info(f"Se encontraron {len(df)} registros de ventas")
        
        # Convertir tipos de datos
        df['precio_total'] = pd.to_numeric(df['precio_total'], errors='coerce')
        df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
        
        # Eliminar filas con valores nulos
        df.dropna(subset=['precio_total', 'fecha_venta'], inplace=True)
        
        # Discretizar ventas (bajo, medio, alto)
        df['nivel_venta'] = pd.qcut(
            df['precio_total'], 
            q=3, 
            labels=['bajo', 'medio', 'alto']
        )
        
        # Extraer características temporales
        df['dia_semana'] = df['fecha_venta'].dt.dayofweek
        df['mes'] = df['fecha_venta'].dt.month
        
        # Verificar si hay suficientes datos para entrenar
        if len(df) < 10:
            logger.warning(f"Pocos datos para entrenar el modelo ({len(df)} registros). Se recomienda más datos.")
            
        return df
        
    except Exception as e:
        logger.error(f"Error al cargar datos: {str(e)}")
        return None

def crear_dbn():
    """
    Define un modelo de Red Bayesiana Dinámica (DBN) simplificado para predecir niveles de ventas.
    """
    try:
        # Crear DBN con el constructor básico
        modelo = DBN()
        
        # Definir nodos para ambos time slices
        modelo.add_nodes_from([
            ('Ventas', 0),
            ('Ventas', 1)
        ])
        
        # Definir aristas entre slices (conexión temporal)
        modelo.add_edge(('Ventas', 0), ('Ventas', 1))
        
        # Inicializar la estructura del DBN
        modelo.initialize_initial_state()
        
        return modelo
    except Exception as e:
        logger.error(f"Error al crear la estructura DBN: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def entrenar_modelo(datos):
    """
    Prepara los datos y entrena el modelo DBN simplificado.
    """
    try:
        from pgmpy.factors.discrete import TabularCPD
        
        # Crear DBN usando el nuevo formato
        modelo = crear_dbn()
        if modelo is None:
            return None, None
        
        # Preparar datos - solo necesitamos el nivel de venta
        datos_ventas = datos[['nivel_venta']].copy()
        datos_ventas.columns = ['Ventas']
        datos_ventas['Ventas'] = datos_ventas['Ventas'].astype(str)
        
        # Obtener estados únicos y cardinalidades
        ventas_states = sorted(datos_ventas['Ventas'].unique())
        ventas_card = len(ventas_states)
        
        logger.info(f"Estados de ventas: {ventas_states}, cardinalidad: {ventas_card}")
        
        # Calcular distribución de probabilidad para los niveles de venta
        ventas_counts = datos_ventas['Ventas'].value_counts(normalize=True)
        ventas_probs = np.array([ventas_counts.get(estado, 0) for estado in ventas_states])
        
        # Asegurar que la probabilidad suma 1 (puede haber errores de redondeo)
        ventas_probs = ventas_probs / ventas_probs.sum()
        
        # 1. CPD para Ventas en t=0 (sin padres)
        # Valores debe ser una matriz con forma (variable_card, 1)
        cpd_ventas_0 = TabularCPD(
            variable=('Ventas', 0),
            variable_card=ventas_card,
            values=ventas_probs.reshape(ventas_card, 1),
            state_names={('Ventas', 0): ventas_states}
        )
        
        # 2. CPD para Ventas en t=1 (con dependencia de Ventas en t=0)
        # Simplificación: usamos una matriz de transición uniforme donde cada fila suma 1
        # Valores debe ser una matriz con forma (variable_card, parent_card)
        transition_matrix = np.ones((ventas_card, ventas_card)) / ventas_card
        
        cpd_ventas_1 = TabularCPD(
            variable=('Ventas', 1),
            variable_card=ventas_card,
            values=transition_matrix,
            evidence=[('Ventas', 0)],
            evidence_card=[ventas_card],
            state_names={
                ('Ventas', 1): ventas_states,
                ('Ventas', 0): ventas_states
            }
        )
        
        # Añadir los CPDs al modelo
        logger.info("Añadiendo CPDs al modelo...")
        modelo.add_cpds(cpd_ventas_0, cpd_ventas_1)
        
        if not modelo.check_model():
            logger.error("Modelo inválido")
            return None, None
        
        # Crear objeto para inferencia
        inferencia = DBNInference(modelo)
        
        return modelo, inferencia
    
    except Exception as e:
        logger.error(f"Error al entrenar el modelo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

def predecir(inferencia, dia_semana=5, mes=6, nivel_anterior='medio'):
    """
    Realiza una predicción para un día específico basado en nivel de ventas anterior.
    """
    try:
        if inferencia is None:
            logger.error("No se puede realizar predicción: modelo no entrenado")
            return None
            
        # Realizar inferencia
        resultado = inferencia.forward_inference(
            [('Ventas', 1)],  # Variable objetivo para predicción (tiempo t+1)
            evidence={
                ('Ventas', 0): nivel_anterior,  # Nivel de ventas en tiempo t
                ('DiaSemana', 0): dia_semana,   # Día de la semana (0=lunes, 6=domingo)
                ('Mes', 0): mes                 # Mes (1-12)
            }
        )
        
        # Obtener distribución de probabilidad
        prob_dist = resultado[('Ventas', 1)]
        
        return prob_dist
        
    except Exception as e:
        logger.error(f"Error al realizar predicción: {str(e)}")
        return None

def main():
    """Función principal"""
    print("=== Sistema de Predicción de Ventas ===\n")
    
    # 1. Cargar datos
    print("[1/3] Cargando datos históricos...")
    datos = cargar_datos()
    if datos is None:
        print("No se pudieron cargar datos. Verifica tu conexión a la base de datos.")
        return
        
    # 2. Construir modelo
    print("[2/3] Construyendo modelo...")
    modelo, inferencia = entrenar_modelo(datos)
    if modelo is None:
        print("No se pudo construir el modelo. Verifica los datos y la estructura.")
        return
    
    # 3. Realizar predicción de ejemplo
    print("[3/3] Realizando predicciones...\n")
    
    # Predicción para sábado (día 5) de junio (mes 6)
    dia = 5  # 5 = sábado
    mes = 6  # 6 = junio
    nivel_anterior = 'medio'
    
    dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][dia]
    mes_nombre = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][mes-1]
    
    print(f"Predicción para: {dia_nombre} de {mes_nombre}")
    print(f"Nivel de ventas anterior: {nivel_anterior}")
    print("-" * 40)
    
    distribucion = predecir(inferencia, dia, mes, nivel_anterior)
    
    if distribucion is not None:
        print("\nDistribución de probabilidades para nivel de ventas:")
        for nivel, prob in distribucion.items():
            print(f"  - {nivel}: {prob:.2%}")
            
        nivel_mas_probable = max(distribucion, key=distribucion.get)
        print(f"\nNivel de ventas más probable: {nivel_mas_probable.upper()} ({distribucion[nivel_mas_probable]:.2%})")
    else:
        print("No se pudo realizar la predicción.")

if __name__ == "__main__":
    main()