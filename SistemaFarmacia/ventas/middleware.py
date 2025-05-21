from django.shortcuts import redirect
from django.urls import reverse, resolve

class TwoFactorAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # El usuario está autenticado
        if request.user.is_authenticated:
            # Excepciones: URLs que están permitidas incluso si no se ha completado el 2FA
            current_url = request.path_info
            # Permitir la URL de verificación, logout y ciertos recursos estáticos
            allowed_urls = ['/verify-code/', '/login/', '/logout/', '/admin/', '/static/']
            is_allowed = any(current_url.startswith(url) for url in allowed_urls)
            
            # Si la sesión no tiene la marca de verificación 2FA y no es una URL permitida
            if not request.session.get('verified_2fa', False) and not is_allowed:
                # Guardar la URL a la que intentaba acceder para redireccionar después
                request.session['next_url'] = current_url
                return redirect('verify_code')
        
        response = self.get_response(request)
        return response
