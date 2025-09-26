import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import speech_recognition as sr
import av
import numpy as np
import queue
import io
from PIL import Image
import time
from Login import verificar_login, logout, registrar_usuario
from base64 import b64encode
import os
from twilio.rest import Client
import uuid
import random
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="ZERO - Asistente Virtual",
    page_icon="favicon.ico",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- ESTADOS DE SESIÓN ---
# Inicializar historial de chat para el usuario actual (solo si está autenticado)
if st.session_state.get("autenticado", False) and st.session_state.get("usuario"):
    usuario_actual = st.session_state.usuario
    if usuario_actual not in st.session_state.chat_history:
        st.session_state.chat_history[usuario_actual] = {}
    if st.session_state.current_chat not in st.session_state.chat_history[usuario_actual]:
        st.session_state.chat_history[usuario_actual][st.session_state.current_chat] = {
            "title": "Nuevo chat",
            "messages": []
        }

# --- ESTILOS CSS ---
def load_css():
    favicon_path = "favicon.ico"
    favicon_base64 = ""

    if os.path.exists(favicon_path):
        with open(favicon_path, "rb") as f:
            favicon_base64 = b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Variables de diseño minimalista */
        :root {{
            --bg-primary: #000000;        /* Fondo negro */
            --bg-card: #1a1a1a;          /* Tarjetas gris oscuro */
            --bg-sidebar: #111111;       /* Sidebar negro más claro */
            --text-primary: #ffffff;      /* Texto blanco */
            --text-secondary: #cccccc;    /* Texto gris claro */
            --text-muted: #888888;        /* Texto gris medio */
            --purple: #8B5CF6;            /* Morado principal */
            --purple-hover: #7C3AED;      /* Morado hover */
            --purple-light: #A78BFA;      /* Morado claro */
            --border: #333333;            /* Bordes grises */
            --shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            
            /* Mensajes chat */
            --assistant-bg: #2a2a2a;
            --assistant-text: #ffffff;
            --user-bg: #8B5CF6;
            --user-text: #ffffff;
            
            --sidebar-width: 300px;
        }}

        /* Reset y fondo negro */
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

        /* Eliminar barra superior */
        .stApp > header {{
            display: none !important;
        }}

        /* Contenedor principal */
        .main {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }}
        
        .main .block-container {{
            background-color: var(--bg-primary);
            padding: 1rem;
        }}

        /* Barra lateral */
        .sidebar .sidebar-content {{
            background-color: var(--bg-sidebar) !important;
            color: var(--text-primary);
            width: var(--sidebar-width);
            border-right: 1px solid var(--border);
            padding: 1rem;
        }}
        
        .css-1d391kg {{
            background-color: var(--bg-sidebar) !important;
        }}

        .sidebar-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--purple);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--purple);
        }}

        .sidebar-section {{
            margin-bottom: 1.5rem;
        }}

        .sidebar-section-title {{
            font-weight: 600;
            color: var(--purple);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* Contenedor del chat */
        .chat-container {{
            max-height: 65vh;
            overflow-y: auto;
            padding: 1rem 0.5rem;
            margin-bottom: 1rem;
            background-color: var(--bg-primary);
            border-radius: 8px;
            scrollbar-width: thin;
            scrollbar-color: var(--purple) var(--bg-primary);
        }}

        .chat-container::-webkit-scrollbar {{
            width: 6px;
        }}

        .chat-container::-webkit-scrollbar-track {{
            background: var(--bg-primary);
        }}

        .chat-container::-webkit-scrollbar-thumb {{
            background-color: var(--purple);
            border-radius: 3px;
        }}

        /* Mensajes del chat - Estilo chatbot */
        .message {{
            margin-bottom: 1.25rem;
            animation: fadeIn 0.3s ease-out;
            display: flex;
            flex-direction: column;
        }}

        /* Mensaje del ASISTENTE (izquierda) */
        .assistant-message {{
            background-color: var(--assistant-bg);
            color: var(--assistant-text);
            padding: 0.8rem 1.2rem;
            border-radius: 18px 18px 18px 4px;
            max-width: 85%;
            align-self: flex-start;
            word-wrap: break-word;
            text-align: left;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-right: auto;
        }}

        /* Mensaje del USUARIO (derecha) */
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

        /* Animaciones */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Input de chat */
        .stTextInput>div>div>input {{
            border-radius: 8px;
            padding: 12px 16px;
            border: 1px solid var(--border);
            box-shadow: none;
            background-color: var(--bg-card) !important;
            color: var(--text-primary) !important;
        }}
        
        .stTextInput>label {{
            color: var(--text-primary) !important;
        }}

        .stTextInput>div>div>input:focus {{
            border-color: var(--purple) !important;
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2) !important;
        }}

        /* Botones morados */
        .stButton>button {{
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            transition: all 0.2s;
            background-color: var(--purple) !important;
            color: var(--text-primary) !important;
            border: none;
        }}

        .stButton>button:hover {{
            background-color: var(--purple-hover) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }}

        /* Botón de cerrar sesión */
        .logout-btn {{
            background-color: transparent !important;
            color: var(--purple) !important;
            border: 1px solid var(--purple) !important;
            margin-top: 1rem;
        }}

        .logout-btn:hover {{
            background-color: rgba(139, 92, 246, 0.1) !important;
        }}

        /* Spinner de carga */
        .spinner {{
            animation: spin 1s linear infinite;
            display: inline-block;
        }}

        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        /* Eliminar espacio blanco no deseado */
        .block-container {{
            padding-top: 0 !important;
        }}

        /* Disclaimer */
        .disclaimer {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-align: center;
            margin-top: 0.5rem;
            padding: 0.5rem;
        }}

        /* Lista de chats */
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

        /* Mejoras para móviles */
        @media (max-width: 768px) {{
            .sidebar .sidebar-content {{
                width: 100%;
            }}

            .chat-container {{
                max-height: 60vh;
            }}

            .assistant-message, .user-message {{
                max-width: 90%;
            }}
        }}
    </style>

    <!-- Favicon personalizado -->
    <link rel=\"icon\" href=\"data:image/x-icon;base64,{favicon_base64}\" type=\"image/x-icon\">
    """, unsafe_allow_html=True)

load_css()

# --- INICIALIZACIÓN DE SERVICIOS ---
# OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    st.error(f"Error al inicializar OpenAI: {e}")
    st.stop()

# Twilio (para verificación SMS)
try:
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
except Exception as e:
    # No es crítico para el funcionamiento básico del app
    st.warning(f"No se pudo inicializar Twilio: {e}")

# --- INICIALIZACIÓN DE ESTADO ---
def initialize_session_state():
    """Inicializa las variables de estado de sesión necesarias"""
    # Variables de autenticación
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None
    
    # Variables de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thinking" not in st.session_state:
        st.session_state.thinking = False
    
    # Variables de interfaz
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = str(uuid.uuid4())

# Inicializar estado al cargar la aplicación
initialize_session_state()

# --- FUNCIONES UTILITARIAS ---
def generate_response():
    """Genera una respuesta del asistente AI (streaming) usando el historial."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil."}] +
                     [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages],
            max_tokens=1200,
            temperature=0.7,
            stream=True,
        )
        return response
    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

def display_message(role, content):
    """Muestra un mensaje en el chat con el estilo adecuado."""
    if role == "assistant":
        # Eliminamos el prefijo "Zero: " si existe
        clean_content = content.replace("Zero:", "").strip()
        st.markdown(
            f"<div class='message'><div class='assistant-message'>{clean_content}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='message'><div class='user-message'>{content}</div></div>",
            unsafe_allow_html=True,
        )

def save_current_chat():
    """Guarda el chat actual en el historial."""
    if st.session_state.messages and "usuario" in st.session_state:
        first_message = st.session_state.messages[0]["content"] if st.session_state.messages else "Nuevo chat"
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        
        # Guardar en el historial del usuario actual
        st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
            "title": title,
            "messages": st.session_state.messages.copy(),
        }

def load_chat(chat_id):
    """Carga un chat del historial."""
    if "usuario" in st.session_state and chat_id in st.session_state.chat_history.get(st.session_state.usuario, {}):
        st.session_state.current_chat = chat_id
        st.session_state.messages = st.session_state.chat_history[st.session_state.usuario][chat_id]["messages"].copy()
        st.rerun()

# --- BARRA LATERAL ---
def sidebar():
    with st.sidebar:
        # Título de la barra lateral
        st.markdown('<div class="sidebar-title">ZERO - Asistente Virtual</div>', unsafe_allow_html=True)

        # Saludo personalizado
        usuario_nombre = st.session_state.get("usuario", "Usuario")
        st.markdown(f'<div style="margin-bottom: 1rem;">Hola, <strong>{usuario_nombre}</strong></div>', unsafe_allow_html=True)

        # Lista de chats
        st.markdown('<div class="sidebar-section-title">💬 Chats anteriores</div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-list">', unsafe_allow_html=True)

        # Renderiza cada chat del usuario actual
        usuario_actual = st.session_state.get("usuario")
        if usuario_actual and usuario_actual in st.session_state.chat_history:
            user_chats = st.session_state.chat_history[usuario_actual]
            
            for chat_id, chat_data in user_chats.items():
                is_active = chat_id == st.session_state.current_chat
                preview = (chat_data["messages"][-1]["content"][:50] + "...") if chat_data["messages"] else "Vacío"

                # Mostrar cada chat
                st.markdown(
                    f"""
                    <div class="chat-item {'active' if is_active else ''}">
                        <div><strong>{chat_data['title']}</strong></div>
                        <div class="chat-preview">{preview}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Botón para cargar el chat
                if st.button("Abrir", key=f"open_{chat_id}"):
                    load_chat(chat_id)

        st.markdown('</div>', unsafe_allow_html=True)

        # Botón de nuevo chat
        if st.button("➕ Nuevo Chat", use_container_width=True):
            save_current_chat()
            st.session_state.current_chat = str(uuid.uuid4())
            st.session_state.messages = []
            if "usuario" in st.session_state:
                st.session_state.chat_history[st.session_state.usuario][st.session_state.current_chat] = {
                    "title": "Nuevo chat",
                    "messages": [],
                }
            st.rerun()

        # Sección de herramientas
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">🛠️ Herramientas</div>', unsafe_allow_html=True)

        # Opciones de menú
        menu_options = ["Chat Principal"]
        if st.session_state.rol == "admin":
            menu_options += ["Análisis de Imágenes", "Transcripción de Audio", "Registro de Usuarios"]

        selected_option = st.radio("", menu_options, key="menu_option", label_visibility="collapsed")

        st.markdown('</div>', unsafe_allow_html=True)

        # Botón de cerrar sesión
        if st.button("🚪 Cerrar sesión", key="logout_btn", use_container_width=True, type="primary"):
            logout()
            st.rerun()

        return selected_option

# --- PÁGINA PRINCIPAL ---
def chat_page():
    # Contenedor del chat
    chat_container = st.container()
    with chat_container:
        st.markdown("<div class='chat-container' id='chat-container'>", unsafe_allow_html=True)

        # Mensaje de bienvenida
        if len(st.session_state.messages) == 0:
            display_message("assistant", f"¿En qué puedo ayudarte hoy, {st.session_state.usuario}?")

        # Mensajes existentes
        for message in st.session_state.messages:
            display_message(message["role"], message["content"])

        # Indicador de "pensando"
        if st.session_state.thinking:
            st.markdown(
                """
                <div class='message'>
                    <div class='assistant-message'>
                        <span class='spinner'>⚙️</span> Zero está procesando...
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # JavaScript para scroll automático
    st.markdown("""
    <script>
        function scrollToBottom() {
            const container = document.getElementById('chat-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
        
        // Scroll al cargar y cuando hay cambios
        setTimeout(scrollToBottom, 100);
        const observer = new MutationObserver(scrollToBottom);
        const config = { childList: true, subtree: true };
        const target = document.getElementById('chat-container');
        if (target) {
            observer.observe(target, config);
        }
    </script>
    """, unsafe_allow_html=True)

    # Input de usuario
    user_input = st.chat_input("Escribe tu mensaje aquí...")

    # Disclaimer
    st.markdown(
        """
        <div class="disclaimer">
            Zero AI puede cometer errores. Verifica siempre la información importante.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user_input and not st.session_state.thinking:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.thinking = True
        save_current_chat()
        st.rerun()

    if st.session_state.thinking:
        response = generate_response()

        if response:
            message_placeholder = st.empty()
            full_response = ""

            for chunk in response:
                delta = None
                try:
                    delta = chunk.choices[0].delta.content
                except Exception:
                    try:
                        delta = chunk.choices[0].message.get("content")
                    except Exception:
                        delta = None

                if delta:
                    full_response += delta
                    message_placeholder.markdown(
                        f"<div class='message'><div class='assistant-message'>{full_response}</div></div>",
                        unsafe_allow_html=True,
                    )

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_current_chat()

        st.session_state.thinking = False
        st.rerun()

# --- PÁGINA DE IMAGEN ---
def image_page():
    st.title("🖼️ Análisis de Imágenes")
    st.write("Sube una imagen para que Zero la analice")

    uploaded_image = st.file_uploader("Elige una imagen", type=["jpg", "png", "jpeg"])

    if uploaded_image:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(uploaded_image, width=300)

        image_bytes = uploaded_image.getvalue()
        image_base64 = b64encode(image_bytes).decode("utf-8")

        with st.spinner("Analizando imagen..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Analiza la imagen en detalle. Describe lo que ves y proporciona información relevante.",
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Por favor analiza esta imagen",
                                },
                            ],
                        },
                    ],
                    max_tokens=1000,
                )

                analysis = response.choices[0].message.content

                with col2:
                    st.markdown("### Análisis de Zero")
                    st.write(analysis)

                if st.button("Agregar al chat principal", type="primary"):
                    st.session_state.messages.extend(
                        [
                            {"role": "user", "content": f"![Imagen analizada](data:image/jpeg;base64,{image_base64})"},
                            {"role": "assistant", "content": analysis},
                        ]
                    )
                    save_current_chat()
                    st.success("¡Añadido al chat!")
            except Exception as e:
                st.error(f"Error al analizar la imagen: {e}")

# --- PÁGINA DE AUDIO ---
def audio_page():
    st.title("🎙️ Transcripción de Audio")
    st.write("Habla y Zero convertirá tu voz en texto")

    audio_queue = queue.Queue()

    class AudioProcessor:
        def __init__(self):
            self.recognizer = sr.Recognizer()
            self.sample_rate = 16000  # valor por defecto; se actualizará desde los frames si es posible

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
        webrtc_ctx.stop()
        st.rerun()

    if st.button("Transcribir audio grabado", type="primary") and not audio_queue.empty():
        try:
            raw_chunks = []
            srates = []
            while not audio_queue.empty():
                raw, rate = audio_queue.get()
                raw_chunks.append(raw)
                srates.append(rate)
            audio_bytes = b"".join(raw_chunks)
            sample_rate = int(np.bincount(np.array(srates)).argmax()) if len(set(srates)) > 1 else srates[0]

            recognizer = sr.Recognizer()
            audio_data = sr.AudioData(audio_bytes, sample_rate=sample_rate, sample_width=2)
            text = recognizer.recognize_google(audio_data, language="es-ES")
            st.success("Texto reconocido:")
            st.write(text)

            if st.button("Usar en chat principal", type="primary"):
                st.session_state.messages.append({"role": "user", "content": text})
                save_current_chat()
                st.rerun()
        except sr.UnknownValueError:
            st.error("No se pudo entender el audio")
        except sr.RequestError as e:
            st.error(f"Error en el servicio de reconocimiento: {e}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

# --- PÁGINA DE REGISTRO ---
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

# --- RUTA PRINCIPAL ---
def main():
    # Verificar si el usuario está autenticado
    if not st.session_state.get("autenticado", False):
        st.error("❌ Acceso denegado. Por favor, inicia sesión.")
        st.stop()
    
    # Verificar que las variables de sesión necesarias estén inicializadas
    if "usuario" not in st.session_state:
        st.error("❌ Error de sesión. Por favor, vuelve a iniciar sesión.")
        if st.button("🔄 Reiniciar Sesión"):
            st.session_state.clear()
            st.rerun()
        st.stop()
    
    selected_option = sidebar()

    if selected_option == "Chat Principal":
        chat_page()
    elif selected_option == "Análisis de Imágenes":
        image_page()
    elif selected_option == "Transcripción de Audio":
        audio_page()
    elif selected_option == "Registro de Usuarios":
        register_page()

if __name__ == "__main__":
    # Verificar autenticación antes de ejecutar la aplicación principal
    if not st.session_state.get("autenticado", False):
        # Si no está autenticado, mostrar login
        verificar_login()
    else:
        # Si está autenticado, ejecutar la aplicación principal
        main()