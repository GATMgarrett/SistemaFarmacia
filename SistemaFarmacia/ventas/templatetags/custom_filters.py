from django import template

register = template.Library()

@register.filter(name='format_number')
def format_number(value):
    """
    Formatea un número con puntos como separadores de miles
    y coma para decimales.
    Ejemplo: 1234567.89 → 1.234.567,89
    """
    if value is None:
        return '0'
    
    try:
        # Convertir a string y separar parte entera y decimal
        str_value = str(value)
        if '.' in str_value:
            integer_part, decimal_part = str_value.split('.')
        else:
            integer_part, decimal_part = str_value, '00'
        
        # Formatear parte entera con puntos cada 3 dígitos
        formatted_integer = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i and i % 3 == 0:
                formatted_integer = '.' + formatted_integer
            formatted_integer = digit + formatted_integer
        
        # Unir parte entera y decimal
        return f"{formatted_integer},{decimal_part[:2]}"
    except:
        return str(value)
