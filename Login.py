import streamlit as st
import json
import os
import time
import random
from lector_nfc import leer_uid_pn532

RUTA_USUARIOS = "usuarios.json"

# --- INICIALIZAR SESSION STATE ---
def inicializar_session_state():
    """Inicializa todas las variables de session state necesarias"""
    if "modo_login" not in st.session_state:
        st.session_state.modo_login = None
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "escanenado_nfc" not in st.session_state:
        st.session_state.escanenado_nfc = False
    if "intentos_fallidos" not in st.session_state:
        st.session_state.intentos_fallidos = 0
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None

# --- CARGAR USUARIOS ---
def cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):
        return {}
    try:
        with open(RUTA_USUARIOS, "r") as f:
            return json.load(f)
    except:
        return {}

# --- GUARDAR USUARIOS ---
def guardar_usuarios(usuarios):
    try:
        with open(RUTA_USUARIOS, "w") as f:
            json.dump(usuarios, f, indent=4)
        return True
    except:
        return False

# --- APLICAR ESTILOS CYBERPUNK GLITCH ---
def aplicar_estilos_alien():
    st.markdown("""
        <style>
            /* Fondo de matriz alienígena */
            .stApp {
                background: 
                    radial-gradient(circle at 20% 80%, #00ff88 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, #ff0080 0%, transparent 50%),
                    radial-gradient(circle at 40% 40%, #8000ff 0%, transparent 50%),
                    linear-gradient(45deg, #000000 0%, #1a0033 100%) !important;
                min-height: 100vh;
                animation: matrixBg 20s linear infinite;
                font-family: 'Courier New', monospace !important;
                overflow: hidden !important;
            }
            
            @keyframes matrixBg {
                0% { background-position: 0% 0%, 0% 0%, 0% 0%; }
                100% { background-position: 100% 100%, 100% 100%, 100% 100%; }
            }
            
            /* Ocultar elementos streamlit */
            .stApp > header, #MainMenu, .stApp > footer, 
            .stApp > div:first-child, .stApp > div[data-testid="stToolbar"],
            .stApp > div[data-testid="stDecoration"] {
                display: none !important;
            }
            
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            
            /* Contenedor principal glitch */
            .cyber-container {
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                position: relative;
                filter: drop-shadow(0 0 30px #00ff88);
            }
            
            /* Tarjeta de cristal alien */
            .alien-card {
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(15px);
                border: 1px solid #00ff88;
                border-image: linear-gradient(45deg, #00ff88, #ff0080, #8000ff) 1;
                padding: 3rem 2.5rem;
                position: relative;
                overflow: hidden;
                animation: hologramFloat 6s ease-in-out infinite;
            }
            
            @keyframes hologramFloat {
                0%, 100% { transform: translateY(0px) rotateX(0deg); }
                50% { transform: translateY(-10px) rotateX(1deg); }
            }
            
            /* Efecto glitch en bordes */
            .alien-card::before {
                content: '';
                position: absolute;
                top: -2px; left: -2px; right: -2px; bottom: -2px;
                background: linear-gradient(45deg, #00ff88, #ff0080, #8000ff, #00ff88);
                z-index: -1;
                animation: glitchBorder 3s infinite linear;
                filter: blur(5px);
            }
            
            @keyframes glitchBorder {
                0% { opacity: 0.8; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(1.02); }
                100% { opacity: 0.8; transform: scale(1); }
            }
            
            /* Header glitch */
            .glitch-header {
                text-align: center;
                margin-bottom: 2.5rem;
                position: relative;
            }
            
            .glitch-title {
                font-size: 3rem;
                font-weight: 900;
                color: #00ff88;
                text-shadow: 
                    0 0 10px #00ff88,
                    0 0 20px #00ff88,
                    0 0 30px #00ff88;
                animation: textGlitch 5s infinite;
                margin-bottom: 0.5rem;
                letter-spacing: 3px;
                text-transform: uppercase;
            }
            
            @keyframes textGlitch {
                0%, 100% { 
                    transform: translate(0);
                    text-shadow: 
                        0 0 10px #00ff88,
                        0 0 20px #00ff88,
                        0 0 30px #00ff88;
                }
                25% { 
                    transform: translate(-2px, 1px);
                    text-shadow: 
                        0 0 10px #ff0080,
                        0 0 20px #ff0080,
                        2px 0 30px #8000ff;
                }
                75% { 
                    transform: translate(1px, -1px);
                    text-shadow: 
                        0 0 10px #8000ff,
                        0 0 20px #8000ff,
                        -2px 0 30px #00ff88;
                }
            }
            
            .glitch-subtitle {
                color: #ff0080;
                font-size: 1rem;
                text-transform: uppercase;
                letter-spacing: 4px;
                animation: subtitleFlicker 3s infinite;
            }
            
            @keyframes subtitleFlicker {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
            
            /* Selector de método cyber */
            .cyber-selector {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .stButton > button {
                background: rgba(0, 255, 136, 0.1) !important;
                border: 2px solid #00ff88 !important;
                border-radius: 0 !important;
                padding: 1.5rem 1rem !important;
                color: #00ff88 !important;
                font-family: 'Courier New', monospace !important;
                font-weight: bold !important;
                text-transform: uppercase !important;
                letter-spacing: 2px !important;
                transition: all 0.3s !important;
                position: relative !important;
                overflow: hidden !important;
            }
            
            .stButton > button:hover {
                background: rgba(0, 255, 136, 0.3) !important;
                box-shadow: 
                    0 0 20px #00ff88,
                    inset 0 0 20px rgba(0, 255, 136, 0.2) !important;
                transform: translateY(-3px) !important;
            }
            
            .stButton > button::before {
                content: '';
                position: absolute;
                top: 0; left: -100%;
                width: 100%; height: 100%;
                background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.4), transparent);
                transition: left 0.5s;
            }
            
            .stButton > button:hover::before {
                left: 100%;
            }
            
            /* Campos de formulario glitch */
            .stTextInput > div > div {
                background: rgba(0, 0, 0, 0.8) !important;
                border: 2px solid #ff0080 !important;
                border-radius: 0 !important;
                transition: all 0.3s !important;
            }
            
            .stTextInput > div > div:focus-within {
                border-color: #8000ff !important;
                box-shadow: 0 0 15px #8000ff !important;
            }
            
            .stTextInput > div > div > input {
                color: #00ff88 !important;
                font-family: 'Courier New', monospace !important;
                font-size: 1.1rem !important;
                padding: 1rem !important;
                background: transparent !important;
                border: none !important;
            }
            
            .stTextInput label {
                color: #ff0080 !important;
                font-family: 'Courier New', monospace !important;
                font-weight: bold !important;
                text-transform: uppercase !important;
                letter-spacing: 2px !important;
            }
            
            /* Botón principal cyber */
            .stButton > button[type="primary"] {
                background: linear-gradient(45deg, #ff0080, #8000ff) !important;
                border: none !important;
                border-radius: 0 !important;
                padding: 1.2rem !important;
                color: white !important;
                font-family: 'Courier New', monospace !important;
                font-weight: bold !important;
                text-transform: uppercase !important;
                letter-spacing: 3px !important;
                transition: all 0.3s !important;
                position: relative !important;
            }
            
            .stButton > button[type="primary"]:hover {
                transform: skewX(-5deg) !important;
                box-shadow: 
                    0 0 30px #ff0080,
                    0 0 60px #8000ff !important;
            }
            
            /* Scanner NFC alien */
            .alien-scanner {
                border: 3px dashed #8000ff;
                padding: 2.5rem 2rem;
                text-align: center;
                margin: 2rem 0;
                background: rgba(128, 0, 255, 0.1);
                animation: scannerPulse 4s infinite;
                position: relative;
            }
            
            @keyframes scannerPulse {
                0%, 100% { 
                    border-color: #8000ff;
                    box-shadow: 0 0 20px #8000ff;
                }
                50% { 
                    border-color: #00ff88;
                    box-shadow: 0 0 40px #00ff88;
                }
            }
            
            .alien-icon {
                font-size: 4rem;
                animation: alienSpin 8s infinite linear;
                filter: drop-shadow(0 0 10px #ff0080);
            }
            
            @keyframes alienSpin {
                0% { transform: rotate(0deg) scale(1); }
                50% { transform: rotate(180deg) scale(1.2); }
                100% { transform: rotate(360deg) scale(1); }
            }
            
            /* Controles NFC */
            .alien-controls {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
                margin: 1.5rem 0;
            }
            
            /* Efectos de partículas matrix */
            .matrix-rain {
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                pointer-events: none;
                z-index: -1;
            }
            
            .code-char {
                position: absolute;
                color: #00ff88;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                animation: matrixFall linear infinite;
            }
            
            @keyframes matrixFall {
                0% { 
                    transform: translateY(-100px);
                    opacity: 0;
                }
                5% { opacity: 1; }
                95% { opacity: 1; }
                100% { 
                    transform: translateY(100vh);
                    opacity: 0;
                }
            }
            
            /* Responsive design glitch */
            @media (max-width: 768px) {
                .cyber-container {
                    max-width: 95%;
                }
                
                .alien-card {
                    padding: 2rem 1.5rem;
                }
                
                .glitch-title {
                    font-size: 2.2rem;
                }
                
                .cyber-selector {
                    grid-template-columns: 1fr;
                }
                
                .alien-controls {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        
        <!-- Efecto lluvia de matriz -->
        <div class="matrix-rain" id="matrixRain"></div>
        
        <script>
            function createMatrixRain() {
                const container = document.getElementById('matrixRain');
                const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
                const charCount = Math.floor(window.innerWidth / 20);
                
                for (let i = 0; i < charCount; i++) {
                    const char = document.createElement('div');
                    char.className = 'code-char';
                    char.textContent = chars[Math.floor(Math.random() * chars.length)];
                    
                    const left = Math.random() * 100;
                    const delay = Math.random() * 10;
                    const duration = Math.random() * 5 + 3;
                    
                    char.style.left = left + '%';
                    char.style.animationDelay = delay + 's';
                    char.style.animationDuration = duration + 's';
                    char.style.opacity = Math.random() * 0.5 + 0.1;
                    
                    container.appendChild(char);
                }
            }
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', createMatrixRain);
            } else {
                createMatrixRain();
            }
        </script>
    """, unsafe_allow_html=True)

# --- VERIFICAR LOGIN CYBERPUNK ---
def verificar_login():
    # INICIALIZAR PRIMERO - ESTO ES CRÍTICO
    inicializar_session_state()
    
    # Aplicar estilos cyberpunk
    aplicar_estilos_alien()
    
    # Contenedor principal
    st.markdown('<div class="cyber-container">', unsafe_allow_html=True)
    st.markdown('<div class="alien-card">', unsafe_allow_html=True)
    
    # Header glitch
    st.markdown('<div class="glitch-header">', unsafe_allow_html=True)
    st.markdown('<h1 class="glitch-title">SYSTEM LOGIN</h1>', unsafe_allow_html=True)
    st.markdown('<div class="glitch-subtitle">ACCESS TERMINAL v7.7.7</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Estado del sistema
    usuarios = cargar_usuarios()
    st.markdown(f'''
        <div style="
            border: 1px solid #00ff88;
            padding: 1rem;
            margin: 1rem 0;
            background: rgba(0, 255, 136, 0.05);
            text-align: center;
            font-family: 'Courier New', monospace;
        ">
            <div style="color: #00ff88; font-weight: bold;">SYSTEM STATUS: <span style="color: #ff0080;">ONLINE</span></div>
            <div style="color: #8000ff; font-size: 0.8rem; margin-top: 0.3rem;">
                USERS: {len(usuarios)} | ENCRYPTION: ACTIVE | THREAT LEVEL: LOW
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # --- SELECTOR DE MÉTODO ---
    # AHORA st.session_state.modo_login está inicializado
    if st.session_state.modo_login is None:
        st.markdown('<div class="cyber-selector">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("""
                🔐
                DIGITAL
                ACCESS
            """, key="btn_password", use_container_width=True):
                st.session_state.modo_login = "password"
                st.rerun()
        
        with col2:
            if st.button("""
                💎
                BIO
                SCAN
            """, key="btn_nfc", use_container_width=True):
                st.session_state.modo_login = "nfc"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Mensaje de advertencia
        st.warning("""
        **⚠️ WARNING: UNAUTHORIZED ACCESS DETECTED**  
        *System will initiate countermeasures*  
        *Terminate connection immediately*
        """)

    # --- LOGIN CON CREDENCIALES ---
    elif st.session_state.modo_login == "password":
        with st.form("login_form"):
            usuario = st.text_input(
                "👤 USER IDENTITY", 
                placeholder="ENTER USER CODE",
                key="login_user"
            )
            
            clave = st.text_input(
                "🔑 ACCESS KEY", 
                type="password", 
                placeholder="••••••••••",
                key="login_pass"
            )
            
            # Opciones de seguridad
            col1, col2 = st.columns(2)
            with col1:
                st.checkbox("💾 SAVE SESSION", value=False, key="remember_session")
            with col2:
                st.markdown("""
                    <div style="text-align: right; padding-top: 0.5rem;">
                        <a href="#" style="color: #ff0080; text-decoration: none; font-family: 'Courier New', monospace;">
                            🔓 RECOVERY MODE
                        </a>
                    </div>
                """, unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 INITIATE LOGIN", use_container_width=True, type="primary"):
                if not usuario or not clave:
                    st.error("❌ ERROR: MISSING CREDENTIALS")
                else:
                    if usuario in usuarios and usuarios[usuario]["clave"] == clave:
                        st.session_state.update({
                            "autenticado": True,
                            "usuario": usuario,
                            "rol": usuarios[usuario]["rol"],
                            "intentos_fallidos": 0
                        })
                        st.success("✅ ACCESS GRANTED")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.intentos_fallidos += 1
                        st.error(f"🚫 ACCESS DENIED: INVALID CREDENTIALS (Attempt {st.session_state.intentos_fallidos}/3)")
        
        if st.button("↶ BACK TO TERMINAL", key="back_pass", use_container_width=True):
            st.session_state.modo_login = None
            st.rerun()

    # --- LOGIN CON NFC ---
    elif st.session_state.modo_login == "nfc":
        # Scanner alien
        st.markdown('<div class="alien-scanner">', unsafe_allow_html=True)
        st.markdown('<div class="alien-icon">👽</div>', unsafe_allow_html=True)
        st.markdown('<h3 style="color: #00ff88; margin: 0; font-family: Courier New;">BIO-SCAN ACTIVE</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: #ff0080; font-family: Courier New; margin: 0.5rem 0 0 0;">AWAITING BIOMETRIC INPUT</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Controles
        st.markdown('<div class="alien-controls">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ START SCAN", key="scan_nfc", use_container_width=True):
                st.session_state.escanenado_nfc = True
                st.rerun()
        
        with col2:
            if st.button("⏹️ ABORT", key="stop_nfc", use_container_width=True):
                st.session_state.escanenado_nfc = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Proceso de escaneo
        if st.session_state.get("escanenado_nfc", False):
            with st.spinner("🔍 SCANNING BIOMETRIC SIGNATURE..."):
                time.sleep(2)
                try:
                    uid = leer_uid_pn532()
                except:
                    uid = None
                
                if uid:
                    usuario_encontrado = None
                    for usuario, datos in usuarios.items():
                        if datos.get("nfc_uid") == uid:
                            usuario_encontrado = usuario
                            break
                    
                    if usuario_encontrado:
                        st.success(f"✅ IDENTITY CONFIRMED: {usuario_encontrado}")
                        st.session_state.update({
                            "autenticado": True,
                            "usuario": usuario_encontrado,
                            "rol": usuarios[usuario_encontrado]["rol"]
                        })
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("🚫 UNREGISTERED BIOMETRIC SIGNATURE")
                else:
                    st.warning("⚠️ NO SIGNAL DETECTED")
        
        if st.button("↶ BACK TO TERMINAL", key="back_nfc", use_container_width=True):
            st.session_state.modo_login = None
            st.session_state.escanenado_nfc = False
            st.rerun()
    
    # Footer cyber
    st.markdown('''
        <div style="
            border-top: 1px solid #8000ff;
            padding-top: 1.5rem;
            margin-top: 2rem;
            text-align: center;
            color: #8000ff;
            font-family: 'Courier New', monospace;
        ">
            <div style="font-weight: bold; letter-spacing: 2px;">CYBER SYSTEMS CORP</div>
            <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 0.3rem;">
                PROPRIETARY TECHNOLOGY © 2077
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Cierre alien-card
    st.markdown('</div>', unsafe_allow_html=True)  # Cierre cyber-container
    
    if not st.session_state.get("autenticado", False):
        st.stop()

# --- CERRAR SESIÓN GLITCH ---
def logout():
    usuario = st.session_state.get("usuario", "USER")
    st.session_state.clear()
    st.error(f"🚫 SESSION TERMINATED: {usuario}")
    time.sleep(1)
    st.rerun()

# --- REGISTRO ALIEN ---
def registrar_usuario(usuario, clave, rol, uid_nfc=None):
    usuarios = cargar_usuarios()
    if usuario in usuarios:
        st.warning("⚠️ USER ALREADY EXISTS")
        return False
    
    usuarios[usuario] = {
        "clave": clave,
        "rol": rol,
        "nfc_uid": uid_nfc,
        "fecha_registro": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if guardar_usuarios(usuarios):
        st.success(f"✅ USER {usuario} REGISTERED")
        return True
    return False