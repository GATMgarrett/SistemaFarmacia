from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def format_number(value):
    """
    Formatea un número con puntos para miles y comas para decimales
    Ejemplo: 1234567.89 -> 1.234.567,89
    """
    try:
        # Asegurarnos que es un número
        if isinstance(value, str):
            if ',' in value:
                # Si ya tiene coma decimal, reemplazarla temporalmente
                value = value.replace(',', '.')
        
        # Convertir a float
        num = float(value)
        
        # Verificar si es un número entero
        es_entero = num == int(num)
        
        if es_entero:
            # Formatear enteros sin decimales
            parts = f"{int(num):,d}".split(',')
            return '.'.join(parts)
        else:
            # Formatear con 2 decimales
            parts = f"{num:.2f}".split('.')
            entero_formateado = f"{int(parts[0]):,d}".split(',')
            return '.'.join(entero_formateado) + ',' + parts[1]
            
    except (ValueError, TypeError):
        return value
