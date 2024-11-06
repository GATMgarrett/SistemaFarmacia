from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import date
from django.views.decorators.http import require_POST


from .models import Laboratorios, Proveedores, Medicamentos, Ventas, DetalleVenta
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
    laboratorios_activos = Laboratorios.objects.filter(activo=True)
    laboratorios_inactivos = Laboratorios.objects.filter(activo=False)
    return render(request, 'laboratorios.html', {
        'laboratorios_activos': laboratorios_activos,
        'laboratorios_inactivos': laboratorios_inactivos
    })
# Vista para la creación de laboratorios
def create_laboratorio_view(request):
    formulario = LaboratorioForm(request.POST or None)
    if formulario.is_valid():
        laboratorio = formulario.save(commit=False)  # Guarda el formulario sin guardar en la base de datos aún
        laboratorio.activo = True  # Establece activo como True por defecto
        laboratorio.save()  # Ahora guarda en la base de datos
        return redirect('ListaLaboratorios')  # Cambia esta URL según tu configuración
    return render(request, 'laboratoriosCRUD/create_laboratorio.html', {'formulario': formulario})
# Vista para la edición de laboratorios
def update_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    formulario = LaboratorioForm(request.POST or None, request.FILES or None, instance=laboratorio)
    if formulario.is_valid():
        formulario.save()
        return redirect('Laboratorios')
    return render(request, 'laboratoriosCRUD/update_laboratorio.html', {'formulario': formulario})
# Vista para la eliminación lógica de laboratorios
def delete_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    laboratorio.activo = False
    laboratorio.save()
    return redirect('Laboratorios')
# Vista para reactivar laboratorios inactivos
def activate_laboratorio_view(request, id):
    laboratorio = get_object_or_404(Laboratorios, id=id)
    laboratorio.activo = True
    laboratorio.save()
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
    proveedores_activos = Proveedores.objects.filter(activo=True)
    proveedores_inactivos = Proveedores.objects.filter(activo=False)
    return render(request, 'proveedores.html', {
        'proveedores_activos': proveedores_activos,
        'proveedores_inactivos': proveedores_inactivos
    })
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
# Vista para la eliminación lógica de proveedores
def delete_proveedor_view(request, id):
    proveedor = Proveedores.objects.get(id=id)
    proveedor.activo = False  # Establece el proveedor como inactivo
    proveedor.save()
    return redirect('Proveedores')
#///////////////////////////////////////////////////////////////Toda esta parte sera solo para los medicamentos(inventario)
# Vista de los medicamentos
def medicamentos_view(request):
    # Medicamentos activos
    medicamentos_activos = Medicamentos.objects.filter(activo=True)
    # Medicamentos inactivos
    medicamentos_inactivos = Medicamentos.objects.filter(activo=False)
    
    return render(request, 'inventario.html', {
        'medicamentos_activos': medicamentos_activos,
        'medicamentos_inactivos': medicamentos_inactivos
    })
# Vista para la creación de medicamentos
def create_medicamento_view(request):
    formulario = MedicamentoForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('Medicamentos')  # Cambia según tu URL de lista
    return render(request, 'inventarioCRUD/create_medicamento.html', {'formulario': formulario})
# Vista para la edición de medicamentos
def update_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    formulario = MedicamentoForm(request.POST or None, request.FILES or None, instance=medicamento)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('Medicamentos')  # Cambia según tu URL de lista
    return render(request, 'inventarioCRUD/update_medicamento.html', {'formulario': formulario})
# Vista para la eliminación lógica de medicamentos
def delete_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    medicamento.activo = False  # Establecer como inactivo
    medicamento.save()
    return redirect('Medicamentos')  # Cambia según tu URL de lista
# Vista para la activación de medicamentos (si deseas restaurarlos)
def activate_medicamento_view(request, id):
    medicamento = Medicamentos.objects.get(id=id)
    medicamento.activo = True  # Activar el medicamento
    medicamento.save()
    return redirect('Medicamentos')  # Cambia según tu URL de lista



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

def create_venta_view(request):
    # Obtener todos los medicamentos disponibles (activos)
    medicamentos = Medicamentos.objects.filter(activo=True)

    # Obtener el carrito actual de la sesión
    carrito = request.session.get('carrito', [])
    productos_carrito = []
    total_carrito = 0

    for item in carrito:
        medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
        cantidad = item['cantidad']
        subtotal = medicamento.precio * cantidad
        productos_carrito.append({
            'medicamento': medicamento,
            'cantidad': cantidad,
            'subtotal': subtotal
        })
        total_carrito += subtotal

    # Si se ha enviado el formulario para confirmar la venta
    if request.method == 'POST':
        venta = Ventas.objects.create(
            usuario=request.user,
            fecha_venta=date.today(),
            precio_total=total_carrito
        )

        # Guardar cada detalle del carrito en `DetalleVenta`
        for item in carrito:
            medicamento = get_object_or_404(Medicamentos, id=item['medicamento_id'])
            DetalleVenta.objects.create(
                venta=venta,
                medicamento=medicamento,
                precio=medicamento.precio,
                cantidad=item['cantidad']
            )

        # Limpiar el carrito después de realizar la venta
        request.session['carrito'] = []
        return redirect('Ventas')

    return render(request, 'ventasCRUD/create_venta.html', {
        'medicamentos': medicamentos,
        'productos_carrito': productos_carrito,
        'total_carrito': total_carrito
    })

@require_POST
def add_to_cart(request, medicamento_id):
    cantidad = int(request.POST.get('cantidad', 1))
    carrito = request.session.get('carrito', [])
    
    # Agregar el medicamento al carrito o actualizar la cantidad
    for item in carrito:
        if item['medicamento_id'] == medicamento_id:
            item['cantidad'] += cantidad
            break
    else:
        carrito.append({'medicamento_id': medicamento_id, 'cantidad': cantidad})
    
    request.session['carrito'] = carrito
    return redirect('CreateVenta')