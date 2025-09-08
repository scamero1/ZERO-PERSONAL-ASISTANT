import streamlit as st
import json
import os
from lector_nfc import leer_uid_pn532
from auth_jwt import JWTAuth
import time

RUTA_USUARIOS = "usuarios.json"
TERMINOS_FILE = "TERMINOS.txt"

# --- CARGAR USUARIOS ---
def cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):
        return {}
    with open(RUTA_USUARIOS, "r", encoding='utf-8') as f:
        return json.load(f)

# --- GUARDAR USUARIOS ---
def guardar_usuarios(usuarios):
    with open(RUTA_USUARIOS, "w", encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

# --- CARGAR TÉRMINOS Y CONDICIONES ---
def cargar_terminos():
    if not os.path.exists(TERMINOS_FILE):
        return "Términos y condiciones no disponibles."
    with open(TERMINOS_FILE, "r", encoding='utf-8') as f:
        return f.read()

# --- REGISTRAR NUEVO USUARIO ---
def registrar_usuario(usuario, clave, rol, uid_nfc=None):
    usuarios = cargar_usuarios()
    if usuario in usuarios:
        st.warning("⚠️ El usuario ya existe.")
        return
    usuarios[usuario] = {
        "clave": clave,
        "rol": rol,
        "nfc_uid": uid_nfc
    }
    guardar_usuarios(usuarios)
    st.success(f"✅ Usuario '{usuario}' registrado con rol '{rol}'")

# --- VERIFICAR LOGIN ---
def verificar_login():
    # Verificar si ya está autenticado con JWT
    if JWTAuth.is_authenticated():
        return
    
    # Inicializar estado
    if "modo_login" not in st.session_state:
        st.session_state.modo_login = None
    if "mostrar_terminos" not in st.session_state:
        st.session_state.mostrar_terminos = False
    if "acepta_terminos" not in st.session_state:
        st.session_state.acepta_terminos = False
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "last_attempt_time" not in st.session_state:
        st.session_state.last_attempt_time = 0

    # Configurar página - CSS mejorado
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
            
            /* 🌟 VARIABLES DE DISEÑO PREMIUM */
            :root {
                --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                --dark-gradient: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
                --glass-bg: rgba(255, 255, 255, 0.08);
                --glass-border: rgba(255, 255, 255, 0.18);
                --text-primary: #ffffff;
                --text-secondary: rgba(255, 255, 255, 0.8);
                --text-accent: #667eea;
                --shadow-premium: 0 25px 50px rgba(0, 0, 0, 0.25);
                --shadow-glow: 0 0 40px rgba(102, 126, 234, 0.3);
                --shadow-intense: 0 30px 60px rgba(102, 126, 234, 0.4);
                --border-radius-xl: 28px;
                --border-radius-lg: 20px;
                --border-radius-md: 16px;
                --transition-premium: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
                --transition-bounce: all 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            }
            
            /* Animaciones mejoradas */
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
            
            @keyframes bounceIn {
                0% {
                    opacity: 0;
                    transform: scale(0.3);
                }
                50% {
                    opacity: 1;
                    transform: scale(1.05);
                }
                70% {
                    transform: scale(0.9);
                }
                100% {
                    opacity: 1;
                    transform: scale(1);
                }
            }
            
            @keyframes nfcPulse {
                0% {
                    box-shadow: 0 0 0 0 rgba(126, 63, 242, 0.7);
                }
                70% {
                    box-shadow: 0 0 0 15px rgba(126, 63, 242, 0);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(126, 63, 242, 0);
                }
            }
            
            @keyframes inputGlow {
                0% {
                    border-color: var(--primary-purple);
                    box-shadow: 0 0 5px rgba(106, 13, 173, 0.3);
                }
                50% {
                    border-color: var(--secondary-purple);
                    box-shadow: var(--shadow-input-focus);
                }
                100% {
                    border-color: var(--primary-purple);
                    box-shadow: 0 0 5px rgba(106, 13, 173, 0.3);
                }
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
                20%, 40%, 60%, 80% { transform: translateX(8px); }
            }
            
            /* Fondo principal - Degradado morado → negro con efecto de partículas */
            .stApp {
                background: linear-gradient(135deg, #6A0DAD 0%, #4B0082 50%, #000000 100%) !important;
                min-height: 100vh !important;
                font-family: 'Poppins', sans-serif !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: relative !important;
                overflow-x: hidden !important;
            }
            
            /* Efecto de partículas en el fondo */
            .stApp::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-image: 
                    radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.3), transparent),
                    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.2), transparent),
                    radial-gradient(1px 1px at 90px 40px, rgba(255,255,255,0.3), transparent),
                    radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.2), transparent),
                    radial-gradient(1px 1px at 260px 80px, rgba(255,255,255,0.2), transparent),
                    radial-gradient(2px 2px at 300px 30px, rgba(255,255,255,0.2), transparent),
                    radial-gradient(1px 1px at 350px 150px, rgba(255,255,255,0.3), transparent),
                    radial-gradient(2px 2px at 420px 60px, rgba(255,255,255,0.2), transparent),
                    radial-gradient(1px 1px at 500px 100px, rgba(255,255,255,0.3), transparent);
                background-repeat: repeat;
                background-size: 600px 600px;
                opacity: 0.5;
                animation: backgroundMove 120s infinite linear;
                z-index: -1;
            }
            
            @keyframes backgroundMove {
                from { background-position: 0 0; }
                to { background-position: 600px 600px; }
            }
            
            /* === CAMPOS DE ENTRADA MEJORADOS === */
            .stTextInput {
                margin-bottom: 2rem !important;
                position: relative !important;
            }
            
            .stTextInput > label {
                font-weight: 600 !important;
                color: var(--white) !important;
                font-size: 1.1rem !important;
                margin-bottom: 0.8rem !important;
                display: block !important;
                font-family: 'Poppins', sans-serif !important;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
            }
            
            .stTextInput > div > div {
                position: relative !important;
            }
            
            .stTextInput > div > div > input {
                /* Diseño mejorado */
                border: 3px solid rgba(255, 255, 255, 0.3) !important;
                border-radius: var(--border-radius-input) !important;
                padding: 1.5rem 1.5rem 1.5rem 4rem !important;
                font-size: 1.1rem !important;
                background: rgba(255, 255, 255, 0.1) !important;
                color: var(--white) !important;
                transition: var(--transition-smooth) !important;
                width: 100% !important;
                backdrop-filter: blur(15px) !important;
                font-family: 'Poppins', sans-serif !important;
                font-weight: 500 !important;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2) !important;
            }
            
            .stTextInput > div > div > input:focus {
                border: 3px solid transparent !important;
                background: linear-gradient(rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.15)) padding-box,
                           linear-gradient(135deg, var(--primary-purple), var(--secondary-purple)) border-box !important;
                outline: none !important;
                transform: translateY(-3px) scale(1.02) !important;
                box-shadow: var(--shadow-input-focus) !important;
                animation: inputGlow 2s ease-in-out infinite !important;
            }
            
            .stTextInput > div > div > input::placeholder {
                color: var(--gray-medium) !important;
                opacity: 0.8 !important;
                font-style: italic !important;
            }
            
            /* Íconos internos para inputs */
            .stTextInput:nth-of-type(1) > div > div::before {
                content: '👤' !important;
                position: absolute !important;
                left: 1.2rem !important;
                top: 50% !important;
                transform: translateY(-50%) !important;
                font-size: 1.3rem !important;
                z-index: 10 !important;
                pointer-events: none !important;
            }
            
            .stTextInput:nth-of-type(2) > div > div::before {
                content: '🔒' !important;
                position: absolute !important;
                left: 1.2rem !important;
                top: 50% !important;
                transform: translateY(-50%) !important;
                font-size: 1.3rem !important;
                z-index: 10 !important;
                pointer-events: none !important;
            }
            
            /* === BOTÓN NFC REDISEÑADO === */
            .stButton:has([data-testid="baseButton-secondary"]) > button,
            .nfc-button {
                background: linear-gradient(135deg, var(--primary-purple) 0%, var(--hover-black) 100%) !important;
                color: var(--white) !important;
                border: 2px solid var(--secondary-purple) !important;
                border-radius: 20px !important;
                padding: 1.8rem 2rem !important;
                font-size: 1.1rem !important;
                font-weight: 600 !important;
                font-family: 'Poppins', sans-serif !important;
                width: 100% !important;
                margin: 1.5rem 0 !important;
                cursor: pointer !important;
                transition: var(--transition-smooth) !important;
                position: relative !important;
                overflow: hidden !important;
                box-shadow: 0 8px 25px rgba(106, 13, 173, 0.3) !important;
                animation: nfcPulse 2s infinite !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 0.8rem !important;
            }
            
            .stButton:has([data-testid="baseButton-secondary"]) > button:hover,
            .nfc-button:hover {
                transform: translateY(-4px) scale(1.05) !important;
                background: linear-gradient(135deg, var(--secondary-purple) 0%, var(--primary-purple) 100%) !important;
                border-color: var(--light-purple) !important;
                box-shadow: 0 15px 40px rgba(126, 63, 242, 0.5), 0 0 30px rgba(126, 63, 242, 0.3) !important;
                filter: brightness(1.2) !important;
            }
            
            /* Ícono NFC animado */
            .nfc-button::before {
                content: '📡' !important;
                font-size: 1.4rem !important;
                animation: nfcPulse 1.5s infinite !important;
            }
            
            /* === BOTÓN PRINCIPAL DE LOGIN === */
            .stButton[data-testid="baseButton-primary"] > button {
                background: linear-gradient(135deg, var(--primary-purple) 0%, var(--white) 50%, var(--hover-black) 100%) !important;
                color: var(--white) !important;
                border: none !important;
                border-radius: 18px !important;
                padding: 1.5rem 3rem !important;
                font-size: 1.2rem !important;
                font-weight: 700 !important;
                font-family: 'Poppins', sans-serif !important;
                width: 100% !important;
                margin: 2rem auto !important;
                display: block !important;
                cursor: pointer !important;
                transition: var(--transition-smooth) !important;
                position: relative !important;
                overflow: hidden !important;
                box-shadow: 0 10px 30px rgba(106, 13, 173, 0.4) !important;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5) !important;
                animation: fadeInUp 0.8s ease-out !important;
            }
            
            .stButton[data-testid="baseButton-primary"] > button:hover {
                transform: translateY(-4px) scale(1.03) !important;
                background: linear-gradient(135deg, var(--light-purple) 0%, var(--white) 50%, var(--secondary-purple) 100%) !important;
                box-shadow: 0 15px 45px rgba(155, 89, 182, 0.6), 0 0 40px rgba(155, 89, 182, 0.4) !important;
                filter: brightness(1.1) !important;
                border: 2px solid rgba(255, 255, 255, 0.8) !important;
            }
            
            /* === TÉRMINOS COMO ENLACE === */
            .terms-link {
                display: inline-block !important;
                color: var(--primary-purple) !important;
                text-decoration: underline !important;
                font-weight: 600 !important;
                font-family: 'Poppins', sans-serif !important;
                font-size: 1rem !important;
                margin: 1.5rem 0 !important;
                cursor: pointer !important;
                transition: var(--transition-smooth) !important;
                text-align: center !important;
                width: 100% !important;
            }
            
            .terms-link:hover {
                color: var(--light-purple) !important;
                text-shadow: 0 0 10px rgba(155, 89, 182, 0.5) !important;
                transform: scale(1.05) !important;
            }
            
            /* === CONTENEDOR PRINCIPAL === */
            .login-container {
                background: rgba(255, 255, 255, 0.15) !important;
                backdrop-filter: blur(20px) !important;
                border-radius: var(--border-radius) !important;
                padding: 3rem !important;
                margin: 2rem auto !important;
                max-width: 450px !important;
                width: 90% !important;
                position: relative !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
                box-shadow: var(--shadow-soft), var(--shadow-glow) !important;
                transition: var(--transition-smooth) !important;
                animation: fadeInUp 0.8s ease-out !important;
            }
            
            .login-container:hover {
                transform: translateY(-5px) !important;
                box-shadow: var(--shadow-hover), var(--shadow-glow) !important;
            }
            
            /* Header del login */
            .login-header {
                text-align: center !important;
                margin-bottom: 3rem !important;
            }
            
            .login-title {
                font-family: 'Poppins', 'Montserrat', sans-serif !important;
                font-size: 3.2rem !important;
                font-weight: 800 !important;
                color: var(--white) !important;
                margin-bottom: 0.5rem !important;
                letter-spacing: -0.02em !important;
                text-shadow: 2px 4px 8px rgba(0, 0, 0, 0.3) !important;
                background: linear-gradient(135deg, #ffffff, #f0f0f0) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                background-clip: text !important;
            }
            
            .login-subtitle {
                color: var(--gray-light) !important;
                font-size: 1.1rem !important;
                font-weight: 400 !important;
                font-family: 'Poppins', 'Montserrat', sans-serif !important;
                letter-spacing: 0.5px !important;
                opacity: 0.9 !important;
            }
            
            /* === MENSAJES DE ALERTA CON SCROLL === */
            .stAlert {
                border-radius: 15px !important;
                margin: 1rem 0 !important;
                animation: fadeInUp 0.5s ease-out !important;
                scroll-behavior: smooth !important;
            }
            
            .stAlert[data-baseweb="notification"] {
                background: rgba(255, 255, 255, 0.1) !important;
                backdrop-filter: blur(10px) !important;
                border: 2px solid !important;
            }
            
            .stAlert[data-baseweb="notification"][kind="success"] {
                border-color: var(--success) !important;
                color: #90EE90 !important;
            }
            
            .stAlert[data-baseweb="notification"][kind="error"] {
                border-color: var(--error) !important;
                color: #FFB6C1 !important;
                animation: shake 0.5s ease-in-out !important;
            }
            
            .stAlert[data-baseweb="notification"][kind="warning"] {
                border-color: var(--warning) !important;
                color: #FFEAA7 !important;
            }
            
            /* === BOTONES DE SELECCIÓN DE MÉTODO - MEJORADOS Y CENTRADOS === */
            .method-selection {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                gap: 3rem !important;
                margin: 4rem auto !important;
                max-width: 700px !important;
                padding: 2rem !important;
            }

            /* Contenedor de columnas mejorado */
            .stColumns {
                display: flex !important;
                justify-content: center !important;
                align-items: stretch !important;
                gap: 3rem !important;
                width: 100% !important;
                margin: 2rem 0 !important;
            }

            .stColumn {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                flex: 1 !important;
            }

            /* === BOTÓN USUARIO Y CONTRASEÑA MEJORADO === */
            .stButton[key="btn_password"] > button,
            .stColumns .stColumn:first-child .stButton > button {
                /* Diseño premium */
                background: linear-gradient(145deg, #6A0DAD 0%, #8A2BE2 50%, #9370DB 100%) !important;
                color: var(--white) !important;
                border: 3px solid rgba(255, 255, 255, 0.2) !important;
                border-radius: 25px !important;
                padding: 3rem 2.5rem !important;
                font-size: 1.2rem !important;
                font-weight: 800 !important;
                font-family: 'Poppins', sans-serif !important;
                width: 100% !important;
                min-height: 180px !important;
                max-width: 280px !important;
                margin: 0 auto !important;
                
                /* Centrado perfecto */
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                gap: 1rem !important;
                
                /* Efectos visuales premium */
                cursor: pointer !important;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
                position: relative !important;
                overflow: hidden !important;
                
                /* Sombras elegantes */
                box-shadow: 
                    0 15px 35px rgba(106, 13, 173, 0.4),
                    0 5px 15px rgba(0, 0, 0, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
                
                /* Animación de entrada */
                animation: fadeInUp 0.8s ease-out !important;
                
                /* Texto con sombra */
                text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
                line-height: 1.3 !important;
                letter-spacing: 0.5px !important;
            }

            .stButton[key="btn_password"] > button:before {
                content: '' !important;
                position: absolute !important;
                top: 0 !important;
                left: -100% !important;
                width: 100% !important;
                height: 100% !important;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent) !important;
                transition: left 0.5s !important;
            }

            .stButton[key="btn_password"] > button:hover {
                transform: translateY(-8px) scale(1.08) !important;
                background: linear-gradient(145deg, #7B1FA2 0%, #9C27B0 50%, #BA68C8 100%) !important;
                border: 3px solid rgba(255, 255, 255, 0.4) !important;
                
                /* Sombra intensa */
                box-shadow: 
                    0 25px 50px rgba(155, 89, 182, 0.6),
                    0 10px 30px rgba(0, 0, 0, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
                
                /* Brillo */
                filter: brightness(1.15) !important;
            }

            .stButton[key="btn_password"] > button:hover:before {
                left: 100% !important;
            }

            /* === BOTÓN TARJETA NFC MEJORADO === */
            .stButton[key="btn_nfc"] > button,
            .stColumns .stColumn:last-child .stButton > button {
                /* Diseño premium con gradiente negro-morado */
                background: linear-gradient(145deg, #1a1a1a 0%, #2d1b69 50%, #6A0DAD 100%) !important;
                color: var(--white) !important;
                border: 3px solid rgba(126, 63, 242, 0.5) !important;
                border-radius: 25px !important;
                padding: 3rem 2.5rem !important;
                font-size: 1.2rem !important;
                font-weight: 800 !important;
                font-family: 'Poppins', sans-serif !important;
                width: 100% !important;
                min-height: 180px !important;
                max-width: 280px !important;
                margin: 0 auto !important;
                
                /* Centrado perfecto */
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                gap: 1rem !important;
                
                /* Efectos visuales premium */
                cursor: pointer !important;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
                position: relative !important;
                overflow: hidden !important;
                
                /* Sombras con efecto NFC */
                box-shadow: 
                    0 15px 35px rgba(0, 0, 0, 0.5),
                    0 5px 15px rgba(126, 63, 242, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
                
                /* Animación de pulso NFC */
                animation: nfcPulseEnhanced 2.5s infinite, fadeInUp 0.8s ease-out !important;
                
                /* Texto con sombra */
                text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6) !important;
                line-height: 1.3 !important;
                letter-spacing: 0.5px !important;
            }

            .stButton[key="btn_nfc"] > button:before {
                content: '' !important;
                position: absolute !important;
                top: 0 !important;
                left: -100% !important;
                width: 100% !important;
                height: 100% !important;
                background: linear-gradient(90deg, transparent, rgba(126, 63, 242, 0.3), transparent) !important;
                transition: left 0.5s !important;
            }

            .stButton[key="btn_nfc"] > button:hover {
                transform: translateY(-8px) scale(1.08) !important;
                background: linear-gradient(145deg, #2d1b69 0%, #6A0DAD 50%, #8A2BE2 100%) !important;
                border: 3px solid rgba(126, 63, 242, 0.8) !important;
                
                /* Sombra intensa con efecto NFC */
                box-shadow: 
                    0 25px 50px rgba(126, 63, 242, 0.6),
                    0 10px 30px rgba(0, 0, 0, 0.4),
                    0 0 40px rgba(126, 63, 242, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
                
                /* Brillo y efecto de señal */
                filter: brightness(1.2) !important;
            }

            .stButton[key="btn_nfc"] > button:hover:before {
                left: 100% !important;
            }

            /* Animación de pulso NFC mejorada */
            @keyframes nfcPulseEnhanced {
                0% {
                    box-shadow: 
                        0 15px 35px rgba(0, 0, 0, 0.5),
                        0 5px 15px rgba(126, 63, 242, 0.3),
                        0 0 0 0 rgba(126, 63, 242, 0.7) !important;
                }
                50% {
                    box-shadow: 
                        0 15px 35px rgba(0, 0, 0, 0.5),
                        0 5px 15px rgba(126, 63, 242, 0.3),
                        0 0 0 20px rgba(126, 63, 242, 0) !important;
                }
                100% {
                    box-shadow: 
                        0 15px 35px rgba(0, 0, 0, 0.5),
                        0 5px 15px rgba(126, 63, 242, 0.3),
                        0 0 0 25px rgba(126, 63, 242, 0) !important;
                }
            }

            /* === DESCRIPCIÓN ZERO AI 2025 === */
            .zero-description {
                text-align: center !important;
                margin: 3rem auto 2rem !important;
                max-width: 600px !important;
                padding: 2rem !important;
                background: rgba(255, 255, 255, 0.05) !important;
                border-radius: 20px !important;
                border: 1px solid rgba(106, 13, 173, 0.3) !important;
                backdrop-filter: blur(10px) !important;
                animation: fadeInUp 1s ease-out 0.5s both !important;
            }

            .zero-title {
                font-size: 1.8rem !important;
                font-weight: 700 !important;
                background: linear-gradient(135deg, #6A0DAD, #8A2BE2, #9370DB) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                background-clip: text !important;
                margin-bottom: 1rem !important;
                font-family: 'Poppins', sans-serif !important;
            }

            .zero-subtitle {
                color: rgba(255, 255, 255, 0.8) !important;
                font-size: 1rem !important;
                line-height: 1.6 !important;
                font-weight: 400 !important;
                margin-bottom: 0.5rem !important;
            }

            .zero-year {
                color: rgba(106, 13, 173, 0.9) !important;
                font-size: 0.9rem !important;
                font-weight: 600 !important;
                letter-spacing: 1px !important;
            }

            /* === RESPONSIVE MEJORADO === */
            @media (max-width: 768px) {
                .method-selection {
                    flex-direction: column !important;
                    gap: 2rem !important;
                    margin: 3rem auto !important;
                    padding: 1rem !important;
                }
                
                .stColumns {
                    flex-direction: column !important;
                    gap: 2rem !important;
                }
                
                .stButton[key="btn_password"] > button,
                .stButton[key="btn_nfc"] > button,
                .stColumns .stColumn .stButton > button {
                    max-width: 100% !important;
                    min-height: 150px !important;
                    padding: 2.5rem 2rem !important;
                    font-size: 1.1rem !important;
                }

                .zero-description {
                    margin: 2rem auto 1rem !important;
                    padding: 1.5rem !important;
                }

                .zero-title {
                    font-size: 1.5rem !important;
                }
            }

            @media (max-width: 480px) {
                .stButton[key="btn_password"] > button,
                .stButton[key="btn_nfc"] > button,
                .stColumns .stColumn .stButton > button {
                    min-height: 130px !important;
                    padding: 2rem 1.5rem !important;
                    font-size: 1rem !important;
                }

                .zero-description {
                    padding: 1rem !important;
                }

                .zero-title {
                    font-size: 1.3rem !important;
                }
            }

            /* Espaciado entre elementos */
            .method-buttons + .stButton {
                margin-top: 2rem !important;
            }

            /* Centrado del botón de términos */
            .stButton[key="ver_terminos"] {
                display: flex !important;
                justify-content: center !important;
                margin: 2rem auto !important;
                max-width: 300px !important;
            }

            .stButton[key="ver_terminos"] > button {
                background: transparent !important;
                color: var(--primary-purple) !important;
                border: 2px solid var(--primary-purple) !important;
                border-radius: 15px !important;
                padding: 1rem 2rem !important;
                font-weight: 600 !important;
                transition: var(--transition-smooth) !important;
                width: 100% !important;
            }

            .stButton[key="ver_terminos"] > button:hover {
                background: var(--primary-purple) !important;
                color: var(--white) !important;
                transform: translateY(-2px) scale(1.02) !important;
                box-shadow: 0 8px 20px rgba(106, 13, 173, 0.4) !important;
            }
            
            /* Progress bar para NFC */
            .nfc-progress {
                height: 6px !important;
                border-radius: 3px !important;
                background: linear-gradient(90deg, var(--primary-purple), var(--secondary-purple)) !important;
                margin: 1rem 0 !important;
                animation: nfcProgress 2s infinite !important;
            }
            
            @keyframes nfcProgress {
                0% { width: 0%; }
                50% { width: 70%; }
                100% { width: 100%; }
            }
            
            /* Ocultar elementos de Streamlit */
            .stDeployButton {
                display: none !important;
            }
            
            header[data-testid="stHeader"] {
                display: none !important;
            }
            
            .stMainBlockContainer {
                padding-top: 0 !important;
            }
            
            /* Tarjeta NFC visual */
            .nfc-card {
                width: 200px;
                height: 120px;
                background: linear-gradient(135deg, #2c3e50, #4a5568);
                border-radius: 12px;
                margin: 1rem auto;
                padding: 1rem;
                position: relative;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
                border: 2px solid rgba(255, 255, 255, 0.1);
                overflow: hidden;
                animation: cardGlow 3s infinite alternate;
            }
            
            .nfc-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 30px;
                background: rgba(255, 255, 255, 0.1);
            }
            
            .nfc-card::after {
                content: 'NFC';
                position: absolute;
                bottom: 10px;
                right: 15px;
                color: rgba(255, 255, 255, 0.7);
                font-weight: bold;
                font-size: 0.8rem;
            }
            
            @keyframes cardGlow {
                0% { box-shadow: 0 10px 25px rgba(106, 13, 173, 0.3); }
                100% { box-shadow: 0 10px 25px rgba(126, 63, 242, 0.6); }
            }
            
            /* Contador de intentos */
            .attempts-warning {
                background: rgba(255, 193, 7, 0.15) !important;
                border: 1px solid var(--warning) !important;
                border-radius: 10px;
                padding: 1rem;
                margin: 1rem 0;
                text-align: center;
                animation: fadeInUp 0.5s ease-out;
            }
        </style>
    """, unsafe_allow_html=True)

    # Mostrar términos y condiciones si se solicita
    if st.session_state.mostrar_terminos:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: var(--primary-purple); margin-bottom: 2rem;'>📋 Términos y Condiciones</h2>", unsafe_allow_html=True)
        
        terminos = cargar_terminos()
        st.markdown(f'<div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); max-height: 400px; overflow-y: auto; border: 2px solid var(--primary-purple);">{terminos}</div>', unsafe_allow_html=True)
        
        if st.button("🔙 Volver al Login", key="back_terminos"):
            st.session_state.mostrar_terminos = False
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # Contenedor principal del login
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Título principal con animación
    st.markdown("""
        <div style="text-align: center; margin-bottom: 3rem;">
            <h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem; 
                       background: linear-gradient(135deg, #ffffff, #f0f0f0);
                       -webkit-background-clip: text;
                       -webkit-text-fill-color: transparent;
                       background-clip: text;">
                🔐 ZERO Login
            </h1>
            <p style="color: var(--gray-light); font-size: 1.1rem;">
                Sistema de autenticación seguro
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón para ver términos y condiciones
    if st.button("📋 Ver Términos y Condiciones", key="ver_terminos"):
        st.session_state.mostrar_terminos = True
        st.rerun()
    
    # Protección contra fuerza bruta
    current_time = time.time()
    if st.session_state.login_attempts >= 3 and current_time - st.session_state.last_attempt_time < 300:
        remaining_time = int(300 - (current_time - st.session_state.last_attempt_time))
        st.markdown(f"""
            <div class="attempts-warning">
                <h3 style="color: var(--warning); margin-bottom: 1rem;">⏰ Demasiados intentos</h3>
                <p>Por seguridad, debes esperar {remaining_time} segundos antes de intentar nuevamente.</p>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # Selección de método de login
    if st.session_state.modo_login is None:
        st.markdown("<h3 style='text-align: center; color: var(--gray-light); margin-bottom: 2rem;'>Selecciona tu método de acceso:</h3>", unsafe_allow_html=True)
        
        # Contenedor para los botones de método
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            if st.button("👤 Usuario y Contraseña", key="btn_password", help="Acceso tradicional con usuario y contraseña"):
                st.session_state.modo_login = "password"
                st.rerun()
        
        with col2:
            if st.button("📡 Tarjeta NFC", key="btn_nfc", help="Acceso rápido con tarjeta NFC"):
                st.session_state.modo_login = "nfc"
                st.rerun()

    # --- LOGIN CON USUARIO Y CONTRASEÑA ---
    elif st.session_state.modo_login == "password":
        st.markdown("<h3 style='text-align: center; color: var(--gray-light); margin-bottom: 2rem;'>👤 Acceso con Usuario y Contraseña</h3>", unsafe_allow_html=True)
        
        # Campos de entrada
        usuario = st.text_input("👤 Usuario:", placeholder="Ingresa tu nombre de usuario", key="login_user")
        clave = st.text_input("🔒 Contraseña:", type="password", placeholder="Ingresa tu contraseña", key="login_pass")
        
        # Términos y condiciones para login tradicional
        acepta_terminos = st.checkbox("He leído y acepto los términos y condiciones", key="acepta_terminos_form")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔙 Volver", key="back_password"):
                st.session_state.modo_login = None
                st.session_state.login_attempts = 0
                st.rerun()
        
        with col2:
            if st.button("🚀 Iniciar Sesión", key="login_submit", type="primary"):
                if not all([usuario, clave]):
                    st.error("⚠️ Por favor, completa todos los campos")
                elif not acepta_terminos:
                    st.error("📋 Debes aceptar los términos y condiciones para continuar")
                else:
                    auth_result = JWTAuth.authenticate_user(usuario, clave)
                    if auth_result:
                        user_data = auth_result
                        token = JWTAuth.login_user(usuario, user_data["rol"])
                        st.session_state.login_attempts = 0
                        st.success(f"✅ ¡Bienvenido, {usuario}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        st.session_state.last_attempt_time = time.time()
                        st.error("❌ Usuario o contraseña incorrectos")

    # --- LOGIN CON NFC ---
    elif st.session_state.modo_login == "nfc":
        st.markdown("<h3 style='text-align: center; color: var(--gray-light); margin-bottom: 2rem;'>📡 Acceso con Tarjeta NFC</h3>", unsafe_allow_html=True)
        
        # Visualización de tarjeta NFC
        st.markdown('<div class="nfc-card"></div>', unsafe_allow_html=True)
        
        # Términos y condiciones para NFC
        acepta_terminos_nfc = st.checkbox("He leído y acepto los términos y condiciones", key="acepta_terminos_nfc")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔙 Volver", key="back_nfc"):
                st.session_state.modo_login = None
                st.rerun()
        
        with col2:
            if st.button("📡 Escanear Tarjeta NFC", key="scan_nfc", type="primary"):
                if not acepta_terminos_nfc:
                    st.error("📋 Debes aceptar los términos y condiciones para usar el login NFC")
                else:
                    # Barra de progreso para la lectura NFC
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i in range(100):
                        progress_bar.progress(i + 1)
                        status_text.text(f"🔍 Escaneando... {i+1}%")
                        time.sleep(0.02)
                    
                    uid = leer_uid_pn532()
                    progress_bar.empty()
                    status_text.empty()
                    
                    if uid:
                        auth_result = JWTAuth.authenticate_nfc(uid)
                        if auth_result:
                            usuario, user_data = auth_result
                            token = JWTAuth.login_user(usuario, user_data["rol"])
                            st.success(f"✅ ¡Bienvenido, {usuario}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Tarjeta NFC no registrada")
                    else:
                        st.error("⚠️ No se pudo leer la tarjeta NFC")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- CERRAR SESIÓN ---
def logout():
    JWTAuth.logout_user()
    st.success("🚪 Has cerrado sesión correctamente.")
    time.sleep(1)
    st.rerun()