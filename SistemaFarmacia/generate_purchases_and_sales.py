# ventas/management/commands/generate_purchases_and_sales.py
from django.core.management.base import BaseCommand
import random
from datetime import timedelta, date
from faker import Faker
from django.contrib.auth.models import User
from ventas.models import (
    Medicamentos, Proveedores, Compras, DetalleCompra, LoteMedicamento,
    Ventas, DetalleVenta
)

class Command(BaseCommand):
    help = 'Genera datos de compras y ventas para 2024'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Configuración: Rango para 2024
        start_date_2024 = date(2024, 1, 1)
        end_date_2024 = date(2024, 11, 19)

        # Función para simular ventas estacionales
        def ventas_estacionales(dia):
            if dia.weekday() == 5:  # Sábado
                return random.randint(10, 30)
            elif dia.weekday() == 6:  # Domingo
                return random.randint(5, 20)
            elif dia.month in [6, 7] or (dia.month == 8 and dia.day <= 15):  # Invierno
                return random.randint(10, 25)
            else:
                return random.randint(0, 15)

        # Obtener datos existentes
        medicamentos = list(Medicamentos.objects.filter(activo=True))
        proveedores = list(Proveedores.objects.filter(activo=True))
        usuarios = list(User.objects.all())

        # Validar datos iniciales
        if not medicamentos or not proveedores or not usuarios:
            print("Error: Se requieren medicamentos, proveedores y usuarios existentes en la base de datos.")
        else:
            # Generar 30 compras para 2024
            for _ in range(30):  # Ajustar el número de compras
                proveedor = random.choice(proveedores)
                fecha_compra = fake.date_between(start_date=start_date_2024, end_date=end_date_2024)

                compra = Compras.objects.create(
                    proveedor=proveedor,
                    fecha_compra=fecha_compra,
                    precio_total=0  # Se calcula al final
                )

                precio_total = 0
                for _ in range(random.randint(1, 5)):  # Entre 1 y 5 medicamentos por compra
                    medicamento = random.choice(medicamentos)
                    cantidad = random.randint(10, 100)
                    precio_compra = round(random.uniform(5, 50), 2)

                    # Crear detalle de compra
                    DetalleCompra.objects.create(
                        compra=compra,
                        medicamento=medicamento,
                        cantidad=cantidad,
                        precio=precio_compra
                    )

                    # Crear lote de medicamentos
                    fecha_produccion = fecha_compra - timedelta(days=random.randint(30, 90))
                    fecha_vencimiento = fecha_produccion + timedelta(days=random.randint(365, 730))
                    LoteMedicamento.objects.create(
                        medicamento=medicamento,
                        cantidad=cantidad,
                        precio_compra=precio_compra,
                        precio_venta=round(precio_compra * random.uniform(1.2, 1.5), 2),  # Margen 20%-50%
                        fecha_compra=fecha_compra,
                        fecha_produccion=fecha_produccion,
                        fecha_vencimiento=fecha_vencimiento
                    )

                    precio_total += cantidad * precio_compra

                # Actualizar el precio total de la compra
                compra.precio_total = precio_total
                compra.save()

            # Generar ventas para 2024
            current_date = start_date_2024
            while current_date <= end_date_2024:
                ventas_del_dia = ventas_estacionales(current_date)  # Ventas ajustadas a estaciones
                for _ in range(ventas_del_dia):
                    usuario = random.choice(usuarios)
                    venta = Ventas.objects.create(
                        usuario=usuario,
                        fecha_venta=current_date,
                        precio_total=0  # Se calcula al final
                    )

                    precio_total = 0
                    for _ in range(random.randint(1, 5)):  # Entre 1 y 5 medicamentos por venta
                        medicamento = random.choice(medicamentos)
                        lotes = LoteMedicamento.objects.filter(
                            medicamento=medicamento,
                            activo=True
                        ).order_by('fecha_compra')

                        if not lotes.exists():
                            continue

                        lote = lotes.first()
                        cantidad = random.randint(1, min(10, lote.cantidad))  # Máximo 10 o lo disponible

                        # Crear detalle de venta
                        precio_venta = lote.precio_venta
                        DetalleVenta.objects.create(
                            venta=venta,
                            medicamento=medicamento,
                            cantidad=cantidad,
                            precio=precio_venta
                        )

                        # Reducir stock del lote
                        lote.cantidad -= cantidad
                        if lote.cantidad <= 0:
                            lote.activo = False  # Desactiva el lote si ya no tiene stock
                        lote.save()

                        precio_total += cantidad * precio_venta

                    # Actualizar el precio total de la venta
                    venta.precio_total = precio_total
                    venta.save()

                current_date += timedelta(days=1)  # Avanzar al siguiente día

            print("Datos de compras y ventas para 2024 generados exitosamente.")
