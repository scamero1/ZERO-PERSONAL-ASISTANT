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

from database import ZeroDatabase
from file_processor import FileProcessor

db = ZeroDatabase()

load_dotenv()

st.set_page_config(
    page_title="ZERO - AI Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--accent-primary);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .user-info {
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .sidebar-section {
            margin-bottom: 2rem;
            padding: 0 1rem;
        }

        .section-title {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-secondary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .section-title::before {
            content: '';
            width: 4px;
            height: 16px;
            background: var(--accent-gradient);
            border-radius: 2px;
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

        .chat-item:hover {
            background: rgba(139, 92, 246, 0.1);
            border-color: var(--accent-primary);
            transform: translateX(5px);
        }

        .chat-item.active {
            background: var(--card-bg);
            border-color: var(--accent-primary);
            box-shadow: var(--shadow-sm);
        }

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

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .user-message {
            background: var(--user-msg-bg);
            border-left: 4px solid var(--accent-primary);
        }

        .assistant-message {
            background: var(--assistant-msg-bg);
            border-left: 4px solid var(--accent-secondary);
        }

        .message-content {
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        }

        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            flex-shrink: 0;
            font-size: 1rem;
            background: var(--accent-gradient);
            color: white;
        }

        .assistant-avatar {
            background: var(--card-bg);
            border: 2px solid var(--accent-primary);
        }

        .message-text {
            flex: 1;
            line-height: 1.6;
            font-size: 0.95rem;
            color: var(--text-primary);
            padding: 0.5rem 0;
        }

        /* Input area moderno */
        .input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--secondary-bg);
            border-top: 1px solid var(--border-color);
            padding: 1.5rem 0;
            backdrop-filter: blur(20px);
        }

        .input-wrapper {
            max-width: 800px;
            margin: 0 auto;
            padding: 0 2rem;
        }

        .stChatInput > div > div {
            background: var(--card-bg) !important;
            border: 2px solid var(--border-color) !important;
            border-radius: 20px !important;
            padding: 1rem 1.5rem !important;
            box-shadow: var(--shadow-md) !important;
            transition: all 0.3s ease !important;
        }

        .stChatInput > div > div:focus-within {
            border-color: var(--accent-primary) !important;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        }

        .stChatInput input {
            color: var(--text-primary) !important;
            font-size: 1rem !important;
            background: transparent !important;
        }

        /* Scrollbar personalizada */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--secondary-bg);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--accent-gradient);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-secondary);
        }

        /* Ecuaciones y código */
        .latex-formula {
            background: rgba(139, 92, 246, 0.1);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-family: 'CMU Serif', serif;
            text-align: center;
            border: 1px solid var(--accent-primary);
            color: var(--accent-secondary);
        }

        .math-block {
            background: rgba(139, 92, 246, 0.05);
            padding: 1.25rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid var(--accent-primary);
        }

        .code-block {
            background: var(--card-bg);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.875rem;
            overflow-x: auto;
            border: 1px solid var(--border-color);
        }

        /* Página de archivos */
        .files-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }

        .upload-section {
            background: var(--card-bg);
            border: 2px dashed var(--border-color);
            border-radius: 20px;
            padding: 3rem;
            text-align: center;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }

        .upload-section:hover {
            border-color: var(--accent-primary);
            background: rgba(139, 92, 246, 0.05);
        }

        .file-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .file-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--accent-gradient);
        }

        .file-card:hover {
            border-color: var(--accent-primary);
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }

        .file-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .file-details {
            flex: 1;
        }

        .file-name {
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }

        .file-meta {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        .file-actions {
            display: flex;
            gap: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

load_css()

# --- VERIFICACIÓN DE AUTENTICACIÓN ---
if not st.session_state.get("autenticado", False):
    verificar_login()
    st.stop()

# --- SIDEBAR ZERO MEJORADO ---
def create_sidebar():
    """Crea la barra lateral con navegación y gestión de archivos"""
    # Título de la barra lateral
    st.markdown('<div class="sidebar-title">ZERO - Asistente Virtual</div>', unsafe_allow_html=True)

    # Saludo personalizado
    usuario_nombre = st.session_state.get("usuario", "Usuario")
    st.markdown(f'<div style="margin-bottom: 1rem;">Hola, <strong>{usuario_nombre}</strong></div>', unsafe_allow_html=True)

    # Lista de chats anteriores
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">💬 Chats anteriores</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-list">', unsafe_allow_html=True)

    # Renderizar chats del usuario actual
    if st.session_state.get("user_id"):
        try:
            user_chats = db.get_user_chats(st.session_state.user_id)
            for chat in user_chats[-10:]:  # Mostrar últimos 10 chats
                is_active = chat['chat_id'] == st.session_state.current_chat
                preview = chat['title'][:50] + "..." if len(chat['title']) > 50 else chat['title']
                st.markdown(
                    f"""
                    <div class="chat-item {'active' if is_active else ''}">
                        <div><strong>{chat['title']}</strong></div>
                        <div class="chat-preview">{preview}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # Botón para cargar el chat
                if st.button("Abrir", key=f"open_{chat['id']}"):
                    st.session_state.current_chat = chat['chat_id']
                    # Cargar mensajes del chat
                    chat_messages = db.get_chat_messages(chat['chat_id'])
                    st.session_state.messages = [
                        {"role": msg['role'], "content": msg['content']}
                        for msg in chat_messages
                    ]
                    st.rerun()
        except Exception as e:
            st.write("No hay chats anteriores")

    st.markdown('</div>', unsafe_allow_html=True)

    # Botón de nuevo chat
    if st.button("➕ Nuevo Chat", use_container_width=True):
        save_current_chat()
        st.session_state.current_chat = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Sección de archivos del usuario
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">📁 Mis Archivos</div>', unsafe_allow_html=True)

    if st.session_state.get("user_files"):
        # Mostrar últimos 5 archivos
        for file_data in st.session_state.user_files[-5:]:
            st.markdown(
                f"""
                <div class="file-item">
                    <div class="file-name">📄 {file_data['filename']}</div>
                    <div class="file-info">{file_data['file_type'].upper()} • {file_data['file_size'] / 1024:.1f} KB</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div style="color: var(--text-secondary); font-size: 0.9rem; text-align: center; padding: 1rem;">No hay archivos subidos</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Sección de herramientas
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-title">🛠️ Herramientas</div>', unsafe_allow_html=True)

    menu_options = ["Chat Principal", "Subir Archivos"]
    if st.session_state.rol == "admin":
        menu_options += ["Análisis de Imágenes", "Transcripción de Audio", "Registro de Usuarios"]

    selected_option = st.radio("", menu_options, key="menu_option", label_visibility="collapsed")

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚪 Cerrar sesión", key="logout_btn", use_container_width=True, type="primary"):
        logout()
        st.rerun()

    # Navegación de página principal
    # Actualiza la página actual según la opción seleccionada
    if selected_option == "Chat Principal":
        st.session_state.current_page = "chat"
    elif selected_option == "Subir Archivos":
        st.session_state.current_page = "files"
    elif selected_option == "Registro de Usuarios":
        st.session_state.current_page = "admin"
    # Puedes agregar más elif para otras opciones si lo deseas

# --- FUNCIONES DE UTILIDAD PARA ARCHIVOS ---
def save_uploaded_file(uploaded_file, user_id):
    """Guarda un archivo subido y lo procesa"""
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
            processor = FileProcessor()
            result = processor.process_file(file_content, uploaded_file.name)
            content = result.get('content', '')[:5000]
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
                    
                    final_response = render_latex_in_message(full_response)
                    message_placeholder.markdown(final_response, unsafe_allow_html=True)
                else:
                    full_response = "Lo siento, hubo un error al procesar tu solicitud. Por favor, intenta nuevamente."
                    message_placeholder.markdown(full_response)
                    
            except Exception as e:
                full_response = "Error de conexión. Por favor, verifica tu conexión a internet."
                message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_current_chat()
        st.rerun()

# --- PÁGINA DE GESTIÓN DE ARCHIVOS ---
def files_page():
    """Página de gestión de archivos"""
    
    st.markdown("""
        <div class="main-header">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">📁</div>
                <div>
                    <h1 style="margin: 0; color: var(--text-primary); font-weight: 800;">
                        Gestor de Archivos
                    </h1>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">
                        Gestiona y analiza tus documentos e imágenes
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="files-container">', unsafe_allow_html=True)
    
    # Sección de subida
    st.markdown("""
        <div class="upload-section">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📤</div>
            <h3 style="margin: 0 0 1rem 0; color: var(--text-primary); font-weight: 700;">Subir Archivos</h3>
            <p style="margin: 0 0 2rem 0; color: var(--text-secondary); font-size: 1rem;">
                Arrastra o selecciona archivos para que Zero los analice automáticamente
            </p>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Seleccionar archivos",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "md", "xlsx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        if st.button("Procesar Archivos", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            for i, uploaded_file in enumerate(uploaded_files):
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                
                with st.spinner(f"Analizando {uploaded_file.name}..."):
                    file_id, error = save_uploaded_file(uploaded_file)
                    if file_id:
                        st.success(f"✅ **{uploaded_file.name}** - Procesado correctamente")
                        st.session_state.user_files = db.get_user_files(st.session_state.user_id)
                    else:
                        st.error(f"❌ **{uploaded_file.name}** - {error}")
            
            progress_bar.empty()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sección de archivos existentes
    st.markdown("### Tus Archivos")
    
    if not st.session_state.get("user_files"):
        st.session_state.user_files = db.get_user_files(st.session_state.user_id)
    
    if st.session_state.user_files:
        for file_data in st.session_state.user_files:
            file_icon = "🖼️" if file_data['file_type'] == 'image' else "📄"
            file_size = f"{file_data['file_size'] / 1024:.1f} KB"
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                    <div class="file-card">
                        <div class="file-header">
                            <div class="file-details">
                                <div class="file-name">{file_icon} {file_data['filename']}</div>
                                <div class="file-meta">
                                    {file_data['file_type'].upper()} • {file_size} • {file_data['uploaded_at']}
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                col_use, col_del = st.columns(2)
                with col_use:
                    if st.button("💬", key=f"use_{file_data['id']}", help="Usar en chat", use_container_width=True):
                        if file_data.get('content_extracted'):
                            content_msg = f"Archivo: {file_data['filename']}\n\n{file_data['content_extracted'][:400]}..."
                            st.session_state.messages.append({"role": "user", "content": content_msg})
                            st.success("Archivo agregado al chat")
                            st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_{file_data['id']}", help="Eliminar", use_container_width=True):
                        try:
                            if os.path.exists(file_data['file_path']):
                                os.remove(file_data['file_path'])
                        except:
                            pass
                        db.delete_file(file_data['id'])
                        st.session_state.user_files = db.get_user_files(st.session_state.user_id)
                        st.success("Archivo eliminado")
                        st.rerun()
    else:
        st.info("""
            <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                <div style="font-size: 4rem; margin-bottom: 1rem;">📁</div>
                <h3 style="color: var(--text-primary); margin-bottom: 1rem;">Aún no hay archivos</h3>
                <p>Comienza subiendo tu primer archivo para que Zero lo analice</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- PÁGINA DE ADMINISTRACIÓN ---
def admin_page():
    """Página de administración de usuarios"""
    
    st.markdown("""
        <div class="main-header">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">👨‍💼</div>
                <div>
                    <h1 style="margin: 0; color: var(--text-primary); font-weight: 800;">
                        Panel de Administración
                    </h1>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">
                        Gestión de usuarios del sistema
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="files-container">', unsafe_allow_html=True)
    
    with st.form("user_registration_form"):
        st.markdown("### Registrar Nuevo Usuario")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Nombre de usuario", placeholder="Ingresa el nombre de usuario")
            new_password = st.text_input("Contraseña", type="password", placeholder="Crea una contraseña segura")
        
        with col2:
            confirm_password = st.text_input("Confirmar contraseña", type="password", placeholder="Repite la contraseña")
            user_role = st.selectbox("Rol del usuario", ["usuario", "admin"])
        
        submitted = st.form_submit_button("Registrar Usuario", use_container_width=True, type="primary")
        
        if submitted:
            if not new_username or not new_password:
                st.error("Todos los campos son obligatorios")
            elif new_password != confirm_password:
                st.error("Las contraseñas no coinciden")
            elif len(new_password) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres")
            else:
                try:
                    success = registrar_usuario(new_username, new_password, user_role)
                    if success:
                        st.success(f"✅ Usuario **{new_username}** registrado exitosamente como {user_role}")
                    else:
                        st.error("Error al registrar usuario. El nombre de usuario puede estar en uso.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES ---
def save_current_chat():
    """Guarda el chat actual en la base de datos"""
    if st.session_state.get("user_id") and st.session_state.messages:
        try:
            title = "Nueva conversación"
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    user_content = msg['content']
                    title = user_content[:25] + "..." if len(user_content) > 25 else user_content
                    break
            
            chat_id = db.save_chat(
                user_id=st.session_state.user_id,
                chat_id=st.session_state.current_chat,
                title=title
            )
            
            for i, message in enumerate(st.session_state.messages):
                db.save_message(
                    chat_id=chat_id,
                    role=message['role'],
                    content=message['content'],
                    message_order=i
                )
                
        except Exception as e:
            print(f"Error guardando chat: {e}")

# --- APLICACIÓN PRINCIPAL ---
def main():
    """Aplicación principal"""
    # Inicializar datos del usuario
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
        files_page()
    elif st.session_state.current_page == "admin":
        admin_page()

if __name__ == "__main__":
    main()



    #prueba actualizaciópn