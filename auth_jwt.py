import jwt
import datetime
import json
import os
import streamlit as st
from typing import Optional, Dict, Any
import uuid

# Clave secreta para JWT (en producción debería estar en variables de entorno)
JWT_SECRET = os.getenv('JWT_SECRET', 'zero_ai_secret_key_2024')
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRY_HOURS = 1

# Archivo para almacenar tokens activos
TOKENS_FILE = 'active_tokens.json'
USUARIOS_FILE = 'usuarios.json'

class JWTAuth:
    @staticmethod
    def load_active_tokens() -> Dict[str, Any]:
        """Carga los tokens activos desde el archivo"""
        if not os.path.exists(TOKENS_FILE):
            return {}
        try:
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    @staticmethod
    def save_active_tokens(tokens: Dict[str, Any]):
        """Guarda los tokens activos en el archivo"""
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=4)
    
    @staticmethod
    def load_usuarios() -> Dict[str, Any]:
        """Carga usuarios desde el archivo"""
        if not os.path.exists(USUARIOS_FILE):
            return {}
        with open(USUARIOS_FILE, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def generate_token(usuario: str, rol: str, device_id: Optional[str] = None) -> str:
        """Genera un token JWT para el usuario"""
        if not device_id:
            device_id = str(uuid.uuid4())
        
        payload = {
            'usuario': usuario,
            'rol': rol,
            'device_id': device_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
            'iat': datetime.datetime.utcnow(),
            'jti': str(uuid.uuid4())  # JWT ID único
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Guardar token activo
        active_tokens = JWTAuth.load_active_tokens()
        if usuario not in active_tokens:
            active_tokens[usuario] = {}
        
        active_tokens[usuario][device_id] = {
            'token': token,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'expires_at': (datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
        }
        
        JWTAuth.save_active_tokens(active_tokens)
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verifica y decodifica un token JWT"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Verificar si el token está en la lista de tokens activos
            active_tokens = JWTAuth.load_active_tokens()
            usuario = payload.get('usuario')
            device_id = payload.get('device_id')
            
            if usuario in active_tokens and device_id in active_tokens[usuario]:
                stored_token = active_tokens[usuario][device_id]['token']
                if stored_token == token:
                    return payload
            
            return None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def invalidate_token(usuario: str, device_id: str):
        """Invalida un token específico"""
        active_tokens = JWTAuth.load_active_tokens()
        if usuario in active_tokens and device_id in active_tokens[usuario]:
            del active_tokens[usuario][device_id]
            if not active_tokens[usuario]:  # Si no quedan tokens para el usuario
                del active_tokens[usuario]
            JWTAuth.save_active_tokens(active_tokens)
    
    @staticmethod
    def invalidate_all_user_tokens(usuario: str):
        """Invalida todos los tokens de un usuario (para logout completo)"""
        active_tokens = JWTAuth.load_active_tokens()
        if usuario in active_tokens:
            del active_tokens[usuario]
            JWTAuth.save_active_tokens(active_tokens)
    
    @staticmethod
    def cleanup_expired_tokens():
        """Limpia tokens expirados"""
        active_tokens = JWTAuth.load_active_tokens()
        current_time = datetime.datetime.utcnow()
        
        users_to_remove = []
        for usuario, devices in active_tokens.items():
            devices_to_remove = []
            for device_id, token_data in devices.items():
                expires_at = datetime.datetime.fromisoformat(token_data['expires_at'])
                if current_time > expires_at:
                    devices_to_remove.append(device_id)
            
            for device_id in devices_to_remove:
                del devices[device_id]
            
            if not devices:
                users_to_remove.append(usuario)
        
        for usuario in users_to_remove:
            del active_tokens[usuario]
        
        JWTAuth.save_active_tokens(active_tokens)
    
    @staticmethod
    def authenticate_user(usuario: str, clave: str) -> Optional[Dict[str, Any]]:
        """Autentica un usuario con credenciales"""
        usuarios = JWTAuth.load_usuarios()
        if usuario in usuarios and usuarios[usuario]['clave'] == clave:
            return usuarios[usuario]
        return None
    
    @staticmethod
    def authenticate_nfc(uid: str) -> Optional[tuple]:
        """Autentica un usuario con NFC"""
        usuarios = JWTAuth.load_usuarios()
        for usuario, datos in usuarios.items():
            if datos.get('nfc_uid') == uid:
                return usuario, datos
        return None
    
    @staticmethod
    def get_device_id() -> str:
        """Obtiene o genera un ID único para el dispositivo/navegador"""
        if 'device_id' not in st.session_state:
            st.session_state.device_id = str(uuid.uuid4())
        return st.session_state.device_id
    
    @staticmethod
    def is_authenticated() -> bool:
        """Verifica si el usuario actual está autenticado"""
        if 'jwt_token' not in st.session_state:
            return False
        
        token = st.session_state.jwt_token
        payload = JWTAuth.verify_token(token)
        
        if payload:
            # Actualizar información de sesión
            st.session_state.usuario = payload['usuario']
            st.session_state.rol = payload['rol']
            st.session_state.device_id = payload['device_id']
            return True
        else:
            # Token inválido, limpiar sesión
            JWTAuth.clear_session()
            return False
    
    @staticmethod
    def clear_session():
        """Limpia la sesión actual"""
        keys_to_remove = ['jwt_token', 'usuario', 'rol', 'autenticado']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    @staticmethod
    def login_user(usuario: str, rol: str) -> str:
        """Inicia sesión de un usuario y retorna el token"""
        device_id = JWTAuth.get_device_id()
        token = JWTAuth.generate_token(usuario, rol, device_id)
        
        # Configurar sesión
        st.session_state.jwt_token = token
        st.session_state.usuario = usuario
        st.session_state.rol = rol
        st.session_state.autenticado = True
        st.session_state.device_id = device_id
        
        return token
    
    @staticmethod
    def logout_user():
        """Cierra sesión del usuario actual"""
        if 'usuario' in st.session_state and 'device_id' in st.session_state:
            JWTAuth.invalidate_token(st.session_state.usuario, st.session_state.device_id)
        JWTAuth.clear_session()

# Función de middleware para verificar autenticación
def require_auth():
    """Middleware que requiere autenticación JWT"""
    JWTAuth.cleanup_expired_tokens()  # Limpiar tokens expirados
    
    if not JWTAuth.is_authenticated():
        return False
    return True