from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models_2fa import VerificationCode
from .email_utils import send_verification_email
from django.urls import reverse

def login_view(request):
    """Vista para el primer paso de login (nombre de usuario y contraseña)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Autenticar al usuario pero NO iniciar sesión todavía
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Si el usuario existe y las credenciales son correctas
            # Generamos un código de verificación
            verification = VerificationCode.generate_code(user)
            
            # Obtenemos el correo electrónico del usuario
            user_email = user.email
            
            # Enviamos el código por correo electrónico
            if user_email:
                send_verification_email(user_email, verification.code)
                
                # Redireccionamos a la página de verificación de código
                # Guardamos el username en la sesión para referencia posterior
                request.session['verification_username'] = username
                return redirect('verify_code')
            else:
                # Si el usuario no tiene correo, mostrar un error
                return render(request, 'registration/login.html', {
                    'error_message': 'No hay correo electrónico asociado a esta cuenta. Contacte al administrador.'
                })
        else:
            # Si las credenciales son incorrectas
            return render(request, 'registration/login.html', {
                'error_message': 'Nombre de usuario o contraseña incorrectos.'
            })
    
    # Si es una petición GET, mostrar el formulario de login
    return render(request, 'registration/login.html')

def verify_code_view(request):
    """Vista para el segundo paso de login (verificación de código)"""
    # Verificar si tenemos un username en la sesión
    username = request.session.get('verification_username')
    
    # Si el usuario está autenticado pero no ha pasado por el 2FA (no tiene username en sesión)
    if request.user.is_authenticated and not username:
        # Cerrar sesión y redirigir al login para forzar el flujo completo
        logout(request)
        messages.warning(request, 'Por seguridad, debes completar la verificación en dos pasos.')
        return redirect('login')
    
    if not username:
        # Si no hay username en la sesión, redirigir al login
        return redirect('login')
    
    if request.method == 'POST':
        # Obtener el código del formulario
        verification_code = request.POST.get('verification_code')
        
        try:
            # Obtener el usuario
            user = User.objects.get(username=username)
            
            # Buscar el código de verificación más reciente para este usuario
            verification = VerificationCode.objects.filter(
                user=user,
                is_used=False,
                code=verification_code
            ).latest('created_at')
            
            # Verificar si el código es válido
            if verification and verification.is_valid():
                # Marcar el código como usado
                verification.is_used = True
                verification.save()
                
                # Iniciar sesión
                login(request, user)
                
                # Marcar la sesión como verificada en 2FA
                request.session['verified_2fa'] = True
                
                # Limpiar la sesión
                if 'verification_username' in request.session:
                    del request.session['verification_username']
                
                # Redirigir a la página almacenada o a la principal si no hay una
                next_url = request.session.get('next_url', None)
                if next_url:
                    del request.session['next_url']
                    return redirect(next_url)
                
                # Si no hay URL guardada, ir a la página principal
                return redirect('index')
            else:
                # Código inválido o expirado
                return render(request, 'registration/verify_code.html', {
                    'error_message': 'Código inválido o expirado.'
                })
        
        except (User.DoesNotExist, VerificationCode.DoesNotExist):
            # Usuario o código no existen
            return render(request, 'registration/verify_code.html', {
                'error_message': 'Código inválido o expirado.'
            })
    
    # Si es una petición GET, mostrar el formulario de verificación
    return render(request, 'registration/verify_code.html')

def resend_code_view(request):
    """Vista para reenviar el código de verificación"""
    # Verificar si tenemos un username en la sesión
    username = request.session.get('verification_username')
    
    if not username:
        # Si no hay username en la sesión, redirigir al login
        return redirect('login')
    
    try:
        # Obtener el usuario
        user = User.objects.get(username=username)
        
        # Generar un nuevo código
        verification = VerificationCode.generate_code(user)
        
        # Enviar el código por correo electrónico
        if user.email:
            send_verification_email(user.email, verification.code)
            
            # Redirigir de vuelta a la página de verificación con mensaje de éxito
            return render(request, 'registration/verify_code.html', {
                'success_message': 'Se ha enviado un nuevo código a su correo electrónico.'
            })
        else:
            # Si el usuario no tiene correo, mostrar un error
            return render(request, 'registration/verify_code.html', {
                'error_message': 'No hay correo electrónico asociado a esta cuenta. Contacte al administrador.'
            })
    
    except User.DoesNotExist:
        # Usuario no existe
        return redirect('login')
