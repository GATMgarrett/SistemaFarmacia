import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from django.contrib.auth.models import User
from ventas.models import (
    Ventas, DetalleVenta, Cliente, Compras, DetalleCompra,
    LoteMedicamento, Medicamentos, Laboratorios, Categorias, Proveedores, Factura
)

class Command(BaseCommand):
    help = 'Simula 3 meses de actividad: compras iniciales y ventas diarias'

    def handle(self, *args, **options):
        fake = Faker('es_ES')
        hoy = timezone.now()
        
        # Configurar fechas para 3 meses de simulación
        fecha_inicio = hoy - timedelta(days=90)  # Hace 3 meses
        fecha_actual = fecha_inicio
        fecha_fin = hoy  # Hasta hoy
        
        self.stdout.write(f"Iniciando simulación desde {fecha_inicio.date()} hasta {fecha_fin.date()}")
        
        # Obtener o crear usuario administrador
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        
        # Crear laboratorio, categoría y proveedor por defecto si no existen
        lab, _ = Laboratorios.objects.get_or_create(
            nombre_laboratorio="Laboratorio Genérico",
            telefono_lab=1234567,
            nit_lab=1234567890
        )
        
        cat, _ = Categorias.objects.get_or_create(
            nombre_categoria="General",
            descripcion="Categoría general para medicamentos"
        )
        
        proveedor, _ = Proveedores.objects.get_or_create(
            nombre_empresa="Proveedor Principal",
            defaults={
                'contacto': "Contacto Principal",
                'telefono_contacto': "12345678",
                'direccion': "Dirección del proveedor",
                'descripcion': "Proveedor por defecto para datos de prueba"
            }
        )

        # 1. Crear compras iniciales (primera semana del primer mes)
        self.stdout.write("\n=== Creando compras iniciales ===")
        medicamentos = []
        for i in range(1, 26):  # 25 medicamentos
            med, _ = Medicamentos.objects.get_or_create(
                nombre=f"Medicamento {fake.word().capitalize()} {i}",
                defaults={
                    'descripcion': fake.sentence(),
                    'laboratorio': lab,
                    'categoria': cat,
                    'stock': 0  # Se actualizará con los lotes
                }
            )
            medicamentos.append(med)
            
            # Crear lote inicial con 100-200 unidades
            fecha_vencimiento = fecha_actual + timedelta(days=random.randint(180, 720))
            precio_compra = round(random.uniform(5, 20), 2)
            precio_venta = round(precio_compra * random.uniform(1.3, 2.0), 2)
            cantidad = random.randint(100, 200)
            
            lote = LoteMedicamento.objects.create(
                medicamento=med,
                cantidad=cantidad,
                precio_compra=precio_compra,
                precio_venta=precio_venta,
                fecha_compra=fecha_actual - timedelta(days=30),  # Comprado 1 mes antes
                fecha_vencimiento=fecha_vencimiento,
                lote_fabricante=f"LOTE-{med.id}-001"
            )
            
            # Actualizar stock del medicamento
            med.stock += cantidad
            med.save()
            
            # Registrar compra
            compra = Compras.objects.create(
                proveedor=proveedor,
                fecha_compra=fecha_actual - timedelta(days=30),  # Comprado 1 mes antes
                precio_total=cantidad * precio_compra
            )
            
            DetalleCompra.objects.create(
                compra=compra,
                medicamento=med,
                precio=precio_compra,
                cantidad=cantidad
            )

        # 2. Crear clientes iniciales
        self.stdout.write("\n=== Creando clientes iniciales ===")
        clientes = []
        for _ in range(15):  # 15 clientes iniciales
            cliente = Cliente.objects.create(
                nombre=fake.name(),
                nit_ci=fake.unique.bothify('#######'),
                telefono=fake.phone_number()[:15]
            )
            clientes.append(cliente)

        # 3. Simular ventas diarias por 3 meses
        self.stdout.write("\n=== Simulando ventas diarias ===\n")
        total_dias = (fecha_fin - fecha_actual).days
        dia_actual = 0
        
        while fecha_actual <= fecha_fin:
            # Mostrar progreso
            dia_actual += 1
            if dia_actual % 10 == 0 or dia_actual == 1 or dia_actual == total_dias:
                progreso = (dia_actual / total_dias) * 100
                self.stdout.write(
                    f"Procesando día {dia_actual} de {total_dias} ({fecha_actual.date()}) - {progreso:.1f}% completado",
                    ending='\r'
                )
                self.stdout.flush()
            
            # Número de ventas del día (más ventas a fin de mes)
            dia_mes = fecha_actual.day
            dia_semana = fecha_actual.weekday()  # 0 = lunes, 6 = domingo
            
            # Ajustar número de ventas según el día
            ventas_base = 5  # Base de ventas diarias
            if dia_semana >= 5:  # Fin de semana
                ventas_base += random.randint(3, 7)
            if dia_mes > 25:  # Fin de mes
                ventas_base += random.randint(2, 5)
            
            num_ventas = random.randint(ventas_base - 2, ventas_base + 2)
            
            for _ in range(num_ventas):
                # Obtener cliente aleatorio o crear uno nuevo (20% de probabilidad)
                if random.random() < 0.2:  # 20% de probabilidad de crear cliente nuevo
                    cliente = Cliente.objects.create(
                        nombre=fake.name(),
                        nit_ci=fake.unique.bothify('#######'),
                        telefono=fake.phone_number()[:15]
                    )
                    clientes.append(cliente)
                else:
                    cliente = random.choice(clientes)
                
                # Crear venta
                venta = Ventas.objects.create(
                    usuario=admin_user,
                    fecha_venta=fecha_actual.replace(
                        hour=random.randint(8, 20),
                        minute=random.randint(0, 59)
                    ),
                    precio_total=0
                )
                
                # 1-5 productos por venta
                total_venta = 0
                num_productos = random.randint(1, 5)
                productos_venta = random.sample(medicamentos, k=min(num_productos, len(medicamentos)))
                
                for med in productos_venta:
                    # Buscar lotes disponibles
                    lotes_disponibles = list(LoteMedicamento.objects.filter(
                        medicamento=med,
                        activo=True,
                        cantidad__gt=0
                    ).order_by('fecha_compra'))
                    
                    if not lotes_disponibles:
                        continue
                        
                    lote = lotes_disponibles[0]
                    cantidad = min(random.randint(1, 5), lote.cantidad)
                    precio_venta = lote.precio_venta
                    subtotal = cantidad * precio_venta
                    total_venta += subtotal
                    
                    try:
                        # Crear detalle de venta
                        detalle = DetalleVenta.objects.create(
                            venta=venta,
                            medicamento=med,
                            precio=precio_venta,
                            cantidad=cantidad
                        )
                        
                        # Procesar la venta (actualizar stock)
                        detalle.procesar_fifo()
                        
                        # Actualizar stock del medicamento
                        med.refresh_from_db()  # Asegurarse de tener los datos actualizados
                        
                    except ValueError as e:
                        self.stdout.write(self.style.WARNING(f"Error al procesar venta: {e}"))
                        continue
                
                # Solo actualizar si hubo productos vendidos
                if total_venta > 0:
                    # Actualizar total de la venta
                    venta.precio_total = total_venta
                    venta.save()
                    
                    # Crear factura para la venta (70% de probabilidad)
                    if random.random() < 0.7:
                        try:
                            # Obtener el último número de factura
                            ultima_factura = Factura.objects.order_by('-numero_factura').first()
                            siguiente_numero = ultima_factura.numero_factura + 1 if ultima_factura else 1
                            
                            Factura.objects.create(
                                venta=venta,
                                cliente=cliente,
                                numero_factura=siguiente_numero,
                                fecha_emision=venta.fecha_venta,
                                monto_total=total_venta,
                                fecha_limite_emision=venta.fecha_venta + timedelta(days=30)
                            )
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error al crear factura: {e}"))
                
                # Reabastecer si el stock está bajo (simulación de compra automática)
                # Solo revisar cada 3 días para mejorar rendimiento
                if random.random() < 0.33:  # Aprox 1 de cada 3 días
                    for med in medicamentos:
                        if med.stock < 30 and random.random() < 0.7:  # 70% de probabilidad si stock < 30
                            cantidad_reponer = random.randint(50, 150)  # Cantidad variable
                            fecha_vencimiento = fecha_actual + timedelta(days=random.randint(180, 720))
                            precio_compra = round(random.uniform(5, 20), 2)
                            precio_venta = round(precio_compra * random.uniform(1.3, 2.0), 2)
                            
                            lote_nuevo = LoteMedicamento.objects.create(
                                medicamento=med,
                                cantidad=cantidad_reponer,
                                precio_compra=precio_compra,
                                precio_venta=precio_venta,
                                fecha_compra=fecha_actual,
                                fecha_vencimiento=fecha_vencimiento,
                                lote_fabricante=f"LOTE-{med.id}-{LoteMedicamento.objects.filter(medicamento=med).count() + 1:03d}"
                            )
                            
                            # Actualizar stock del medicamento
                            med.stock += cantidad_reponer
                            med.save()
                            
                            # Registrar compra de reabastecimiento
                            compra = Compras.objects.create(
                                proveedor=proveedor,
                                fecha_compra=fecha_actual,
                                precio_total=cantidad_reponer * precio_compra
                            )
                            
                            DetalleCompra.objects.create(
                                compra=compra,
                                medicamento=med,
                                precio=precio_compra,
                                cantidad=cantidad_reponer
                            )
            
            # Pasar al siguiente día
            fecha_actual += timedelta(days=1)
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS('¡Simulación de 3 meses completada exitosamente!'))
        self.stdout.write("="*50)
        self.stdout.write(f"Total de ventas generadas: {Ventas.objects.count()}")
        self.stdout.write(f"Total de clientes registrados: {Cliente.objects.count()}")
        self.stdout.write(f"Total de medicamentos: {Medicamentos.objects.count()}")
        self.stdout.write(f"Total de lotes creados: {LoteMedicamento.objects.count()}")
        self.stdout.write(f"Total de facturas generadas: {Factura.objects.count()}")
        self.stdout.write("="*50)