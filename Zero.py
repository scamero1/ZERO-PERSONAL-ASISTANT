# Zero.py — Versión Profesional 3.0: Voz (TTS), Historial Robusto y Estética Dinámica.
# -----------------------------------------------------------------------------------------------
# 🔴 INSTALACIÓN OBLIGATORIA DE DEPENDENCIAS (Asegúrate de que no falte ninguna)
# -----------------------------------------------------------------------------------------------
# Comando completo, incluyendo gTTS para la voz:
# pip install streamlit requests python-dotenv twilio PyPDF2 python-pptx pandas openpyxl xlrd pytesseract pillow gTTS
# -----------------------------------------------------------------------------------------------

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ExifTags
from dotenv import load_dotenv
from twilio.rest import Client
from pathlib import Path
from datetime import datetime
import time, os, json, uuid, requests
import base64
import io # <-- NECESARIO para gTTS

# --- Dependencia de Voz (TTS) ---
try:
    from gtts import gTTS
except Exception:
    gTTS = None
    print("ADVERTENCIA: gTTS no está instalado. Instala con 'pip install gTTS' para habilitar la voz.")

# --- Fallback imports protegidos ---
# Muestra errores claros si faltan las dependencias de lectura
try: import PyPDF2
except Exception: PyPDF2 = None
try: from pptx import Presentation
except Exception: Presentation = None
try: from openpyxl import Workbook; import pandas as pd
except Exception: pd = None
try: import pytesseract
except Exception: pytesseract = None

# --- Proyecto (Importa tus clases externas) ---
# ***********************************************************************************
# IMPORTANTE: Debes tener los archivos 'Login.py', 'database.py' y 'file_processor.py'
# ***********************************************************************************
try:
    from Login import verificar_login, logout as user_logout_logic, registrar_usuario
    from database import ZeroDatabase
    from file_processor import FileProcessor
except ImportError as e:
    st.error(f"Error de importación de módulos internos (Login, database, file_processor). Asegúrate de que existan los archivos .py: {e}")
    st.stop()
    
# ------------------ Configuración ------------------
load_dotenv()
st.set_page_config(page_title="ZERO - Asistente Virtual", page_icon="💡", layout="wide")

db = ZeroDatabase()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    # Esto no detiene la ejecución, permite probar sin API key si se quiere solo la UI
    print("ADVERTENCIA: Falta GROQ_API_KEY en tu entorno (.env). La IA no funcionará.")

API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
BASE_HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

LOCAL_CHAT_DIR = "local_chats"         
SESSION_STORE_DIR = ".auth_sessions"   
INACTIVITY_LIMIT_SECS = 60 * 60        # 1 hora
MAX_CONTEXT_MESSAGES = 10              

# ------------------ Helpers ------------------
def safe_text(x):
    if x is None: return ""
    if not isinstance(x, str): x = str(x)
    try: return x.encode("latin1").decode("utf-8")
    except Exception: return x

def _normalize_process_result(res):
    content = summary = error = None
    if isinstance(res, dict):
        content = res.get("content") or res.get("text") or res.get("content_extracted")
        summary = res.get("summary") or res.get("analysis") or res.get("brief")
        error = res.get("error")
        return content, summary, error
    if isinstance(res, (list, tuple)):
        if len(res) == 3: content, summary, error = res
        elif len(res) == 2:
            a, b = res
            if isinstance(b, Exception) or (isinstance(b, str) and ("error" in b.lower() or "traceback" in b.lower())):
                content, error = a, b
            else:
                content, summary = a, b
        elif len(res) == 1:
            content = res[0]
        return content, summary, error
    if res is not None: content = str(res)
    return content, summary, error

def clean_session():
    ss = st.session_state
    if ss.get("user_id"):
        try: (_sess_file(ss["user_id"])).unlink(missing_ok=True)
        except Exception: pass
    user_logout_logic()
    ss.autenticado = False
    ss.usuario = None
    ss.rol = None
    ss.auth_token = None
    ss.user_id = None
    ss.messages = []
    ss.current_chat = str(uuid.uuid4())
    ss.current_chat_title = "Nuevo Chat"
    st.rerun()

def _init_state():
    ss = st.session_state
    ss.setdefault("messages", [])
    ss.setdefault("current_chat", str(uuid.uuid4()))
    ss.setdefault("current_chat_title", "Nuevo Chat") 
    ss.setdefault("usuario", None)
    ss.setdefault("user_id", None)
    ss.setdefault("rol", None)
    ss.setdefault("autenticado", False)
    ss.setdefault("user_files", [])
    ss.setdefault("user_context", [])
    ss.setdefault("auth_token", None)
    ss.setdefault("last_activity", time.time())
    ss.setdefault("typing_effect", True)
    ss.setdefault("selected_local_key", "")
    ss.setdefault("selected_page", "Chat Principal")
_init_state()

# ------------------ Estilos (Barra de escritura dinámica) ------------------
def load_css():
    """Estilos personalizados para una UI moderna, oscura y profesional."""
    st.markdown("""
    <style>
    /* VARIABLES GLOBALES */
    :root {
        color-scheme: dark;
        --bg: #111217;        /* Fondo principal (Deep Dark) */
        --card: #1C1E26;      
        --sidebar: #1C1E26;   
        --text: #EAEBF0;      
        --muted: #8E929E;
        --accent: #A962FF;    /* Púrpura/Violeta profesional y moderno */
        --accent-hover: #934BEA;
        --border: #33363D;
        --user-bg: #272B33;
        --input-bg: #22242D;
        --shadow: rgba(0, 0, 0, 0.3); 
    }
    
    /* Configuración de la aplicación y ocultar elementos */
    [data-testid="stMainMenu"], [data-testid="stToolbar"], header { display:none !important; }
    .stApp, [data-testid="stAppViewContainer"], .block-container {
        background: var(--bg) !important; color: var(--text) !important;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar) !important;
        padding: 15px;
        box-shadow: 2px 0 5px var(--shadow);
    }
    
    /* Contenedor principal: añadir espacio inferior para el chat input fijo */
    [data-testid="stAppViewContainer"] > div:nth-child(1) > div:nth-child(1) {
        padding-bottom: 120px !important; 
    }

    /* Contenedor del chat principal con scroll */
    .chat-box {
        background: var(--bg);
        max-height: 80vh; 
        overflow-y: auto; 
        padding: 10px;
        padding-bottom: 10px; 
        scrollbar-color: var(--accent) transparent; 
        scrollbar-width: thin;
    }

    /* Mensajes de Chat */
    [data-testid="stChatMessage"] {
        background: var(--card); 
        border: 1px solid var(--border);
        border-radius: 16px; 
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px var(--shadow);
    }
    [data-testid="stChatMessage"]:has([data-testid="stAvatarUser"]) {
        background: var(--user-bg);
        border-color: #4A4D57;
    }
    
    /* Chat Input (Sticky Footer look - FIX DINÁMICO) */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 0 !important;
        z-index: 10 !important;
        padding: 20px !important;
        background: var(--bg) !important; 
        box-shadow: 0 -4px 10px var(--shadow) !important; 
        
        /* 🔥 FIX: Calcula el ancho y la posición según el ancho de la sidebar (st-s-width) */
        left: var(--st-s-width, 300px) !important; 
        width: calc(100% - var(--st-s-width, 300px)) !important;
        
        margin: 0 !important;
    }
    
    /* Botones */
    .stButton>button { 
        background: var(--accent) !important; 
        border: none; color:white; 
        border-radius: 12px; 
        font-weight: 600; 
        padding: 10px 20px;
        transition: background 0.2s, transform 0.1s;
    }
    .stButton>button:hover:not([disabled]) { 
        background: var(--accent-hover) !important; 
        transform: translateY(-1px);
    }
    
    /* Inputs de texto */
    .stTextInput>div>div>input, .stTextArea textarea, [data-testid="stChatInput"] input {
        background: var(--input-bg) !important; 
        color: var(--text) !important; 
        border: 1px solid var(--border) !important; 
        border-radius: 12px !important;
        padding: 15px 20px;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.5); 
    }

    /* Títulos y Sidebar */
    .sidebar-title {
        font-size:1.5rem; font-weight:700; color:var(--accent); 
        text-shadow: 0 0 5px rgba(169, 98, 255, 0.5);
        border-bottom:3px solid var(--accent); padding-bottom:10px; margin-bottom:15px;
    }
    
    </style>
    """, unsafe_allow_html=True)
load_css()

# ------------------ Sesión persistente y Actividad ------------------
def _sess_dir(): d = Path(SESSION_STORE_DIR); d.mkdir(parents=True, exist_ok=True); return d
def _sess_file(user_id): return _sess_dir() / f"{user_id}.json"

def persist_login():
    ss = st.session_state
    if not (ss.get("autenticado") and ss.get("user_id")): return
    data = {
        "auth_token": ss.get("auth_token") or str(uuid.uuid4()),
        "user_id": ss["user_id"],
        "usuario": ss["usuario"],
        "rol": ss["rol"],
        "last_activity": time.time()
    }
    ss.auth_token = data["auth_token"]
    _sess_file(ss["user_id"]).write_text(json.dumps(data), encoding="utf-8")

def restore_any_session():
    ss = st.session_state
    if ss.get("autenticado"): return
    try:
        files = list(_sess_dir().glob("*.json"))
        if not files: return
        best, best_ts = None, 0
        for fp in files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                ts = float(data.get("last_activity", 0))
                if ts > best_ts and (time.time()-ts) <= INACTIVITY_LIMIT_SECS:
                    best, best_ts = data, ts
            except Exception:
                continue
        if best:
            ss.autenticado = True
            ss.user_id = best["user_id"]
            ss.usuario = best.get("usuario")
            ss.rol = best.get("rol")
            ss.auth_token = best.get("auth_token")
            ss.last_activity = time.time()
            ss.user_files = db.get_user_files(ss.user_id)
            ss.user_context = db.get_user_context(ss.user_id)
            # Reintentar la ejecución para refrescar la UI al restaurar
            st.rerun() 
    except Exception:
        pass

def update_activity():
    ss = st.session_state
    ss.last_activity = time.time()
    if ss.get("user_id"):
        data = {
            "auth_token": ss.get("auth_token") or str(uuid.uuid4()),
            "user_id": ss["user_id"],
            "usuario": ss.get("usuario"),
            "rol": ss.get("rol"),
            "last_activity": ss.last_activity
        }
        _sess_file(ss["user_id"]).write_text(json.dumps(data), encoding="utf-8")

def check_inactivity():
    ss = st.session_state
    if not (ss.get("autenticado") and ss.get("user_id")): return
    try:
        data = json.loads(_sess_file(ss["user_id"]).read_text(encoding="utf-8"))
        last = float(data.get("last_activity", 0))
        if time.time() - last > INACTIVITY_LIMIT_SECS:
            st.warning("Sesión cerrada por inactividad (1 hora).")
            clean_session()
            st.stop()
    except Exception:
        pass

# ------------------ GROQ y Servicios ------------------
def _system_prompt():
    """Genera el prompt de sistema, incluyendo contexto."""
    base = "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil. Responde en español."
    context_list = st.session_state.get("user_context") or []
    if context_list:
        base += "\n\nContexto personalizado del usuario (archivos relevantes o datos recientes):\n"
        for ctx in context_list[-3:]: 
            content_snippet = (ctx['context_value'][:500] + "...") if len(ctx['context_value']) > 500 else ctx['context_value']
            base += f"- Clave: {ctx['context_key']}. Contenido:\n{content_snippet}\n"
    return {"role":"system","content":base}

def groq_chat(messages, *, max_tokens=1600, temperature=0.7):
    """Llama a la API de chat de Groq con la configuración de contexto y mensajes."""
    if not GROQ_API_KEY:
        return "⚠️ Error: GROQ_API_KEY no está configurada. No puedo contactar a la IA."
        
    history = messages[-(MAX_CONTEXT_MESSAGES - 1):]
    
    payload = {
        "model": GROQ_TEXT_MODEL, 
        "messages": [_system_prompt()] + history,
        "max_tokens": max_tokens, 
        "temperature": temperature
    }
    
    try:
        r = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=90)
        if r.status_code != 200:
            return f"⚠️ Error {r.status_code}: {r.text}"
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "❌ Error: La solicitud a la IA agotó el tiempo de espera (90s). Intenta de nuevo."
    except Exception as e:
        return f"❌ Error de conexión con Groq: {e}"

# ------------------ Historial local (Robustez mejorada) ------------------
def _user_local_dir(owner):
    """Crea el directorio local para el usuario si no existe (historial independiente)."""
    d = Path(LOCAL_CHAT_DIR) / str(owner or "anon")
    d.mkdir(parents=True, exist_ok=True) 
    return d

def get_chat_title_from_messages(messages):
    title = "Nuevo chat"
    for m in messages:
        if m["role"] == "user" and m["content"].strip():
            first_line = m["content"].strip().split('\n')[0] 
            title = (first_line[:50] + "...") if len(first_line)>50 else first_line
            break
    return title

def local_save_chat(user_id, chat_id, messages, title=None):
    if not title:
        title = get_chat_title_from_messages(messages)
    
    d = _user_local_dir(user_id) 
    payload = {"chat_id": chat_id, "title": title, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "messages": messages}
    
    try:
        (d / f"{chat_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el chat local {chat_id}: {e}")

def local_list_all(user_id):
    items = []
    # Incluye el historial del usuario logueado y el anónimo (si existe)
    owners = [user_id] if user_id else ["anon"] 
    if user_id and user_id != "anon": 
        if "anon" not in owners: owners.append("anon")

    for owner in owners:
        d = _user_local_dir(owner) 
        for fp in d.glob("*.json"):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                title = data.get("title") or "Nuevo chat"
                updated = data.get("updated_at") or ""
                count = len(data.get("messages") or [])
                prefix = "👤" if owner != "anon" else "👻"
                key = f"{owner}||{fp.name}"
                label = f"{prefix} {title} — {updated}  ·  💬 {count}"
                items.append((key, label, str(fp)))
            except Exception:
                continue
    
    def _ts(lbl):
        try:
            t = lbl.split(" — ")[1].split("  ·")[0].strip()
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.min
    items.sort(key=lambda x: _ts(x[1]), reverse=True)
    return items

def local_open_chat(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data
    
def local_delete_chat(path):
    Path(path).unlink(missing_ok=True)

def save_chat():
    try:
        title = get_chat_title_from_messages(st.session_state.messages)
        st.session_state.current_chat_title = title
        
        # Guardar en BD (si está autenticado)
        if st.session_state.get("user_id"):
            chat_id = db.save_chat(user_id=st.session_state.user_id, chat_id=st.session_state.current_chat, title=title)
            db.delete_messages_by_chat_id(chat_id) 
            for i, m in enumerate(st.session_state.messages):
                db.save_message(chat_id=chat_id, role=m["role"], content=m["content"], message_order=i)
        
        # Guardar en local (para todos, incluyendo 'anon')
        local_save_chat(st.session_state.get("user_id"), st.session_state.current_chat, st.session_state.messages, title=title)
    except Exception as e:
        print("Error guardando chat:", e)

# ------------------ Voz (Text-to-Speech) ------------------
def text_to_audio_base64(text, lang='es'):
    """Convierte texto a audio MP3 en memoria y devuelve la cadena base64."""
    if not gTTS: return None # Verifica que la librería esté importada

    mp3_fp = io.BytesIO()
    try:
        # Limita el texto a 2000 caracteres para evitar problemas de procesamiento
        text = text[:2000]
        
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        b64 = base64.b64encode(mp3_fp.read()).decode()
        return f"data:audio/mp3;base64,{b64}"
    except Exception as e:
        print(f"Error en gTTS: {e}")
        return None

# ------------------ Chat Principal ------------------
def _auto_scroll():
    components.html("""
    <script>
    const tryScroll = () => {
        const els = parent.document.querySelectorAll('.chat-box');
        if (els.length) { 
            const el = els[els.length-1]; 
            el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        }
    };
    setTimeout(tryScroll, 50); setTimeout(tryScroll, 200); setTimeout(tryScroll, 600); 
    </script>
    """, height=0)

def render_chat(messages):
    st.markdown('<div class="chat-box">', unsafe_allow_html=True) 
    for m in messages:
        role = m["role"] if m["role"] in ("user","assistant") else "assistant"
        icon = "👤" if role == "user" else "💡"
        
        with st.chat_message(role, avatar=icon):
            st.markdown(m["content"])
            st.caption(datetime.now().strftime("%H:%M")) 
    st.markdown('</div>', unsafe_allow_html=True)
    _auto_scroll()

def typewriter_markdown(full_text, delay=0.005):
    placeholder = st.empty()
    acc = ""
    lines = full_text.split("\n")
    for i, line in enumerate(lines):
        for char in line:
            acc += char
            placeholder.markdown(acc)
            time.sleep(delay)
        if i < len(lines) - 1:
             acc += "\n"
             placeholder.markdown(acc)
    return acc

def get_personalized_context(user_id, query):
    try:
        ctxs = st.session_state.get("user_context") or db.get_user_context(user_id)
        if not ctxs: return ""
        ql = (query or "").lower().split()
        relev = []
        for c in ctxs:
            body = (c.get("context_data") or "").lower()[-2500:] 
            if any(w for w in ql if len(w) > 3 and w in body):
                relev.append((c.get("context_key","Contexto"), c.get("context_data","")))
        
        relev.reverse() 
        
        if not relev: return ""
        out = "\n\n--- Contexto personalizado de Archivos Relevantes ---\n"
        for k,v in relev[:2]: 
            out += f"\n**{k}:**\n{v[:1000]}{'...' if len(v)>1000 else ''}\n"
        out += "--------------------------------------------------------\n"
        return out
    except Exception:
        return ""

def chat_page():
    st.title(f"💬 {st.session_state.get('current_chat_title', 'Chat con Zero')}")

    render_chat(st.session_state.messages)

    if prompt := st.chat_input("Escribe tu mensaje o adjunta archivos para contexto..."):
        # 1. Mensaje de usuario
        st.session_state.messages.append({"role":"user","content":prompt})
        
        # 2. Crear prompt mejorado con contexto de archivos
        enhanced = prompt
        if st.session_state.get("user_id"):
            ctx = get_personalized_context(st.session_state.user_id, prompt) 
            if ctx: enhanced = f"{prompt}\n\n{ctx}"
        
        # Preparar mensajes para la API
        api_messages = [{"role":m["role"],"content":m["content"]} for m in st.session_state.messages[:-1]]
        api_messages.append({"role":"user","content":enhanced}) 

        # Renderizar el último mensaje del usuario inmediatamente
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
            st.caption(datetime.now().strftime("%H:%M"))
        
        with st.spinner("Zero está pensando..."):
            raw_reply = groq_chat(api_messages)
        
        reply = safe_text(raw_reply)

        with st.chat_message("assistant", avatar="💡"):
            if st.session_state.get("typing_effect", True):
                rendered = typewriter_markdown(reply, delay=0.005) 
            else:
                st.markdown(reply)
                rendered = reply
            st.caption(datetime.now().strftime("%H:%M"))
            
            # 🔊 LÓGICA DE VOZ (TTS) - Reproducción Automática
            if gTTS:
                audio_b64 = text_to_audio_base64(rendered)
                if audio_b64:
                    st.components.v1.html(
                        f"""
                        <audio controls autoplay style="display:none">
                            <source src="{audio_b64}" type="audio/mp3">
                        </audio>
                        """,
                        height=0,
                    )
                    st.caption("🔊 **(Zero ha hablado)**")
                else:
                    st.caption("⚠️ Error al generar la voz.")
            else:
                st.caption("⚠️ gTTS no está disponible para generar voz.")

        # 3. Guardar el mensaje del asistente
        st.session_state.messages.append({"role":"assistant","content":rendered})

        # 4. Guardar estado y actividad
        save_chat(); update_activity()
        _auto_scroll()

# ------------------ Extractores Fallback CORREGIDOS ------------------
def extract_pdf_text(path):
    """Extrae texto de PDF con manejo robusto de errores."""
    if not PyPDF2: 
        return None, "Módulo PyPDF2 no instalado (pip install PyPDF2)."
    try:
        # Convierte Path a string y verifica existencia
        path_str = str(path)
        if not os.path.exists(path_str):
            return None, f"El archivo no existe: {path_str}"
        
        text = []
        with open(path_str, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for p in reader.pages: 
                page_text = p.extract_text() or ""
                if page_text.strip():  # Solo añadir páginas con texto
                    text.append(page_text)
        
        result = "\n".join(text).strip()
        return result if result else None, "PDF vacío o sin texto extraíble"
        
    except Exception as e: 
        return None, f"PDF error: {str(e)}"

def extract_pptx_text(path):
    if not Presentation: return None, "Módulo python-pptx no instalado (pip install python-pptx)."
    try:
        path_str = str(path)
        if not os.path.exists(path_str):
            return None, f"El archivo no existe: {path_str}"
            
        prs = Presentation(path_str); parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape,"has_text_frame") and shape.has_text_frame: parts.append(shape.text)
        return "\n".join(parts).strip(), None
    except Exception as e: return None, f"PPTX error: {e}"

def extract_excel_text(path):
    if not pd: return None, "Módulos pandas, openpyxl/xlrd no instalados (pip install pandas openpyxl xlrd)."
    try:
        path_str = str(path)
        if not os.path.exists(path_str):
            return None, f"El archivo no existe: {path_str}"
            
        lower = path_str.lower()
        if lower.endswith(".csv"): df = pd.read_csv(path_str, nrows=200)
        elif lower.endswith(".xlsx"): df = pd.read_excel(path_str, engine="openpyxl")
        elif lower.endswith(".xls"): df = pd.read_excel(path_str)
        else: return None, "Formato excel no reconocido"
        return df.head(50).to_csv(index=False), None 
    except Exception as e: return None, f"Excel error: {e}"

def extract_image_text_or_meta(path):
    if not pytesseract: return None, "Módulo pytesseract no instalado (pip install pytesseract pillow)."
    try:
        path_str = str(path)
        if not os.path.exists(path_str):
            return None, f"El archivo no existe: {path_str}"
            
        img = Image.open(path_str); txt = ""; 
        try: txt = (pytesseract.image_to_string(img) or "").strip()
        except Exception: pass
        meta = [f"Imagen: {os.path.basename(path_str)}", f"Tamaño: {img.size[0]}x{img.size[1]} px"]; final_content = (f"{txt}\n\n---\n[Metadatos]\n" + "\n".join(meta)).strip() if txt else "\n".join(meta).strip()
        if not final_content: return None, f"No se pudo extraer texto ni metadatos de {os.path.basename(path_str)}"
        return final_content, None
    except Exception as e: return None, f"Imagen error: {e}"

def fallback_extract(path):
    # Convierte Path a string si es necesario
    path_str = str(path)
    
    # Verifica que el archivo exista
    if not os.path.exists(path_str):
        return None, f"Archivo no encontrado: {path_str}"
    
    ext = os.path.splitext(path_str)[1].lower()
    if ext == ".pdf": return extract_pdf_text(path_str)
    if ext == ".pptx": return extract_pptx_text(path_str)
    if ext in (".xlsx",".xls",".csv"): return extract_excel_text(path_str)
    if ext in (".jpg",".jpeg",".png",".gif",".bmp",".webp",".tif",".tiff"): return extract_image_text_or_meta(path_str)
    return None, f"Sin extractor de reserva para la extensión: {ext}"

# ------------------ Archivos (Lógica de procesamiento mejorada) ------------------
def save_uploaded_file(uploaded_file, user_id):
    """Guarda y procesa archivos con mejor manejo de errores."""
    user_dir = Path("uploads") / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Usa el nombre original pero sanitizado
    safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in ".-_ ")
    dst = user_dir / safe_name
    
    try:
        # Guarda el archivo correctamente
        with open(dst, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        return None, f"Error al guardar el archivo: {e}", None
    
    processor = FileProcessor()
    content = summary = error = None
    fallback_used = False
    raw = None
    
    try:
        raw = processor.process_file(str(dst), uploaded_file.name)
    except Exception as e:
        raw = {"error": f"Error del procesador: {e}"}
    
    content, summary, error_main = _normalize_process_result(raw)
    
    # Lógica de fallback...
    if (not content or not content.strip() or error_main):
        fb_text, fb_err = fallback_extract(str(dst))
        if fb_text and fb_text.strip():
            content = fb_text if not content else f"{content}\n\n---\n[Fallback]\n{fb_text}"
            summary = summary or f"Contenido extraído de {uploaded_file.name} (vía Fallback)."
            error = None
            fallback_used = True
        elif fb_err and not content:
            error = error_main or ""
            error += f"\n[Fallback Error]: {fb_err}"
    
    if not content or not content.strip():
        try:
            dst.unlink(missing_ok=True)
        except Exception:
            pass
        return None, str(error or "Error: Archivo sin texto legible"), fallback_used
    
    # Guarda en base de datos
    file_type = uploaded_file.name.split(".")[-1].lower() if "." in uploaded_file.name else "txt"
    file_id = db.save_file(
        user_id=user_id, filename=uploaded_file.name, 
        file_path=str(dst), file_type=file_type, 
        file_size=uploaded_file.size, 
        content_extracted=content.strip(), 
        analysis_summary=summary or ""
    )
    
    if content.strip():
        db.save_user_context(user_id, f"Archivo: {uploaded_file.name}", content.strip(), file_id)
    
    return file_id, None, fallback_used

def file_upload_page():
    st.title("📁 Gestión de Archivos y Contexto")
    st.write("Sube documentos (**PDF, DOCX, XLSX, CSV, PPTX, TXT**) o imágenes para que Zero los use como **contexto** en el chat.")
    if not st.session_state.get("usuario"): st.error("❌ Error de sesión. Vuelve a iniciar sesión."); return
    user_id = db.get_user_id_by_username(st.session_state.usuario);
    if not user_id: st.error("❌ No se pudo obtener información del usuario. Intenta cerrar e iniciar sesión."); return
    st.session_state.user_id = user_id 
    up = st.file_uploader("Elige un archivo", type=["pdf","docx","doc","txt","xlsx","xls","csv","pptx","jpg","jpeg","png","gif","bmp","webp","tif","tiff"], key="file_uploader")
    if up is not None and st.button("🚀 Procesar Archivo y Añadir Contexto"):
        with st.spinner(f"Procesando '{up.name}'... Esto puede tomar unos segundos."):
            file_id, error_msg, fallback_used = save_uploaded_file(up, user_id)
            if file_id is None: st.error(f"❌ El procesamiento falló. {error_msg}") 
            else:
                success_msg = f"✅ Archivo '{up.name}' procesado y guardado."
                if fallback_used: st.warning("⚠️ **Advertencia:** Se utilizó un extractor de reserva para este archivo. Asegúrate de que tienes todas las librerías necesarias instaladas (PyPDF2, pandas, etc.).")
                st.success(success_msg)
                st.session_state.user_files = db.get_user_files(user_id)
                st.session_state.user_context = db.get_user_context(user_id)
                update_activity(); st.rerun() 
    
    st.subheader("📋 Archivos Subidos")
    if "user_files" not in st.session_state or not st.session_state.user_files:
        st.session_state.user_files = db.get_user_files(user_id)
    if st.session_state.user_files:
        for f in st.session_state.user_files[::-1]: 
            with st.expander(f"📄 **{f['filename']}** ({f['file_type'].upper()})"):
                col1, col2 = st.columns([3,1]);
                with col1:
                    st.write(f"**Tamaño:** {f['file_size']/1024:.1f} KB"); st.write(f"**Subido:** {f['uploaded_at']}"); summary = f.get("analysis_summary")
                    if summary: st.markdown(f"**Resumen:** {summary[:300]}{'...' if len(summary)>300 else ''}")
                    else: st.caption("No hay resumen disponible, solo contenido extraído.")
                with col2:
                    if st.button("🗑️ Eliminar", key=f"del_{f['id']}", use_container_width=True):
                        try:
                            if os.path.exists(f['file_path']): os.remove(f['file_path'])
                        except Exception: pass
                        db.delete_file(f['id'], user_id); st.session_state.user_files = db.get_user_files(user_id)
                        st.session_state.user_context = db.get_user_context(user_id); update_activity(); st.success("✅ Archivo y contexto eliminado."); st.rerun()
                    if st.button("💬 Usar en Chat", key=f"use_{f['id']}", use_container_width=True):
                        content_extracted = f.get("content_extracted")
                        if content_extracted:
                            snippet = content_extracted[:1500]; prompt = f"📄 **Contenido del Archivo {f['filename']} ({f['file_type'].upper()}):**\n\n{snippet}..."
                            st.session_state.messages.append({"role":"user","content":prompt}); save_chat(); st.session_state.selected_page = "Chat Principal"
                            update_activity(); st.rerun()
                        else: st.warning("El archivo no tiene contenido de texto extraído.")
    else: st.info("No hay archivos subidos aún.")

# ------------------ Sidebar ------------------
def sidebar():
    st.markdown('<div class="sidebar-title">ZERO - Asistente Virtual</div>', unsafe_allow_html=True)
    st.caption(f"Bienvenido, **{st.session_state.get('usuario','Anónimo')}**")
    
    # 1. Nuevo Chat
    if st.button("➕ Nuevo Chat", use_container_width=True, key="new_chat_top"):
        save_chat() 
        st.session_state.current_chat = str(uuid.uuid4())
        st.session_state.current_chat_title = "Nuevo Chat"
        st.session_state.messages = []
        update_activity(); st.rerun()

    st.divider()
    
    # 2. Navegación
    st.subheader("🧭 Navegación")
    options = ["Chat Principal", "Subir Archivos"]
    if st.session_state.get("rol") == "admin":
        options += ["Análisis de Imágenes", "Transcripción de Audio", "Registro de Usuarios"]
    
    # Aquí se utiliza st.session_state.selected_page como valor inicial
    if st.session_state.selected_page not in options:
        st.session_state.selected_page = "Chat Principal"
    
    choice = st.radio("", options, index=options.index(st.session_state.selected_page))
    
    st.divider()

    # 3. Historial local
    with st.expander("💾 Historial Local", expanded=True):
        uid = st.session_state.get("user_id") if st.session_state.get("user_id") is not None else "anon"
        items = local_list_all(uid)

        initial_index = 0
        if st.session_state.selected_local_key:
            try:
                keys = [key for key, _, _ in items]
                initial_index = keys.index(st.session_state.selected_local_key)
            except ValueError:
                st.session_state.selected_local_key = ""

        if not items:
            st.caption("No hay chats locales aún.")
            selected_key = ""
        else:
            labels = [lbl for _, lbl, _ in items]
            keys = [key for key, _, _ in items]
            paths = {key: path for key, _, path in items}

            selected_label = st.selectbox("Mis chats", labels, index=initial_index, key="local_chat_selector")
            selected_key = keys[labels.index(selected_label)] if labels else ""
            st.session_state.selected_local_key = selected_key 

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Abrir", key="open_local", use_container_width=True, disabled=not selected_key):
                    data = local_open_chat(paths[selected_key])
                    st.session_state.current_chat = data.get("chat_id") or str(uuid.uuid4())
                    st.session_state.messages = data.get("messages") or []
                    st.session_state.current_chat_title = data.get("title") or "Chat Abierto"
                    update_activity(); st.rerun()
            with col2:
                if selected_key:
                    with open(paths[selected_key], "rb") as fh:
                        st.download_button("Descargar", data=fh.read(),
                                        file_name=os.path.basename(paths[selected_key]),
                                        mime="application/json", use_container_width=True)
                else:
                    st.button("Descargar", disabled=True, use_container_width=True)
            with col3:
                if st.button("Eliminar", key="delete_local", use_container_width=True, disabled=not selected_key):
                    local_delete_chat(paths[selected_key])
                    st.session_state.selected_local_key = ""
                    update_activity(); st.rerun()

    st.divider()

    # 4. Controles de Sesión y Configuración
    with st.expander("⚙️ Sesión y Configuración", expanded=False):
        # Historial BD (opcional)
        if st.session_state.get("user_id"):
            st.subheader("Historial en BD")
            try:
                user_chats = db.get_user_chats(st.session_state.user_id)
                if not user_chats: st.caption("No hay chats en BD.")
                else:
                    titles = [f"{c.get('title','Nuevo chat')} ({c.get('updated_at').split(' ')[0]})" for c in user_chats[::-1]] 
                    sel = st.selectbox("Chats en BD", titles, key="db_chat_selector") if titles else None
                    if sel:
                        idx = titles.index(sel)
                        chat = user_chats[::-1][idx]
                        if st.button("Abrir chat BD", use_container_width=True):
                            msgs = db.get_chat_messages(chat["chat_id"])
                            st.session_state.current_chat = chat["chat_id"]
                            st.session_state.messages = [{"role":m["role"],"content":m["content"]} for m in msgs]
                            st.session_state.current_chat_title = chat.get("title") or "Chat Abierto (BD)"
                            update_activity(); st.rerun()
            except Exception:
                st.caption("Base de datos no disponible o error de conexión.")
        
        st.markdown("---")
        
        st.toggle("✍️ Mostrar efecto de escritura", value=st.session_state.get("typing_effect", True), key="typing_effect")
        
        st.markdown("---")

        if st.button("🚪 Cerrar sesión", use_container_width=True):
            clean_session() 

    return choice

# ------------------ Páginas extra ------------------
def image_page():
    st.title("🖼️ Análisis de Imágenes con Groq Vision")
    if st.session_state.get("rol") != "admin": st.error("❌ Acceso denegado. Se requiere rol de administrador."); return
    
    up = st.file_uploader("Elige una imagen (JPG, PNG, GIF, etc.)", type=["jpg","jpeg","png","gif","bmp","webp","tif","tiff"])
    
    if up is not None:
        st.image(up, caption="Imagen a analizar", use_column_width=True)
        
        prompt_txt = st.text_input("Instrucción para la IA (ej. 'Describe esta imagen en detalle')", 
                                   value=f"Analiza esta imagen '{up.name}' y proporciona un resumen conciso y profesional, enfocándote en los elementos clave.",
                                   key="vision_prompt")
        
        if st.button("🔍 Analizar Imagen con IA Vision"):
            with st.spinner("Analizando imagen..."):
                try:
                    img_base64 = base64.b64encode(up.getvalue()).decode("utf-8")
                    mime_type = up.type if up.type else "image/jpeg"
                    
                    payload = {
                        "model": GROQ_VISION_MODEL,
                        "messages": [{
                            "role":"user",
                            "content":[
                                {"type":"text","text":prompt_txt},
                                {"type":"image_url","image_url":{"url":f"data:{mime_type};base64,{img_base64}"}}
                            ]
                        }],
                        "max_tokens":1000,"temperature":0.3
                    }
                    
                    r = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=90)
                    
                    if r.status_code == 200:
                        st.success("Análisis completado.")
                        st.markdown(r.json()["choices"][0]["message"]["content"])
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                
                except requests.exceptions.Timeout:
                    st.error("❌ Tiempo de espera agotado. La IA tardó demasiado en responder.")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error en la solicitud: {e}")

            update_activity()
    update_activity()

def audio_page():
    st.title("🎤 Transcripción de Audio")
    st.info("En construcción. Implementa una API de transcripción aquí (por ejemplo, OpenAI Whisper).")
    update_activity()

def register_page():
    st.title("👥 Registro de Usuarios")
    if st.session_state.get("rol") != "admin": st.error("❌ Acceso denegado. Solo administradores pueden registrar nuevos usuarios."); return
    with st.form("registro_form"):
        st.subheader("Crear Nuevo Usuario"); user = st.text_input("Nombre de usuario"); pwd = st.text_input("Contraseña", type="password"); cpwd = st.text_input("Confirmar contraseña", type="password")
        col_rol, col_email = st.columns(2)
        with col_rol:
            rol = st.selectbox("Rol", ["usuario","admin"])
        with col_email: email = st.text_input("Email (Opcional)"); ok = st.form_submit_button("Registrar Usuario")
        if ok:
            if not user or not pwd: st.error("El nombre de usuario y la contraseña son obligatorios."); return
            if pwd != cpwd: st.error("Las contraseñas no coinciden."); return
            if len(pwd) < 6: st.error("La contraseña debe tener al menos 6 caracteres."); return
            try:
                done = registrar_usuario(user, pwd, rol, email) 
                if done: st.success(f"✅ Usuario '{user}' registrado con el rol de '{rol}'.")
                else: st.error("❌ No se pudo registrar. El usuario ya existe o hubo un error de BD.")
            except Exception as e: st.error(f"❌ Error al registrar: {str(e)}")
    update_activity()

# ------------------ Main (Lógica de Sesión) ------------------
def main():
    check_inactivity()
    restore_any_session()

    if not st.session_state.get("autenticado", False):
        verificar_login()
        if st.session_state.get("autenticado") and st.session_state.get("user_id"):
            persist_login(); update_activity()
        else:
            return 
    else:
        update_activity()

    if st.session_state.get("user_id") and (not st.session_state.get("user_files") or not st.session_state.get("user_context")):
        st.session_state.user_files = db.get_user_files(st.session_state.user_id)
        st.session_state.user_context = db.get_user_context(st.session_state.user_id)

    with st.sidebar:
        choice = sidebar()
    
    st.session_state.selected_page = choice 

    if st.session_state.selected_page == "Chat Principal":
        chat_page()
    elif st.session_state.selected_page == "Subir Archivos":
        file_upload_page()
    elif st.session_state.selected_page == "Análisis de Imágenes":
        if st.session_state.get("rol") == "admin": image_page()
        else: st.error("Acceso denegado.")
    elif st.session_state.selected_page == "Transcripción de Audio":
        if st.session_state.get("rol") == "admin": audio_page()
        else: st.error("Acceso denegado.")
    elif st.session_state.selected_page == "Registro de Usuarios":
        if st.session_state.get("rol") == "admin": register_page()
        else: st.error("Acceso denegado.")

if __name__ == "__main__":
    main()