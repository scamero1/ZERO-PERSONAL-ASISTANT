import json
import os
from flask import session

RUTA_USUARIOS = "usuarios.json"

# Cargar usuarios
def cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):
        return {}
    try:
        with open(RUTA_USUARIOS, "r") as f:
            return json.load(f)
    except:
        return {}

# Guardar usuarios
def guardar_usuarios(usuarios):
    try:
        with open(RUTA_USUARIOS, "w") as f:
            json.dump(usuarios, f, indent=4)
        return True
    except:
        return False

# Verificar login
def verificar_login(usuario, clave):
    usuarios = cargar_usuarios()
    if usuario in usuarios and usuarios[usuario]["clave"] == clave:
        return True
    return False

# Cerrar sesión
def logout():
    session.clear()

# Registrar usuario
def registrar_usuario(usuario, clave, rol="usuario", nfc_uid=None):
    usuarios = cargar_usuarios()
    if usuario in usuarios:
        return False, "El usuario ya existe"
    
    usuarios[usuario] = {
        "clave": clave,
        "rol": rol,
        "nfc_uid": nfc_uid
    }
    
    if guardar_usuarios(usuarios):
        return True, "Usuario registrado correctamente"
    else:
        return False, "Error al guardar el usuario"