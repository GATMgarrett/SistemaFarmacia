from firebase_admin import credentials, firestore, initialize_app

# Inicializar Firebase
cred = credentials.Certificate('C:\\ProyectoGrado\\sistemafarmacia-87e60-firebase-adminsdk-ar1j6-480ea9d19a.json')
initialize_app(cred)

def generar_datos_medicamentos_proximos_a_vencer():
    # Genera los datos (puedes ajustar esto según tu lógica actual)
    return [
        {"medicamento": "Paracetamol", "cantidad": 10, "fecha_vencimiento": "2024-12-15"},
        {"medicamento": "Ibuprofeno", "cantidad": 20, "fecha_vencimiento": "2024-12-20"}
    ]

def enviar_medicamentos_a_firestore():
    datos = generar_datos_medicamentos_proximos_a_vencer()

    db = firestore.client()
    doc_ref = db.collection("medicamentos_vencer").document("lista")

    try:
        doc_ref.set({"medicamentos": datos})
        print("Datos subidos a Firestore con éxito")
    except Exception as e:
        print("Error al subir datos a Firestore:", e)

# Llamar la función
enviar_medicamentos_a_firestore()
