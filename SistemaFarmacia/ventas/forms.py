from django import forms
from django.contrib.auth.models import User, Group
from .models import Laboratorios, Proveedores, Medicamentos
from django_select2.forms import Select2Widget
from .models import Ventas, DetalleVenta, Categorias, Tipos

    
# Aqui vamos a crear las clases de los fomrularios de los modelos

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,  # Hacerlo opcional
        help_text="Dejar en blanco para mantener la contraseña actual (solo en edición)"
    )
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        widget=Select2Widget,
        label='Grupo',
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'grupo')
    
    def save(self, commit=True):
        user = super(UsuarioForm, self).save(commit=False)
        # Solo actualizar la contraseña si se proporciona una
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
            if self.cleaned_data.get("grupo"):
                # Limpiar grupos existentes y agregar el nuevo
                user.groups.clear()
                user.groups.add(self.cleaned_data["grupo"])
        return user

class LaboratorioForm(forms.ModelForm):
    class Meta:
        model = Laboratorios
        fields = ['nombre_laboratorio', 'telefono_lab', 'direccion', 'abreviatura_lab', 'nit_lab']  # excluye 'activo'

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedores
        fields = ['nombre_empresa', 'contacto', 'correo_contacto', 'telefono_contacto', 'descripcion', 'direccion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer 'activo' por defecto como True sin que aparezca en el formulario
        self.instance.activo = True
        
class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamentos
        fields = ['nombre', 'descripcion', 'laboratorio', 'categoria', 'tipo']  # Campo stock eliminado
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
        }

    laboratorio = forms.ModelChoiceField(
        queryset=Laboratorios.objects.filter(activo=True),
        empty_label="Seleccione un laboratorio",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    categoria = forms.ModelChoiceField(
        queryset=Categorias.objects.filter(activo=True),  # Asegúrate de tener un campo 'activo' en Categorias
        empty_label="Seleccione una categoría",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    tipo = forms.ModelChoiceField(
        queryset=Tipos.objects.filter(activo=True),  # Asegúrate de tener un campo 'activo' en Tipos
        empty_label="Seleccione un tipo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = ['nombre_categoria', 'descripcion']

class TipoForm(forms.ModelForm):
    class Meta:
        model = Tipos
        fields = ['nombre_tipo', 'descripcion']

# Aqui vamos a crear las clases de los fomrularios de los modelos de ventas y detalle de ventas
class VentaForm(forms.ModelForm):
    class Meta:
        model = Ventas
        fields = ['usuario', 'fecha_venta']

class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['medicamento', 'cantidad']
