
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import speech_recognition as sr
import time
from Login import verificar_login, logout, registrar_usuario
from base64 import b64encode
from twilio.rest import Client
import uuid
from dotenv import load_dotenv
import requests
import json


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


if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = str(uuid.uuid4())

if st.session_state.get("autenticado", False) and st.session_state.get("usuario"):
    usuario_actual = st.session_state.usuario
    if usuario_actual not in st.session_state.chat_history:
        st.session_state.chat_history[usuario_actual] = {}
    if st.session_state.current_chat not in st.session_state.chat_history[usuario_actual]:
        st.session_state.chat_history[usuario_actual][st.session_state.current_chat] = {
            "title": "Nuevo chat",
            "messages": []
        }

 --- ESTILOS CSS ---
def load_css():
    favicon_path = "favicon.ico"
    favicon_base64 = ""

    if os.path.exists(favicon_path):
        with open(favicon_path, "rb") as f:
            favicon_base64 = b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        :root {{
            --bg-primary: 000000;
            --bg-card: 1a1a1a;
            --bg-sidebar: 111111;
            --text-primary: ffffff;
            --text-secondary: cccccc;
            --text-muted: 888888;
            --purple: 8B5CF6;
            --purple-hover: 7C3AED;
            --purple-light: A78BFA;
            --border: 333333;
            --shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            --assistant-bg: 2a2a2a;
            --assistant-text: ffffff;
            --user-bg: 8B5CF6;
            --user-text: ffffff;
            --sidebar-width: 300px;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        .stApp {{
            background-color: var(--bg-primary) !important;
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
        }}

        .stApp > header {{
            display: none !important;
        }}

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

 --- INICIALIZACIÓN DE SERVICIOS ---
 Twilio (para verificación SMS)
try:
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
except Exception as e:
    st.warning(f"No se pudo inicializar Twilio: {e}")

 --- INICIALIZACIÓN DE ESTADO ---
def initialize_session_state():
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
    
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = str(uuid.uuid4())

initialize_session_state()

 --- GROQ HELPERS ---
def _system_prompt():
     Crear prompt personalizado basado en el contexto del usuario
    base_prompt = "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil."
    
     Agregar contexto de archivos si existe
    if st.session_state.get("user_context"):
        context_info = "\n\nContexto personalizado del usuario:\n"
        for ctx in st.session_state.user_context[-5:]:   Últimos 5 contextos
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
                             FIX ENCODING por si llega interpretado raro
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

 --- FUNCIONES UTILITARIAS UI ---
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
    """Guarda el chat actual en el historial."""
    if st.session_state.messages and st.session_state.get("usuario") and st.session_state.get("user_id"):
        first_message = st.session_state.messages[0]["content"] if st.session_state.messages else "Nuevo chat"
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        
         Actualizar en session_state
        st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
            "title": safe_text(title),
            "messages": st.session_state.messages.copy(),
        }
        
         Guardar en base de datos
        db.update_chat_title(st.session_state.current_chat, safe_text(title))
        
         Guardar mensajes nuevos
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

 --- BARRA LATERAL MEJORADA ---
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
            for chat in user_chats[-10:]:   Mostrar últimos 10 chats
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
                
                 Botón para cargar el chat
                if st.button("Abrir", key=f"open_{chat['id']}"):
                    st.session_state.current_chat = chat['chat_id']
                     Cargar mensajes del chat
                    chat_messages = db.get_chat_messages(chat['chat_id'])
                    st.session_state.messages = [
                        {"role": msg['role'], "content": msg['content']}
                        for msg in chat_messages
                    ]
                    st.rerun()
        except Exception:
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
    
    return selected_option
    
    return selected_option

 --- FUNCIONES DE UTILIDAD PARA ARCHIVOS ---
def save_uploaded_file(uploaded_file, user_id):
    """Guarda un archivo subido y lo procesa"""
    try:
         Crear directorio del usuario si no existe
        user_dir = f"uploads/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        
         Guardar archivo físico
        file_path = os.path.join(user_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
         Procesar archivo
        processor = FileProcessor()
        content, summary, error = processor.process_file(file_path)
        
        if error:
            return None, error
        
         Guardar en base de datos
        file_id = db.save_file(
            user_id=user_id,
            filename=uploaded_file.name,
            file_path=file_path,
            file_type=FileProcessor.get_file_type(uploaded_file.name),
            file_size=uploaded_file.size,
            content_extracted=content,
            analysis_summary=summary
        )
        
         Agregar al contexto del usuario
        if content:
            context_key = f"Archivo: {uploaded_file.name}"
            db.save_user_context(user_id, context_key, content, file_id)
        
        return file_id, None
        
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
        user_context = db.get_user_context(user_id)
        if not user_context:
            return ""
        
         Buscar contexto relevante basado en la consulta
        relevant_context = []
        query_lower = query.lower()
        
        for context in user_context:
            context_content = context['context_data'].lower()
             Búsqueda simple por palabras clave
            if any(word in context_content for word in query_lower.split() if len(word) > 3):
                relevant_context.append({
                    'key': context['context_key'],
                    'content': context['context_data'][:500] + "..." if len(context['context_data']) > 500 else context['context_data']
                })
        
        if relevant_context:
            context_text = "\n\nContexto personalizado basado en tus archivos:\n"
            for ctx in relevant_context[:3]:   Limitar a 3 contextos más relevantes
                context_text += f"\n**{ctx['key']}:**\n{ctx['content']}\n"
            return context_text
        
        return ""
        
    except Exception as e:
        print(f"Error obteniendo contexto personalizado: {e}")
        return ""

 --- FUNCIONES DE CHAT MEJORADAS ---
def chat_page():
    """Página principal de chat con contexto personalizado"""
    st.title("💬 Chat con Zero")
    
     Mostrar mensajes del chat actual
    chat_container = st.container()
    with chat_container:
        if st.session_state.messages:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
    
     Input del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
         Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
         Obtener contexto personalizado
        personalized_context = ""
        if st.session_state.get("user_id"):
            personalized_context = get_personalized_context(st.session_state.user_id, prompt)
        
         Preparar mensaje con contexto
        enhanced_prompt = prompt
        if personalized_context:
            enhanced_prompt = f"{prompt}{personalized_context}"
        
         Generar respuesta
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                 Preparar mensajes para la API
                messages_for_api = []
                for msg in st.session_state.messages[:-1]:   Excluir el último mensaje del usuario
                    messages_for_api.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                 Agregar el mensaje actual con contexto
                messages_for_api.append({
                    "role": "user",
                    "content": enhanced_prompt
                })
                
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
        
         Guardar respuesta del asistente
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
         Guardar chat en base de datos
        save_current_chat()
        
         Auto-scroll
        st.rerun()

def save_current_chat():
    """Guarda el chat actual en la base de datos"""
    if st.session_state.get("user_id") and st.session_state.messages:
        try:
             Generar título del chat basado en el primer mensaje
            title = "Nuevo chat"
            if st.session_state.messages:
                first_user_msg = next((msg['content'] for msg in st.session_state.messages if msg['role'] == 'user'), "")
                if first_user_msg:
                    title = first_user_msg[:50] + "..." if len(first_user_msg) > 50 else first_user_msg
            
             Guardar o actualizar chat
            chat_id = db.save_chat(
                user_id=st.session_state.user_id,
                chat_id=st.session_state.current_chat,
                title=title
            )
            
             Guardar mensajes
            for i, message in enumerate(st.session_state.messages):
                db.save_message(
                    chat_id=chat_id,
                    role=message['role'],
                    content=message['content'],
                    message_order=i
                )
                
        except Exception as e:
            print(f"Error guardando chat: {e}")

 --- FUNCIONES EXISTENTES MEJORADAS ---
def image_page():
    """Página de análisis de imágenes mejorada"""
    st.title("🖼️ Análisis de Imágenes")
    st.write("Sube una imagen para que Zero la analice usando Groq Vision.")
    
    uploaded_files = st.file_uploader(
        "Seleccionar archivos",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "md", "xlsx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
         Mostrar imagen
        image = Image.open(uploaded_file)
        st.image(image, caption=uploaded_file.name, use_column_width=True)
        
        if st.button("🔍 Analizar Imagen", type="primary"):
            with st.spinner("Analizando imagen..."):
                 Convertir a base64
                image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                
                 Analizar con Groq Vision
                analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                
                 Mostrar resultado
                st.subheader("📋 Análisis de la Imagen")
                st.write(analysis)
                
                 Guardar análisis si el usuario está autenticado
                if st.session_state.get("user_id"):
                    try:
                        db.save_image_analysis(
                            user_id=st.session_state.user_id,
                            image_path=f"temp/{uploaded_file.name}",
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
    
     Configuración de WebRTC
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    if webrtc_ctx.audio_receiver:
        st.write("🎙️ Grabando... Habla ahora")
        
         Procesar audio (implementación simplificada)
        audio_frames = []
        while True:
            try:
                audio_frame = webrtc_ctx.audio_receiver.get_frame(timeout=1)
                audio_frames.append(audio_frame)
            except queue.Empty:
                break
        
        if audio_frames:
            st.write("🔄 Procesando audio...")
             Aquí iría la lógica de transcripción
            st.write("📝 Transcripción: [Funcionalidad en desarrollo]")

def register_page():
    """Página de registro de usuarios (solo admin)"""
    st.title("👥 Registro de Usuarios")
    
    if st.session_state.get("rol") != "admin":
        st.error("❌ Acceso denegado. Solo administradores pueden registrar usuarios.")
        return
    
    with st.form("registro_form"):
        st.subheader("Crear Nuevo Usuario")
        
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
                    st.error(f"❌ Error: {str(e)}")
def file_upload_page():
    """Página para subir y gestionar archivos"""
    st.title("📁 Gestión de Archivos")
    st.write("Sube documentos e imágenes para que Zero pueda usarlos en las conversaciones.")
    
     Verificar que el usuario esté autenticado
    if not st.session_state.get("usuario"):
        st.error("❌ Error de sesión. Por favor, vuelve a iniciar sesión.")
        return
    
     Obtener user_id desde la base de datos usando el username
    username = st.session_state.usuario
    user_id = db.get_user_id_by_username(username)
    
    if not user_id:
        st.error("❌ No se pudo obtener la información del usuario.")
        return
    
     Sección de subida de archivos
    st.subheader("📤 Subir Nuevo Archivo")
    
    uploaded_file = st.file_uploader(
        "Elige un archivo",
        type=["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "jpg", "jpeg", "png", "gif", "bmp", "webp"],
        help="Formatos soportados: PDF, Word, Excel, TXT, CSV e imágenes"
    )
    
    if uploaded_file is not None:
         Mostrar información del archivo
        st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 Procesar Archivo", type="primary"):
            with st.spinner("Procesando archivo..."):
                 Guardar y procesar archivo
                file_id, error = save_uploaded_file(uploaded_file, user_id)
                
                if error:
                    st.error(f"❌ Error al procesar archivo: {error}")
                else:
                    st.success("✅ Archivo procesado y guardado exitosamente")
                    
                     Si es una imagen, realizar análisis con Groq Vision
                    if uploaded_file.type.startswith('image/'):
                        with st.spinner("Analizando imagen con Groq Vision..."):
                            image_base64 = b64encode(uploaded_file.getvalue()).decode('utf-8')
                            analysis = analyze_image_with_groq(image_base64, uploaded_file.name)
                            
                             Guardar análisis
                            db.save_image_analysis(
                                user_id=user_id,
                                image_path=f"uploads/{user_id}/{uploaded_file.name}",
                                analysis_result=analysis,
                                model_used=GROQ_VISION_MODEL,
                                archivo_id=file_id
                            )
                            
                             Agregar análisis al contexto
                            context_key = f"Análisis de imagen: {uploaded_file.name}"
                            db.save_user_context(user_id, context_key, analysis, file_id)
                            
                            st.success("🖼️ Imagen analizada con Groq Vision")
                    
                     Actualizar archivos en sesión
                    st.session_state.user_files = db.get_user_files(user_id)
                    st.session_state.user_context = db.get_user_context(user_id)
                    
                    st.rerun()
    
     Sección de archivos existentes
    st.subheader("📋 Archivos Subidos")
    
     Cargar archivos del usuario si no están en sesión
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
                         Eliminar archivo físico
                        try:
                            if os.path.exists(file_data['file_path']):
                                os.remove(file_data['file_path'])
                        except:
                            pass
                        
                         Eliminar de base de datos
                        db.delete_file(file_data['id'], user_id)
                        
                         Actualizar sesión
                        st.session_state.user_files = db.get_user_files(user_id)
                        st.session_state.user_context = db.get_user_context(user_id)
                        
                        st.success("🗑️ Archivo eliminado")
                        st.rerun()
                    
                    if st.button(f"💬 Usar en Chat", key=f"use_{file_data['id']}"):
                        if file_data.get('content_extracted'):
                             Agregar contenido al chat actual
                            content_message = f"📄 **Contenido de {file_data['filename']}:**\n\n{file_data['content_extracted'][:1000]}..."
                            st.session_state.messages.append({
                                "role": "user", 
                                "content": content_message
                            })
                            
                             Cambiar a página de chat
                            st.session_state.menu_option = "Chat Principal"
                            st.success(f"📄 Contenido de {file_data['filename']} agregado al chat")
                            st.rerun()
    else:
        st.info("📭 No tienes archivos subidos aún. ¡Sube tu primer archivo!")
        
 --- FUNCIÓN PRINCIPAL ---
def main():
    """Función principal de la aplicación"""
    load_css()
    
     Verificar autenticación
    if not st.session_state.get("autenticado", False):
        verificar_login()
        return
    
     Inicializar base de datos y cargar datos del usuario
    if st.session_state.get("user_id") and "user_files" not in st.session_state:
        st.session_state.user_files = db.get_user_files(st.session_state.user_id)
        st.session_state.user_context = db.get_user_context(st.session_state.user_id)
        
         Cargar historial de chats
        user_chats = db.get_user_chats(st.session_state.user_id)
        if user_chats:
             Cargar mensajes del chat actual
            current_chat_messages = db.get_chat_messages(st.session_state.current_chat)
            if current_chat_messages:
                st.session_state.messages = [
                    {"role": msg['role'], "content": msg['content']} 
                    for msg in current_chat_messages
                ]
    
     Sidebar con navegación
    with st.sidebar:
        selected_option = create_sidebar()
    
     Navegación principal
    if selected_option == "Chat Principal":
        chat_page()
    elif st.session_state.current_page == "files":
        files_page()
    elif st.session_state.current_page == "admin":
        admin_page()

if __name__ == "__main__":
    main()



    #prueba actualizaciópn