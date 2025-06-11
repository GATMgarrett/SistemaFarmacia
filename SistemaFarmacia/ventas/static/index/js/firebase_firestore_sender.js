// firebase_firestore_sender.js

// Importa las funciones que necesitas de los SDKs de Firebase
// initializeApp para inicializar la app principal
// getFirestore para obtener la instancia de Firestore
// collection, addDoc, doc, setDoc, getDoc para trabajar con colecciones y documentos
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.2/firebase-app.js";
// Si usas Analytics, descomenta la siguiente línea:
// import { getAnalytics } from "https://www.gstatic.com/firebasejs/11.0.2/firebase-analytics.js";
import { getFirestore, collection, addDoc, doc, setDoc, getDoc, getDocs, query, where } from "https://www.gstatic.com/firebasejs/11.0.2/firebase-firestore.js";

// --- Tu configuración de Firebase ---
// Copia y pega ESTO EXACTAMENTE desde la configuración de tu app web en la consola
const firebaseConfig = {
  apiKey: "AIzaSyAO-jbPHYiHU2wEmDPDgAjnsl5YCz-AIGg",
  authDomain: "sistemafarmacia-87e60.firebaseapp.com",
  projectId: "sistemafarmacia-87e60",
  storageBucket: "sistemafarmacia-87e60.firebasestorage.app",
  messagingSenderId: "33840948655",
  appId: "1:33840948655:web:ac0941dd49a8f11275bb5a", // ¡Este es el ID de tu app web!
  // Si usas Analytics, asegúrate de que measurementId esté aquí:
  measurementId: "G-Z3D6KR6JQQ"
};

// --- Inicializa Firebase ---
// Esto debe llamarse UNA VEZ cuando tu script se carga
const app = initializeApp(firebaseConfig);

// Si usas Analytics, inicialízalo aquí:
// const analytics = getAnalytics(app);
// console.log("Firebase Analytics inicializado (si está configurado)");


// --- Obtén la instancia de Firestore ---
// Esta instancia 'db' es la que usarás para interactuar con tu base de datos
const db = getFirestore(app);
console.log("Firebase Firestore inicializado y listo para usar."); // Puedes verificar esto en la consola del navegador

// Variable para controlar si ya se enviaron los datos en esta sesión
let datosEnviados = false;


// --- Función para enviar o actualizar datos a Firestore ---
// Esta función usa setDoc con un ID específico para evitar duplicaciones
// 'collectionName' es el nombre de la colección donde quieres guardar los datos
// 'data' es un objeto JavaScript con los datos del documento
// 'documentId' es un ID único para el documento (para evitar duplicados)
export async function sendOrUpdateFirestore(collectionName, data, documentId) {
  if (!collectionName || typeof data !== 'object' || data === null || !documentId) {
    console.error("Error: Parámetros inválidos para enviar a Firestore.");
    return null; // Retorna null si hay error
  }

  console.log(`Intentando enviar/actualizar documento con ID '${documentId}' en la colección '${collectionName}'...`);

  try {
    // Crear una referencia al documento con el ID específico
    const docRef = doc(db, collectionName, documentId);
    
    // Añadir un timestamp para saber cuándo se actualizó por última vez
    data.ultima_actualizacion = new Date();
    
    // Usar setDoc para crear o actualizar el documento
    await setDoc(docRef, data, { merge: true });

    console.log(`Documento con ID ${documentId} guardado/actualizado con éxito.`);
    return documentId;

  } catch (e) {
    console.error("Error al guardar/actualizar documento en Firestore: ", e);
    throw e;
  }
}

// Función original de envío (mantenida para compatibilidad)
export async function sendDataToFirestore(collectionName, data) {
  if (!collectionName || typeof data !== 'object' || data === null) {
    console.error("Error: Nombre de colección o datos inválidos para enviar a Firestore.");
    return null; // Retorna null si hay error
  }

  console.log(`Intentando añadir documento a la colección '${collectionName}'...`);

  try {
    // Añade un nuevo documento a la colección especificada.
    // Firestore generará automáticamente un ID único para este documento.
    const docRef = await addDoc(collection(db, collectionName), data);

    console.log("Documento escrito con ID: ", docRef.id);
    return docRef.id; // Retorna el ID del documento creado

  } catch (e) {
    console.error("Error al añadir documento a Firestore: ", e);
    // Puedes relanzar el error o manejarlo según necesites
    throw e;
  }
}

// --- Función para extraer datos de la tabla de medicamentos próximos a vencer ---
export function extraerMedicamentosProximosVencer() {
  // Verificar si la tabla existe
  const tabla = document.querySelector('table.table-hover.table-striped');
  if (!tabla) {
    console.log('Tabla de medicamentos próximos a vencer no encontrada');
    return [];
  }

  console.log('Extrayendo datos de medicamentos próximos a vencer...');
  const medicamentosProximos = [];
  const filas = tabla.querySelectorAll('tbody tr');

  filas.forEach(fila => {
    const celdas = fila.querySelectorAll('td');
    if (celdas.length >= 6) {
      const medicamento = celdas[0].textContent.trim();
      let cantidad = celdas[1].textContent.trim();
      cantidad = parseInt(cantidad.replace(/[^0-9]/g, '')) || 0;
      const fechaVencimiento = celdas[2].textContent.trim();
      const diasRestantes = celdas[3].textContent.trim();
      const loteId = celdas[4].textContent.trim();
      const loteFabricante = celdas[5].textContent.trim();

      medicamentosProximos.push({
        medicamento,
        cantidad,
        fecha_vencimiento: fechaVencimiento,
        dias_restantes: parseInt(diasRestantes.replace(/[^0-9]/g, '')) || 0,
        lote_id: loteId,
        lote_fabricante: loteFabricante,
        tipo: 'proximo_vencer'
      });
    }
  });

  console.log(`Se extrajeron ${medicamentosProximos.length} medicamentos próximos a vencer`);
  return medicamentosProximos;
}

// --- Función para extraer datos de medicamentos con diferencia stock-demanda ---
export function extraerMedicamentosDiferenciaStock() {
  // Buscar la tabla en dashboard_predicciones.html
  const tabla = document.querySelector('.card-header.bg-warning + .card-body .table');
  if (!tabla) {
    console.log('Tabla de medicamentos con diferencia stock-demanda no encontrada');
    return [];
  }

  console.log('Extrayendo medicamentos con mayor diferencia stock-demanda...');
  const medicamentosDiferencia = [];
  const filas = tabla.querySelectorAll('tbody tr');

  filas.forEach(fila => {
    const celdas = fila.querySelectorAll('td');
    if (celdas.length >= 6) {
      try {
        const posicion = celdas[0].textContent.trim();
        const medicamento = celdas[1].textContent.trim();
        const stockActual = parseInt(celdas[2].textContent.trim().replace(/[^0-9]/g, '')) || 0;
        const demandaEstimada = parseInt(celdas[3].textContent.trim().replace(/[^0-9]/g, '')) || 0;
        const promedioMensual = parseInt(celdas[4].textContent.trim().replace(/[^0-9]/g, '')) || 0;
        const diferencia = parseInt(celdas[5].textContent.trim().replace(/[^0-9]/g, '')) || 0;

        medicamentosDiferencia.push({
          posicion: parseInt(posicion) || 0,
          medicamento,
          stock_actual: stockActual,
          demanda_estimada: demandaEstimada,
          promedio_mensual: promedioMensual,
          diferencia,
          tipo: 'diferencia_stock_demanda'
        });
      } catch (e) {
        console.error('Error al procesar una fila:', e);
      }
    }
  });

  console.log(`Se extrajeron ${medicamentosDiferencia.length} medicamentos con diferencia stock-demanda`);
  return medicamentosDiferencia;
}

// --- Función para extraer datos de usuarios del sistema ---
export function extraerDatosUsuarios() {
  // Intentaremos extraer datos de usuarios de diferentes maneras:
  // 1. De la navegación donde suele aparecer el nombre del usuario
  // 2. De elementos que tengan clases o IDs relacionadas con usuarios
  
  console.log('Intentando extraer datos de usuarios...');
  
  const datosUsuarios = [];
  let username = '';
  let email = '';
  let rol = '';
  
  // Intentar obtener el nombre de usuario del menú de navegación
  const navbarDropdown = document.querySelector('#navbarDropdown');
  if (navbarDropdown) {
    username = navbarDropdown.textContent.trim();
    console.log('Nombre de usuario encontrado en navbar:', username);
  }
  
  // Intentar obtener correo de algún elemento que lo contenga
  const emailElements = [...document.querySelectorAll('*')]
    .filter(el => el.textContent && el.textContent.includes('@') && el.textContent.includes('.'));
  
  if (emailElements.length > 0) {
    // Tomar el primer elemento que parece contener un email
    const emailText = emailElements[0].textContent.trim();
    // Extraer el email usando regex básica
    const emailMatch = emailText.match(/[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}/g);
    if (emailMatch && emailMatch.length > 0) {
      email = emailMatch[0];
      console.log('Email encontrado:', email);
    }
  }
  
  // Si no encontramos email pero tenemos username, podemos construir uno ficticio
  if (!email && username) {
    email = `${username.toLowerCase().replace(/\s+/g, '.')}@farmacia.com`;
    console.log('Email construido:', email);
  }
  
  // Intentar determinar el rol del usuario
  if (document.querySelector('.admin-indicator')) {
    rol = 'Administrador';
  } else if (document.querySelector('.staff-indicator')) {
    rol = 'Staff';
  } else {
    rol = 'Usuario';
  }
  
  // Si tenemos al menos un nombre de usuario, crear el registro
  if (username) {
    datosUsuarios.push({
      username: username,
      email: email,
      rol: rol,
      ultima_actividad: new Date(),
      activo: true
    });
  }
  
  console.log(`Se encontraron datos de ${datosUsuarios.length} usuarios`);
  return datosUsuarios;
}

// --- Función principal para enviar todos los datos ---
export async function enviarDatosTablasAFirestore() {
  // Evitar múltiples envíos simultáneos
  if (window.enviandoDatos) {
    alert('Ya hay un proceso de sincronización en curso. Por favor espere...');
    return;
  }
  
  window.enviandoDatos = true;
  console.log('Iniciando proceso de envío de datos a Firebase...');
  
  try {
    // Mostrar alerta de inicio
    alert('Iniciando sincronización con Firebase...');
    
    // 1. Extraer datos de las tablas y usuarios
    const medicamentosVencer = extraerMedicamentosProximosVencer();
    const medicamentosDiferencia = extraerMedicamentosDiferenciaStock();
    const datosUsuarios = extraerDatosUsuarios();
    
    // Contador para seguimiento
    let documentosEnviados = 0;
    
    // 2. Enviar datos de medicamentos próximos a vencer
    for (const med of medicamentosVencer) {
      const docId = `vencimiento_${med.lote_id || 'sin_lote'}_${med.medicamento.replace(/\s+/g, '_').toLowerCase()}`;
      await sendOrUpdateFirestore('medicamentos_proximos_vencer', med, docId);
      documentosEnviados++;
    }
    
    // 3. Enviar datos de medicamentos con diferencia stock-demanda
    for (const med of medicamentosDiferencia) {
      const docId = `diferencia_${med.medicamento.replace(/\s+/g, '_').toLowerCase()}`;
      await sendOrUpdateFirestore('medicamentos_diferencia_stock', med, docId);
      documentosEnviados++;
    }
    
    // 4. Enviar datos de usuarios
    for (const user of datosUsuarios) {
      const docId = `user_${user.username.replace(/\s+/g, '_').toLowerCase()}`;
      await sendOrUpdateFirestore('usuarios', user, docId);
      documentosEnviados++;
    }
    
    // Si no hay usuario logueado actualmente, enviar al menos un registro de usuario de muestra
    if (datosUsuarios.length === 0) {
      const usuarioMuestra = {
        username: 'Usuario Farmacia',
        email: 'usuario@farmacia.com',
        rol: 'Demostración',
        ultima_actividad: new Date(),
        activo: true
      };
      await sendOrUpdateFirestore('usuarios', usuarioMuestra, 'user_demo');
      documentosEnviados++;
    }
    
    console.log(`✅ Se sincronizaron ${documentosEnviados} documentos con Firebase Firestore`);
    
    // Mostrar mensaje de éxito al usuario
    alert(`¡Sincronización exitosa! Se enviaron ${documentosEnviados} registros a Firebase.`);
    
  } catch (error) {
    console.error('Error al enviar datos a Firestore:', error);
    alert('Error al sincronizar: ' + error.message);
  } finally {
    window.enviandoDatos = false;
  }
}

// --- Función para mostrar un mensaje de éxito al usuario ---
function mostrarMensajeExito() {
  // Crear un elemento de alerta
  const alerta = document.createElement('div');
  alerta.className = 'alert alert-success alert-dismissible fade show position-fixed';
  alerta.style.top = '20px';
  alerta.style.right = '20px';
  alerta.style.zIndex = '9999';
  alerta.role = 'alert';
  alerta.innerHTML = `
    <strong>¡Éxito!</strong> Los datos han sido sincronizados con la aplicación móvil.
    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>
  `;
  
  // Añadir al DOM
  document.body.appendChild(alerta);
  
  // Eliminar después de 5 segundos
  setTimeout(() => {
    $(alerta).alert('close');
  }, 5000);
}

// --- Añadir botón de sincronización al DOM ---
export function agregarBotonSincronizacion() {
  console.log('Intentando agregar botón de sincronización...');
  
  // Esperar a que el DOM esté completamente cargado
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', realizarAgregarBoton);
  } else {
    realizarAgregarBoton();
  }
}

// Función auxiliar para agregar el botón
function realizarAgregarBoton() {
  // Verificar si ya existe el botón
  if (document.getElementById('btn-sincronizar-firebase')) {
    console.log('El botón ya existe, no se creará otro');
    return;
  }
  
  // Determinar en qué pantalla estamos
  const esPantallaInventario = window.location.href.includes('dashboard_inventario');
  const esPantallaPredicciones = window.location.href.includes('dashboard_predicciones');
  
  if (!esPantallaInventario && !esPantallaPredicciones) {
    console.log('No estamos en una pantalla de dashboard relevante para la sincronización');
    return;
  }
  
  console.log('Estamos en una pantalla de dashboard relevante, buscando donde colocar el botón...');
  
  // Buscar donde colocar el botón (diferentes opciones por si cambia la estructura HTML)
  let contenedor = document.querySelector('#refreshData')?.parentNode;
  
  if (!contenedor) {
    // Segunda opción: buscar el encabezado del card principal
    contenedor = document.querySelector('.card-header');
  }
  
  if (contenedor) {
    console.log('Contenedor encontrado, creando botón...');
    
    // Crear el botón
    const boton = document.createElement('button');
    boton.id = 'btn-sincronizar-firebase';
    boton.className = 'btn btn-primary btn-sm ml-2';
    boton.style.marginLeft = '10px';
    boton.innerHTML = '<i class="fas fa-sync"></i> Sincronizar con App';
    boton.onclick = function() {
      // Mostrar mensaje al usuario
      alert('Sincronizando datos con Firebase para la app móvil...');
      // Ejecutar la función de sincronización
      enviarDatosTablasAFirestore();
    };
    
    // Añadir el botón al DOM
    contenedor.appendChild(boton);
    console.log('✅ Botón de sincronización añadido exitosamente');
  } else {
    console.error('❌ No se encontró un lugar adecuado para colocar el botón de sincronización');
  }
}

// --- Verificar y ejecutar cuando el DOM está listo ---
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM cargado, configurando Firebase Firestore Sender...');
  
  // Agregar botón de sincronización al DOM
  setTimeout(agregarBotonSincronizacion, 1000); // Pequeño retardo para asegurar que el DOM esté listo
});
