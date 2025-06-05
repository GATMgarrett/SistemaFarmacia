#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sistema de predicción de ventas mensuales de medicamentos para planificación de abastecimiento.

Este script analiza el historial de ventas de medicamentos específicos, agrupados por mes,
y predice las cantidades esperadas para los próximos 3 meses para facilitar
la planificación de inventario.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import unicodedata
# Importar pgmpy para redes bayesianas dinámicas
from pgmpy.models import DynamicBayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import DBNInference
import itertools
from collections import Counter
import matplotlib.pyplot as plt

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

def cargar_datos_ventas_mensuales(anios=3):
    """
    Carga datos históricos de ventas de medicamentos desde la base de datos,
    agrupados por mes para facilitar el análisis de tendencias mensuales.
    
    Args:
        anios: Número de años hacia atrás para consultar (default=3)
        
    Returns:
        DataFrame con datos de ventas mensuales por medicamento
    """
    from ventas.models import DetalleVenta, Medicamentos
    try:
        # Consultar ventas de los últimos X años
        fecha_inicio = datetime.now() - timedelta(days=365 * anios)
        logger.info(f"Consultando ventas de medicamentos desde {fecha_inicio.date()} ({anios} años)")
        
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
                'medicamento_nombre': limpiar_texto(detalle.medicamento.nombre),
                'cantidad': detalle.cantidad,
            })
        
        if not datos:
            logger.warning("No se encontraron datos de ventas")
            return None
            
        df = pd.DataFrame(datos)
        
        # Convertir fecha a datetime y extraer el mes y año
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['anio_mes'] = df['fecha'].dt.to_period('M')
        
        # Agrupar por mes y medicamento, sumando las cantidades
        df_mensual = df.groupby(['anio_mes', 'medicamento_id', 'medicamento_nombre'])['cantidad'].sum().reset_index()
        
        # Crear una columna con fecha en formato datetime para el primer día del mes
        df_mensual['fecha'] = df_mensual['anio_mes'].dt.to_timestamp()
        
        # Ordenar por medicamento y fecha
        df_mensual = df_mensual.sort_values(['medicamento_id', 'fecha'])
        
        logger.info(f"Datos agrupados por mes: {len(df_mensual)} registros")
        
        return df_mensual
    
    except Exception as e:
        logger.error(f"Error al cargar datos mensuales: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def completar_series_mensuales(df_mensual):
    """
    Completa las series temporales para cada medicamento, añadiendo meses sin ventas
    para tener una serie continua necesaria para el modelo predictivo.
    
    Args:
        df_mensual: DataFrame con datos de ventas mensuales por medicamento
        
    Returns:
        DataFrame con series temporales completas para cada medicamento
    """
    try:
        # Identificar el rango completo de fechas mensuales en el dataset
        fecha_min = df_mensual['fecha'].min()
        fecha_max = df_mensual['fecha'].max()
        
        # Crear un rango completo de meses
        meses_completos = pd.date_range(start=fecha_min, end=fecha_max, freq='MS')
        
        # Obtener la lista única de medicamentos
        medicamentos = df_mensual[['medicamento_id', 'medicamento_nombre']].drop_duplicates()
        
        # Crear un DataFrame completo para todos los medicamentos y todos los meses
        series_completas = []
        
        for _, med in medicamentos.iterrows():
            # Para cada medicamento, crear una serie con todos los meses
            for fecha in meses_completos:
                series_completas.append({
                    'medicamento_id': med['medicamento_id'],
                    'medicamento_nombre': med['medicamento_nombre'],
                    'fecha': fecha
                })
        
        # Convertir a DataFrame
        df_completo = pd.DataFrame(series_completas)
        
        # Combinar con los datos originales para obtener las cantidades reales
        df_final = pd.merge(
            df_completo,
            df_mensual[['medicamento_id', 'fecha', 'cantidad']],
            on=['medicamento_id', 'fecha'],
            how='left'
        )
        
        # Rellenar con 0 los meses sin ventas
        df_final['cantidad'] = df_final['cantidad'].fillna(0)
        
        logger.info(f"Series temporales completadas: {len(df_final)} registros")
        
        return df_final
    
    except Exception as e:
        logger.error(f"Error al completar series temporales: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def filtrar_medicamentos_relevantes(df, min_ventas=5, min_meses=3):
    """
    Filtra los medicamentos que tienen un historial de ventas relevante.
    
    Args:
        df: DataFrame con datos de ventas mensuales completos
        min_ventas: Cantidad mínima total de ventas para considerar un medicamento
        min_meses: Número mínimo de meses con ventas para considerar un medicamento
        
    Returns:
        Lista de medicamentos que cumplen los criterios
    """
    try:
        # Agrupar por medicamento para obtener estadísticas
        stats = df.groupby(['medicamento_id', 'medicamento_nombre']).agg(
            total_ventas=('cantidad', 'sum'),
            meses_con_ventas=('cantidad', lambda x: (x > 0).sum())
        ).reset_index()
        
        # Filtrar medicamentos relevantes
        relevantes = stats[(stats['total_ventas'] >= min_ventas) & 
                           (stats['meses_con_ventas'] >= min_meses)]
        
        logger.info(f"Medicamentos relevantes identificados: {len(relevantes)} de {len(stats)}")
        
        return relevantes
    
    except Exception as e:
        logger.error(f"Error al filtrar medicamentos relevantes: {str(e)}")
        return None

def discretizar_cantidades(datos_med, num_niveles=4):
    """
    Discretiza las cantidades de ventas en niveles para el modelo DBN.
    
    Args:
        datos_med: DataFrame con el historial de ventas de un medicamento
        num_niveles: Número de niveles para la discretización (default=4)
    
    Returns:
        DataFrame con las cantidades discretizadas y los rangos de cada nivel
    """
    try:
        # Copia para no modificar el original
        df = datos_med.copy()
        
        # Extraer valores únicos no nulos
        valores = df['cantidad'].values
        valores_positivos = valores[valores > 0]
        
        if len(valores_positivos) < 2:
            # Si hay muy pocos valores positivos, usar discretización más simple
            df['nivel_demanda'] = np.where(df['cantidad'] > 0, 'bajo', 'nulo')
            rangos = {0: 'nulo', 1: 'bajo'}
            return df, rangos
        
        # Calcular cuantiles para la discretización
        cuantiles = []
        for i in range(1, num_niveles):
            q = np.percentile(valores_positivos, i * 100 / num_niveles)
            cuantiles.append(q)
            
        # Etiquetar cada valor según su nivel
        etiquetas = ['nulo']
        for i in range(1, num_niveles):
            if i == 1:
                etiquetas.append('bajo')
            elif i == num_niveles - 1:
                etiquetas.append('alto')
            else:
                etiquetas.append('medio')
        
        # Asignar nivel a cada valor
        niveles = np.zeros(len(valores), dtype=int)
        for i in range(len(valores)):
            if valores[i] == 0:
                niveles[i] = 0  # Nivel 'nulo'
            else:
                nivel = 1  # Por defecto 'bajo'
                for j in range(len(cuantiles)):
                    if valores[i] > cuantiles[j]:
                        nivel = j + 2
                niveles[i] = min(nivel, num_niveles - 1)
        
        # Convertir niveles numéricos a etiquetas
        df['nivel_demanda'] = [etiquetas[n] for n in niveles]
        
        # Crear diccionario de rangos para interpretación
        rangos = {0: 'nulo'}
        rango_previo = 0
        for i, q in enumerate(cuantiles, 1):
            rangos[i] = f"{etiquetas[i]} ({rango_previo}-{int(q)})"
            rango_previo = int(q)
        rangos[num_niveles-1] = f"{etiquetas[-1]} (>{rango_previo})"
        
        return df, rangos
        
    except Exception as e:
        logger.warning(f"Error en discretización: {str(e)}. Usando discretización simple.")
        df = datos_med.copy()
        df['nivel_demanda'] = np.where(df['cantidad'] > 0, 'bajo', 'nulo')
        rangos = {0: 'nulo', 1: 'bajo'}
        return df, rangos

def entrenar_modelo_dbn(datos_discretizados, etiquetas_niveles):
    """
    Crea y entrena un modelo de Red Bayesiana Dinámica (DBN) para predecir
    niveles de demanda futura basado en datos históricos.
    
    Args:
        datos_discretizados: DataFrame con niveles de demanda discretizados
        etiquetas_niveles: Lista de posibles niveles de demanda
    
    Returns:
        Modelo DBN entrenado y matriz de transición estimada
    """
    try:
        # Extraer secuencia de niveles de demanda
        secuencia = datos_discretizados['nivel_demanda'].tolist()
        
        # Crear modelo DBN con un solo nodo en dos tiempos
        model = DynamicBayesianNetwork()
        
        # Añadir nodos para dos time slices
        # En pgmpy, los nodos DBN deben ser tuplas (nombre_nodo, time_slice)
        model.add_node(('Demanda', 0))
        model.add_node(('Demanda', 1))
        
        # Añadir borde entre los nodos de tiempo consecutivos
        model.add_edge(('Demanda', 0), ('Demanda', 1))
        
        # Calcular matriz de transición a partir de los datos históricos
        transiciones = {}
        for i in range(len(secuencia) - 1):
            estado_actual = secuencia[i]
            estado_siguiente = secuencia[i + 1]
            par = (estado_actual, estado_siguiente)
            transiciones[par] = transiciones.get(par, 0) + 1
        
        # Convertir conteos a probabilidades
        matriz_transicion = {}
        estados = sorted(set(secuencia))
        
        # Inicializar matriz con valores uniformes
        for estado_actual in estados:
            total = sum([transiciones.get((estado_actual, s), 0) for s in estados])
            if total == 0:  # Si no hay transiciones desde este estado
                matriz_transicion[estado_actual] = {s: 1.0/len(estados) for s in estados}
            else:
                matriz_transicion[estado_actual] = {}
                for estado_siguiente in estados:
                    conteo = transiciones.get((estado_actual, estado_siguiente), 0)
                    matriz_transicion[estado_actual][estado_siguiente] = conteo / total
        
        # Crear CPDs para el modelo DBN
        # CPD para ('Demanda', 0) (distribución inicial)
        conteo_estados = Counter(secuencia)
        total_estados = len(secuencia)
        
        if total_estados == 0:
            # Si no hay datos, usar distribución uniforme
            probabilidades_iniciales = [1.0/len(estados) for _ in estados]
        else:
            # Usar frecuencias empíricas
            probabilidades_iniciales = [conteo_estados.get(s, 0)/total_estados for s in estados]
        
        # Asegurar que las probabilidades sumen 1
        if sum(probabilidades_iniciales) == 0:
            probabilidades_iniciales = [1.0/len(estados) for _ in estados]
        else:
            probabilidades_iniciales = [p/sum(probabilidades_iniciales) for p in probabilidades_iniciales]
        
        # Corregir el formato de los valores para la CPD inicial (debe ser una columna)
        # La forma debe ser (num_estados, 1) y no (1, num_estados)
        valores_cpd_inicial = np.array(probabilidades_iniciales).reshape(len(estados), 1)
        
        cpd_demanda_0 = TabularCPD(
            variable=('Demanda', 0),
            variable_card=len(estados),
            values=valores_cpd_inicial,
            state_names={('Demanda', 0): estados}
        )
        
        # CPD para ('Demanda', 1) (transiciones)
        # En pgmpy, para un nodo con un padre, la matriz debe tener forma (variable_card, evidence_card[0])
        valores_transicion = []
        for estado_siguiente in estados:
            fila = [matriz_transicion[estado_actual].get(estado_siguiente, 1.0/len(estados)) 
                    for estado_actual in estados]
            valores_transicion.append(fila)
        
        # Convertir lista de listas a array numpy con la forma correcta
        matriz_transicion_np = np.array(valores_transicion)
        
        cpd_demanda_1 = TabularCPD(
            variable=('Demanda', 1),
            variable_card=len(estados),
            values=matriz_transicion_np,  # Ya tiene la forma correcta (estado_siguiente, estado_actual)
            evidence=[('Demanda', 0)],
            evidence_card=[len(estados)],
            state_names={('Demanda', 0): estados, ('Demanda', 1): estados}
        )
        
        # Añadir CPDs al modelo
        model.add_cpds(cpd_demanda_0, cpd_demanda_1)
        
        # Verificar modelo
        if not model.check_model():
            logger.warning("El modelo DBN no es válido, ajustando...")
            # Ajustes para casos problematicos
        
        return model, matriz_transicion, estados
    
    except Exception as e:
        logger.error(f"Error al crear modelo DBN: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None

def predecir_ventas_medicamento(datos_med, horizonte=3):
    """
    Predice ventas futuras para un medicamento específico usando
    una Red Bayesiana Dinámica (DBN).
    
    Args:
        datos_med: DataFrame con historial de ventas del medicamento
        horizonte: Número de meses a predecir hacia adelante
        
    Returns:
        Series con valores predichos para los próximos meses
    """
    try:
        # Si hay muy pocos datos, usar método simple
        if len(datos_med) < 6:
            # Cálculo simple basado en promedio
            promedio = datos_med['cantidad'].mean()
            ultima_fecha = datos_med['fecha'].max()
            fechas_prediccion = pd.date_range(start=ultima_fecha + pd.DateOffset(months=1), 
                                           periods=horizonte, freq='MS')
            return pd.Series([int(promedio)] * horizonte, index=fechas_prediccion)
        
        # 1. Discretizar las cantidades para el modelo DBN
        datos_discretizados, rangos_niveles = discretizar_cantidades(datos_med)
        
        # 2. Entrenar modelo DBN
        niveles_unicos = sorted(datos_discretizados['nivel_demanda'].unique())
        modelo_dbn, matriz_transicion, estados = entrenar_modelo_dbn(datos_discretizados, niveles_unicos)
        
        if modelo_dbn is None or matriz_transicion is None:
            # Si falló el modelo, usar método alternativo simple
            promedio = datos_med['cantidad'].mean()
            ultima_fecha = datos_med['fecha'].max()
            fechas_prediccion = pd.date_range(start=ultima_fecha + pd.DateOffset(months=1), 
                                           periods=horizonte, freq='MS')
            return pd.Series([int(promedio)] * horizonte, index=fechas_prediccion)
        
        # 3. Estado actual (el último conocido)
        estado_actual = datos_discretizados.iloc[-1]['nivel_demanda']
        if estado_actual not in estados:
            estado_actual = estados[0]  # Valor predeterminado si hay algún problema
        
        # 4. Predicción de estados futuros usando la matriz de transición
        estados_predichos = []
        for _ in range(horizonte):
            # Obtener probabilidades de transición desde el estado actual
            probs = [matriz_transicion[estado_actual][s] for s in estados]
            # Elegir siguiente estado basado en estas probabilidades
            indice = np.random.choice(range(len(estados)), p=probs)
            siguiente_estado = estados[indice]
            estados_predichos.append(siguiente_estado)
            # Actualizar estado actual para la siguiente iteración
            estado_actual = siguiente_estado
        
        # 5. Convertir niveles predichos a cantidades numéricas
        # Calcular valores representativos para cada nivel de demanda
        valores_por_nivel = {}
        for nivel in niveles_unicos:
            valores = datos_med.loc[datos_discretizados['nivel_demanda'] == nivel, 'cantidad']
            if len(valores) > 0:
                valores_por_nivel[nivel] = int(valores.mean())
            else:
                valores_por_nivel[nivel] = 0
        
        # Si 'nulo' tiene un valor mayor que cero, corregirlo
        if 'nulo' in valores_por_nivel and valores_por_nivel['nulo'] > 0:
            valores_por_nivel['nulo'] = 0
        
        # Convertir estados predichos a cantidades
        cantidades_predichas = [valores_por_nivel.get(estado, 0) for estado in estados_predichos]
        
        # Fechas para las predicciones
        ultima_fecha = datos_med['fecha'].max()
        fechas_prediccion = pd.date_range(start=ultima_fecha + pd.DateOffset(months=1), 
                                       periods=horizonte, freq='MS')
        
        # Crear Series con las predicciones
        predicciones = pd.Series(cantidades_predichas, index=fechas_prediccion)
        
        return predicciones
    
    except Exception as e:
        logger.warning(f"Error en predicción DBN: {str(e)}. Usando método alternativo.")
        # Método alternativo simple basado en promedio
        try:
            promedio = datos_med['cantidad'].mean()
            ultima_fecha = datos_med['fecha'].max()
            fechas_prediccion = pd.date_range(start=ultima_fecha + pd.DateOffset(months=1), 
                                           periods=horizonte, freq='MS')
            return pd.Series([int(promedio)] * horizonte, index=fechas_prediccion)
        except:
            return None

def generar_predicciones(df_completo, medicamentos_relevantes, horizonte=3):
    """
    Genera predicciones para todos los medicamentos relevantes.
    
    Args:
        df_completo: DataFrame con series temporales completas
        medicamentos_relevantes: DataFrame con medicamentos a predecir
        horizonte: Número de meses a predecir
    
    Returns:
        DataFrame con predicciones para cada medicamento
    """
    try:
        resultados = []
        total_med = len(medicamentos_relevantes)
        
        for i, (_, med) in enumerate(medicamentos_relevantes.iterrows(), 1):
            med_id = med['medicamento_id']
            med_nombre = med['medicamento_nombre']
            
            logger.info(f"[{i}/{total_med}] Procesando {med_nombre} (ID: {med_id})...")
            
            # Obtener datos históricos del medicamento
            datos_med = df_completo[df_completo['medicamento_id'] == med_id].sort_values('fecha')
            
            # Última venta conocida (estado actual)
            ultimo_mes = datos_med.iloc[-1]
            
            # Predecir ventas futuras
            predicciones = predecir_ventas_medicamento(datos_med, horizonte)
            
            if predicciones is not None:
                # Crear registro de resultado
                resultado = {
                    'medicamento_id': med_id,
                    'medicamento_nombre': med_nombre,
                    'total_historico': datos_med['cantidad'].sum(),
                    'promedio_mensual': datos_med['cantidad'].mean(),
                    'ultimo_mes_cantidad': ultimo_mes['cantidad'],
                    'ultimo_mes_fecha': ultimo_mes['fecha']
                }
                
                # Añadir predicciones para cada mes futuro
                for i, (fecha, cantidad) in enumerate(predicciones.items(), 1):
                    mes_nombre = fecha.strftime('%B %Y')
                    resultado[f'mes_{i}_nombre'] = mes_nombre
                    resultado[f'mes_{i}_cantidad'] = cantidad
                
                resultados.append(resultado)
        
        # Convertir a DataFrame
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            logger.info(f"Predicciones generadas para {len(df_resultados)} medicamentos")
            return df_resultados
        else:
            logger.warning("No se generaron predicciones para ningún medicamento")
            return None
    
    except Exception as e:
        logger.error(f"Error al generar predicciones: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def guardar_resultados(df_predicciones, ruta_salida=None):
    """
    Guarda los resultados en un archivo CSV y/o los muestra en pantalla.
    
    Args:
        df_predicciones: DataFrame con predicciones
        ruta_salida: Ruta para guardar el archivo CSV (opcional)
    """
    if df_predicciones is None or df_predicciones.empty:
        logger.warning("No hay resultados para guardar")
        return
    
    # Mostrar resumen en consola
    print("\n[REPORTE DE PREDICCIONES DE VENTAS MENSUALES]\n")
    
    # Obtener los nombres de los meses predichos del DataFrame
    meses_cols = [col for col in df_predicciones.columns if col.startswith('mes_') and col.endswith('_nombre')]
    n_meses = len(meses_cols)
    
    print(f"Se han generado predicciones para {len(df_predicciones)} medicamentos relevantes.")
    print(f"Periodos de predicción: {n_meses} meses\n")
    
    # Ordenar por cantidad total predicha (descendente)
    cantidades_cols = [col for col in df_predicciones.columns if col.startswith('mes_') and col.endswith('_cantidad')]
    df_predicciones['total_prediccion'] = df_predicciones[cantidades_cols].sum(axis=1)
    df_ordenado = df_predicciones.sort_values('total_prediccion', ascending=False)
    
    # Mostrar top 20 medicamentos con mayor demanda predicha
    print("\n[TOP 20 MEDICAMENTOS CON MAYOR DEMANDA PREDICHA]")
    print("--------------------------------------------------")
    top20 = df_ordenado.head(20)
    
    for _, med in top20.iterrows():
        print(f"\n{med['medicamento_nombre']}")
        print(f"  Venta histórica promedio: {med['promedio_mensual']:.1f} unidades/mes")
        print("  Cantidades predichas:")
        
        for i in range(1, n_meses + 1):
            print(f"    {med[f'mes_{i}_nombre']}: {med[f'mes_{i}_cantidad']} unidades")
        
        print(f"  TOTAL 3 MESES: {med['total_prediccion']} unidades")
    
    # Guardar a CSV si se especifica ruta
    if ruta_salida:
        try:
            df_ordenado.to_csv(ruta_salida, index=False, encoding='utf-8')
            logger.info(f"Resultados guardados en {ruta_salida}")
            print(f"\nReporte completo guardado en: {ruta_salida}")
        except Exception as e:
            logger.error(f"Error al guardar archivo CSV: {str(e)}")
    
    return df_ordenado

def main():
    """
    Función principal que ejecuta todo el flujo de predicción de ventas mensuales.
    """
    try:
        print("\n[SISTEMA DE PREDICCIÓN DE VENTAS MENSUALES DE MEDICAMENTOS]\n")
        print("Inicializando sistema...")
        
        # Parámetros configurables
        anios_historia = 3  # Años de historia a considerar
        horizonte_prediccion = 3  # Meses a predecir hacia adelante
        min_ventas_totales = 5  # Ventas mínimas para considerar un medicamento
        min_meses_con_ventas = 3  # Mínimo de meses con ventas para considerar un medicamento
        
        # 1. Cargar datos históricos
        print(f"\nCargando datos históricos de {anios_historia} años...")
        df_mensual = cargar_datos_ventas_mensuales(anios=anios_historia)
        if df_mensual is None or df_mensual.empty:
            print("Error: No se pudieron cargar datos históricos de ventas.")
            return False
        
        # 2. Completar series temporales
        print("Completando series temporales...")
        df_completo = completar_series_mensuales(df_mensual)
        if df_completo is None or df_completo.empty:
            print("Error: No se pudieron completar las series temporales.")
            return False
        
        # 3. Filtrar medicamentos relevantes
        print(f"Identificando medicamentos relevantes (min. {min_ventas_totales} ventas en al menos {min_meses_con_ventas} meses)...")
        medicamentos_relevantes = filtrar_medicamentos_relevantes(
            df_completo, 
            min_ventas=min_ventas_totales,
            min_meses=min_meses_con_ventas
        )
        if medicamentos_relevantes is None or medicamentos_relevantes.empty:
            print("Error: No se identificaron medicamentos relevantes para predicción.")
            return False
            
        print(f"Se identificaron {len(medicamentos_relevantes)} medicamentos relevantes para predicción.")
        
        # 4. Generar predicciones
        print(f"\nGenerando predicciones para {horizonte_prediccion} meses...")
        df_predicciones = generar_predicciones(
            df_completo,
            medicamentos_relevantes,
            horizonte=horizonte_prediccion
        )
        
        # 5. Guardar y mostrar resultados
        ruta_salida = 'predicciones_mensuales_medicamentos.csv'
        df_resultados = guardar_resultados(df_predicciones, ruta_salida)
        
        # 6. Mostrar instrucciones para usar los resultados
        print("\n[RECOMENDACIONES PARA USO DE RESULTADOS]")
        print("1. El archivo CSV contiene las predicciones completas para todos los medicamentos.")
        print("2. Las cantidades predichas son el número estimado de unidades que se venderán cada mes.")
        print("3. Para planificar el abastecimiento, considerar un margen de seguridad adicional.")
        print("4. Revisar especialmente los medicamentos del TOP 20 para garantizar su disponibilidad.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en ejecución principal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\nError en la ejecución del sistema: {str(e)}")
        return False

# Ejecutar el script si se llama directamente
if __name__ == "__main__":
    main()
