import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import speech_recognition as sr
import av
import numpy as np
import queue
from PIL import Image
import time
from Login import verificar_login, logout, registrar_usuario
from base64 import b64encode
import os
from twilio.rest import Client
import uuid
from dotenv import load_dotenv
import requests
import json
import io
import re
from datetime import datetime

# Añadidos para enviar emails
import smtplib
from email.message import EmailMessage

from database import ZeroDatabase
from file_processor import FileProcessor

db = ZeroDatabase()

# Load environment variables
load_dotenv()

# Email por defecto para PQRS (puede sobrescribirse con la variable de entorno PQRS_EMAIL)
PQRS_DEFAULT_EMAIL = os.getenv("PQRS_EMAIL", "soporte@zero-va.com")

# Get API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY no encontrada en las variables de entorno")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

BASE_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}
STREAM_HEADERS = {
    **BASE_HEADERS,
    "Accept": "text/event-stream",
}

def safe_text(text: str) -> str:
    """Repara textos con problemas de encoding"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text

# --- INICIALIZACIÓN DE ESTADO ---
def initialize_session_state():
    default_states = {
        "autenticado": False,
        "usuario": None,
        "rol": None,
        "user_id": None,
        "messages": [],
        "thinking": False,
        "current_chat": str(uuid.uuid4()),
        "user_files": [],
        "user_context": [],
        "sidebar_collapsed": False
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# --- DISEÑO ZERO MEJORADO ---
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        /* Valores por defecto (modo oscuro) */
        :root {
            --primary-bg: #0a0a0a;
            --secondary-bg: #111111;
            --sidebar-bg: #1a1a1a;
            --card-bg: #222222;
            --accent-primary: #8b5cf6;
            --accent-secondary: #a78bfa;
            --accent-gradient: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
            --text-primary: #ffffff;
            --text-secondary: #e2e8f0;
            --text-muted: #94a3b8;
            --border-color: #2d3748;
            --border-light: #374151;
            --user-msg-bg: #1e293b;
            --assistant-msg-bg: #1a1a1a;
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.4);
            --shadow-md: 0 8px 25px rgba(0, 0, 0, 0.5);
            --shadow-lg: 0 15px 40px rgba(0, 0, 0, 0.6);
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }

        /* Modo claro: sobreescribe variables cuando el sistema lo prefiera */
        @media (prefers-color-scheme: light) {
            :root {
                --primary-bg: #f8fafc;
                --secondary-bg: #ffffff;
                --sidebar-bg: #f3f4f6;
                --card-bg: #ffffff;
                --accent-primary: #6d28d9;
                --accent-secondary: #7c3aed;
                --accent-gradient: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%);
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --text-muted: #6b7280;
                --border-color: #e5e7eb;
                --border-light: #e6e9ef;
                --user-msg-bg: #e6eef8;
                --assistant-msg-bg: #f8fafc;
                --shadow-sm: 0 1px 3px rgba(15,23,42,0.06);
                --shadow-md: 0 4px 12px rgba(15,23,42,0.06);
                --shadow-lg: 0 10px 30px rgba(15,23,42,0.08);
                --success: #059669;
                --warning: #d97706;
                --error: #dc2626;
            }

            /* Ajustes secundarios para modo claro */
            .stApp {
                color: var(--text-primary);
            }
            .css-1d391kg, .css-1lcbmhc {
                background: var(--sidebar-bg) !important;
                border-right: 1px solid var(--border-color);
            }
            .stButton > button {
                color: white;
            }
        }

        .stApp {
            background: var(--primary-bg);
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        /* Sidebar elegante */
        .css-1d391kg, .css-1lcbmhc {
            background: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color);
        }

        .sidebar-header {
            padding: 2rem 1.5rem 1.5rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }

        /* Reducir espacio del header y del gap interno para acercarlo al contenido siguiente */
        .main-header {
            background: var(--secondary-bg);
            padding: 0.6rem 1.2rem;   /* menos padding vertical */
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 0.2rem;    /* pequeño espacio entre header y chat */
        }
        .main-header > div {
            display: flex;
            align-items: center;
            gap: 0.5rem;              /* gap más pequeño entre icono y texto */
        }

        /* Acercar el chat-container al header */
        .chat-container {
            background: var(--primary-bg);
            margin-top: 0;                        /* asegurar sin margen extra */
            min-height: calc(100vh - 72px);      /* ajustar cálculo para nuevo header */
            padding: 0;
        }

        /* Botones morados */
        .stButton > button {
            border-radius: 12px;
            padding: 0.875rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
            background: var(--accent-gradient);
            color: white;
            font-size: 0.9rem;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        .new-chat-btn {
            width: 100%;
            margin-bottom: 2rem;
            background: var(--accent-gradient) !important;
            border: none !important;
            font-weight: 600 !important;
        }

        .secondary-btn {
            background: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 2px solid var(--border-color) !important;
        }

        .secondary-btn:hover {
            border-color: var(--accent-primary) !important;
            transform: translateY(-2px) !important;
        }

        /* Lista de chats */
        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .chat-item {
            padding: 1rem;
            border-radius: 12px;
            background: transparent;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.875rem;
        }

        .user-message {{
            background-color: var(--user-bg);
            color: var(--user-text);
            padding: 0.8rem 1.2rem;
            border-radius: 18px 18px 4px 18px;
            max-width: 85%;
            align-self: flex-end;
            word-wrap: break-word;
            text-align: left;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-left: auto;
        }}

        .chat-title {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }

        .chat-preview {
            font-size: 0.75rem;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Archivos en sidebar */
        .file-item {
            padding: 0.75rem;
            border-radius: 8px;
            background: transparent;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
        }

        .file-item:hover {
            background: rgba(139, 92, 246, 0.1);
            border-color: var(--accent-primary);
        }

        .file-name {
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 0.125rem;
        }

        .file-info {
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* Área principal */
        .main-header {
            background: var(--secondary-bg);
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 0;
        }

        .chat-container {
            background: var(--primary-bg);
            min-height: calc(100vh - 120px);
            padding: 0;
        }

        /* Mensajes elegantes */
        .message {
            padding: 1.5rem 2rem;
            animation: slideIn 0.4s ease;
        }

        .chat-list {{
            max-height: 40vh;
            overflow-y: auto;
            margin-bottom: 1rem;
        }}

        .chat-item {{
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
        }}

        .chat-item:hover {{
            background-color: rgba(139, 92, 246, 0.1);
            border-color: var(--purple);
        }}

        .chat-item.active {{
            background-color: var(--purple);
            color: var(--text-primary);
            border-color: var(--purple);
        }}

        .chat-preview {{
            font-size: 0.8rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--text-secondary);
        }}

        .chat-item.active .chat-preview {{
            color: rgba(255,255,255,0.8);
        }}

        /* Estilos para archivos */
        .file-item {{
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            transition: all 0.2s;
        }}

        .file-item:hover {{
            border-color: var(--purple);
            background-color: rgba(139, 92, 246, 0.05);
        }}

        .file-name {{
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }}

        .file-info {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}

        .file-actions {{
            margin-top: 0.5rem;
            display: flex;
            gap: 0.5rem;
        }}

        .file-actions button {{
            font-size: 0.8rem !important;
            padding: 0.25rem 0.5rem !important;
        }}

        @media (max-width: 768px) {{
            .sidebar .sidebar-content {{ width: 100%; }}
            .chat-container {{ max-height: 60vh; }}
            .assistant-message, .user-message {{ max-width: 90%; }}
        }}
    </style>

    <link rel="icon" href="data:image/x-icon;base64,{favicon_base64}" type="image/x-icon">
    """, unsafe_allow_html=True)

load_css()

# --- INICIALIZACIÓN DE SERVICIOS ---
# Twilio (para verificación SMS)
try:
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
except Exception as e:
    st.warning(f"No se pudo inicializar Twilio: {e}")

# --- INICIALIZACIÓN DE ESTADO ---
def initialize_session_state():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thinking" not in st.session_state:
        st.session_state.thinking = False
    
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = str(uuid.uuid4())

initialize_session_state()

# --- GROQ HELPERS ---
def _system_prompt():
    # Crear prompt personalizado basado en el contexto del usuario
    base_prompt = "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil."
    
    # Agregar contexto de archivos si existe
    if st.session_state.get("user_context"):
        context_info = "\n\nContexto personalizado del usuario:\n"
        # Últimos 5 contextos
        for ctx in st.session_state.user_context[-5:]:
            context_info += f"- {ctx['context_key']}: {ctx['context_value'][:200]}...\n"
        base_prompt += context_info
    
    return {"role": "system", "content": base_prompt}

def groq_chat_stream(history_messages, *, model=None, max_tokens=1200, temperature=0.7):
    """
    Streaming SSE con requests.iter_lines() (sin SDK extra).
    Devuelve un generador de "delta" (fragmentos de texto) como en OpenAI.
    """
    m = model or GROQ_TEXT_MODEL
    payload = {
        "model": m,
        "messages": [_system_prompt()] + history_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    try:
        with requests.post(API_URL, headers=STREAM_HEADERS, json=payload, stream=True, timeout=300) as r:
            r.raise_for_status()
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("data: "):
                    data = raw[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            # FIX ENCODING por si llega interpretado raro
                            yield safe_text(delta)
                    except Exception:
                        continue
    except requests.HTTPError as http_err:
        yield safe_text(f"⚠️ Error HTTP: {http_err}")
    except Exception as e:
        yield safe_text(f"⚠️ Error en streaming: {e}")

def groq_chat_nonstream(history_messages, *, model=None, max_tokens=1200, temperature=0.7):
    """
    Llamada normal (no streaming) al endpoint OpenAI-compatible de Groq.
    """
    m = model or GROQ_TEXT_MODEL
    payload = {
        "model": m,
        "messages": [_system_prompt()] + history_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        r = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=90)
        if r.status_code != 200:
            return safe_text(f"⚠️ Error {r.status_code}: {r.text}")
        data = r.json()
        return safe_text(data["choices"][0]["message"]["content"])
    except Exception as e:
        return safe_text(f"⚠️ Error en la conexión: {e}")

# --- FUNCIONES UTILITARIAS UI ---
def display_message(role, content):
    """Muestra un mensaje en el chat con el estilo adecuado."""
    if role == "assistant":
        clean_content = safe_text(str(content)).replace("Zero:", "").strip()
        st.markdown(
            f"<div class='message'><div class='assistant-message'>{clean_content}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='message'><div class='user-message'>{safe_text(str(content))}</div></div>",
            unsafe_allow_html=True,
        )

def save_current_chat():
    """Guarda el chat actual en el historial y DB."""
    if st.session_state.messages and st.session_state.get("usuario") and st.session_state.get("user_id"):
        first_message = st.session_state.messages[0]["content"] if st.session_state.messages else "Nuevo chat"
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        
        # Actualizar en session_state
        if st.session_state.usuario not in st.session_state.chat_history:
            st.session_state.chat_history[st.session_state.usuario] = {}
        st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
            "title": safe_text(title),
            "messages": st.session_state.messages.copy(),
        }

        # Asegurar que el chat exista en DB
        try:
            # Intentar actualizar título; si el chat no existe, crearlo
            db.update_chat_title(st.session_state.current_chat, safe_text(title))
        except Exception:
            pass
        user_chats = db.get_user_chats(st.session_state.user_id)
        if not any(c["id"] == st.session_state.current_chat for c in user_chats):
            st.session_state.current_chat = db.create_chat(st.session_state.user_id, safe_text(title))
        else:
            db.update_chat_title(st.session_state.current_chat, safe_text(title))
        
        # Guardar mensajes (nota: simple, puede duplicar si llamas muchas veces)
        for message in st.session_state.messages:
            db.add_message(
                st.session_state.current_chat,
                message["role"],
                message["content"]
            )

def load_chat(chat_id):
    """Carga un chat del historial."""
    if "usuario" in st.session_state and chat_id in st.session_state.chat_history.get(st.session_state.usuario, {}):
        st.session_state.current_chat = chat_id
        st.session_state.messages = st.session_state.chat_history[st.session_state.usuario][chat_id]["messages"].copy()
        st.rerun()

# --- SIDEBAR ZERO MEJORADO ---
def create_sidebar():
    """Crea la barra lateral con diseño Zero mejorado"""
    with st.sidebar:
        # Header del sidebar
        username = st.session_state.get('usuario') or 'Invitado'
        st.markdown(f"""
            <div class="sidebar-header">
                <div class="sidebar-title">
                    <div>⚡</div>
                    <div>ZERO</div>
                </div>
                <div class="user-info">
                    Hola, {username}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Botón nuevo chat morado
        if st.button("Nuevo Chat", key="new_chat_btn", use_container_width=True, type="primary"):
            save_current_chat()
            st.session_state.current_chat = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
        
        # Sección de chats anteriores
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Conversaciones</div>', unsafe_allow_html=True)
        
        if st.session_state.get("user_id"):
            try:
                user_chats = db.get_user_chats(st.session_state.user_id)
                if user_chats:
                    user_chats.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                    
                    for chat in user_chats[:8]:
                        is_active = chat['id'] == st.session_state.current_chat
                        title_val = chat.get('title') or "Nuevo chat"
                        preview = title_val[:25] + "..." if len(title_val) > 25 else title_val
                        
                        if st.button(
                            preview,
                            key=f"chat_{chat['id']}",
                            use_container_width=True,
                            type="primary" if is_active else "secondary"
                        ):
                            st.session_state.current_chat = chat['id']
                            chat_messages = db.get_chat_messages(chat['id'])
                            st.session_state.messages = [
                                {"role": msg['role'], "content": msg['content']}
                                for msg in chat_messages
                            ]
                            st.rerun()
                else:
                    st.info("Inicia tu primera conversación")
            except Exception as e:
                st.error("Error cargando conversaciones")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Sección de archivos
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Archivos</div>', unsafe_allow_html=True)
        
        if not st.session_state.get("user_files"):
            st.session_state.user_files = db.get_user_files(st.session_state.user_id)
        
        if st.session_state.user_files:
            for file_data in st.session_state.user_files[:4]:
                if st.button(
                    f"{file_data['filename'][:20]}...",
                    key=f"sidebar_file_{file_data['id']}",
                    use_container_width=True,
                    help=f"Usar {file_data['filename']} en el chat"
                ):
                    if file_data.get('content_extracted'):
                        content_msg = f"Archivo: {file_data['filename']}\n\n{file_data['content_extracted'][:250]}..."
                        st.session_state.messages.append({"role": "user", "content": content_msg})
                        st.success("Archivo agregado al chat")
                        st.rerun()
        else:
            st.info("Sube tu primer archivo")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navegación principal con botones morados
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Navegación</div>', unsafe_allow_html=True)
        
        if st.button("Chat con Zero", key="nav_chat", use_container_width=True, type="primary"):
            st.session_state.current_page = "chat"
            st.rerun()

        if st.button("Gestor de Archivos", key="nav_files", use_container_width=True, type="primary"):
            st.session_state.current_page = "files"
            st.rerun()

        # NUEVO: Botón PQRS
        if st.button("PQRS", key="nav_pqrs", use_container_width=True, type="primary"):
            st.session_state.current_page = "pqrs"
            st.rerun()

        if st.session_state.rol == "admin":
            if st.button("Panel Admin", key="nav_admin", use_container_width=True, type="primary"):
                st.session_state.current_page = "admin"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Footer del sidebar
        st.markdown("---")
        # Cerrar sesión en la misma pestaña (target="_self")
        st.markdown(
            '''
            <a href="https://zero-va.com/logout" target="_self"
               style="display:block;text-align:center;padding:0.875rem 1.5rem;border-radius:12px;
                      background:linear-gradient(135deg,#8b5cf6 0%,#a78bfa 100%);
                      color:white;text-decoration:none;font-weight:600;">
                Cerrar Sesión
            </a>
            ''',
            unsafe_allow_html=True
        )

# --- SISTEMA DE ARCHIVOS ---
def analyze_document_with_groq(content, filename):
    """Analiza documentos con Groq"""
    try:
        content_preview = content[:3000]
        
        prompt = f"""
        Analiza este documento '{filename}' y proporciona un análisis profesional:

        Resumen Ejecutivo
        Extrae los puntos más importantes

        Información Clave 
        Datos, cifras y información relevante

        Análisis y Perspectiva
        Interpretación y contexto

        Aplicaciones Prácticas
        Cómo usar esta información

        Contenido:
        {content_preview}
        """

        payload = {
            "model": GROQ_TEXT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.3
        }

        response = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Análisis completado para {filename}"
            
    except Exception as e:
        return f"Documento procesado: {filename}"

def analyze_image_with_groq(image_base64, filename):
    """Analiza imágenes con Groq Vision"""
    try:
        payload = {
            "model": GROQ_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analiza esta imagen '{filename}' de manera profesional:

Descripción Visual
Describe el contenido de forma detallada

Elementos Principales 
Objetos, colores, texto visible

Contexto e Interpretación
Significado y contexto posible

Detalles Destacados
Elementos notables o importantes"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        response = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Análisis visual completado para {filename}"
            
    except Exception as e:
        return f"Imagen procesada: {filename}"

def save_uploaded_file(uploaded_file):
    """Guarda y procesa archivos subidos"""
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        file_types = {
            'pdf': 'pdf', 'docx': 'word', 'doc': 'word', 'txt': 'text',
            'md': 'markdown', 'xlsx': 'excel', 'xls': 'excel', 'csv': 'csv',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image'
        }
        file_type = file_types.get(file_type, 'unknown')
        
        if file_type == 'unknown':
            return None, "Tipo de archivo no soportado"

        user_dir = f"user_uploads/{st.session_state.user_id}"
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, uploaded_file.name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        content = ""
        analysis = ""
        
        if file_type == 'image':
            image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
            analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
            content = "Imagen procesada para análisis visual"
        else:
            file_content = uploaded_file.getvalue()
            
            if file_type in ['pdf', 'word']:
                processor = FileProcessor()
                result = processor.process_file(file_content, uploaded_file.name)
                content = result.get('content', '')[:5000]
            else:
                try:
                    content = file_content.decode('utf-8')[:5000]
                except:
                    content = file_content.decode('latin-1')[:5000]
            
            if content and len(content.strip()) > 50:
                analysis = analyze_document_with_groq(content, uploaded_file.name)
            else:
                analysis = f"Documento procesado: {uploaded_file.name}"

        file_id = db.save_file(
            user_id=st.session_state.user_id,
            filename=uploaded_file.name,
            file_path=file_path,
            file_type=file_type,
            file_size=uploaded_file.size,
            content_extracted=content,
            analysis_summary=analysis[:350]
        )

        if analysis:
            context_key = f"Archivo: {uploaded_file.name}"
            db.save_user_context(st.session_state.user_id, context_key, analysis, file_id)

        return file_id, None

    except Exception as e:
        return None, f"Error procesando archivo: {str(e)}"

# --- PROCESAMIENTO DE ECUACIONES ---
def render_latex_in_message(content):
    """Convierte ecuaciones LaTeX en formato legible"""
    inline_pattern = r'\$(.*?)\$'
    block_pattern = r'\$\$(.*?)\$\$'
    
    content = re.sub(block_pattern, r'<div class="latex-formula">\1</div>', content)
    content = re.sub(inline_pattern, r'<span class="latex-formula">\1</span>', content)
    
    return content

# --- PÁGINA PRINCIPAL DEL CHAT ---
def chat_page():
    """Página principal del chat con diseño Zero"""
    
    # Header
    st.markdown("""
        <div class="main-header">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">⚡</div>
                <div>
                    <h1 style="margin: 0; color: var(--text-primary); font-weight: 800;">
                        ZERO AI
                    </h1>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">
                        Tu asistente de IA avanzado
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Contenedor del chat
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Mostrar mensajes
    if st.session_state.messages:
        for message in st.session_state.messages:
            avatar = "👤" if message["role"] == "user" else "⚡"
            bg_class = "user-message" if message["role"] == "user" else "assistant-message"
            avatar_class = "message-avatar" if message["role"] == "user" else "message-avatar assistant-avatar"
            
            content_with_math = render_latex_in_message(safe_text(message["content"]))
            
            st.markdown(f"""
                <div class="message {bg_class}">
                    <div class="message-content">
                        <div class="{avatar_class}">{avatar}</div>
                        <div class="message-text">{content_with_math}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # Mensaje de bienvenida
        st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                <div style="font-size: 6rem; margin-bottom: 2rem;">⚡</div>
                <h2 style="color: var(--text-primary); margin-bottom: 1rem; font-weight: 800;">
                    Bienvenido a ZERO
                </h2>
                <p style="margin-bottom: 3rem; line-height: 1.6; font-size: 1.1rem; color: var(--text-secondary);">
                    Asistente de IA avanzado con capacidades de análisis de documentos,<br>
                    procesamiento de imágenes y soporte para ecuaciones matemáticas.
                </p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; max-width: 800px; margin: 0 auto;">
                    <div style="background: var(--card-bg); padding: 2rem; border-radius: 16px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">💬</div>
                        <div style="font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); font-size: 1.1rem;">Chat Inteligente</div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary);">Conversaciones naturales y contextuales</div>
                    </div>
                    <div style="background: var(--card-bg); padding: 2rem; border-radius: 16px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📁</div>
                        <div style="font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); font-size: 1.1rem;">Análisis de Archivos</div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary);">Procesa documentos e imágenes</div>
                    </div>
                    <div style="background: var(--card-bg); padding: 2rem; border-radius: 16px; border: 1px solid var(--border-color); text-align: center;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">🧮</div>
                        <div style="font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); font-size: 1.1rem;">Soporte Matemático</div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary);">Ecuaciones y análisis avanzado</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input del chat
    if prompt := st.chat_input("Escribe tu mensaje..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Mostrar animación de typing
                message_placeholder.markdown("""
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--text-muted);">
                        <div style="display: flex; gap: 3px;">
                            <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent-primary); animation: bounce 1.4s infinite ease-in-out;"></div>
                            <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent-primary); animation: bounce 1.4s infinite ease-in-out 0.2s;"></div>
                            <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent-primary); animation: bounce 1.4s infinite ease-in-out 0.4s;"></div>
                        </div>
                        <div>Zero está pensando...</div>
                    </div>
                    <style>
                        @keyframes bounce {
                            0%, 80%, 100% { transform: scale(0); }
                            40% { transform: scale(1); }
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                # Pre-chequeo de clave
                if not GROQ_API_KEY:
                    full_response = "GROQ_API_KEY no configurada en el entorno de Streamlit. Verifica tu archivo .env o variables del sistema."
                    message_placeholder.markdown(full_response)
                else:
                    messages_for_api = st.session_state.messages.copy()
                    
                    payload = {
                        "model": GROQ_TEXT_MODEL,
                        "messages": messages_for_api,
                        "stream": True,
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                    
                    response = requests.post(API_URL, headers=STREAM_HEADERS, json=payload, stream=True, timeout=120)
                    
                    if response.status_code == 200:
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith('data: '):
                                    data = line[6:]
                                    if data.strip() == '[DONE]':
                                        break
                                    try:
                                        json_data = json.loads(data)
                                        if 'choices' in json_data and json_data['choices']:
                                            delta = json_data['choices'][0].get('delta', {})
                                            if 'content' in delta:
                                                full_response += delta['content']
                                                response_with_math = render_latex_in_message(full_response + "▌")
                                                message_placeholder.markdown(response_with_math, unsafe_allow_html=True)
                                    except:
                                        continue
                        # Si no hubo contenido, informar
                        if not full_response.strip():
                            full_response = "La IA no devolvió contenido. Revisa el modelo o reintenta."
                        final_response = render_latex_in_message(full_response)
                        message_placeholder.markdown(final_response, unsafe_allow_html=True)
                    else:
                        # Mensajes de error específicos y detalle
                        try:
                            body = response.text[:300]
                        except:
                            body = ""
                        if response.status_code == 401:
                            full_response = "Clave de API inválida o no configurada. Verifica GROQ_API_KEY."
                        elif response.status_code == 404:
                            full_response = f"Modelo no encontrado: {GROQ_TEXT_MODEL}. Ajusta GROQ_TEXT_MODEL."
                        else:
                            full_response = f"Error de la IA ({response.status_code}). {body}"
                        message_placeholder.markdown(full_response)
                    
            except Exception as e:
                full_response = "Error de conexión. Por favor, verifica tu conexión a internet."
                message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_current_chat()
        st.rerun()

# --- PÁGINAS EXISTENTES MEJORADAS ---
def image_page():
    """Página de análisis de imágenes mejorada"""
    st.title("🖼️ Análisis de Imágenes")
    st.write("Sube una imagen para que Zero la analice usando Groq Vision.")
    
    uploaded_file = st.file_uploader(
        "Elige una imagen",
        type=["jpg", "jpeg", "png", "gif", "bmp", "webp"]
    )
    
    if uploaded_file is not None:
        # Mostrar imagen
        image = Image.open(uploaded_file)
        st.image(image, caption=uploaded_file.name, use_column_width=True)
        
        if st.button("🔍 Analizar Imagen", type="primary"):
            with st.spinner("Analizando imagen..."):
                # Convertir a base64
                image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                
                # Analizar con Groq Vision
                analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                
                # Mostrar resultado
                st.subheader("📋 Análisis de la Imagen")
                st.write(analysis)
                
                # Guardar análisis si el usuario está autenticado
                if st.session_state.get("user_id"):
                    try:
                        image_disk_path = f"uploads/{st.session_state.user_id}/{uploaded_file.name}"
                        db.save_image_analysis(
                            user_id=st.session_state.user_id,
                            image_path=image_disk_path,
                            analysis_result=analysis,
                            model_used=GROQ_VISION_MODEL
                        )
                        st.success("✅ Análisis guardado en tu historial")
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo guardar el análisis: {str(e)}")

def audio_page():
    """Página de transcripción de audio (función existente)"""
    st.title("🎤 Transcripción de Audio")
    st.write("Habla y Zero convertirá tu voz a texto.")
    
    # Configuración de WebRTC
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    if webrtc_ctx.audio_receiver:
        st.write("🎙️ Grabando... Habla ahora")
        
        # Procesar audio (implementación simplificada)
        audio_frames = []
        while True:
            try:
                audio_frame = webrtc_ctx.audio_receiver.get_frame(timeout=1)
                audio_frames.append(audio_frame)
            except queue.Empty:
                break
        
        if audio_frames:
            st.write("🔄 Procesando audio...")
            # Aquí iría la lógica de transcripción
            st.write("📝 **Transcripción:** [Funcionalidad en desarrollo]")

def register_page():
    """Página de registro de usuarios (solo admin)"""
    st.title("👥 Registro de Usuarios")
    
    if st.session_state.get("rol") != "admin":
        st.error("❌ Acceso denegado. Solo administradores pueden registrar usuarios.")
        return
    
    with st.form("registro_form"):
        st.subheader("Crear Nuevo Usuario")
        
        username = st.text_input("Nombre de usuario")
        password = st.text_input("Contraseña", type="password")
        confirm_password = st.text_input("Confirmar contraseña", type="password")
        rol = st.selectbox("Rol", ["usuario", "admin"])
        nfc_uid = st.text_input("NFC UID (opcional)")
        
        submitted = st.form_submit_button("Registrar Usuario")
        
        if submitted:
            if not username or not password:
                st.error("❌ Todos los campos son obligatorios")
            elif password != confirm_password:
                st.error("❌ Las contraseñas no coinciden")
            elif len(password) < 6:
                st.error("❌ La contraseña debe tener al menos 6 caracteres")
            else:
                try:
                    success = registrar_usuario(username, password, rol, nfc_uid or None)
                    if success:
                        st.success(f"✅ Usuario '{username}' registrado exitosamente")
                    else:
                        st.error("❌ Error al registrar usuario. Puede que ya exista.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

def file_upload_page():
    """Página para subir y gestionar archivos"""
    st.title("📁 Gestión de Archivos")
    st.write("Sube documentos e imágenes para que Zero pueda usarlos en las conversaciones.")

    # Verificar que el usuario esté autenticado
    if not st.session_state.get("usuario"):
        st.error("❌ Error de sesión. Por favor, vuelve a iniciar sesión.")
        return

    # Obtener user_id desde la base de datos usando el username
    username = st.session_state.usuario
    user_id = db.get_user_id_by_username(username)

    if not user_id:
        st.error("❌ No se pudo obtener la información del usuario.")
        return

    # Sección de subida de archivos
    st.subheader("📤 Subir Nuevo Archivo")

    uploaded_file = st.file_uploader(
        "Elige un archivo",
        type=["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "jpg", "jpeg", "png", "gif", "bmp", "webp"],
        help="Formatos soportados: PDF, Word, Excel, TXT, CSV e imágenes"
    )

    if uploaded_file is not None:
        st.info(f"📄 {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        if st.button("🚀 Procesar Archivo", type="primary"):
            with st.spinner("Procesando archivo..."):
                # Guardar y procesar archivo
                file_id, error = save_uploaded_file(uploaded_file)
                if error:
                    st.error(f"❌ Error al procesar archivo: {error}")
                else:
                    st.success("✅ Archivo procesado y guardado exitosamente")
                    # Si es una imagen, realizar análisis con Groq Vision
                    if uploaded_file.type.startswith('image/'):
                        with st.spinner("Analizando imagen con Groq Vision..."):
                            image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                            analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                            db.save_image_analysis(
                                user_id=user_id,
                                image_path=f"user_uploads/{user_id}/{uploaded_file.name}",
                                analysis_result=analysis,
                                model_used=GROQ_VISION_MODEL,
                                archivo_id=file_id
                            )
                            context_key = f"Análisis de imagen: {uploaded_file.name}"
                            db.save_user_context(user_id, context_key, analysis, file_id)
                            st.success("🖼️ Imagen analizada con Groq Vision")
                    # Actualizar archivos y contexto en sesión
                    st.session_state.user_files = db.get_user_files(user_id)
                    st.session_state.user_context = db.get_user_context(user_id)
                    st.rerun()

    # Sección de archivos existentes
    st.subheader("📋 Archivos Subidos")

    if "user_files" not in st.session_state:
        st.session_state.user_files = db.get_user_files(user_id)

    if st.session_state.get("user_files"):
        for file_data in st.session_state.user_files:
            with st.expander(f"📄 {file_data['filename']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Tipo:** {file_data['file_type'].upper()}")
                    st.write(f"**Tamaño:** {file_data['file_size'] / 1024:.1f} KB")
                    st.write(f"**Subido:** {file_data['uploaded_at']}")
                    if file_data.get('analysis_summary'):
                        st.write(f"**Resumen:** {file_data['analysis_summary'][:200]}...")
                with col2:
                    if st.button(f"🗑️ Eliminar", key=f"delete_{file_data['id']}"):
                        try:
                            if os.path.exists(file_data['file_path']):
                                os.remove(file_data['file_path'])
                        except Exception:
                            pass
                        db.delete_file(file_data['id'], user_id)
                        st.session_state.user_files = db.get_user_files(user_id)
                        st.session_state.user_context = db.get_user_context(user_id)
                        st.success("🗑️ Archivo eliminado")
                        st.rerun()
                    if st.button(f"💬 Usar en Chat", key=f"use_{file_data['id']}"):
                        if file_data.get('content_extracted'):
                            content_message = f"📄 **Contenido de {file_data['filename']}**:\n\n{file_data['content_extracted'][:1000]}..."
                            st.session_state.messages.append({
                                "role": "user",
                                "content": content_message
                            })
                            # Cambiar a página de chat de forma segura
                            st.session_state.current_page = "chat"
                            st.success(f"📄 Contenido de {file_data['filename']} agregado al chat")
                            st.rerun()
    else:
        st.info("📭 No tienes archivos subidos aún. ¡Sube tu primer archivo!")

def pqrs_page():
    """Página PQRS: formulario para enviar mensaje a un correo (espacio para añadir el correo destino)."""
    st.title("📮 PQRS")
    st.write("Escribe tu mensaje y envíalo por correo. Introduce el correo destino abajo (o utiliza el valor por defecto).")

    # Formulario simple
    with st.form("pqrs_form"):
        dest_email = st.text_input("Correo destino (añade aquí el correo):", value=PQRS_DEFAULT_EMAIL)
        subject = st.text_input("Asunto:", value="PQRS desde ZERO")
        message_body = st.text_area("Mensaje:", height=200)
        submit = st.form_submit_button("Enviar mensaje")

    if submit:
        if not dest_email.strip():
            st.error("Por favor indica el correo destino.")
        elif not message_body.strip():
            st.error("Escribe el mensaje antes de enviar.")
        else:
            # Intentar enviar usando variables SMTP en .env
            SMTP_HOST = os.getenv("SMTP_HOST", "")
            SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
            SMTP_USER = os.getenv("SMTP_USER", "")
            SMTP_PASS = os.getenv("SMTP_PASS", "")
            FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or os.getenv("PQRS_FROM", ""))

            if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
                st.warning("No están configuradas las credenciales SMTP en el entorno. Puedes copiar el mensaje y enviarlo manualmente, o configura las variables SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS y FROM_EMAIL en tu .env para envío automático.")
                st.code(f"Para: {dest_email}\nAsunto: {subject}\n\n{message_body}")
            else:
                try:
                    msg = EmailMessage()
                    msg["From"] = FROM_EMAIL or SMTP_USER
                    msg["To"] = dest_email
                    msg["Subject"] = subject
                    msg.set_content(message_body)

                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
                        smtp.starttls()
                        smtp.login(SMTP_USER, SMTP_PASS)
                        smtp.send_message(msg)

                    st.success("✅ Mensaje enviado correctamente.")
                except Exception as e:
                    st.error(f"⚠️ Error al enviar el correo: {e}")
                    st.info("Puedes revisar la configuración SMTP en las variables de entorno o enviar el mensaje manualmente:")
                    st.code(f"Para: {dest_email}\nAsunto: {subject}\n\n{message_body}")

# --- FUNCIÓN PRINCIPAL ---
def main():
    """Aplicación principal"""
    # Siempre tomar el usuario desde query params si está presente
    qp = st.query_params
    usuario_qp = qp.get("usuario")
    if usuario_qp:
        st.session_state.usuario = usuario_qp
        user_info = db.get_user_by_username(usuario_qp)
        if user_info:
            st.session_state.rol = user_info.get("rol", "usuario")
            st.session_state.user_id = user_info.get("id")

    # Si tenemos user_id, precargar lista de archivos del usuario
    if st.session_state.get("user_id") and "user_files" not in st.session_state:
        try:
            st.session_state.user_files = db.get_user_files(st.session_state.user_id)
        except:
            st.session_state.user_files = []

    # Navegación desde sidebar
    create_sidebar()

    # Determinar página actual (simplificado)
    if "current_page" not in st.session_state:
        st.session_state.current_page = "chat"

    # Renderizar página seleccionada
    if st.session_state.current_page == "chat":
        chat_page()
    elif st.session_state.current_page == "files":
        file_upload_page()
    elif st.session_state.current_page == "admin":
        register_page()
    elif st.session_state.current_page == "pqrs":
        pqrs_page()

if __name__ == "__main__":
    main()