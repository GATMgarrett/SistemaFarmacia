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
    help = 'Genera datos de compras y ventas para 2023-2024'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Configuración: Rango desde julio 2023 hasta noviembre 2024
        start_date = date(2023, 7, 1)
        end_date = date(2024, 11, 20)

        # Función para simular ventas estacionales
        def ventas_estacionales(dia):
            base_ventas = 10  # Ventas base para días regulares
            if dia.weekday() == 5:  # Sábado
                return base_ventas + random.randint(5, 15)  # Sábado tiene más ventas
            elif dia.weekday() == 6:  # Domingo
                return base_ventas + random.randint(3, 12)  # Domingo tiene más ventas, pero no tanto como el sábado
            elif dia.month in [6, 7] or (dia.month == 8 and dia.day <= 15):  # Invierno
                return base_ventas + random.randint(5, 10)  # Invierno tiene una ligera alza
            elif dia.month in [11, 12]:  # Diciembre (fin de año) tiene ventas más altas
                return base_ventas + random.randint(8, 18)
            else:
                return base_ventas + random.randint(0, 5)  # Para el resto de los meses

        # Medicamentos manualmente asignados
        medicamentos = [
            Medicamentos(id=1, nombre="ALCA", descripcion="Es", stock=47, laboratorio_id=1, activo=True, categoria_id=2, tipo_id=2),
            Medicamentos(id=2, nombre="Acetazolamida", descripcion="Tratamiento del glaucoma, comprimidos de 250gr", stock=66, laboratorio_id=2, activo=True, categoria_id=3, tipo_id=13),
            Medicamentos(id=3, nombre="DIOXIQUINA", descripcion="Analgésico usado para el alivio de dolores leves a moderados", stock=48, laboratorio_id=1, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=4, nombre="ACETAMOL 1G", descripcion="Comprimido para fiebre y dolor leve, ideal para adultos", stock=0, laboratorio_id=2, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=5, nombre="DOLOFEN FORTE TAB CJA X 60 UND CIAL", descripcion="Alivia dolores fuertes, formulado para dolencias musculares", stock=0, laboratorio_id=5, activo=True, categoria_id=1, tipo_id=2),
            Medicamentos(id=6, nombre="PARACETAMOL LCH. 500MG", descripcion="Analgésico común para fiebre y dolores leves, de rápido efecto", stock=5, laboratorio_id=7, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=7, nombre="PIREDOL 500MG", descripcion="Alternativa económica para el manejo de fiebre y dolor", stock=0, laboratorio_id=6, activo=True, categoria_id=1, tipo_id=2),
            Medicamentos(id=8, nombre="PARACETAMOL 500MG", descripcion="Comprimido ampliamente usado para reducir fiebre y aliviar dolor", stock=0, laboratorio_id=11, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=9, nombre="PARACETAMOL 125MG/5ML", descripcion="Jarabe pediátrico para fiebre y dolores menores en niños", stock=0, laboratorio_id=8, activo=True, categoria_id=3, tipo_id=1),
            Medicamentos(id=10, nombre="Z-MOL 1G", descripcion="Tableta potente para el manejo de dolores moderados y severos", stock=0, laboratorio_id=12, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=11, nombre="TRAMAGESIC 100MG", descripcion="Analgésico para el tratamiento de dolor intenso o crónico", stock=0, laboratorio_id=14, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=12, nombre="PARACETAMOL 120MG/5ML", descripcion="Jarabe para aliviar dolores leves y fiebre en niños", stock=0, laboratorio_id=15, activo=True, categoria_id=3, tipo_id=1),
            Medicamentos(id=13, nombre="TAILGIN", descripcion="Tableta analgésica rápida para dolores de cabeza o musculares", stock=0, laboratorio_id=16, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=14, nombre="NODOLEX", descripcion="Medicamento básico para dolores comunes y fiebre leve", stock=0, laboratorio_id=17, activo=True, categoria_id=1, tipo_id=1),
            Medicamentos(id=15, nombre="AZITROALCOS + COMPRIMIDOS", descripcion="Antibiótico para infecciones respiratorias y urinarias", stock=0, laboratorio_id=18, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=16, nombre="SULFATRIM", descripcion="Usado para tratar infecciones bacterianas comunes", stock=0, laboratorio_id=19, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=17, nombre="MACROZIT", descripcion="Antibiótico de amplio espectro, efectivo contra diversas infecciones", stock=0, laboratorio_id=4, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=18, nombre="CEFABIOCT", descripcion="Cefalosporina para infecciones severas, incluidas respiratorias", stock=0, laboratorio_id=20, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=19, nombre="TRIAFLEX 400MG", descripcion="Antibiótico para infecciones severas y recurrentes", stock=0, laboratorio_id=21, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=20, nombre="MEROPENEM 500MG DUTRICÉ", descripcion="Antibiótico de uso hospitalario para infecciones graves", stock=0, laboratorio_id=22, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=21, nombre="AMBROXOL CLORHIDRATO", descripcion="Expectorante usado para aliviar tos y facilitar la respiración", stock=0, laboratorio_id=1, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=22, nombre="FLUIDIMUC", descripcion="Ayuda a diluir la mucosidad para aliviar la congestión", stock=0, laboratorio_id=2, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=23, nombre="ACETIL CISTEINA 300", descripcion="Expectorante eficaz en el tratamiento de enfermedades respiratorias", stock=0, laboratorio_id=5, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=24, nombre="MUXOL", descripcion="Expectorante usado en el tratamiento de la tos seca", stock=0, laboratorio_id=7, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=25, nombre="PIRAXON FLU", descripcion="Expectorante que ayuda a aliviar los síntomas de la gripe", stock=0, laboratorio_id=6, activo=True, categoria_id=12, tipo_id=4)
        ]

        # Proveedores y usuarios
        proveedores = list(Proveedores.objects.filter(activo=True))
        usuarios = list(User.objects.all())

        # Validar datos iniciales
        if not proveedores or not usuarios:
            print("Error: Se requieren proveedores y usuarios existentes en la base de datos.")
        else:
            # Generar compras distribuidas de manera creciente
            total_compras = 50
            fecha_compra = start_date
            for i in range(total_compras):
                proveedor = random.choice(proveedores)
                compra = Compras.objects.create(
                    proveedor=proveedor,
                    fecha_compra=fecha_compra,
                    precio_total=0  # Se calcula al final
                )

                precio_total = 0
                medicamentos_comprados = 0
                cantidad_a_comprar = (i + 1)  # Distribuir compras crecientes

                for _ in range(random.randint(1, 5)):  # Entre 1 y 5 medicamentos por compra
                    medicamento = random.choice(medicamentos)
                    cantidad = min(medicamento.stock + cantidad_a_comprar, 100)  # No exceder el stock máximo
                    precio_compra = round(random.uniform(5, 50), 2)

                    # Crear detalle de compra
                    DetalleCompra.objects.create(
                        compra=compra,
                        medicamento=medicamento,
                        cantidad=cantidad,
                        precio=precio_compra
                    )

                    # Crear lote de medicamento
                    LoteMedicamento.objects.create(
                        medicamento=medicamento,
                        cantidad=cantidad,
                        precio_compra=precio_compra,
                        precio_venta=round(precio_compra * 1.3, 2),  # 30% de margen
                        fecha_compra=fecha_compra,
                        fecha_produccion=fecha_compra,
                        fecha_vencimiento=fecha_compra + timedelta(days=random.randint(365, 730)),
                    )

                    precio_total += cantidad * precio_compra
                    medicamentos_comprados += 1

                compra.precio_total = precio_total
                compra.save()

                # Incrementar la fecha para la siguiente compra (distancia creciente)
                fecha_compra += timedelta(days=random.randint(1, 15))  # Cambiar la lógica de fechas si es necesario

            # Generar ventas solo después de las compras
            current_date = start_date
            while current_date <= end_date:
                ventas_del_dia = ventas_estacionales(current_date)  # Ventas ajustadas a estaciones
                ventas_del_dia = min(ventas_del_dia, 5)  # Limitar las ventas a 5 por día
                for _ in range(ventas_del_dia):
                    usuario = random.choice(usuarios)
                    venta = Ventas.objects.create(
                        usuario=usuario,
                        fecha_venta=current_date,
                        precio_total=0  # Se calcula al final
                    )

                    precio_total = 0
                    medicamentos_asignados = 0  # Contador para verificar si se asignaron medicamentos

                    for _ in range(random.randint(1, 5)):  # Entre 1 y 5 medicamentos por venta
                        # Buscar medicamento disponible
                        medicamento = random.choice(medicamentos)

                        # Verificar si existen lotes disponibles para el medicamento
                        lotes = LoteMedicamento.objects.filter(
                            medicamento=medicamento,
                            activo=True
                        ).order_by('fecha_compra')

                        if not lotes.exists():
                            # Si no hay lotes, asignar un medicamento de todos modos
                            medicamento = random.choice(medicamentos)
                            # Verificar si hay stock disponible
                            if medicamento.stock <= 0:
                                continue  # Si no hay stock, continuar con otro ciclo

                            # Crear un lote ficticio para este medicamento si no hay lotes disponibles
                            LoteMedicamento.objects.create(
                                medicamento=medicamento,
                                cantidad=medicamento.stock,
                                precio_compra=round(random.uniform(5, 50), 2),
                                precio_venta=round(random.uniform(1.2, 1.5) * 10, 2),
                                fecha_compra=current_date,
                                fecha_produccion=current_date,
                                fecha_vencimiento=current_date + timedelta(days=random.randint(365, 730)),
                            )
                            lotes = LoteMedicamento.objects.filter(
                                medicamento=medicamento,
                                activo=True
                            ).order_by('fecha_compra')

                        lote = lotes.first()  # Tomamos el primer lote disponible
                        cantidad = random.randint(1, min(10, lote.cantidad))  # Máximo 10 o lo disponible

                        # Asegúrate de que 'precio_venta' no sea None antes de multiplicar
                        precio_venta = lote.precio_venta if lote.precio_venta is not None else 0  # Si es None, asigna 0

                        # Crear detalle de venta
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
                        medicamentos_asignados += 1  # Incrementar contador de medicamentos asignados

                    # Si no se asignaron medicamentos en toda la venta, forzamos la asignación de un medicamento
                    if medicamentos_asignados == 0:
                        medicamento = random.choice(medicamentos)
                        DetalleVenta.objects.create(
                            venta=venta,
                            medicamento=medicamento,
                            cantidad=1,  # Asignamos 1 medicamento como último recurso
                            precio=10  # Precio arbitrario en caso de no encontrar precio_venta
                        )

                    # Actualizar el precio total de la venta
                    venta.precio_total = precio_total
                    venta.save()

                current_date += timedelta(days=1)  # Avanzar al siguiente día

        self.stdout.write(self.style.SUCCESS('Datos de compras y ventas generados correctamente.'))
