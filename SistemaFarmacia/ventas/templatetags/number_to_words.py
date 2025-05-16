from django import template

register = template.Library()

@register.filter
def number_to_words(value):
    """Convierte números a palabras en español"""
    unidades = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
    decenas = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISÉIS', 
            'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE']
    veintenas = ['VEINTE', 'VEINTIUNO', 'VEINTIDÓS', 'VEINTITRÉS', 'VEINTICUATRO', 
                'VEINTICINCO', 'VEINTISÉIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE']
    decenas_superiores = ['', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 
                         'SETENTA', 'OCHENTA', 'NOVENTA', 'CIEN']
    centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 
            'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']
    
    try:
        num = int(float(value))
    except:
        return ''
    
    if num == 0:
        return 'CERO'
    
    palabras = []
    if num >= 1000:
        miles = num // 1000
        num = num % 1000
        if miles == 1:
            palabras.append('MIL')
        else:
            palabras.append(number_to_words(miles) + ' MIL')
    
    if num >= 100:
        centena = num // 100
        num = num % 100
        palabras.append(centenas[centena])
    
    if num >= 20:
        decena = num // 10
        num = num % 10
        if decena == 2:
            palabras.append(veintenas[num])
            num = 0
        else:
            palabras.append(decenas_superiores[decena])
    
    if num >= 10:
        palabras.append(decenas[num-10])
        num = 0
    
    if num > 0:
        palabras.append(unidades[num])
    
    return ' '.join(palabras).strip()