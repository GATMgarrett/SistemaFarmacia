#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sistema de predicción de ventas usando redes bayesianas dinámicas (DBN)
con datos del sistema de farmacia.

Este script implementa un modelo de predicción de ventas basado en pgmpy.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar entorno Django
# Obtener la ruta al directorio de proyecto
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SistemaFarmacia.settings")

import django
django.setup()

# Importar DBN después de configurar Django
from pgmpy.models import DynamicBayesianNetwork as DBN
from pgmpy.inference import DBNInference
from pgmpy.factors.discrete import TabularCPD

def cargar_datos_ventas():
    """
    Carga datos históricos de ventas desde la base de datos de Django.
    """
    from ventas.models import Ventas
    try:
        # Consultar ventas de los últimos 180 días
        fecha_inicio = datetime.now() - timedelta(days=180)
        logger.info(f"Consultando ventas desde {fecha_inicio.date()}")
        
        # Obtener todas las ventas en ese período
        ventas = Ventas.objects.filter(fecha_venta__gte=fecha_inicio)
        logger.info(f"Se encontraron {ventas.count()} registros de ventas")
        
        # Convertir a DataFrame para análisis
        datos = []
        for venta in ventas:
            datos.append({
                'fecha': venta.fecha_venta,
                'total': float(venta.precio_total),
                'dia_semana': venta.fecha_venta.weekday(),  # 0=Lunes, 6=Domingo
                'mes': venta.fecha_venta.month
            })
        
        df = pd.DataFrame(datos)
        
        # Discretizar ventas en niveles (bajo, medio, alto)
        cuantiles = df['total'].quantile([0.33, 0.66]).values
        
        def categorizar_venta(valor):
            if valor <= cuantiles[0]:
                return "bajo"
            elif valor <= cuantiles[1]:
                return "medio"
            else:
                return "alto"
        
        df['nivel_venta'] = df['total'].apply(categorizar_venta)
        
        return df
    
    except Exception as e:
        logger.error(f"Error al cargar datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def crear_modelo_dbn():
    """
    Crea un modelo de red bayesiana dinámica (DBN) simple
    que modela la dependencia de ventas entre diferentes períodos de tiempo.
    """
    try:
        # Crear el modelo DBN vacío
        modelo = DBN()
        
        # Agregar nodos para ambos time slices
        modelo.add_node(('Ventas', 0))
        modelo.add_node(('Ventas', 1))
        
        # Agregar aristas entre time slices
        modelo.add_edge(('Ventas', 0), ('Ventas', 1))
        
        return modelo
    except Exception as e:
        logger.error(f"Error al crear modelo DBN: {str(e)}")
        return None

def entrenar_modelo(datos):
    """
    Entrena el modelo DBN utilizando los datos históricos de ventas.
    """
    try:
        # Obtener estados únicos para la variable Ventas
        ventas_states = sorted(datos['nivel_venta'].unique())
        ventas_card = len(ventas_states)
        
        # Crear la estructura básica del DBN
        modelo = crear_modelo_dbn()
        if modelo is None:
            return None
        
        # Calcular probabilidades para Ventas(t=0)
        ventas_probs = datos['nivel_venta'].value_counts(normalize=True)
        ventas_probs = [ventas_probs.get(estado, 0) for estado in ventas_states]
        
        # Crear CPD para Ventas(t=0)
        cpd_ventas_0 = TabularCPD(
            variable=('Ventas', 0),
            variable_card=ventas_card,
            values=np.array(ventas_probs).reshape(ventas_card, 1),
            state_names={('Ventas', 0): ventas_states}
        )
        
        # Crear una matriz de transición simple
        # En un caso real, se estimaría esta matriz a partir de datos secuenciales
        # Aquí usamos una matriz uniforme como ejemplo
        transition_matrix = np.ones((ventas_card, ventas_card)) / ventas_card
        
        # Si tuviéramos secuencias de datos, podríamos estimar la matriz así:
        # Contar transiciones de un estado a otro y normalizar las filas
        
        # Crear CPD para Ventas(t=1) con dependencia de Ventas(t=0)
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
        modelo.add_cpds(cpd_ventas_0, cpd_ventas_1)
        logger.info("CPDs añadidos al modelo")
        
        # Verificar el modelo
        if modelo.check_model():
            logger.info("Modelo validado correctamente")
        else:
            logger.error("El modelo no es válido")
            return None
        
        # IMPORTANTE: Guardar la matriz de transición junto con el modelo
        # para que podamos usarla directamente en la predicción
        return modelo, ventas_states, transition_matrix
    
    except Exception as e:
        logger.error(f"Error al entrenar el modelo: {str(e)}")
        return None, None, None

def predecir_ventas_futuras(transition_matrix, estado_actual, ventas_states):
    """
    Realiza una predicción de ventas para el próximo período
    dado el estado actual, utilizando directamente la matriz de transición.
    """
    try:
        # Obtener índice del estado actual
        indice_estado_actual = ventas_states.index(estado_actual)
        
        # Obtener la fila correspondiente de la matriz de transición
        # que representa P(Ventas_t1 | Ventas_t0 = estado_actual)
        probabilidades = transition_matrix[:, indice_estado_actual]
        
        # Obtener el nivel más probable
        indice_max = np.argmax(probabilidades)
        nivel_predicho = ventas_states[indice_max]
        
        logger.info(f"Predicción para próximas ventas:")
        for i, nivel in enumerate(ventas_states):
            logger.info(f"- {nivel}: {probabilidades[i]:.4f}")
        
        return nivel_predicho, probabilidades
    
    except Exception as e:
        logger.error(f"Error al predecir: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

def ejecutar_ejemplo():
    """
    Ejecuta un ejemplo completo de predicción con datos reales.
    """
    print("=== Sistema de Predicción de Ventas ===\n")
    
    # Paso 1: Cargar datos históricos
    print("[1/3] Cargando datos históricos...")
    datos = cargar_datos_ventas()
    if datos is None or datos.empty:
        print("No se pudieron cargar los datos históricos.")
        return
    
    # Paso 2: Entrenar modelo
    print("[2/3] Construyendo modelo...")
    modelo, estados, matriz_transicion = entrenar_modelo(datos)
    if modelo is None:
        print("No se pudo construir el modelo. Verifica los datos y la estructura.")
        return
    
    # Paso 3: Realizar predicción
    print("[3/3] Realizando predicción...\n")
    
    # Obtener último estado conocido (último día en los datos)
    ultimo_estado = datos.iloc[-1]['nivel_venta']
    print(f"Estado actual de ventas: {ultimo_estado}")
    
    # Predecir próximo estado usando directamente la matriz de transición
    prediccion, probs = predecir_ventas_futuras(matriz_transicion, ultimo_estado, estados)
    
    if prediccion:
        print(f"\nPredicción: El próximo nivel de ventas será {prediccion.upper()}")
        print("\nProbabilidades:")
        for i, estado in enumerate(estados):
            print(f"- {estado}: {probs[i]:.2%}")
    else:
        print("No se pudo realizar la predicción.")
        
    print("\nNota: Este modelo utiliza una matriz de transición uniforme para las predicciones.")
    print("Para mejorar las predicciones, se recomienda estimar esta matriz a partir")
    print("de secuencias históricas de ventas.")
    

if __name__ == '__main__':
    ejecutar_ejemplo()
