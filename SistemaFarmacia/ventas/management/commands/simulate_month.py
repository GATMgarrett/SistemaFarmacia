from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from ventas.models import (
    Medicamentos, Proveedores, Compras, DetalleCompra, LoteMedicamento,
    Ventas, DetalleVenta, Cliente, Factura
)
from faker import Faker
from datetime import datetime, timedelta, date
import random
import decimal
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Simula la actividad de compras y ventas durante un período de tiempo específico'

    def add_arguments(self, parser):
        parser.add_argument('--meses', type=int, default=6, help='Número de meses a simular')
        parser.add_argument('--fecha_inicio', type=str, default=None, help='Fecha de inicio (YYYY-MM-DD)')
        parser.add_argument('--seed', type=int, default=42, help='Semilla para reproducibilidad')

    def handle(self, *args, **options):
        # Configuración inicial
        meses = options['meses']
        fecha_inicio_str = options['fecha_inicio']
        seed = options['seed']
        
        # Establecer semilla para reproducibilidad
        random.seed(seed)
        fake = Faker('es_ES')
        Faker.seed(seed)
        
        # Determinar fecha de inicio
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        else:
            # Si no se especifica, empezar hace 'meses' meses desde hoy
            fecha_inicio = date.today() - timedelta(days=30*meses)
        
        fecha_fin = fecha_inicio + timedelta(days=30*meses)
        
        self.stdout.write(self.style.SUCCESS(f'Iniciando simulación desde {fecha_inicio} hasta {fecha_fin}'))
        
        # Verificar que haya datos necesarios
        if not self._verificar_datos_iniciales():
            return
        
        # Simular los meses
        fecha_actual = fecha_inicio
        while fecha_actual < fecha_fin:
            mes_actual = fecha_actual.month
            año_actual = fecha_actual.year
            
            self.stdout.write(self.style.SUCCESS(f'Simulando mes {mes_actual}/{año_actual}'))
            
            # Simular compras al inicio del mes (reabastecimiento)
            self._simular_compras_mes(fecha_actual, fake)
            
            # Simular ventas diarias durante todo el mes
            self._simular_ventas_mes(fecha_actual, fake)
            
            # Avanzar al siguiente mes
            if fecha_actual.month == 12:
                fecha_actual = date(fecha_actual.year + 1, 1, 1)
            else:
                fecha_actual = date(fecha_actual.year, fecha_actual.month + 1, 1)
        
        self.stdout.write(self.style.SUCCESS('Simulación completada con éxito'))

    def _verificar_datos_iniciales(self):
        """Verifica que existan los datos necesarios para la simulación"""
        # Verificar medicamentos
        count_medicamentos = Medicamentos.objects.filter(activo=True).count()
        if count_medicamentos == 0:
            self.stdout.write(self.style.ERROR('No hay medicamentos activos en la base de datos'))
            return False
        
        # Verificar proveedores
        count_proveedores = Proveedores.objects.filter(activo=True).count()
        if count_proveedores == 0:
            self.stdout.write(self.style.ERROR('No hay proveedores activos en la base de datos'))
            return False
        
        # Verificar usuarios
        count_usuarios = User.objects.filter(is_active=True).count()
        if count_usuarios == 0:
            self.stdout.write(self.style.ERROR('No hay usuarios activos en la base de datos'))
            return False
        
        self.stdout.write(self.style.SUCCESS(f'Datos iniciales verificados: {count_medicamentos} medicamentos, {count_proveedores} proveedores, {count_usuarios} usuarios'))
        return True

    def _simular_compras_mes(self, fecha_inicio_mes, fake):
        """Simula las compras de medicamentos para un mes"""
        self.stdout.write(f'Simulando compras para {fecha_inicio_mes.month}/{fecha_inicio_mes.year}')
        
        # Obtener medicamentos y proveedores activos
        medicamentos = list(Medicamentos.objects.filter(activo=True))
        proveedores = list(Proveedores.objects.filter(activo=True))
        
        # Determinar cuántas compras hacer este mes (entre 3 y 6)
        num_compras = random.randint(3, 6)
        
        for i in range(num_compras):
            # Seleccionar un proveedor aleatorio
            proveedor = random.choice(proveedores)
            
            # Fecha de compra aleatoria dentro del mes
            max_dia = 28 if fecha_inicio_mes.month == 2 else 30
            dia_compra = random.randint(1, max_dia)
            fecha_compra = date(fecha_inicio_mes.year, fecha_inicio_mes.month, dia_compra)
            
            # Decidir cuántos medicamentos diferentes se comprarán (entre 5 y 15)
            num_medicamentos = random.randint(5, 15)
            medicamentos_seleccionados = random.sample(medicamentos, min(num_medicamentos, len(medicamentos)))
            
            # Crear la compra
            with transaction.atomic():
                try:
                    # Crear la compra principal
                    precio_total = decimal.Decimal('0.00')
                    compra = Compras.objects.create(
                        proveedor=proveedor,
                        fecha_compra=fecha_compra,
                        precio_total=precio_total,
                        activo=True
                    )
                    
                    # Crear detalle de compra y lotes para cada medicamento
                    for medicamento in medicamentos_seleccionados:
                        # Generar cantidad y precios
                        cantidad = random.randint(50, 200)
                        precio_compra = decimal.Decimal(random.uniform(5.0, 50.0)).quantize(decimal.Decimal('0.01'))
                        precio_venta = precio_compra * decimal.Decimal(random.uniform(1.2, 1.5)).quantize(decimal.Decimal('0.01'))
                        
                        # Calcular fechas
                        fecha_produccion = fecha_compra - timedelta(days=random.randint(30, 180))
                        fecha_vencimiento = fecha_compra + timedelta(days=random.randint(180, 720))
                        
                        # Crear lote de medicamento
                        lote = LoteMedicamento.objects.create(
                            medicamento=medicamento,
                            cantidad=cantidad,
                            precio_compra=precio_compra,
                            precio_venta=precio_venta,
                            fecha_compra=fecha_compra,
                            fecha_produccion=fecha_produccion,
                            fecha_vencimiento=fecha_vencimiento,
                            lote_fabricante=f'LOT-{fake.bothify(text='??###')}',
                            activo=True
                        )
                        
                        # Crear detalle de compra
                        DetalleCompra.objects.create(
                            compra=compra,
                            medicamento=medicamento,
                            precio=precio_compra,
                            cantidad=cantidad,
                            activo=True
                        )
                        
                        # Actualizar precio total
                        subtotal = precio_compra * decimal.Decimal(cantidad)
                        precio_total += subtotal
                    
                    # Actualizar el precio total de la compra
                    compra.precio_total = precio_total
                    compra.save()
                    
                    self.stdout.write(f'  Compra #{compra.id} creada: {len(medicamentos_seleccionados)} medicamentos por ${precio_total}')
                    
                except Exception as e:
                    logger.error(f'Error al crear compra: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'Error al crear compra: {str(e)}'))

    def _simular_ventas_mes(self, fecha_inicio_mes, fake):
        """Simula las ventas de medicamentos para un mes"""
        self.stdout.write(f'Simulando ventas para {fecha_inicio_mes.month}/{fecha_inicio_mes.year}')
        
        # Obtener usuarios que pueden realizar ventas
        usuarios = list(User.objects.filter(is_active=True))
        if not usuarios:
            self.stdout.write(self.style.ERROR('No hay usuarios activos para realizar ventas'))
            return
        
        # Simular ventas para cada día del mes
        dias_en_mes = 28 if fecha_inicio_mes.month == 2 else 30
        for dia in range(1, dias_en_mes + 1):
            fecha_venta = date(fecha_inicio_mes.year, fecha_inicio_mes.month, dia)
            
            # Factores que afectan el número de ventas:
            # - Día de la semana (más ventas los lunes y fines de semana)
            # - Día del mes (más ventas a principio y fin de mes)
            # - Temporada (más ventas en invierno por enfermedades respiratorias)
            
            dia_semana = fecha_venta.weekday()  # 0=Lunes, 6=Domingo
            es_inicio_mes = dia <= 5
            es_fin_mes = dia >= dias_en_mes - 5
            es_invierno = fecha_venta.month in [6, 7, 8]  # Para hemisferio sur
            
            # Base: 5-10 ventas diarias
            num_ventas_base = random.randint(5, 10)
            
            # Ajustes según factores
            if dia_semana == 0 or dia_semana >= 5:  # Lunes o fin de semana
                num_ventas_base += random.randint(2, 5)
            if es_inicio_mes or es_fin_mes:
                num_ventas_base += random.randint(1, 3)
            if es_invierno:
                num_ventas_base += random.randint(2, 4)
            
            # Simular cada venta del día
            for i in range(num_ventas_base):
                # Seleccionar un usuario aleatorio para la venta
                usuario = random.choice(usuarios)
                
                # Crear o seleccionar un cliente
                if random.random() < 0.7:  # 70% de probabilidad de crear nuevo cliente
                    cliente = Cliente.objects.create(
                        nombre=fake.name(),
                        nit_ci=fake.bothify(text='########'),
                        telefono=fake.phone_number(),
                        activo=True
                    )
                else:
                    # Usar cliente existente
                    clientes_existentes = Cliente.objects.filter(activo=True)
                    if clientes_existentes.exists():
                        cliente = random.choice(list(clientes_existentes))
                    else:
                        cliente = Cliente.objects.create(
                            nombre=fake.name(),
                            nit_ci=fake.bothify(text='########'),
                            telefono=fake.phone_number(),
                            activo=True
                        )
                
                # Crear venta
                with transaction.atomic():
                    try:
                        # Obtener lotes disponibles
                        lotes_disponibles = LoteMedicamento.objects.filter(
                            activo=True, 
                            cantidad__gt=0
                        ).select_related('medicamento')
                        
                        if not lotes_disponibles:
                            self.stdout.write(self.style.WARNING(f'No hay lotes disponibles para la venta del día {fecha_venta}'))
                            continue
                        
                        # Decidir cuántos medicamentos diferentes se venderán (entre 1 y 4)
                        num_medicamentos = random.randint(1, 4)
                        
                        # Agrupar lotes por medicamento
                        lotes_por_medicamento = {}
                        for lote in lotes_disponibles:
                            if lote.medicamento_id not in lotes_por_medicamento:
                                lotes_por_medicamento[lote.medicamento_id] = []
                            lotes_por_medicamento[lote.medicamento_id].append(lote)
                        
                        # Seleccionar medicamentos que tienen lotes disponibles
                        medicamentos_con_lotes = list(lotes_por_medicamento.keys())
                        if not medicamentos_con_lotes:
                            continue
                            
                        medicamentos_seleccionados = random.sample(
                            medicamentos_con_lotes, 
                            min(num_medicamentos, len(medicamentos_con_lotes))
                        )
                        
                        if not medicamentos_seleccionados:
                            continue
                        
                        # Crear la venta principal
                        venta = Ventas.objects.create(
                            usuario=usuario,
                            fecha_venta=fecha_venta,
                            precio_total=decimal.Decimal('0.00'),
                            activo=True
                        )
                        
                        precio_total_venta = decimal.Decimal('0.00')
                        
                        # Crear detalle de venta para cada medicamento
                        for medicamento_id in medicamentos_seleccionados:
                            # Obtener objeto medicamento
                            medicamento = Medicamentos.objects.get(id=medicamento_id)
                            
                            # Obtener lotes disponibles para este medicamento
                            lotes_med = lotes_por_medicamento[medicamento_id]
                            
                            # Decidir cantidad a vender (entre 1 y 5)
                            cantidad_vender = random.randint(1, 5)
                            
                            # Verificar si hay suficiente stock
                            stock_disponible = sum(lote.cantidad for lote in lotes_med)
                            if stock_disponible < cantidad_vender:
                                cantidad_vender = stock_disponible
                            
                            if cantidad_vender <= 0:
                                continue
                            
                            # Usar el precio de venta del primer lote disponible
                            precio_venta = lotes_med[0].precio_venta
                            
                            # Crear detalle de venta
                            detalle = DetalleVenta.objects.create(
                                venta=venta,
                                medicamento=medicamento,
                                precio=precio_venta,
                                cantidad=cantidad_vender,
                                activo=True
                            )
                            
                            # Procesar FIFO para reducir el stock
                            detalle.procesar_fifo()
                            
                            # Actualizar precio total
                            subtotal = precio_venta * decimal.Decimal(cantidad_vender)
                            precio_total_venta += subtotal
                        
                        # Si no se pudieron agregar detalles, eliminar la venta
                        if DetalleVenta.objects.filter(venta=venta).count() == 0:
                            venta.delete()
                            continue
                        
                        # Actualizar el precio total de la venta
                        venta.precio_total = precio_total_venta
                        venta.save()
                        
                        # Crear factura para la venta (80% de probabilidad)
                        if random.random() < 0.8:
                            Factura.objects.create(
                                venta=venta,
                                cliente=cliente,
                                monto_total=precio_total_venta,
                                activo=True
                            )
                        
                        if i % 10 == 0:  # Log cada 10 ventas para no saturar la consola
                            self.stdout.write(f'  Venta #{venta.id} creada: {DetalleVenta.objects.filter(venta=venta).count()} medicamentos por ${precio_total_venta}')
                            
                    except Exception as e:
                        logger.error(f'Error al crear venta: {str(e)}')
                        self.stdout.write(self.style.ERROR(f'Error al crear venta: {str(e)}'))
