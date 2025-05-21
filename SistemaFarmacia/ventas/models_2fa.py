from django.db import models
from django.contrib.auth.models import User
import random
import string
from datetime import timedelta
from django.utils import timezone

class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    @classmethod
    def generate_code(cls, user, expiry_minutes=10):
        # Generar un código aleatorio de 6 dígitos
        code = ''.join(random.choices(string.digits, k=6))
        
        # Calcular la fecha de expiración
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Invalidar códigos anteriores para este usuario
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Crear y guardar el nuevo código
        verification = cls(
            user=user,
            code=code,
            expires_at=expires_at
        )
        verification.save()
        
        return verification
    
    def is_valid(self):
        now = timezone.now()
        return not self.is_used and now < self.expires_at
