# Generated by Django 4.2.5 on 2023-10-08 03:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Producto',
        ),
        migrations.DeleteModel(
            name='Usuario',
        ),
    ]
