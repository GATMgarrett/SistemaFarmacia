# Generated by Django 4.2.5 on 2023-10-08 03:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ventas', '0002_delete_producto_delete_usuario'),
    ]

    operations = [
        migrations.CreateModel(
            name='Compras',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_compra', models.DateField()),
                ('cantidad', models.IntegerField()),
                ('precio_total', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='Laboratorios',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_laboratorio', models.CharField(max_length=255)),
                ('telefono_lab', models.IntegerField()),
                ('direccion', models.CharField(blank=True, max_length=255, null=True)),
                ('abreviatura_lab', models.CharField(blank=True, max_length=255, null=True)),
                ('nit_lab', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Proveedores',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_empresa', models.CharField(max_length=255)),
                ('contacto', models.CharField(blank=True, max_length=255, null=True)),
                ('correo_contacto', models.EmailField(blank=True, max_length=254, null=True)),
                ('telefono_contacto', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Roles',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_rol', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Usuarios',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('apellido', models.CharField(max_length=255)),
                ('correo', models.EmailField(max_length=254)),
                ('contrasena', models.CharField(max_length=255)),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.roles')),
            ],
        ),
        migrations.CreateModel(
            name='Ventas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_venta', models.DateField()),
                ('precio_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.usuarios')),
            ],
        ),
        migrations.CreateModel(
            name='Medicamentos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('descripcion', models.CharField(blank=True, max_length=255, null=True)),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fecha_vencimiento', models.IntegerField()),
                ('stock', models.IntegerField()),
                ('laboratorio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.laboratorios')),
            ],
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cantidad', models.IntegerField()),
                ('medicamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.medicamentos')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.ventas')),
            ],
        ),
        migrations.CreateModel(
            name='DetalleCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cantidad', models.IntegerField()),
                ('compra', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles_compra', to='ventas.compras')),
                ('medicamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.medicamentos')),
            ],
        ),
        migrations.AddField(
            model_name='compras',
            name='medicamento',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.medicamentos'),
        ),
        migrations.AddField(
            model_name='compras',
            name='proveedor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.proveedores'),
        ),
    ]
