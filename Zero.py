# Zero_personalizado.py — Chat (Groq) + "Mis archivos" (RAG BM25 interno) + Imagen + Audio + Registro
# ---------------------------------------------------------------------------------------------------
# Requisitos (sin OpenAI):
#   pip install streamlit requests PyPDF2 python-docx pandas openpyxl streamlit-webrtc SpeechRecognition av numpy pillow python-dotenv twilio
#   (Opcional para OCR local) -> pip install pytesseract
#   Nota OCR: Instala Tesseract en Windows (ruta típica C:\Program Files\Tesseract-OCR\tesseract.exe) y los idiomas spa/eng.
#
# Variables .env (coloca en el mismo directorio):
#   GROQ_API_KEY=tu_api_key_de_groq
#   GROQ_TEXT_MODEL=llama-3.3-70b-versatile
#   GROQ_VISION_MODEL=llama-3.2-11b-vision-preview

import os
import io
import json
import uuid
import queue
import pathlib
import math
import requests
from typing import List, Dict, Any
from collections import Counter
from base64 import b64encode

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# Audio
import av
import speech_recognition as sr
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Twilio (opcional)
from twilio.rest import Client

# Lectura de documentos
from PyPDF2 import PdfReader          # PDF
from docx import Document             # DOCX

# Login propio del proyecto (debes tener este módulo en tu proyecto)
from Login import verificar_login, logout, registrar_usuario

# =============================================================================
# Config inicial
# =============================================================================
load_dotenv()

st.set_page_config(
    page_title="ZERO - Asistente Virtual (Groq)",
    page_icon="favicon.ico",
    layout="centered",
    initial_sidebar_state="auto"
)

# =============================================================================
# Estilos (look&feel)
# =============================================================================
def load_css():
    st.markdown("""
    <style>
    /* ========== VARIABLES FUTURISTAS ========== */
    :root {
        --primary-neon: #00ffff;
        --secondary-neon: #ff00ff;
        --accent-electric: #00ff88;
        --bg-dark: #0a0a0f;
        --bg-glass: rgba(15, 15, 25, 0.8);
        --text-bright: #ffffff;
        --text-glow: #e0e0ff;
        --hologram-1: linear-gradient(45deg, #00ffff, #ff00ff, #00ff88);
        --hologram-2: linear-gradient(135deg, #ff00ff, #00ffff, #ffff00);
        --glass-border: rgba(255, 255, 255, 0.2);
        --shadow-neon: 0 0 20px rgba(0, 255, 255, 0.5);
        --font-cyber: 'Orbitron', 'Courier New', monospace;
        --font-modern: 'Exo 2', 'Arial', sans-serif;
    }

    /* ========== IMPORTAR FUENTES FUTURISTAS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600;700&display=swap');

    /* ========== ANIMACIONES AVANZADAS ========== */
    @keyframes hologramShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    @keyframes neonPulse {
        0%, 100% { 
            box-shadow: 0 0 5px var(--primary-neon), 0 0 10px var(--primary-neon), 0 0 15px var(--primary-neon);
            text-shadow: 0 0 5px var(--primary-neon);
        }
        50% { 
            box-shadow: 0 0 10px var(--primary-neon), 0 0 20px var(--primary-neon), 0 0 30px var(--primary-neon);
            text-shadow: 0 0 10px var(--primary-neon);
        }
    }

    @keyframes dataStream {
        0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { transform: translateY(-100vh) rotate(360deg); opacity: 0; }
    }

    @keyframes glitchEffect {
        0%, 100% { transform: translate(0); }
        20% { transform: translate(-2px, 2px); }
        40% { transform: translate(-2px, -2px); }
        60% { transform: translate(2px, 2px); }
        80% { transform: translate(2px, -2px); }
    }

    @keyframes matrixRain {
        0% { transform: translateY(-100vh); }
        100% { transform: translateY(100vh); }
    }

    /* ========== FONDO FUTURISTA CON EFECTOS ========== */
    .stApp {
        background: var(--bg-dark);
        background-image: 
            radial-gradient(circle at 20% 80%, rgba(0, 255, 255, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 0, 255, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(0, 255, 136, 0.1) 0%, transparent 50%);
        position: relative;
        overflow-x: hidden;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            linear-gradient(90deg, transparent 98%, rgba(0, 255, 255, 0.03) 100%),
            linear-gradient(0deg, transparent 98%, rgba(255, 0, 255, 0.03) 100%);
        background-size: 50px 50px;
        animation: dataStream 20s linear infinite;
        pointer-events: none;
        z-index: 1;
    }

    /* ========== OCULTAR ELEMENTOS STREAMLIT ========== */
    .stDeployButton, #MainMenu, footer, header {
        visibility: hidden !important;
    }

    /* ========== CONTENEDOR PRINCIPAL GLASSMORPHISM ========== */
    .main .block-container {
        background: var(--bg-glass);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem;
        box-shadow: var(--shadow-neon);
        position: relative;
        z-index: 10;
    }

    .main .block-container::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: var(--hologram-1);
        background-size: 400% 400%;
        animation: hologramShift 3s ease infinite;
        border-radius: 22px;
        z-index: -1;
    }

    /* ========== SIDEBAR FUTURISTA ========== */
    .css-1d391kg {
        background: linear-gradient(180deg, rgba(10, 10, 15, 0.95) 0%, rgba(20, 20, 30, 0.95) 100%);
        backdrop-filter: blur(15px);
        border-right: 2px solid var(--primary-neon);
        box-shadow: 5px 0 15px rgba(0, 255, 255, 0.3);
    }

    .sidebar-title {
        font-family: var(--font-cyber);
        font-size: 1.8rem;
        font-weight: 900;
        background: var(--hologram-2);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: hologramShift 2s ease infinite, neonPulse 2s ease-in-out infinite;
        text-align: center;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 3px;
    }

    .sidebar-section-title {
        font-family: var(--font-modern);
        font-size: 1rem;
        font-weight: 600;
        color: var(--accent-electric);
        text-shadow: 0 0 10px var(--accent-electric);
        margin: 1.5rem 0 0.8rem 0;
        padding: 0.5rem;
        border-left: 3px solid var(--accent-electric);
        background: rgba(0, 255, 136, 0.1);
        border-radius: 0 10px 10px 0;
    }

    /* ========== BOTONES FUTURISTAS ========== */
    .stButton > button {
        background: linear-gradient(45deg, var(--primary-neon), var(--secondary-neon));
        color: var(--bg-dark);
        border: none;
        border-radius: 15px;
        padding: 0.8rem 1.5rem;
        font-family: var(--font-modern);
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 255, 255, 0.4);
    }

    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        transition: left 0.5s;
    }

    .stButton > button:hover {
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 8px 25px rgba(0, 255, 255, 0.6);
        animation: neonPulse 1s ease-in-out infinite;
    }

    .stButton > button:hover::before {
        left: 100%;
    }

    /* ========== CHAT CONTAINER FUTURISTA ========== */
    .chat-container {
        background: rgba(15, 15, 25, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        position: relative;
    }

    .chat-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--hologram-1);
        background-size: 200% 200%;
        animation: hologramShift 2s linear infinite;
    }

    /* ========== MENSAJES DEL CHAT ========== */
    .message {
        margin: 1rem 0;
        animation: fadeInUp 0.5s ease-out;
    }

    .user-message {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(0, 255, 136, 0.2));
        color: var(--text-bright);
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 5px 20px;
        border: 1px solid var(--primary-neon);
        margin-left: 20%;
        font-family: var(--font-modern);
        box-shadow: 0 4px 15px rgba(0, 255, 255, 0.3);
        position: relative;
    }

    .user-message::before {
        content: '👤';
        position: absolute;
        top: -10px;
        right: -10px;
        background: var(--primary-neon);
        color: var(--bg-dark);
        border-radius: 50%;
        width: 25px;
        height: 25px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
    }

    .assistant-message {
        background: linear-gradient(135deg, rgba(255, 0, 255, 0.2), rgba(255, 255, 0, 0.1));
        color: var(--text-glow);
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        border: 1px solid var(--secondary-neon);
        margin-right: 20%;
        font-family: var(--font-modern);
        box-shadow: 0 4px 15px rgba(255, 0, 255, 0.3);
        position: relative;
    }

    .assistant-message::before {
        content: '🤖';
        position: absolute;
        top: -10px;
        left: -10px;
        background: var(--secondary-neon);
        color: var(--bg-dark);
        border-radius: 50%;
        width: 25px;
        height: 25px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        animation: neonPulse 2s ease-in-out infinite;
    }

    /* ========== INPUTS FUTURISTAS ========== */
    .stTextInput > div > div > input {
        background: rgba(15, 15, 25, 0.8);
        border: 2px solid var(--primary-neon);
        border-radius: 15px;
        color: var(--text-bright);
        font-family: var(--font-modern);
        padding: 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--accent-electric);
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        background: rgba(0, 255, 136, 0.1);
    }

    /* ========== CHAT INPUT ESPECIAL ========== */
    .stChatInput > div {
        background: rgba(15, 15, 25, 0.9);
        border: 2px solid var(--primary-neon);
        border-radius: 25px;
        backdrop-filter: blur(10px);
    }

    .stChatInput input {
        background: transparent;
        color: var(--text-bright);
        font-family: var(--font-modern);
        font-size: 1rem;
        border: none;
    }

    /* ========== LISTA DE CHATS ========== */
    .chat-list {
        max-height: 300px;
        overflow-y: auto;
        padding: 0.5rem;
    }

    .chat-item {
        background: rgba(0, 255, 255, 0.1);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 10px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: var(--font-modern);
    }

    .chat-item:hover {
        background: rgba(0, 255, 255, 0.2);
        border-color: var(--primary-neon);
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(0, 255, 255, 0.4);
    }

    .chat-preview {
        font-size: 0.8rem;
        color: var(--text-glow);
        opacity: 0.8;
        margin-top: 0.3rem;
    }

    /* ========== TÍTULOS FUTURISTAS ========== */
    h1, h2, h3 {
        font-family: var(--font-cyber);
        background: var(--hologram-1);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: hologramShift 3s ease infinite;
        text-align: center;
        margin: 1.5rem 0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* ========== SLIDERS Y CONTROLES ========== */
    .stSlider > div > div > div {
        background: var(--primary-neon);
    }

    .stToggle > div {
        background: rgba(0, 255, 255, 0.2);
        border: 1px solid var(--primary-neon);
        border-radius: 20px;
    }

    /* ========== SELECTBOX FUTURISTA ========== */
    .stSelectbox > div > div {
        background: rgba(15, 15, 25, 0.8);
        border: 2px solid var(--primary-neon);
        border-radius: 15px;
        color: var(--text-bright);
    }

    /* ========== RADIO BUTTONS ========== */
    .stRadio > div {
        background: rgba(15, 15, 25, 0.6);
        border-radius: 15px;
        padding: 1rem;
        border: 1px solid var(--glass-border);
    }

    .stRadio label {
        color: var(--text-bright);
        font-family: var(--font-modern);
        padding: 0.5rem;
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    .stRadio label:hover {
        background: rgba(0, 255, 255, 0.1);
        color: var(--primary-neon);
    }

    /* ========== FILE UPLOADER ========== */
    .stFileUploader > div {
        background: rgba(15, 15, 25, 0.8);
        border: 2px dashed var(--accent-electric);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .stFileUploader > div:hover {
        border-color: var(--primary-neon);
        background: rgba(0, 255, 255, 0.1);
        box-shadow: 0 4px 20px rgba(0, 255, 255, 0.3);
    }

    /* ========== ALERTAS Y NOTIFICACIONES ========== */
    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(0, 255, 255, 0.1));
        border: 1px solid var(--accent-electric);
        border-radius: 15px;
        color: var(--accent-electric);
        font-family: var(--font-modern);
    }

    .stError {
        background: linear-gradient(135deg, rgba(255, 0, 100, 0.2), rgba(255, 0, 255, 0.1));
        border: 1px solid #ff0066;
        border-radius: 15px;
        color: #ff0066;
        font-family: var(--font-modern);
    }

    .stInfo {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(255, 0, 255, 0.1));
        border: 1px solid var(--primary-neon);
        border-radius: 15px;
        color: var(--primary-neon);
        font-family: var(--font-modern);
    }

    /* ========== DISCLAIMER FUTURISTA ========== */
    .disclaimer {
        text-align: center;
        font-size: 0.8rem;
        color: var(--text-glow);
        opacity: 0.7;
        margin-top: 1rem;
        padding: 0.5rem;
        border-top: 1px solid rgba(0, 255, 255, 0.3);
        font-family: var(--font-modern);
        font-style: italic;
    }

    /* ========== EFECTOS ESPECIALES ========== */
    .matrix-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        opacity: 0.1;
    }

    .matrix-char {
        position: absolute;
        color: var(--accent-electric);
        font-family: 'Courier New', monospace;
        font-size: 14px;
        animation: matrixRain 10s linear infinite;
    }

    /* ========== SCROLLBAR FUTURISTA ========== */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(15, 15, 25, 0.5);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary-neon), var(--secondary-neon));
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, var(--accent-electric), var(--primary-neon));
    }

    /* ========== ANIMACIONES DE ENTRADA ========== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* ========== RESPONSIVE DESIGN ========== */
    @media (max-width: 768px) {
        .main .block-container {
            margin: 0.5rem;
            padding: 1rem;
        }
        
        .sidebar-title {
            font-size: 1.4rem;
        }
        
        .user-message, .assistant-message {
            margin-left: 5%;
            margin-right: 5%;
        }
    }

    /* ========== EFECTOS HOVER GLOBALES ========== */
    * {
        transition: all 0.3s ease;
    }

    /* ========== LOADING SPINNER FUTURISTA ========== */
    .stSpinner > div {
        border-color: var(--primary-neon) transparent var(--secondary-neon) transparent;
        animation: spin 1s linear infinite, neonPulse 2s ease-in-out infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# Servicios externos: Groq y Twilio
# =============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

if not GROQ_API_KEY:
    st.error("Falta GROQ_API_KEY en el .env")
    st.stop()

# Cliente Twilio opcional
try:
    twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
except Exception as e:
    st.warning(f"No se pudo inicializar Twilio: {e}")

# =============================================================================
# Estado de sesión
# =============================================================================
def init_session():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thinking" not in st.session_state:
        st.session_state.thinking = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = str(uuid.uuid4())

init_session()

# =============================================================================
# Personalidad del asistente
# =============================================================================
def system_prompt_text() -> str:
    return (
        "Eres ZERO, un asistente digital especializado en la optimización de búsqueda y análisis de información "
        "para facilitar la accesibilidad y distribución de datos. Sé claro, profesional y útil. "
        "Cuando recibas CONTEXT_START/CONTEXT_END, usa ese contexto y cita el archivo cuando corresponda."
    )

# =============================================================================
# Groq API helpers (chat y visión)
# =============================================================================
def groq_chat_completion(messages: List[Dict[str, Any]], max_tokens: int = 1200, temperature: float = 0.7) -> str:
    """
    Llama a Groq /openai/v1/chat/completions (no streaming).
    messages: [{"role":"system"/"user"/"assistant","content":str}, ...]
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_TEXT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as e:
        return f"(Error con Groq chat: {e})"

def groq_vision_ocr(image_bytes: bytes) -> str:
    """
    OCR con Groq visión: devuelve SOLO el texto extraído.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    b64 = b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": GROQ_VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "Eres un OCR. Devuelve SOLO el texto legible de la imagen, sin comentarios."},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": "Extrae el TEXTO TAL CUAL se lee en la imagen."}
                ]
            }
        ]
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""

# =============================================================================
# UI helpers de chat
# =============================================================================
def display_message(role, content):
    if role == "assistant":
        clean = str(content).replace("Zero:", "").strip()
        st.markdown(f"<div class='message'><div class='assistant-message'>{clean}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='message'><div class='user-message'>{content}</div></div>", unsafe_allow_html=True)

def save_current_chat():
    if st.session_state.messages and "usuario" in st.session_state:
        first = st.session_state.messages[0]["content"] if st.session_state.messages else "Nuevo chat"
        title = first[:30] + "..." if len(first) > 30 else first
        st.session_state.chat_history.setdefault(st.session_state.usuario, {})
        st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
            "title": title, "messages": st.session_state.messages.copy()
        }

def load_chat(chat_id):
    if "usuario" in st.session_state and chat_id in st.session_state.chat_history.get(st.session_state.usuario, {}):
        st.session_state.current_chat = chat_id
        st.session_state.messages = st.session_state.chat_history[st.session_state.usuario][chat_id]["messages"].copy()
        st.rerun()

# =============================================================================
# ========== RAG por usuario (BM25 interno + almacenamiento local) ==========
# =============================================================================
def _user_root() -> pathlib.Path:
    user = st.session_state.get("usuario", "anon")
    root = pathlib.Path("storage") / user
    root.mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "index").mkdir(exist_ok=True)
    return root

def _index_path() -> pathlib.Path:
    return _user_root() / "index" / "bm25_index.json"

def _load_index() -> Dict[str, Any]:
    p = _index_path()
    if not p.exists():
        return {"docs": [], "chunks": [], "tokens": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"docs": [], "chunks": [], "tokens": []}

def _save_index(idx: Dict[str, Any]) -> None:
    _index_path().write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

def _simple_tokenize(txt: str) -> List[str]:
    return [t for t in "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in txt.lower()).split() if t]

# --- Lectura de archivos ---
def _read_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages)

def _read_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                t = cell.text.strip()
                if t:
                    parts.append(t)
    return "\n".join(parts)

def _read_pptx(file_bytes: bytes) -> str:
    """
    Extrae texto de .pptx leyendo los XML internos (sin python-pptx).
    Captura títulos, cuadros de texto y celdas de tablas básicas.
    """
    import zipfile
    from xml.etree import ElementTree as ET

    parts = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            slide_names = sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
            ns = {
                "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
                "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }
            for sname in slide_names:
                try:
                    root = ET.fromstring(z.read(sname))
                    for tnode in root.findall(".//a:t", ns):
                        txt = (tnode.text or "").strip()
                        if txt:
                            parts.append(txt)
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n".join(parts)

def _read_excel(file_bytes: bytes, filename: str) -> str:
    # Lee todas las hojas y concatena en texto tipo CSV
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        parts = []
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            parts.append(f"--- Hoja: {sheet} ---")
            parts.extend(["\t".join(map(lambda x: "" if pd.isna(x) else str(x), row)) for row in df.astype(str).values.tolist()])
        return "\n".join(parts)
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            parts = []
            for sheet, sdf in df.items():
                parts.append(f"--- Hoja: {sheet} ---")
                parts.extend(["\t".join(map(lambda x: "" if pd.isna(x) else str(x), row)) for row in sdf.astype(str).values.tolist()])
            return "\n".join(parts)
        except Exception:
            return ""

def _preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    from PIL import ImageFilter, ImageOps
    w, h = img.size
    scale = 2 if max(w, h) < 1600 else 1
    if scale > 1:
        img = img.resize((w * scale, h * scale))
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    try:
        arr = np.array(img)
        thr = int(arr.mean())
        bw = (arr > thr).astype(np.uint8) * 255
        img = Image.fromarray(bw)
    except Exception:
        pass
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=150, threshold=3))
    return img

def _try_init_tesseract():
    try:
        import pytesseract
        try:
            _ = pytesseract.get_tesseract_version()
            return pytesseract
        except Exception:
            pass
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                _ = pytesseract.get_tesseract_version()
                return pytesseract
        return None
    except Exception:
        return None

def _ocr_with_tesseract(image_bytes: bytes, lang_hint: str = "spa+eng") -> str:
    pytesseract = _try_init_tesseract()
    if not pytesseract:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = _preprocess_image_for_ocr(img)
        cfg = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, lang=lang_hint, config=cfg) or ""
        if len(text.strip()) < 8:
            try:
                osd = pytesseract.image_to_osd(img)
                rot = 0
                for line in osd.splitlines():
                    if "Rotate:" in line:
                        rot = int(line.split(":")[1].strip())
                        break
                if rot in (90, 180, 270):
                    img = img.rotate(360 - rot, expand=True)
                    text2 = pytesseract.image_to_string(img, lang=lang_hint, config=cfg) or ""
                    if len(text2.strip()) > len(text.strip()):
                        text = text2
            except Exception:
                pass
        return text.strip()
    except Exception:
        return ""

def _ocr_with_groq(image_bytes: bytes) -> str:
    return groq_vision_ocr(image_bytes)

def _read_image(file_bytes: bytes) -> str:
    # 1) Tesseract local
    text = _ocr_with_tesseract(file_bytes, lang_hint="spa+eng")
    if text and len(text.strip()) >= 4:
        return text
    # 2) Respaldo con Groq (visión)
    text = _ocr_with_groq(file_bytes)
    return text or ""

def _read_plain(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return file_bytes.decode("latin1", errors="ignore")

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _read_pdf(file_bytes)
    if name.endswith(".docx"):
        return _read_docx(file_bytes)
    if name.endswith(".pptx"):
        return _read_pptx(file_bytes)
    if name.endswith((".xlsx", ".xls")):
        return _read_excel(file_bytes, filename)
    if name.endswith((".txt", ".md", ".csv")):
        return _read_plain(file_bytes)
    if name.endswith((".jpg", ".jpeg", ".png")):
        return _read_image(file_bytes)
    return ""

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> List[str]:
    text = text.replace("\r", "")
    out, i, n = [], 0, len(text)
    while i < n:
        j = min(i + max_chars, n)
        out.append(text[i:j])
        if j == n:
            break
        i = j - overlap
        if i < 0:
            i = 0
    return out

def add_document_to_index(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Guarda el archivo en storage/<usuario>/docs, lo fragmenta y actualiza el índice BM25 interno.
    """
    root = _user_root()
    (root / "docs" / filename).write_bytes(file_bytes)
    text = extract_text_from_file(file_bytes, filename).strip()
    if not text:
        raise ValueError("No se pudo extraer texto del archivo o está vacío.")
    chunks = chunk_text(text, max_chars=1000, overlap=200)
    idx = _load_index()
    start = len(idx["chunks"])
    for k, ch in enumerate(chunks):
        idx["chunks"].append({"filename": filename, "chunk_index": start + k, "text": ch})
    idx["tokens"] = [_simple_tokenize(c["text"]) for c in idx["chunks"]]
    _save_index(idx)
    return {"filename": filename, "num_chunks": len(chunks), "total_chunks": len(idx["chunks"])}

def bm25_search(query: str, top_k: int = 5, k1: float = 1.5, b: float = 0.75) -> List[Dict[str, Any]]:
    idx = _load_index()
    docs_tokens = idx.get("tokens", [])
    chunks = idx.get("chunks", [])
    if not docs_tokens:
        return []
    N = len(docs_tokens)
    df = Counter()
    for d in docs_tokens:
        df.update(set(d))
    idf = {t: math.log(1 + (N - df_t + 0.5) / (df_t + 0.5)) for t, df_t in df.items()}
    avgdl = sum(len(d) for d in docs_tokens) / float(N) if N else 0.0
    q_tokens = _simple_tokenize(query)
    scores = np.zeros(N, dtype=float)
    for i, d in enumerate(docs_tokens):
        dl = len(d) or 1
        tf = Counter(d)
        s = 0.0
        denom_norm = k1 * (1 - b + b * (dl / (avgdl or 1.0)))
        for t in q_tokens:
            f = tf.get(t, 0)
            if f == 0:
                continue
            s += idf.get(t, 0.0) * ((f * (k1 + 1)) / (f + denom_norm))
        scores[i] = s
    order = np.argsort(-scores)[:top_k]
    out = []
    for idx_i in order:
        ch = chunks[int(idx_i)]
        out.append({
            "filename": ch["filename"],
            "chunk_index": ch["chunk_index"],
            "text": ch["text"],
            "score": float(scores[int(idx_i)]),
        })
    return out

# =============================================================================
# Sidebar
# =============================================================================
def sidebar():
    with st.sidebar:
        st.markdown('<div class="sidebar-title">ZERO - Asistente Virtual</div>', unsafe_allow_html=True)
        usuario_nombre = st.session_state.get("usuario", "Usuario")
        st.markdown(f'Hola, <strong>{usuario_nombre}</strong>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-title">🗂️ Menú</div>', unsafe_allow_html=True)
        menu_options = ["Chat Principal", "Mis archivos"]
        if st.session_state.rol == "admin":
            menu_options += ["Análisis de Imágenes", "Transcripción de Audio", "Registro de Usuarios"]
        selected_option = st.radio("", menu_options, key="menu_option", label_visibility="collapsed")

        st.markdown('<div class="sidebar-section-title">💬 Chats anteriores</div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-list">', unsafe_allow_html=True)
        usuario_actual = st.session_state.get("usuario")
        if usuario_actual:
            st.session_state.chat_history.setdefault(usuario_actual, {})
            for chat_id, chat_data in st.session_state.chat_history[usuario_actual].items():
                preview = (chat_data["messages"][-1]["content"][:50] + "...") if chat_data["messages"] else "Vacío"
                st.markdown(
                    f"""
                    <div class="chat-item">
                        <div><strong>{chat_data['title']}</strong></div>
                        <div class="chat-preview">{preview}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Abrir", key=f"open_{chat_id}"):
                    load_chat(chat_id)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("➕ Nuevo Chat", use_container_width=True):
            save_current_chat()
            st.session_state.current_chat = str(uuid.uuid4())
            st.session_state.messages = []
            if "usuario" in st.session_state:
                st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
                    "title": "Nuevo chat", "messages": []
                }
            st.rerun()

        if st.button("🚪 Cerrar sesión", key="logout_btn", use_container_width=True, type="primary"):
            logout()
            st.rerun()

        return selected_option

# =============================================================================
# Página: Mis archivos (subir e indexar)
# =============================================================================
def my_files_page():
    st.title("📚 Mis archivos (Personalización)")
    st.write("Sube **PDF, DOCX, TXT/MD/CSV, EXCEL (.xlsx/.xls), PowerPoint (.pptx) e IMÁGENES (.jpg/.jpeg/.png)**. "
             "Se indexarán para que Zero responda usando tu contenido. "
             "Para OCR en imágenes instala pytesseract + Tesseract; hay respaldo con Groq Visión.")

    uploaded = st.file_uploader(
        "Selecciona archivos",
        type=["pdf","docx","txt","md","csv","xlsx","xls","pptx","jpg","jpeg","png"],
        accept_multiple_files=True
    )

    if uploaded and st.button("Indexar", type="primary"):
        ok, err = 0, 0
        for f in uploaded:
            try:
                info = add_document_to_index(f.name, f.read())
                st.success(f"✅ {info['filename']} — {info['num_chunks']} fragmentos añadidos")
                ok += 1
            except Exception as e:
                st.error(f"❌ {f.name}: {e}")
                err += 1
        st.info(f"Terminado. Éxitos: {ok}, Errores: {err}")

    # Vista rápida del índice (primeros 10)
    idx = _load_index()
    if idx["chunks"]:
        st.markdown("### Vista rápida (primeros 10 fragmentos)")
        for i, ch in enumerate(idx["chunks"][:10]):
            with st.expander(f"{ch['filename']} — frag {i}"):
                st.write(ch["text"])
    else:
        st.info("Aún no hay documentos indexados.")

# =============================================================================
# Chat principal (con toggle RAG) — usa Groq
# =============================================================================
def chat_page():
    st.markdown("<div class='chat-container' id='chat-container'>", unsafe_allow_html=True)

    colA, colB = st.columns([1,1])
    with colA:
        usar_mis_archivos = st.toggle("Usar mis archivos (RAG)", value=True)
    with colB:
        temperature = st.slider("Creatividad", 0.0, 1.2, 0.7, 0.1)

    if len(st.session_state.messages) == 0:
        display_message("assistant", f"Soy ZERO (Groq). ¿En qué puedo ayudarte hoy, {st.session_state.get('usuario','')}?")

    for m in st.session_state.messages:
        display_message(m["role"], m["content"])

    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.chat_input("Escribe tu mensaje aquí...")
    st.markdown('<div class="disclaimer">Zero puede cometer errores. Verifica información importante.</div>', unsafe_allow_html=True)

    if user_input and not st.session_state.thinking:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.thinking = True
        save_current_chat()
        st.rerun()

    if st.session_state.thinking:
        extra_messages = []
        if usar_mis_archivos and st.session_state.messages:
            last_user = st.session_state.messages[-1]["content"]
            hits = bm25_search(last_user, top_k=5)
            if hits:
                ctx_lines = []
                for h in hits:
                    snippet = h["text"].replace("\n"," ").strip()
                    ctx_lines.append(f"[{h['filename']}#{h['chunk_index']}] {snippet}")
                context_block = "\n".join(ctx_lines)[:6000]
                extra_messages = [{
                    "role": "system",
                    "content": (
                        "CONTEXT_START\n" + context_block +
                        "\nCONTEXT_END\nUsa este contexto si es relevante y cita el nombre del archivo cuando corresponda."
                    ),
                }]

        history_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        final_messages = [
            {"role": "system", "content": system_prompt_text()}
        ] + history_msgs[:-1] + extra_messages + [history_msgs[-1]]

        # Llamada no-streaming a Groq
        reply = groq_chat_completion(final_messages, max_tokens=1200, temperature=temperature)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_current_chat()

        st.session_state.thinking = False
        st.rerun()

# =============================================================================
# Página: Análisis de Imágenes (usa Groq visión)
# =============================================================================
def image_page():
    st.title("🖼️ Análisis de Imágenes (Groq visión)")
    st.write("Sube una imagen para que Zero la analice o para extraer texto (OCR).")

    uploaded_image = st.file_uploader("Elige una imagen", type=["jpg", "png", "jpeg"])
    if uploaded_image:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(uploaded_image, width=300)

        image_bytes = uploaded_image.getvalue()
        with st.spinner("Analizando con Groq visión..."):
            # Prompt genérico de análisis
            b64 = b64encode(image_bytes).decode("utf-8")
            messages = [
                {"role": "system", "content": "Eres un analista de imágenes. Sé claro y conciso."},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": "Describe la imagen y dame insights útiles."},
                ]},
            ]
            analysis = groq_chat_completion(messages, max_tokens=800, temperature=0.2)

            # OCR adicional
            text_ocr = _read_image(image_bytes)

        with col2:
            st.markdown("### Análisis de Zero")
            st.write(analysis)
            st.markdown("### Texto (OCR)")
            if text_ocr:
                st.code(text_ocr)
                if st.button("Guardar OCR como documento", type="primary"):
                    try:
                        fname = f"OCR_{uploaded_image.name}.txt"
                        add_document_to_index(fname, text_ocr.encode("utf-8"))
                        st.success("OCR guardado e indexado correctamente.")
                    except Exception as e:
                        st.error(f"No se pudo guardar el OCR: {e}")
            else:
                st.info("No se detectó texto legible.")

# =============================================================================
# Transcripción de Audio (igual que antes)
# =============================================================================
def audio_page():
    st.title("🎙️ Transcripción de Audio")
    st.write("Habla y Zero convertirá tu voz en texto")
    audio_queue = queue.Queue()

    class AudioProcessor:
        def __init__(self):
            self.recognizer = sr.Recognizer()
            self.sample_rate = 16000
        def recv(self, frame: av.AudioFrame):
            if hasattr(frame, "sample_rate") and frame.sample_rate:
                self.sample_rate = int(frame.sample_rate)
            audio = frame.to_ndarray()
            if audio.ndim > 1:
                audio = np.mean(audio, axis=0)
            audio = audio.astype(np.int16)
            audio_queue.put((audio.tobytes(), self.sample_rate))
            return av.AudioFrame.from_ndarray(audio, layout="mono")

    webrtc_ctx = webrtc_streamer(
        key="audio_transcriber",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=256,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"audio": True, "video": False},
        audio_processor_factory=AudioProcessor,
    )

    if webrtc_ctx.state.playing and st.button("Detener grabación"):
        webrtc_ctx.stop(); st.rerun()

    if st.button("Transcribir audio grabado", type="primary") and not audio_queue.empty():
        try:
            raw_chunks, srates = [], []
            while not audio_queue.empty():
                raw, rate = audio_queue.get()
                raw_chunks.append(raw); srates.append(rate)
            audio_bytes = b"".join(raw_chunks)
            sample_rate = int(np.bincount(np.array(srates)).argmax()) if len(set(srates)) > 1 else srates[0]
            recognizer = sr.Recognizer()
            audio_data = sr.AudioData(audio_bytes, sample_rate=sample_rate, sample_width=2)
            text = recognizer.recognize_google(audio_data, language="es-ES")
            st.success("Texto reconocido:"); st.write(text)
            if st.button("Usar en chat principal", type="primary"):
                st.session_state.messages.append({"role": "user", "content": text})
                save_current_chat(); st.rerun()
        except sr.UnknownValueError:
            st.error("No se pudo entender el audio")
        except sr.RequestError as e:
            st.error(f"Error en el servicio de reconocimiento: {e}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

# =============================================================================
# Registro de Usuarios (igual que antes)
# =============================================================================
def register_page():
    st.title("📝 Registro de Usuarios")
    with st.form("register_form"):
        username = st.text_input("Nombre de usuario", max_chars=20)
        password = st.text_input("Contraseña", type="password")
        confirm_password = st.text_input("Confirmar contraseña", type="password")
        role = st.selectbox("Rol", ["usuario", "admin"])
        submitted = st.form_submit_button("Registrar", type="primary")
        if submitted:
            if password != confirm_password:
                st.error("Las contraseñas no coinciden")
            elif len(username) < 3:
                st.error("El nombre de usuario debe tener al menos 3 caracteres")
            elif len(password) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres")
            else:
                registrar_usuario(username, password, role)
                st.success(f"Usuario {username} registrado exitosamente")

# =============================================================================
# Router
# =============================================================================
def sidebar_router():
    choice = sidebar()
    if choice == "Chat Principal":
        chat_page()
    elif choice == "Mis archivos":
        my_files_page()
    elif choice == "Análisis de Imágenes":
        image_page()
    elif choice == "Transcripción de Audio":
        audio_page()
    elif choice == "Registro de Usuarios":
        register_page()

# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    if not st.session_state.get("autenticado", False):
        verificar_login()
    else:
        sidebar_router()
