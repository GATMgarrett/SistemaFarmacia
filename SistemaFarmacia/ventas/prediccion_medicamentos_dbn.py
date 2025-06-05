#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sistema de predicción de demanda de medicamentos usando redes bayesianas dinámicas (DBN).

Este script analiza el historial de ventas de medicamentos específicos y predice
su demanda futura para ayudar en la gestión de inventario.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import unicodedata

# Configurar la codificación para la salida estándar
def limpiar_texto(texto):
    """Limpia textos para evitar problemas de codificación"""
    if not texto:
        return ''
    # Normalizar y reemplazar caracteres problemáticos
    try:
        texto_limpio = unicodedata.normalize('NFKD', texto)
        # Eliminar caracteres no ASCII
        texto_limpio = ''.join([c for c in texto_limpio if ord(c) < 128])
        return texto_limpio
    except Exception:
        return 'Nombre no disponible'

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
from pgmpy.factors.discrete import TabularCPD

def cargar_datos_ventas_medicamentos(dias=180):
    """
    Carga datos históricos de ventas de medicamentos desde la base de datos.
    
    Args:
        dias: Número de días hacia atrás para consultar (default=180)
        
    Returns:
        DataFrame con datos de ventas por medicamento y día
    """
    from ventas.models import DetalleVenta, Medicamentos
    try:
        # Consultar ventas de los últimos X días
        fecha_inicio = datetime.now() - timedelta(days=dias)
        logger.info(f"Consultando ventas de medicamentos desde {fecha_inicio.date()}")
        
        # Obtener todos los detalles de ventas en ese período
        detalles = DetalleVenta.objects.filter(
            venta__fecha_venta__gte=fecha_inicio,
            activo=True
        ).select_related('venta', 'medicamento')
        
        logger.info(f"Se encontraron {detalles.count()} registros de detalle de ventas")
        
        # Convertir a DataFrame para análisis
        datos = []
        for detalle in detalles:
            datos.append({
                'fecha': detalle.venta.fecha_venta,
                'medicamento_id': detalle.medicamento.id,
                'medicamento_nombre': detalle.medicamento.nombre,
                'cantidad': detalle.cantidad,
                'dia_semana': detalle.venta.fecha_venta.weekday(),  # 0=Lunes, 6=Domingo
                'mes': detalle.venta.fecha_venta.month
            })
        
        df = pd.DataFrame(datos)
        return df
    
    except Exception as e:
        logger.error(f"Error al cargar datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def preparar_datos_por_medicamento(df):
    """
    Prepara los datos para el análisis agrupándolos por medicamento y fecha,
    y discretiza las cantidades en niveles de demanda.
    
    Args:
        df: DataFrame con datos de ventas
        
    Returns:
        dict: Diccionario con DataFrames procesados por medicamento
    """
    if df is None or df.empty:
        return None
    
    try:
        # Agrupar por fecha y medicamento, sumando las cantidades
        df_agrupado = df.groupby(['fecha', 'medicamento_id', 'medicamento_nombre'])[['cantidad']].sum().reset_index()
        
        # Crear una serie temporal completa con todas las fechas
        fecha_min = df['fecha'].min()
        fecha_max = df['fecha'].max()
        todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
        
        # Diccionario para almacenar DataFrames por medicamento
        datos_medicamentos = {}
        
        # Obtener lista de medicamentos únicos
        medicamentos = df[['medicamento_id', 'medicamento_nombre']].drop_duplicates()
        
        # Procesar cada medicamento
        for _, med in medicamentos.iterrows():
            med_id = med['medicamento_id']
            med_nombre = med['medicamento_nombre']
            
            # Filtrar datos para este medicamento
            df_med = df_agrupado[df_agrupado['medicamento_id'] == med_id].copy()
            
            # Asegurar que la columna fecha sea datetime en df_med
            df_med['fecha'] = pd.to_datetime(df_med['fecha'])
            
            # Crear índice temporal completo para este medicamento
            df_completo = pd.DataFrame({'fecha': todas_fechas})
            
            # Realizar el merge asegurando que las fechas sean del mismo tipo
            df_completo = df_completo.merge(
                df_med[['fecha', 'cantidad']], 
                on='fecha', 
                how='left'
            )
            
            # Rellenar días sin ventas con 0
            df_completo['cantidad'] = df_completo['cantidad'].fillna(0)
            
            # Añadir información temporal
            df_completo['dia_semana'] = df_completo['fecha'].dt.dayofweek
            df_completo['mes'] = df_completo['fecha'].dt.month
            
            # Discretizar cantidades en niveles (nulo, bajo, medio, alto)
            # Primero, tratamos ceros como una categoría aparte ('nulo')
            df_completo['nivel_demanda'] = 'nulo'
            
            # Solo discretizamos valores mayores que cero
            valores_positivos = df_completo[df_completo['cantidad'] > 0]
            
            if not valores_positivos.empty:
                cuantiles = valores_positivos['cantidad'].quantile([0.33, 0.66]).values
                
                # Aplicar categorización solo a filas con valores positivos
                mascara_positivos = df_completo['cantidad'] > 0
                
                # Función de categorización
                def categorizar_demanda(valor):
                    if valor == 0:
                        return "nulo"
                    elif valor <= cuantiles[0]:
                        return "bajo"
                    elif valor <= cuantiles[1]:
                        return "medio"
                    else:
                        return "alto"
                
                # Aplicar categorización
                df_completo['nivel_demanda'] = df_completo.apply(
                    lambda row: categorizar_demanda(row['cantidad']), axis=1
                )
            
            # Guardar el DataFrame procesado
            datos_medicamentos[med_id] = {
                'id': med_id,
                'nombre': limpiar_texto(med_nombre),
                'datos': df_completo,
                'cuantiles': cuantiles if not valores_positivos.empty else [0, 0]
            }
            
            logger.info(f"Medicamento {med_nombre} (ID: {med_id}): {len(df_completo)} días procesados")
        
        return datos_medicamentos
    
    except Exception as e:
        logger.error(f"Error al preparar datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def estimar_matriz_transicion(datos_medicamento):
    """
    Estima la matriz de transición para un medicamento específico
    basándose en las secuencias históricas de demanda.
    
    Args:
        datos_medicamento: Dict con datos procesados del medicamento
        
    Returns:
        np.array: Matriz de transición estimada
        list: Estados de demanda
    """
    try:
        df = datos_medicamento['datos']
        
        # Obtener estados de demanda ordenados
        estados = ['nulo', 'bajo', 'medio', 'alto']
        num_estados = len(estados)
        
        # Inicializar matriz de transición con ceros
        matriz = np.zeros((num_estados, num_estados))
        
        # Contar transiciones de un día a otro
        for i in range(len(df) - 1):
            estado_hoy = df.iloc[i]['nivel_demanda']
            estado_manana = df.iloc[i + 1]['nivel_demanda']
            
            # Convertir estados a índices
            idx_hoy = estados.index(estado_hoy)
            idx_manana = estados.index(estado_manana)
            
            # Incrementar contador de transición
            matriz[idx_manana, idx_hoy] += 1
        
        # Normalizar por columna para obtener probabilidades
        # (sumando pequeño epsilon para evitar divisiones por cero)
        sumas_columnas = matriz.sum(axis=0)
        for j in range(num_estados):
            if sumas_columnas[j] > 0:
                matriz[:, j] = matriz[:, j] / sumas_columnas[j]
            else:
                # Si no hay transiciones desde este estado, usar distribución uniforme
                matriz[:, j] = 1.0 / num_estados
                
        return matriz, estados
        
    except Exception as e:
        logger.error(f"Error al estimar matriz de transición: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

def crear_modelo_dbn_medicamento(datos_medicamento):
    """
    Crea un modelo DBN para un medicamento específico.
    
    Args:
        datos_medicamento: Dict con datos procesados del medicamento
        
    Returns:
        tuple: (modelo DBN, estados, matriz de transición)
    """
    try:
        # Obtener matriz de transición estimada
        matriz_transicion, estados = estimar_matriz_transicion(datos_medicamento)
        if matriz_transicion is None:
            return None, None, None
            
        # Número de estados (nulo, bajo, medio, alto)
        num_estados = len(estados)
        
        # Crear modelo DBN vacío
        modelo = DBN()
        
        # Añadir nodos para ambos time slices
        modelo.add_node(('Demanda', 0))
        modelo.add_node(('Demanda', 1))
        
        # Añadir arista entre time slices
        modelo.add_edge(('Demanda', 0), ('Demanda', 1))
        
        # Calcular distribución inicial (frecuencia de estados)
        df = datos_medicamento['datos']
        dist_inicial = np.zeros(num_estados)
        for estado in df['nivel_demanda'].values:
            idx = estados.index(estado)
            dist_inicial[idx] += 1
        dist_inicial = dist_inicial / len(df)  # Normalizar
            
        # Crear CPD para el nodo Demanda(t=0)
        cpd_demanda_0 = TabularCPD(
            variable=('Demanda', 0),
            variable_card=num_estados,
            values=dist_inicial.reshape(num_estados, 1),
            state_names={('Demanda', 0): estados}
        )
        
        # Crear CPD para el nodo Demanda(t=1) usando la matriz de transición
        cpd_demanda_1 = TabularCPD(
            variable=('Demanda', 1),
            variable_card=num_estados,
            values=matriz_transicion,
            evidence=[('Demanda', 0)],
            evidence_card=[num_estados],
            state_names={
                ('Demanda', 1): estados,
                ('Demanda', 0): estados
            }
        )
        
        # Añadir CPDs al modelo
        modelo.add_cpds(cpd_demanda_0, cpd_demanda_1)
        
        # Verificar modelo
        if modelo.check_model():
            logger.info(f"Modelo para {datos_medicamento['nombre']} validado correctamente")
        else:
            logger.error(f"El modelo para {datos_medicamento['nombre']} no es válido")
            return None, None, None
            
        return modelo, estados, matriz_transicion
        
    except Exception as e:
        logger.error(f"Error al crear modelo DBN: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None

def predecir_demanda_medicamento(matriz_transicion, estado_actual, estados, pasos=7):
    """
    Predice la demanda futura de un medicamento específico para varios días.
    
    Args:
        matriz_transicion: Matriz de transición estimada
        estado_actual: Estado actual de demanda
        estados: Lista de posibles estados de demanda
        pasos: Número de días a predecir
        
    Returns:
        list: Lista de predicciones para los próximos días
    """
    try:
        # Obtener índice del estado actual
        indice_estado = estados.index(estado_actual)
        
        # Vector de estado actual (one-hot)
        estado_vector = np.zeros(len(estados))
        estado_vector[indice_estado] = 1.0
        
        # Lista para almacenar predicciones
        predicciones = []
        
        # Realizar predicciones para cada paso
        for paso in range(pasos):
            # Predecir próximo estado
            proximo_estado_probs = np.dot(matriz_transicion, estado_vector)
            
            # Obtener estado más probable
            indice_max = np.argmax(proximo_estado_probs)
            estado_predicho = estados[indice_max]
            
            # Guardar predicción con sus probabilidades
            predicciones.append({
                'paso': paso + 1,
                'estado_predicho': estado_predicho,
                'probabilidades': {
                    estados[i]: float(proximo_estado_probs[i]) 
                    for i in range(len(estados))
                }
            })
            
            # Actualizar vector de estado para la siguiente iteración
            estado_vector = proximo_estado_probs
            
        return predicciones
        
    except Exception as e:
        logger.error(f"Error al predecir demanda: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def ejecutar_prediccion_medicamentos():
    """
    Ejecuta un análisis completo para predecir la demanda futura
    de todos los medicamentos con ventas históricas.
    """
    print("=== Sistema de Predicción de Demanda de Medicamentos ===\n")
    
    # Paso 1: Cargar datos históricos
    print("[1/4] Cargando datos históricos de ventas...")
    df_ventas = cargar_datos_ventas_medicamentos()
    if df_ventas is None or df_ventas.empty:
        print("No se pudieron cargar los datos históricos.")
        return
    
    # Paso 2: Preparar datos por medicamento
    print("[2/4] Procesando datos por medicamento...")
    datos_medicamentos = preparar_datos_por_medicamento(df_ventas)
    if datos_medicamentos is None:
        print("No se pudieron procesar los datos por medicamento.")
        return
    
    print(f"Se han procesado datos para {len(datos_medicamentos)} medicamentos.\n")
    
    # Paso 3: Construir modelos y predecir
    print("[3/4] Construyendo modelos y realizando predicciones...\n")
    
    resultados = {}
    dias_prediccion = 7  # Predecir para la próxima semana
    
    for med_id, datos_med in datos_medicamentos.items():
        print(f"Procesando {datos_med['nombre']} (ID: {med_id})...")
        
        # Crear modelo DBN
        modelo, estados, matriz_trans = crear_modelo_dbn_medicamento(datos_med)
        
        if modelo is None:
            print(f"  No se pudo crear el modelo para {datos_med['nombre']}.")
            continue
        
        # Obtener estado actual (último día en los datos)
        ultimo_estado = datos_med['datos'].iloc[-1]['nivel_demanda']
        print(f"  Estado actual de demanda: {ultimo_estado}")
        
        # Predecir demanda futura
        predicciones = predecir_demanda_medicamento(
            matriz_trans, ultimo_estado, estados, dias_prediccion
        )
        
        if predicciones:
            resultados[med_id] = {
                'nombre': datos_med['nombre'],
                'predicciones': predicciones
            }
            
            # Mostrar resultados
            print(f"  Predicciones para los próximos {dias_prediccion} días:")
            for pred in predicciones:
                dia = pred['paso']
                estado = pred['estado_predicho']
                prob = pred['probabilidades'][estado] * 100
                print(f"    Día {dia}: {estado.upper()} ({prob:.1f}%)")
            print()
        else:
            print(f"  No se pudieron generar predicciones para {datos_med['nombre']}.\n")
    
    # Paso 4: Resumen de resultados
    print("\n[4/4] Resumen de resultados:")
    print(f"Se han generado predicciones para {len(resultados)} medicamentos.")
    
    # Encontrar medicamentos con alta demanda en los próximos días
    alta_demanda = []
    for med_id, res in resultados.items():
        for pred in res['predicciones']:
            if pred['paso'] == 1 and pred['estado_predicho'] == 'alto':
                alta_demanda.append(res['nombre'])
                break
    
    if alta_demanda:
        print("\nMedicamentos con predicción de alta demanda para mañana:")
        for med_nombre in alta_demanda:
            print(f"- {med_nombre}")
    
    print("\nNota: Este análisis puede ser utilizado para planificar el abastecimiento")
    print("y optimizar el inventario de medicamentos.")
    
    return resultados

if __name__ == '__main__':
    ejecutar_prediccion_medicamentos()
