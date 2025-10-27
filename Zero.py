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
import hashlib
import io
import csv
import re
from datetime import datetime
import unicodedata
import smtplib
from email.message import EmailMessage
from database import ZeroDatabase
from file_processor import FileProcessor
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

db = ZeroDatabase()

load_dotenv()

PQRS_DEFAULT_EMAIL = os.getenv("PQRS_EMAIL", "soporte@zero-va.com")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY no encontrada en las variables de entorno")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "https://zero-va.com")

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

# Helpers para API por empresa

def _company_ai_headers(stream: bool = False):
    empresa_id = st.session_state.get("empresa_id")
    api_key = GROQ_API_KEY
    if empresa_id:
        try:
            empresa = db.get_company_by_id(empresa_id)
            if empresa and empresa.get("groq_api_key"):
                api_key = empresa.get("groq_api_key")
        except Exception:
            pass
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    return headers


def _company_model(default_model: str) -> str:
    empresa_id = st.session_state.get("empresa_id")
    if empresa_id:
        try:
            empresa = db.get_company_by_id(empresa_id)
            if empresa and empresa.get("model_name"):
                return empresa.get("model_name")
        except Exception:
            pass
    return default_model

def normalize_str(s: str) -> str:
    s = (s or "")
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def safe_text(text: str) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text

def initialize_session_state():
    default_states = {
        "autenticado": False,
        "usuario": None,
        "rol": None,
        "user_id": None,
        "empresa_id": None,
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

        .css-1d391kg, .css-1lcbmhc {
            background: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color);
        }

        .sidebar-header {
            padding: 2rem 1.5rem 1.5rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }

        .main-header {
            background: var(--secondary-bg);
            padding: 0.6rem 1.2rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 0.2rem;
        }
        .main-header > div {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .chat-container {
            background: var(--primary-bg);
            margin-top: 0;
            min-height: calc(100vh - 72px);
            padding: 0;
        }

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

try:
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
except Exception as e:
    st.warning(f"No se pudo inicializar Twilio: {e}")

def initialize_session_state():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "empresa_id" not in st.session_state:
        st.session_state.empresa_id = None
    
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

def _system_prompt():
    base_prompt = "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil."

    # Añadir contexto de empresa si existe en sesión
    empresa_info_text = ""
    try:
        empresa_id = st.session_state.get("empresa_id")
        if empresa_id:
            empresa = db.get_company_by_id(empresa_id)
            if empresa:
                nombre_emp = empresa.get("nombre") or empresa.get("slug") or str(empresa_id)
                empresa_info_text += f"\n\nEmpresa activa: {nombre_emp}."
                # Añadir resumen de políticas/contexto de empresa si disponible
                ctx_list = db.get_company_context(empresa_id)
                if ctx_list:
                    sample_items = ctx_list[:2]
                    resumen = "; ".join([(item.get("context_value") or item.get("content") or "")[:120] for item in sample_items])
                    if resumen.strip():
                        empresa_info_text += f" Políticas relevantes (resumen): {resumen}"
    except Exception:
        pass
    
    # Añadir contexto personalizado del usuario
    if st.session_state.get("user_context"):
        context_info = "\n\nContexto personalizado del usuario:\n"
        for ctx in st.session_state.user_context[-5:]:
            try:
                key = ctx.get('context_key', 'contexto')
                val = ctx.get('context_value', '')
            except Exception:
                key, val = 'contexto', str(ctx)
            context_info += f"- {key}: {str(val)[:200]}...\n"
        base_prompt += context_info

    return {"role": "system", "content": base_prompt + empresa_info_text}

def groq_chat_stream(history_messages, *, model=None, max_tokens=1200, temperature=0.7):
    m = _company_model(model or GROQ_TEXT_MODEL)
    payload = {
        "model": m,
        "messages": [_system_prompt()] + history_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    try:
        with requests.post(API_URL, headers=_company_ai_headers(True), json=payload, stream=True, timeout=300) as r:
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
                            yield safe_text(delta)
                    except Exception:
                        continue
    except requests.HTTPError as http_err:
        yield safe_text(f"⚠️ Error HTTP: {http_err}")
    except Exception as e:
        yield safe_text(f"⚠️ Error en streaming: {e}")

def groq_chat_nonstream(history_messages, *, model=None, max_tokens=1200, temperature=0.7):
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

def display_message(role, content):
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
    if st.session_state.messages and st.session_state.get("usuario") and st.session_state.get("user_id"):
        first_message = st.session_state.messages[0]["content"] if st.session_state.messages else "Nuevo chat"
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        
        if st.session_state.usuario not in st.session_state.chat_history:
            st.session_state.chat_history[st.session_state.usuario] = {}
        st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
            "title": safe_text(title),
            "messages": st.session_state.messages.copy(),
        }

        try:
            db.update_chat_title(st.session_state.current_chat, safe_text(title))
        except Exception:
            pass
        user_chats = db.get_user_chats(st.session_state.user_id)
        if not any(c["id"] == st.session_state.current_chat for c in user_chats):
            st.session_state.current_chat = db.create_chat(st.session_state.user_id, safe_text(title))
        else:
            db.update_chat_title(st.session_state.current_chat, safe_text(title))
        
        for message in st.session_state.messages:
            db.add_message(
                st.session_state.current_chat,
                message["role"],
                message["content"]
            )

def load_chat(chat_id):
    if "usuario" in st.session_state and chat_id in st.session_state.chat_history.get(st.session_state.usuario, {}):
        st.session_state.current_chat = chat_id
        st.session_state.messages = st.session_state.chat_history[st.session_state.usuario][chat_id]["messages"].copy()
        st.rerun()

def create_sidebar():
    with st.sidebar:
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

        if "selected_chats" not in st.session_state:
            st.session_state.selected_chats = set()

        if st.session_state.selected_chats:
            col_del = st.columns([1])[0]
            with col_del:
                btn_style = """
                    <style>
                    .delete-selected-btn button {
                        width: 100% !important;
                        background: linear-gradient(90deg,#a78bfa 0%,#8b5cf6 100%) !important;
                        color: white !important;
                        font-weight: 600 !important;
                        border-radius: 10px !important;
                        font-size: 1rem !important;
                        margin-bottom: 0.5rem;
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                        gap: 0.5rem !important;
                    }
                    </style>
                """
                st.markdown(btn_style, unsafe_allow_html=True)
                if st.button("🗑️ Eliminar seleccionadas", key="delete_selected_chats", use_container_width=True, help="Eliminar todas las conversaciones seleccionadas", type="secondary"):
                    for chat_id in list(st.session_state.selected_chats):
                        db.delete_chat(chat_id, st.session_state.user_id)
                        st.session_state.selected_chats.remove(chat_id)
                    st.session_state.chat_history = {}
                    st.session_state.messages = []
                    st.success("Conversaciones eliminadas")
                    st.rerun()
                st.markdown(f"<span style='color:var(--text-muted);font-size:0.9rem;'>({len(st.session_state.selected_chats)} seleccionadas)</span>", unsafe_allow_html=True)

        if st.button("Nuevo Chat", key="new_chat_btn", use_container_width=True, type="primary"):
            save_current_chat()
            st.session_state.current_chat = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

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

                        col1, col2 = st.columns([1, 8])
                        with col1:
                            checked = chat['id'] in st.session_state.selected_chats
                            select = st.checkbox(
                                "",
                                value=checked,
                                key=f"select_chat_{chat['id']}",
                                label_visibility="collapsed"
                            )
                            if select:
                                st.session_state.selected_chats.add(chat['id'])
                            else:
                                st.session_state.selected_chats.discard(chat['id'])
                        with col2:
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
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Navegación</div>', unsafe_allow_html=True)
        
        if st.button("Chat con Zero", key="nav_chat", use_container_width=True, type="primary"):
            st.session_state.current_page = "chat"
            st.rerun()

        if st.button("Gestor de Archivos", key="nav_files", use_container_width=True, type="primary"):
            st.session_state.current_page = "files"
            st.rerun()

        if st.button("PQRS", key="nav_pqrs", use_container_width=True, type="primary"):
            st.session_state.current_page = "pqrs"
            st.rerun()

        if st.session_state.rol == "admin":
            if st.button("Panel Admin", key="nav_admin", use_container_width=True, type="primary"):
                st.session_state.current_page = "admin"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("Cerrar Sesión", key="logout_btn", use_container_width=True, type="primary"):
            try:
                # Cerrar sesión local (Streamlit)
                logout()
                # Cerrar sesión backend (Flask) para limpiar cookie
                try:
                    requests.get(f"{PUBLIC_SITE_URL}/logout", timeout=3)
                except Exception:
                    pass
            finally:
                st.rerun()

def analyze_document_with_groq(content, filename):
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
            "model": _company_model(GROQ_TEXT_MODEL),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.3
        }

        response = requests.post(API_URL, headers=_company_ai_headers(False), json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Análisis completado para {filename}"
            
    except Exception as e:
        return f"Documento procesado: {filename}"

def analyze_image_with_groq(image_base64, filename):
    try:
        payload = {
            "model": _company_model(GROQ_VISION_MODEL),
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
        
        response = requests.post(API_URL, headers=_company_ai_headers(False), json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Análisis visual completado para {filename}"
            
    except Exception as e:
        return f"Imagen procesada: {filename}"

def save_uploaded_file(uploaded_file):
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

        empresa_id = st.session_state.get("empresa_id")
        encrypt_enabled = False
        if empresa_id:
            try:
                settings = db.get_company_settings(empresa_id)
                encrypt_enabled = bool(settings.get("encrypt_files"))
                if encrypt_enabled:
                    db.ensure_empresa_key(empresa_id)
            except Exception:
                encrypt_enabled = False

        user_id = st.session_state.user_id
        base_dir = "user_uploads_enc" if encrypt_enabled else "user_uploads"
        user_dir = os.path.join(base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        safe_name = uploaded_file.name
        file_path = os.path.join(user_dir, safe_name + (".enc" if encrypt_enabled else ""))

        raw_bytes = uploaded_file.getvalue()

        if encrypt_enabled:
            data_key = db.get_active_empresa_key(empresa_id)
            if not data_key:
                # Fallback: guardar sin cifrado si no hay clave activa
                encrypt_enabled = False
                base_dir = "user_uploads"
                user_dir = os.path.join(base_dir, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                file_path = os.path.join(user_dir, safe_name)
                with open(file_path, "wb") as f:
                    f.write(raw_bytes)
                try:
                    st.warning("No hay clave activa de cifrado; archivo guardado sin cifrado.")
                except Exception:
                    pass
            else:
                aes = AESGCM(data_key)
                nonce = os.urandom(12)
                aad = f"{empresa_id}:{user_id}".encode()
                ciphertext = aes.encrypt(nonce, raw_bytes, associated_data=aad)
                with open(file_path, "wb") as f:
                    f.write(nonce + ciphertext)
        else:
            with open(file_path, "wb") as f:
                f.write(raw_bytes)

        content = ""
        analysis = ""
        
        if file_type == 'image':
            image_base64 = b64encode(raw_bytes).decode('utf-8')
            analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
            content = "Imagen procesada para análisis visual"
        else:
            file_content = raw_bytes
            
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
            user_id=user_id,
            filename=uploaded_file.name,
            file_path=file_path,
            file_type=file_type,
            file_size=uploaded_file.size,
            content_extracted=content,
            analysis_summary=(analysis or "")[:350]
        )

        if analysis:
            context_key = f"Archivo: {uploaded_file.name}"
            db.save_user_context(user_id, context_key, analysis, file_id)

        return file_id, None

    except Exception as e:
        return None, f"Error procesando archivo: {str(e)}"

def is_advice_question(prompt: str) -> bool:
    norm = normalize_str(prompt)
    intents = [
        "como puedo", "cómo puedo", "como hacer", "cómo hacer",
        "recomendacion", "recomendación", "recomendaciones",
        "sugerencia", "sugerencias",
        "estrategia", "guia", "guía",
        "pasos", "buenas practicas", "buenas prácticas",
        "ideas", "alternativas", "riesgos",
        "plan", "que hacer", "qué hacer",
        "mejorar", "optimizar", "explicame", "explícame", "explicacion", "explicación"
    ]
    return any(k in norm for k in intents)

def is_greeting_or_smalltalk(prompt: str) -> bool:
    norm = normalize_str(prompt)
    intents = [
        "hola", "buenos dias", "buenas tardes", "buenas noches",
        "que tal", "qué tal", "como estas", "cómo estás", "hey",
        "hi", "hello", "saludos"
    ]
    if len(norm.split()) <= 3 and any(k in norm for k in intents):
        return True
    return any(k in norm for k in intents)

def is_analysis_question(prompt: str) -> bool:
    norm = normalize_str(prompt)
    intents = [
        "analiza", "analisis", "análisis",
        "compara", "comparacion", "comparación",
        "resume", "resumen", "sintetiza", "desglosa", "detalla",
        "extrae", "extraer", "identifica", "clasifica",
        "calcula", "grafica", "gráfico", "grafico",
        "que dice", "qué dice", "que contiene", "qué contiene",
        "busca en el documento", "buscar en el documento"
    ]
    return any(k in norm for k in intents)

def generate_advice_response(prompt: str, user_id: int | None, recent_messages: list[dict]) -> str:
    try:
        convo = []
        for m in recent_messages[-8:]:
            role = m.get("role", "user")
            content = (m.get("content") or "").strip()
            if content:
                convo.append(f"{role.upper()}: {content}")
        contexto = "\n".join(convo)

        instrucciones = (
            "Eres un asesor en español. Da recomendaciones claras y accionables.\n"
            "- Basarte en el contexto reciente del chat (no inventes datos).\n"
            "- Estructura en pasos, quick wins y métricas a monitorear.\n"
            "- Incluye riesgos/consideraciones y alternativas.\n"
            "- Si faltan datos, indica qué pedir o calcular del documento.\n"
        )
        prompt_llm = (
            f"{instrucciones}\n\nPregunta del usuario:\n{prompt}\n\n"
            f"=== CONTEXTO RECIENTE ===\n{contexto}\n=== FIN CONTEXTO ==="
        )

        resp = analyze_document_with_groq(prompt_llm, "asesoria_estrategica")
        if not resp or not resp.strip():
            return ""

        try:
            resp = rewrite_with_editor(resp, "Formato claro, pasos accionables y métricas.")
        except Exception:
            pass

        return resp.strip()
    except Exception:
        return ""

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    t = (text or "")
    if len(t) <= max_chars:
        return [t]
    chunks = []
    start = 0
    while start < len(t):
        end = min(start + max_chars, len(t))
        chunks.append(t[start:end])
        if end == len(t):
            break
        start = max(0, end - overlap)
    return chunks

def _spanish_stopwords() -> set[str]:
    return {
        "el","la","los","las","un","una","unos","unas","de","del","al","y","o","u",
        "que","qué","cuál","cual","donde","dónde","como","cómo","en","por","para",
        "a","con","sin","se","su","sus","mi","mis","tu","tus","lo","le","les","es",
        "hay","tengo","tienes","tener","esto","eso","aqui","aquí","alli","allí"
    }

import difflib

def extract_keywords(query: str) -> list[str]:
    q = normalize_str(query or "")
    stops = _spanish_stopwords()
    return [t for t in q.split() if t not in stops and len(t) > 2]

def fuzzy_contains(haystack: str, needle: str, threshold: float = 0.82) -> bool:
    h = normalize_str(haystack)
    n = normalize_str(needle)
    if n in h:
        return True
    return difflib.SequenceMatcher(None, h, n).ratio() >= threshold

def _score_chunk(norm_chunk: str, norm_query: str, name: str) -> int:
    tokens = extract_keywords(norm_query)
    score = 0
    for t in tokens:
        if t in norm_chunk:
            score += 2
        elif fuzzy_contains(norm_chunk, t, 0.88):
            score += 1
        if t in normalize_str(name) or fuzzy_contains(name, t, 0.88):
            score += 3
    return score

def sync_user_files_from_disk(user_id: int):
    base_dirs = [os.path.join("user_uploads", str(user_id)), os.path.join("uploads", str(user_id))]
    try:
        existing = db.get_user_files(user_id)
        existing_paths = {f.get("file_path") for f in existing if f.get("file_path")}
    except Exception:
        existing_paths = set()

    ext_map = {
        'pdf': 'pdf', 'docx': 'word', 'doc': 'word', 'txt': 'text',
        'md': 'markdown', 'xlsx': 'excel', 'xls': 'excel', 'csv': 'csv',
        'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image'
    }

    for base_dir in base_dirs:
        if not os.path.isdir(base_dir):
            continue
        for name in os.listdir(base_dir):
            path = os.path.join(base_dir, name)
            if not os.path.isfile(path):
                continue
            if path in existing_paths:
                continue

            ext = name.split('.')[-1].lower()
            file_type = ext_map.get(ext, 'unknown')
            if file_type == 'unknown':
                continue

            try:
                with open(path, "rb") as f:
                    data = f.read()
                content = ""
                analysis = ""
                if file_type in ['pdf', 'word']:
                    processor = FileProcessor()
                    result = processor.process_file(data, name)
                    content = (result.get('content') or "")[:8000]
                else:
                    try:
                        content = data.decode('utf-8', errors='ignore')[:8000]
                    except Exception:
                        content = data.decode('latin-1', errors='ignore')[:8000]

                if content and len(content.strip()) > 50:
                    try:
                        analysis = analyze_document_with_groq(content, name)
                    except Exception:
                        analysis = f"Documento indexado: {name}"
                else:
                    analysis = f"Documento indexado: {name}"

                db.save_file(
                    user_id=user_id,
                    filename=name,
                    file_path=path,
                    file_type=file_type,
                    file_size=os.path.getsize(path),
                    content_extracted=content,
                    analysis_summary=(analysis or "")[:350]
                )
            except Exception:
                continue

def search_user_documents(user_id: int, query: str):
    q = normalize_str((query or "").strip())
    if not q:
        return []

    try:
        files = db.get_user_files(user_id)
    except Exception:
        files = []

    results = []
    for f in files:
        name = normalize_str(f.get("filename") or "")
        content = normalize_str(f.get("content_extracted") or "")
        score = 0
        if q in name:
            score += 2
        if q in content:
            score += 1
        if score > 0:
            results.append((score, f))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results]

def maybe_answer_doc_query(prompt: str, user_id: int | None):
    text = (prompt or "")
    norm = normalize_str(text)
    intents = [
        "que libro", "qué libro", "que documentos", "qué documentos",
        "que archivo", "qué archivo", "donde esta", "dónde está",
        "donde lo encuentro", "dónde lo encuentro", "que tengo", "qué tengo",
        "buscar", "lista de archivos", "listar archivos"
    ]
    if not any(k in norm for k in intents):
        return None

    if not user_id:
        return "No encuentro tu sesión de usuario. Inicia sesión para buscar en tus documentos."

    matches = search_user_documents(user_id, text)
    if not matches:
        return "No encuentro coincidencias en tus documentos. Prueba con el nombre o tema exacto."

    lines = []
    for f in matches[:8]:
        ruta = f.get("file_path") or f"user_uploads/{user_id}/{f.get('filename')}"
        lines.append(f"- {f.get('filename')} (lo encuentras en: {ruta})")

    header = "Encontré estos documentos:\n" if len(matches) > 1 else "Encontré este documento:\n"
    return header + "\n".join(lines)

def rewrite_with_editor(text: str, instrucciones: str | None = None) -> str:
    try:
        if not text or not text.strip():
            return text

        if is_greeting_or_smalltalk(text) or len(text.strip()) < 20:
            return text

        cleaned = re.sub(
            r"^\s*\*\*An[aá]lisis del Documento.*?\*\*\s*",
            "",
            text,
            flags=re.IGNORECASE | re.MULTILINE
        )

        return cleaned.strip()
    except Exception:
        return text

def answer_with_docs(prompt: str, user_id: int) -> str | None:
    if is_greeting_or_smalltalk(prompt) or not is_analysis_question(prompt):
        return None

    try:
        files = db.get_user_files(user_id)
    except Exception:
        files = []

    norm_q = normalize_str(prompt)
    candidates = []
    for f in files:
        name = f.get("filename") or ""
        path = f.get("file_path") or f"user_uploads/{user_id}/{name}"
        content = f.get("content_extracted") or ""
        if not content:
            continue
        for ch in chunk_text(content):
            norm_ch = normalize_str(ch)
            score = _score_chunk(norm_ch, norm_q, name)
            if score > 0:
                candidates.append((score, ch, name, path))

    if not candidates:
        suggestions = search_user_documents(user_id, prompt)
        if suggestions:
            posibles = "\n".join([f"- {s.get('filename')} (ruta: {s.get('file_path')})" for s in suggestions[:6]])
            return (
                "No encuentro texto relevante en los documentos actuales para responder.\n"
                "Podría estar en alguno de estos archivos:\n" + posibles
            )
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    top = candidates[:8]

    if top[0][0] < 3 and len(top) < 3:
        suggestions = search_user_documents(user_id, prompt)
        if suggestions:
            posibles = "\n".join([f"- {s.get('filename')} (ruta: {s.get('file_path')})" for s in suggestions[:6]])
            return (
                "El contexto recuperado es insuficiente para una respuesta fiable.\n"
                "Podría estar en:\n" + posibles
            )
        return None

    contexto = "\n\n".join([f"Fuente: {n}\nRuta: {p}\nContenido:\n{ch}" for _, ch, n, p in top])
    fuentes_unicas = []
    vistos = set()
    for _, _, n, p in top:
        key = (n, p)
        if key not in vistos:
            vistos.add(key)
            fuentes_unicas.append((n, p))

    instrucciones = (
        "Responde EXCLUSIVAMENTE usando el texto provisto en CONTEXTO.\n"
        "Reglas estrictas:\n"
        "1) Usa SOLO el texto dado de los documentos.\n"
        "2) Si hay información relacionada en varios documentos, combina la evidencia y cita sus nombres.\n"
        "3) Si el documento no menciona explícitamente el tema, dilo claramente.\n"
        "4) Considera variaciones ortográficas/semánticas al interpretar el texto, pero NO inventes información.\n"
        "5) Si no hay información suficiente, sugiere posibles archivos donde podría estar la respuesta.\n"
        "- Cita al final las 'Fuentes' con nombre y ruta.\n"
        "- Si el contexto entra en conflicto, explica la discrepancia brevemente.\n"
    )
    prompt_llm = (
        f"{instrucciones}\n\nPregunta del usuario:\n{prompt}\n\n=== CONTEXTO ===\n{contexto}\n=== FIN CONTEXTO ==="
    )

    try:
        respuesta = analyze_document_with_groq(prompt_llm, "consulta_documentos")
    except Exception:
        respuesta = None

    if not respuesta or not respuesta.strip():
        suggestions = search_user_documents(user_id, prompt)
        if suggestions:
            posibles = "\n".join([f"- {s.get('filename')} (ruta: {s.get('file_path')})" for s in suggestions[:6]])
            return (
                "No fue posible redactar una respuesta solo con el contexto disponible.\n"
                "Podría estar en:\n" + posibles
            )
        return None

    fuentes_txt = "\n".join([f"- {n} (ruta: {p})" for n, p in fuentes_unicas])
    respuesta_final = respuesta.strip() + "\n\nFuentes:\n" + fuentes_txt

    try:
        respuesta_final = rewrite_with_editor(respuesta_final, "Mantén nombres y rutas exactas; sin encabezados tipo informe.")
    except Exception:
        pass

    return respuesta_final

def render_latex_in_message(content):
    inline_pattern = r'\$(.*?)\$'
    block_pattern = r'\$\$(.*?)\$\$'
    
    content = re.sub(block_pattern, r'<div class="latex-formula">\1</div>', content)
    content = re.sub(inline_pattern, r'<span class="latex-formula">\1</span>', content)
    
    return content

def chat_page():
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
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
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
    
    prompt = st.chat_input(
        "Escribe tu mensaje...",
        key=f"chat_input_{st.session_state.get('user_id','anon')}_{st.session_state.get('current_chat','default')}"
    )
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        if is_greeting_or_smalltalk(prompt):
            pass
        else:
            local = maybe_answer_doc_query(prompt, st.session_state.get("user_id"))
            if local:
                try:
                    local = rewrite_with_editor(local, "Mantén el listado y rutas tal cual.")
                except Exception:
                    pass
                st.session_state.messages.append({"role": "assistant", "content": local})
                save_current_chat()
                st.rerun()
                return

            if st.session_state.get("user_id") and is_analysis_question(prompt):
                doc_answer = answer_with_docs(prompt, st.session_state.user_id)
                if doc_answer:
                    st.session_state.messages.append({"role": "assistant", "content": doc_answer})
                    save_current_chat()
                    st.rerun()
                    return

            if is_advice_question(prompt):
                advice = generate_advice_response(
                    prompt,
                    st.session_state.get("user_id"),
                    st.session_state.messages
                )
                if advice:
                    st.session_state.messages.append({"role": "assistant", "content": advice})
                    save_current_chat()
                    st.rerun()
                    return

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
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
                
                # Determinar API key a usar (empresa → global)
                current_api_key = GROQ_API_KEY
                try:
                    emp = db.get_company_by_id(st.session_state.get("empresa_id")) if st.session_state.get("empresa_id") else None
                    if emp and emp.get("groq_api_key"):
                        current_api_key = emp.get("groq_api_key")
                except Exception:
                    pass

                if not current_api_key:
                    full_response = "GROQ_API_KEY no configurada para esta empresa ni globalmente. Configura una API key."
                    message_placeholder.markdown(full_response)
                else:
                    messages_for_api = [_system_prompt()] + st.session_state.messages.copy()
                    payload = {
                        "model": _company_model(GROQ_TEXT_MODEL),
                        "messages": messages_for_api,
                        "stream": True,
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                    response = requests.post(API_URL, headers=_company_ai_headers(True), json=payload, stream=True, timeout=120)
                    
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
                        if not full_response.strip():
                            full_response = "La IA no devolvió contenido. Revisa el modelo o reintenta."
                        try:
                            if is_analysis_question(prompt) or is_advice_question(prompt):
                                final = rewrite_with_editor(full_response)
                                if final:
                                    full_response = final
                        except Exception:
                            pass
                        final_response = render_latex_in_message(full_response)
                        message_placeholder.markdown(final_response, unsafe_allow_html=True)
                    else:
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

def image_page():
    st.title("🖼️ Análisis de Imágenes")
    st.write("Sube una imagen para que Zero la analice usando Groq Vision.")
    
    uploaded_file = st.file_uploader(
        "Elige una imagen",
        type=["jpg", "jpeg", "png", "gif", "bmp", "webp"]
    )
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption=uploaded_file.name, use_column_width=True)
        
        if st.button("🔍 Analizar Imagen", type="primary"):
            with st.spinner("Analizando imagen..."):
                image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                
                analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                
                st.subheader("📋 Análisis de la Imagen")
                st.write(analysis)
                
                edited_analysis = rewrite_with_editor(analysis, "Mantén el análisis técnico pero hazlo más claro y conciso.")
                if st.session_state.get("user_id"):
                    try:
                        image_disk_path = f"uploads/{st.session_state.user_id}/{uploaded_file.name}"
                        db.save_image_analysis(
                            user_id=st.session_state.user_id,
                            image_path=image_disk_path,
                            analysis_result=edited_analysis,
                            model_used=GROQ_VISION_MODEL
                        )
                        st.success("✅ Análisis guardado en tu historial")
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo guardar el análisis: {str(e)}")

def audio_page():
    st.title("🎤 Transcripción de Audio")
    st.write("Habla y Zero convertirá tu voz a texto.")
    
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    if webrtc_ctx.audio_receiver:
        st.write("🎙️ Grabando... Habla ahora")
        
        audio_frames = []
        while True:
            try:
                audio_frame = webrtc_ctx.audio_receiver.get_frame(timeout=1)
                audio_frames.append(audio_frame)
            except queue.Empty:
                break
        
        if audio_frames:
            st.write("🔄 Procesando audio...")
            st.write("📝 **Transcripción:** [Funcionalidad en desarrollo]")

def register_page():
    st.title("🛠️ Panel Admin")
    
    if st.session_state.get("rol") != "admin":
        st.error("❌ Acceso denegado. Solo administradores.")
        return
    
    # Datos iniciales
    try:
        companies = db.list_companies()
    except Exception:
        companies = []
    try:
        users = db.list_users()
    except Exception:
        users = []

    tab1, tab2, tab3 = st.tabs(["Crear Empresa", "Asignar Usuario", "Empresas"])

    # --- Crear Empresa ---
    with tab1:
        st.subheader("Nueva Empresa")
        with st.form("form_create_company"):
            nombre = st.text_input("Nombre")
            slug = st.text_input("Slug (opcional)")
            model_name = st.text_input("Modelo IA (opcional)", value=GROQ_TEXT_MODEL)
            groq_api_key = st.text_input("Groq API Key (opcional)", type="password")
            settings_json = st.text_area("Settings JSON (opcional)")

            submitted = st.form_submit_button("Crear empresa", type="primary")
            if submitted:
                if not nombre.strip():
                    st.error("Nombre es requerido")
                else:
                    settings = None
                    if settings_json and settings_json.strip():
                        try:
                            settings = json.loads(settings_json)
                        except Exception as e:
                            st.warning(f"Settings inválidos: {e}")
                    try:
                        empresa_id = db.create_company(
                            nombre.strip(),
                            slug.strip() or None,
                            settings,
                            groq_api_key.strip() or None,
                            model_name.strip() or None
                        )
                        st.success(f"Empresa creada: id {empresa_id}")
                        companies = db.list_companies()
                    except Exception as e:
                        st.error(f"Error creando empresa: {e}")

    # --- Asignar Usuario ---
    with tab2:
        st.subheader("Asignar Usuario a Empresa")
        if not users or not companies:
            st.info("Primero asegúrate de tener usuarios y empresas creadas.")
        else:
            user_opt = st.selectbox(
                "Usuario",
                options=[(u['id'], u['username']) for u in users],
                format_func=lambda x: f"{x[1]} (id: {x[0]})"
            )
            comp_opt = st.selectbox(
                "Empresa",
                options=[(c['id'], c['nombre']) for c in companies],
                format_func=lambda x: f"{x[1]} (id: {x[0]})"
            )
            if st.button("Asignar", type="primary"):
                try:
                    ok = db.assign_user_to_company(user_opt[0], comp_opt[0])
                    if ok:
                        st.success(f"Usuario {user_opt[1]} asignado a {comp_opt[1]}")
                        if st.session_state.get('user_id') == user_opt[0]:
                            st.session_state.empresa_id = comp_opt[0]
                    else:
                        st.error("No se pudo asignar usuario")
                except Exception as e:
                    st.error(f"Error asignando: {e}")

    # --- Empresas ---
    with tab3:
        st.subheader("Empresas registradas")
        if not companies:
            st.info("No hay empresas aún.")
        else:
            for c in companies:
                with st.expander(f"{c.get('nombre')} (id: {c.get('id')})", expanded=False):
                    st.write(f"Slug: {c.get('slug')}")
                    st.write(f"Modelo: {c.get('model_name')}")
                    # Ajustes de seguridad y cifrado por empresa
                    try:
                        settings = db.get_company_settings(c.get('id')) or {}
                    except Exception:
                        settings = {}
                    enc_enabled = bool(settings.get("encrypt_files"))

                    with st.form(f"settings_company_{c.get('id')}"):
                        enc_checked = st.checkbox(
                            "Encriptar archivos de esta empresa",
                            value=enc_enabled,
                            key=f"enc_chk_{c.get('id')}"
                        )
                        save_settings = st.form_submit_button("Guardar ajustes", type="primary")
                        if save_settings:
                            ok = db.update_company_settings(c.get('id'), {"encrypt_files": bool(enc_checked)})
                            if ok and enc_checked:
                                try:
                                    db.ensure_empresa_key(c.get('id'))
                                except Exception as e:
                                    st.warning(f"No se pudo asegurar clave de cifrado: {e}")
                            st.success("Ajustes actualizados")

                    if enc_enabled:
                        if st.button("Rotar clave de cifrado", key=f"rotar_{c.get('id')}"):
                            try:
                                v = db.rotate_empresa_key(c.get('id'))
                                st.success(f"Clave rotada. Nueva versión: {v}")
                            except Exception as e:
                                st.error(f"No se pudo rotar clave: {e}")

                    # Export CSV inline
                    try:
                        files = db.get_company_files(c.get('id'))
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        writer.writerow(["file_id","user_id","filename","file_type","file_size","uploaded_at","analysis_summary"])
                        for doc in files:
                            writer.writerow([
                                doc.get("id"), doc.get("user_id"), doc.get("filename"), doc.get("file_type"),
                                doc.get("file_size"), doc.get("uploaded_at"), (doc.get("analysis_summary") or "").replace("\n"," ")
                            ])
                        csv_bytes = buf.getvalue().encode("utf-8")
                        st.download_button(
                            label="Descargar CSV de documentos",
                            data=csv_bytes,
                            file_name=f"empresa_{c.get('id')}_documentos.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.warning(f"No se pudo generar CSV: {e}")

def file_upload_page():
    st.title("📁 Gestión de Archivos")
    st.write("Sube documentos e imágenes para que Zero pueda usarlos en las conversaciones.")

    if not st.session_state.get("usuario"):
        st.error("❌ Error de sesión. Por favor, vuelve a iniciar sesión.")
        return

    username = st.session_state.usuario
    user_id = db.get_user_id_by_username(username)

    if not user_id:
        st.error("❌ No se pudo obtener la información del usuario.")
        return

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
                file_id, error = save_uploaded_file(uploaded_file)
                if error:
                    st.error(f"❌ Error al procesar archivo: {error}")
                else:
                    st.success("✅ Archivo procesado y guardado exitosamente")
                    if uploaded_file.type.startswith('image/'):
                        with st.spinner("Analizando imagen con Groq Vision..."):
                            image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                            analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                            # Usar la ruta real guardada (puede ser cifrada)
                            file_rec = db.get_file_by_id(file_id)
                            real_path = file_rec.get("file_path") if file_rec else f"user_uploads/{user_id}/{uploaded_file.name}"
                            db.save_image_analysis(
                                user_id=user_id,
                                image_path=real_path,
                                analysis_result=analysis,
                                model_used=_company_model(GROQ_VISION_MODEL),
                                archivo_id=file_id
                            )
                            context_key = f"Análisis de imagen: {uploaded_file.name}"
                            db.save_user_context(user_id, context_key, analysis, file_id)
                            st.success("🖼️ Imagen analizada con Groq Vision")
                    st.session_state.user_files = db.get_user_files(user_id)
                    st.session_state.user_context = db.get_user_context(user_id)
                    st.rerun()

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
                            st.session_state.current_page = "chat"
                            st.success(f"📄 Contenido de {file_data['filename']} agregado al chat")
                            st.rerun()
    else:
        st.info("📭 No tienes archivos subidos aún. ¡Sube tu primer archivo!")

def pqrs_page():
    st.title("📮 PQRS")
    st.write("Escribe tu mensaje y envíalo por correo. El mensaje será enviado automáticamente a soporte@zero-va.com.")

    with st.form("pqrs_form"):
        dest_email = "soporte@zero-va.com"
        subject = st.text_input("Asunto:", value="")
        message_body = st.text_area("Mensaje:", height=200)
        submit = st.form_submit_button("Enviar mensaje")

    if submit:
        if not subject.strip():
            st.error("Por favor indica el asunto del mensaje.")
        elif not message_body.strip():
            st.error("Escribe el mensaje antes de enviar.")
        else:
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

def main():
    qp = st.query_params
    usuario_qp = qp.get("usuario")
    if usuario_qp:
        st.session_state.usuario = usuario_qp
        user_info = db.get_user_by_username(usuario_qp)
        if user_info:
            st.session_state.rol = user_info.get("rol", "usuario")
            st.session_state.user_id = user_info.get("id")
            st.session_state.empresa_id = user_info.get("empresa_id")

    if st.session_state.get("user_id") and not st.session_state.get("files_synced"):
        try:
            sync_user_files_from_disk(st.session_state.user_id)
            st.session_state.user_files = db.get_user_files(st.session_state.user_id)
        except Exception:
            pass
        st.session_state.files_synced = True

    create_sidebar()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "chat"

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