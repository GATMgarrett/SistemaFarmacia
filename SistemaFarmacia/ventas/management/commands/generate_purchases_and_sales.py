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
            Medicamentos(id=2, nombre="Acetazolamida", descripcion="Tratamiento del glaucoma, comprimidos de 250gr", stock=56, laboratorio_id=2, activo=True, categoria_id=3, tipo_id=13),
            Medicamentos(id=3, nombre="DIOXIQUINA", descripcion="Analgésico usado para el alivio de dolores leves a...", stock=43, laboratorio_id=1, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=4, nombre="ACETAMOL 1G", descripcion="Comprimido para fiebre y dolor leve, ideal para ad...", stock=0, laboratorio_id=2, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=5, nombre="DOLOFEN FORTE TAB CJA X 60 UND CIAL", descripcion="Alivia dolores fuertes, formulado para dolencias m...", stock=0, laboratorio_id=5, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=6, nombre="PARACETAMOL LCH. 500MG", descripcion="Analgésico común para fiebre y dolores leves, de r...", stock=5, laboratorio_id=7, activo=True, categoria_id=2, tipo_id=1),
            Medicamentos(id=7, nombre="PIREDOL 500MG", descripcion="Alternativa económica para el manejo de fiebre y d...", stock=0, laboratorio_id=6, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=8, nombre="PARACETAMOL 500MG", descripcion="Comprimido ampliamente usado para reducir fiebre y...", stock=0, laboratorio_id=11, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=9, nombre="PARACETAMOL 125MG/5ML", descripcion="Jarabe pediátrico para fiebre y dolores menores en...", stock=0, laboratorio_id=8, activo=False, categoria_id=3, tipo_id=1),
            Medicamentos(id=10, nombre="Z-MOL 1G", descripcion="Tableta potente para el manejo de dolores moderado...", stock=0, laboratorio_id=12, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=11, nombre="TRAMAGESIC 100MG", descripcion="Analgésico para el tratamiento de dolor intenso o ...", stock=0, laboratorio_id=14, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=12, nombre="PARACETAMOL 120MG/5ML", descripcion="Jarabe para aliviar dolores leves y fiebre en niño...", stock=0, laboratorio_id=15, activo=False, categoria_id=3, tipo_id=1),
            Medicamentos(id=13, nombre="TAILGIN", descripcion="Tableta analgésica rápida para dolores de cabeza o...", stock=0, laboratorio_id=16, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=14, nombre="NODOLEX", descripcion="Medicamento básico para dolores comunes y fiebre l...", stock=0, laboratorio_id=17, activo=False, categoria_id=2, tipo_id=1),
            Medicamentos(id=15, nombre="AZITROALCOS + COMPRIMIDOS", descripcion="Antibiótico para infecciones respiratorias y urina...", stock=0, laboratorio_id=18, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=16, nombre="SULFATRIM", descripcion="Usado para tratar infecciones bacterianas comunes.", stock=0, laboratorio_id=19, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=17, nombre="MACROZIT", descripcion="Antibiótico de amplio espectro, efectivo contra di...", stock=0, laboratorio_id=4, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=18, nombre="CEFABIOCT", descripcion="Cefalosporina para infecciones severas, incluidas ...", stock=0, laboratorio_id=20, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=19, nombre="TRIAFLEX 400MG", descripcion="Antibiótico para infecciones severas y recurrentes...", stock=0, laboratorio_id=21, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=20, nombre="MEROPENEM 500MG DUTRICÉ", descripcion="Antibiótico de uso hospitalario para infecciones g...", stock=0, laboratorio_id=22, activo=False, categoria_id=1, tipo_id=1),
            Medicamentos(id=21, nombre="AMBROXOL CLORHIDRATO", descripcion="Expectorante usado para aliviar tos y facilitar la...", stock=0, laboratorio_id=1, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=22, nombre="FLUIDIMUC", descripcion="Ayuda a diluir la mucosidad para aliviar la conges...", stock=0, laboratorio_id=2, activo=True, categoria_id=12, tipo_id=3),
            Medicamentos(id=23, nombre="ACETIL CISTEINA 300", descripcion="Expectorante eficaz en el tratamiento de enfermeda...", stock=0, laboratorio_id=5, activo=False, categoria_id=12, tipo_id=1),
            Medicamentos(id=24, nombre="MUXOL", descripcion="Expectorante usado en el tratamiento de la tos sec...", stock=0, laboratorio_id=7, activo=False, categoria_id=12, tipo_id=3),
            Medicamentos(id=25, nombre="PIRAXON FLU", descripcion="Expectorante que ayuda a aliviar los síntomas de l...", stock=0, laboratorio_id=6, activo=False, categoria_id=12, tipo_id=4)
        ]

        # Proveedores y usuarios
        proveedores = list(Proveedores.objects.filter(activo=True))
        usuarios = list(User.objects.all())

        # Validar datos iniciales
        if not proveedores or not usuarios:
            print("Error: Se requieren proveedores y usuarios existentes en la base de datos.")
        else:
            # Generar 30 compras para 2024
            for _ in range(40):  # Ajustar el número de compras
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

                compra.precio_total = precio_total
                compra.save()

            # Generar ventas para 2024
            current_date = start_date_2024
            while current_date <= end_date_2024:
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
