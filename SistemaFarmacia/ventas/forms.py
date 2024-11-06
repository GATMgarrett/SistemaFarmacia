from django import forms
from django.contrib.auth.models import User, Group
from .models import Laboratorios, Proveedores, Medicamentos
from django_select2.forms import Select2Widget
    
    
# Aqui vamos a crear las clases de los fomrularios de los modelos

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        widget=Select2Widget,
        label='Grupo',
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'grupo')
        widgets = {
            'password': forms.PasswordInput(),  # Esto asegura que el campo de la contraseña se muestre como tal
        }
    
    def save(self, commit=True):
        user = super(UsuarioForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            if self.cleaned_data["grupo"]:
                user.groups.add(self.cleaned_data["grupo"])
        return user

class LaboratorioForm(forms.ModelForm):
    class Meta:
        model = Laboratorios
        fields = ['nombre_laboratorio', 'telefono_lab', 'direccion', 'abreviatura_lab', 'nit_lab']  # excluye 'activo'

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedores
        fields = '__all__'
        
class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamentos
        fields = ['nombre', 'descripcion', 'precio', 'fecha_vencimiento', 'stock', 'laboratorio']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    laboratorio = forms.ModelChoiceField(
        queryset=Laboratorios.objects.filter(activo=True),
        empty_label="Seleccione un laboratorio",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
        
# Aqui vamos a crear las clases de los fomrularios de los modelos de ventas y detalle de ventas
from django import forms
from .models import Ventas, DetalleVenta

class VentaForm(forms.ModelForm):
    class Meta:
        model = Ventas
        fields = ['usuario', 'fecha_venta']

class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['medicamento', 'cantidad']
