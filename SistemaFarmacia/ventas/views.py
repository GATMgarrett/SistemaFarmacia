from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.urls import reverse


from .models import Laboratorios, Proveedores, Medicamentos
from .forms import UsuarioForm, LaboratorioForm, ProveedorForm, MedicamentoForm, VentaForm, DetalleVentaForm

# Vamos a llamar a Usuario y producto


# Create your views here.
# Aqui van la creacion de las vistas

# Vista de las ventas
def ventas_view(request):
    num_ventas = 156 #esto solo es un dato que estamos enviando a num ventas
    context = {
        'num_ventas': num_ventas
    }
    return render(request, 'ventas.html', context)

# Vista de las compras
def compras_view(request):
    return render(request, 'compras.html')


#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los laboratorios
# Vista de los laboratorios
def laboratorios_view(request):
    laboratorios = Laboratorios.objects.all()
    return render(request, 'laboratorios.html', {'laboratorios': laboratorios})
# Vista para la creacion de los laboratorios
def create_laboratorios_view(request):
    formulario = LaboratorioForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Laboratorios')
    return render(request, 'laboratoriosCRUD/create_lab.html', {'formulario': formulario})
# Vista para la edicion de los laboratorios
def update_laboratorios_view(request, id):
    laboratorios = Laboratorios.objects.get(id=id)
    formulario = LaboratorioForm(request.POST or None, request.FILES or None, instance=laboratorios)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Laboratorios')
    return render(request, 'laboratoriosCRUD/create_lab.html', {'formulario': formulario})
# Vista para la eliminacion de los laboratorios
def delete_laboratorio_view(request, id):
    laboratorios = Laboratorios.objects.get(id=id)
    laboratorios.delete()
    return redirect('Laboratorios')
#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los usuarios
# Vista de los usuarios
def usuarios_view(request):
    # Usuarios activos
    usuarios_activos = User.objects.filter(is_active=True).prefetch_related('groups')
    # Usuarios inactivos
    usuarios_inactivos = User.objects.filter(is_active=False).prefetch_related('groups')
    
    return render(request, 'usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos
    })

# Vista para la creacion de los ususarios

# Vista de los usuarios
def usuarios_view(request):
    # Usuarios activos
    usuarios_activos = User.objects.filter(is_active=True).prefetch_related('groups')
    # Usuarios inactivos
    usuarios_inactivos = User.objects.filter(is_active=False).prefetch_related('groups')
    
    return render(request, 'usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos
    })

# Vista para la creación de los usuarios
def create_user_view(request):
    if request.method == 'POST':
        formulario = UsuarioForm(request.POST)
        if formulario.is_valid():
            user = formulario.save(commit=False)  # No se guarda todavía en la base de datos
            user.set_password(formulario.cleaned_data['password'])  # Usa la contraseña del formulario
            user.save()  # Guarda el usuario en la base de datos
            if formulario.cleaned_data['grupo']:
                user.groups.add(formulario.cleaned_data['grupo'])  # Asigna el grupo seleccionado
            return redirect('Usuarios')  # Redirige a la lista de usuarios o a donde necesites
    else:
        formulario = UsuarioForm()  # Crea una nueva instancia del formulario

    return render(request, 'usuariosCRUD/create_user.html', {'formulario': formulario})

# Vista para la edición de los usuarios
def update_user_view(request, id):
    usuario = User.objects.get(id=id)
    formulario = UsuarioForm(request.POST or None, request.FILES or None, instance=usuario)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Usuarios')
    return render(request, 'usuariosCRUD/update_user.html', {'formulario': formulario})

# Vista para la eliminación de los usuarios
def delete_user_view(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = False  # Desactivar el usuario en lugar de eliminarlo
    usuario.save()
    return redirect('Usuarios')

# Vista para la activación de los usuarios
def activate_user_view(request, id):
    usuario = User.objects.get(id=id)
    usuario.is_active = True  # Activar el usuario
    usuario.save()
    return redirect('Usuarios')

#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los proveedores
# Vista de los proveedores
def proveedores_view(request):
    proveedores = Proveedores.objects.all()
    return render(request, 'proveedores.html', {'proveedores': proveedores})
# Vista para la creacion de los proveedores
def create_proveedor_view(request):
    formulario = ProveedorForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Proveedores')
    return render(request, 'proveedoresCRUD/create_proveedor.html', {'formulario': formulario})
# Vista para la edicion de los proveedores
def update_proveedor_view(request, id):
    proveedores = Proveedores.objects.get(id=id)
    formulario = ProveedorForm(request.POST or None, request.FILES or None, instance=proveedores)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Proveedores')
    return render(request, 'proveedoresCRUD/update_proveedor.html', {'formulario': formulario})
# Vista para la eliminacion de los proveedores
def delete_proveedor_view(request, id):
    proveedores = Proveedores.objects.get(id=id)
    proveedores.delete()
    return redirect('Proveedores')
#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los medicamentos(inventario)
# Vista de los medicamentos
def medicamentos_view(request):
    medicamentos = Medicamentos.objects.all()
    return render(request, 'inventario.html', {'medicamentos': medicamentos})
# Vista para la creacion de los proveedores
def create_medicamento_view(request):
    formulario = MedicamentoForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Medicamentos')
    return render(request, 'inventarioCRUD/create_medicamento.html', {'formulario': formulario})
# Vista para la edicion de los proveedores
def update_medicamento_view(request, id):
    medicamentos = Medicamentos.objects.get(id=id)
    formulario = MedicamentoForm(request.POST or None, request.FILES or None, instance=medicamentos)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Medicamentos')
    return render(request, 'inventarioCRUD/update_medicamento.html', {'formulario': formulario})
# Vista para la eliminacion de los proveedores
def delete_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    medicamento.delete()
    return redirect('Medicamentos')



# Vista del dashboard
def dashboard_view(request):
    return render(request, 'dashboard.html')


###/////////////////////////////Todo esto va a ser para el login
def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('Ventas'))
        else:
            # Puedes simplemente pasar un contexto con el mensaje de error al mismo template.
            #return render(request, "registration/login.html", {"message": "Invalid credentials."})
            return render(request, "registration/login.html", {"error_message": "Usuario o contraseña incorrectos"})
        
    else:
        return render(request, "registration/login.html")
    
###/////////////////////////////////////////////////////////////////////////Esto va a ser para las vistas de ventas y detalle ventas

def registrar_venta(request):
    if request.method == 'POST':
        venta_form = VentaForm(request.POST)
        detalle_venta_formset = DetalleVentaForm(request.POST)

        if venta_form.is_valid() and detalle_venta_formset.is_valid():
            venta = venta_form.save()
            detalles = detalle_venta_formset.save(commit=False)
            for detalle in detalles:
                detalle.venta = venta
                detalle.save()
                # Actualiza el stock del medicamento
                medicamento = detalle.medicamento
                medicamento.stock -= detalle.cantidad
                medicamento.save()
            return redirect('alguna_url_después_de_registro')
    else:
        venta_form = VentaForm()
        detalle_venta_formset = DetalleVentaForm()
    return render(request, 'ventasCRUD/create_venta.html', {
        'venta_form': venta_form,
        'detalle_venta_formset': detalle_venta_formset
    })