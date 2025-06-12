import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import string
import random

def generate_random_password(length=12):
    """
    Genera una contraseña aleatoria segura
    """
    # Definir los caracteres para la contraseña
    caracteres = string.ascii_letters + string.digits + string.punctuation
    # Excluir algunos caracteres que pueden ser confusos o causar problemas
    caracteres = caracteres.replace('"', '').replace("'", '').replace('`', '').replace('\\', '').replace(';', '')
    
    # Generar la contraseña aleatoria
    password = ''
    for i in range(length):
        password += random.choice(caracteres)
    
    return password

def send_user_credentials(user_email, username, password):
    """
    Envía un correo electrónico con las credenciales de acceso al nuevo usuario
    """
    # Configuración del servidor SMTP
    smtp_server = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    smtp_user = settings.EMAIL_HOST_USER
    smtp_password = settings.EMAIL_HOST_PASSWORD
    
    # Crear el mensaje
    message = MIMEMultipart()
    message['From'] = smtp_user
    message['To'] = user_email
    message['Subject'] = 'Farmacia Yasney - Credenciales de Acceso'
    
    # Contenido del mensaje
    html = f'''
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
            <h2 style="color: #007bff; text-align: center;">Farmacia Yasney</h2>
            <p>Estimado(a) {username},</p>
            <p>Se ha creado una cuenta para ti en el sistema de Farmacia Yasney. A continuación, encontrarás tus credenciales de acceso:</p>
            <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0;">
                <p><strong>Usuario:</strong> {username}</p>
                <p><strong>Contraseña:</strong> {password}</p>
            </div>
            <p>Por razones de seguridad, te recomendamos cambiar tu contraseña después de iniciar sesión por primera vez.</p>
            <p>Para acceder al sistema, visita: <a href="#">Portal de Farmacia Yasney</a></p>
            <p>Saludos,<br>El equipo de Farmacia Yasney</p>
        </div>
    </body>
    </html>
    '''
    
    message.attach(MIMEText(html, 'html'))
    
    try:
        # Establecer conexión con el servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Iniciar TLS para seguridad
        server.login(smtp_user, smtp_password)
        
        # Enviar correo
        text = message.as_string()
        server.sendmail(smtp_user, user_email, text)
        
        # Cerrar la conexión
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False

def send_verification_email(user_email, verification_code):
    """
    Envía un correo electrónico con un código de verificación para el 2FA
    """
    # Configuración del servidor SMTP
    smtp_server = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    smtp_user = settings.EMAIL_HOST_USER
    smtp_password = settings.EMAIL_HOST_PASSWORD
    
    # Crear el mensaje
    message = MIMEMultipart()
    message['From'] = smtp_user
    message['To'] = user_email
    message['Subject'] = 'Farmacia Yasney - Código de Verificación'
    
    # Contenido del mensaje
    html = f'''
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
            <h2 style="color: #007bff; text-align: center;">Farmacia Yasney</h2>
            <p>Estimado(a) usuario,</p>
            <p>Para completar su inicio de sesión, por favor utilice el siguiente código de verificación:</p>
            <div style="background-color: #f5f5f5; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;">
                {verification_code}
            </div>
            <p>Este código expirará en 10 minutos.</p>
            <p>Si no ha intentado iniciar sesión, por favor ignore este mensaje y considere cambiar su contraseña.</p>
            <p>Saludos,<br>El equipo de Farmacia Noemi</p>
        </div>
    </body>
    </html>
    '''
    
    message.attach(MIMEText(html, 'html'))
    
    try:
        # Establecer conexión con el servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Iniciar TLS para seguridad
        server.login(smtp_user, smtp_password)
        
        # Enviar correo
        text = message.as_string()
        server.sendmail(smtp_user, user_email, text)
        
        # Cerrar la conexión
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
