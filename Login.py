import streamlit as st
import json
import os
from lector_nfc import leer_uid_pn532

RUTA_USUARIOS = "usuarios.json"

# --- CARGAR USUARIOS ---
def cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):
        return {}
    with open(RUTA_USUARIOS, "r") as f:
        return json.load(f)

# --- GUARDAR USUARIOS ---
def guardar_usuarios(usuarios):
    with open(RUTA_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=4)

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
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Diseño premium centrado en la parte superior
    st.markdown("""
        <style>
            /* Reset completo para centrado perfecto */
            .stApp {
                background: radial-gradient(ellipse at top center, #0f0c29 0%, #302b63 50%, #24243e 100%) !important;
                min-height: 100vh;
                display: flex !important;
                align-items: flex-start !important;
                justify-content: center !important;
                padding-top: 5vh !important;
                overflow: auto !important;
            }
            
            /* Ocultar TODOS los elementos nativos de Streamlit */
            .stApp > header, 
            #MainMenu, 
            .stApp > footer,
            .stApp > div:first-child,
            .stApp > div[data-testid="stToolbar"],
            .stApp > div[data-testid="stDecoration"] {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
                margin: 0px !important;
                padding: 0px !important;
            }
            
            /* Container principal de Streamlit */
            .main .block-container {
                padding: 0px !important;
                max-width: 100% !important;
                margin-top: 0px !important;
            }
            
            /* Contenedor cósmico centrado en la parte superior */
            .cosmic-main {
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                min-height: 90vh;
                background: 
                    radial-gradient(circle at 50% 10%, rgba(120, 119, 198, 0.4) 0%, transparent 60%),
                    radial-gradient(circle at 90% 30%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                    radial-gradient(circle at 10% 30%, rgba(120, 219, 255, 0.3) 0%, transparent 50%);
                animation: cosmicDrift 25s ease-in-out infinite;
            }
            
            @keyframes cosmicDrift {
                0%, 100% { 
                    background-position: 0% 0%, 0% 0%, 0% 0%;
                }
                25% { 
                    background-position: -2% -1%, 1% 2%, -1% 1%;
                }
                50% { 
                    background-position: 1% 2%, -1% -2%, 2% -1%;
                }
                75% { 
                    background-position: -1% 1%, 2% -1%, -2% 2%;
                }
            }
            
            /* Tarjeta holográfica centrada arriba */
            .holographic-card {
                background: rgba(15, 12, 41, 0.98);
                backdrop-filter: blur(25px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 28px;
                padding: 4rem 3rem;
                width: 100%;
                max-width: 520px;
                box-shadow: 
                    0 20px 100px rgba(138, 43, 226, 0.4),
                    0 10px 60px rgba(75, 0, 130, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2),
                    0 0 0 1px rgba(255, 255, 255, 0.05);
                position: relative;
                margin: 2rem;
                animation: cardFloat 2s ease-out;
                transform-origin: top center;
            }
            
            @keyframes cardFloat {
                0% { 
                    opacity: 0;
                    transform: translateY(-50px) scale(0.9);
                }
                100% { 
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }
            
            /* Efecto de borde neón mejorado */
            .holographic-card::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #8A2BE2, #00D4FF, #FF6B6B, #8A2BE2);
                background-size: 400% 400%;
                border-radius: 30px;
                z-index: -1;
                animation: neonBorder 4s ease infinite;
                filter: blur(10px);
                opacity: 0.7;
            }
            
            @keyframes neonBorder {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            
            .holographic-card::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            }
            
            /* Logo superior centrado */
            .quantum-header {
                text-align: center;
                margin-bottom: 3rem;
                position: relative;
            }
            
            .logo-orbital {
                font-size: 6rem;
                background: linear-gradient(135deg, #8A2BE2 0%, #00D4FF 50%, #FF6B6B 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: orbitalSpin 10s linear infinite;
                filter: drop-shadow(0 0 30px rgba(138, 43, 226, 0.6));
                display: inline-block;
                margin-bottom: 1rem;
            }
            
            @keyframes orbitalSpin {
                0% { transform: rotate(0deg) scale(1); }
                50% { transform: rotate(180deg) scale(1.05); }
                100% { transform: rotate(360deg) scale(1); }
            }
            
            /* Título principal */
            .quantum-title {
                text-align: center;
                font-size: 3rem;
                font-weight: 900;
                background: linear-gradient(135deg, #8A2BE2, #00D4FF, #FF6B6B);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
                letter-spacing: 2px;
                animation: titlePulse 3s ease-in-out infinite;
            }
            
            @keyframes titlePulse {
                0%, 100% { 
                    text-shadow: 0 0 20px rgba(138, 43, 226, 0.5),
                               0 0 40px rgba(0, 212, 255, 0.3);
                }
                50% { 
                    text-shadow: 0 0 30px rgba(138, 43, 226, 0.8),
                               0 0 60px rgba(0, 212, 255, 0.5),
                               0 0 80px rgba(255, 107, 107, 0.3);
                }
            }
            
            .quantum-subtitle {
                text-align: center;
                color: rgba(255, 255, 255, 0.8);
                font-size: 1.2rem;
                margin-bottom: 3rem;
                font-weight: 300;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            }
            
            /* Grid de métodos de login centrado */
            .method-grid-container {
                display: flex;
                justify-content: center;
                margin-bottom: 3rem;
            }
            
            .method-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.5rem;
                width: 100%;
                max-width: 400px;
            }
            
            /* Botones de Streamlit personalizados */
            .stButton > button {
                width: 100% !important;
                height: 100px !important;
                background: linear-gradient(135deg, rgba(138, 43, 226, 0.1), rgba(0, 212, 255, 0.05)) !important;
                border: 2px solid rgba(138, 43, 226, 0.4) !important;
                border-radius: 20px !important;
                color: white !important;
                font-weight: 700 !important;
                font-size: 1.1rem !important;
                transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 8px !important;
                position: relative !important;
                overflow: hidden !important;
            }
            
            .stButton > button:hover {
                border-color: #8A2BE2 !important;
                transform: translateY(-5px) !important;
                box-shadow: 0 15px 40px rgba(138, 43, 226, 0.4) !important;
                background: linear-gradient(135deg, rgba(138, 43, 226, 0.2), rgba(0, 212, 255, 0.1)) !important;
            }
            
            .stButton > button:active {
                transform: translateY(-2px) !important;
            }
            
            /* Campos de formulario centrados */
            .form-container {
                max-width: 400px;
                margin: 0 auto;
            }
            
            .stTextInput > div > div {
                background: rgba(255, 255, 255, 0.05) !important;
                border: 2px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 15px !important;
                transition: all 0.3s ease !important;
            }
            
            .stTextInput > div > div:hover {
                border-color: rgba(138, 43, 226, 0.5) !important;
            }
            
            .stTextInput > div > div > input {
                color: white !important;
                font-size: 1.1rem !important;
                padding: 1.3rem 1.5rem !important;
                background: transparent !important;
                border: none !important;
            }
            
            .stTextInput > div > div > input:focus {
                outline: none !important;
                box-shadow: none !important;
            }
            
            .stTextInput > div > div > input::placeholder {
                color: rgba(255, 255, 255, 0.4) !important;
            }
            
            .stTextInput label {
                color: rgba(255, 255, 255, 0.9) !important;
                font-weight: 600 !important;
                font-size: 1rem !important;
                text-transform: uppercase !important;
                letter-spacing: 1.5px !important;
                margin-bottom: 1rem !important;
            }
            
            /* Botón de login principal */
            .stButton > button[type="primary"] {
                background: linear-gradient(135deg, #8A2BE2, #00D4FF) !important;
                border: none !important;
                border-radius: 15px !important;
                padding: 1.3rem !important;
                font-size: 1.2rem !important;
                font-weight: 700 !important;
                height: auto !important;
                margin-top: 2rem !important;
                position: relative !important;
                overflow: hidden !important;
            }
            
            .stButton > button[type="primary"]::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s;
            }
            
            .stButton > button[type="primary"]:hover::before {
                left: 100%;
            }
            
            /* Scanner NFC centrado */
            .nfc-hologram-center {
                text-align: center;
                padding: 3.5rem 2.5rem;
                border: 2px dashed rgba(138, 43, 226, 0.6);
                border-radius: 25px;
                margin: 2rem auto;
                background: rgba(138, 43, 226, 0.08);
                backdrop-filter: blur(10px);
                max-width: 400px;
                animation: hologramGlow 3s ease-in-out infinite;
                position: relative;
            }
            
            @keyframes hologramGlow {
                0%, 100% { 
                    box-shadow: 0 0 20px rgba(138, 43, 226, 0.3);
                    border-color: rgba(138, 43, 226, 0.6);
                }
                50% { 
                    box-shadow: 0 0 40px rgba(0, 212, 255, 0.4);
                    border-color: rgba(0, 212, 255, 0.8);
                }
            }
            
            .nfc-icon-orbital {
                font-size: 5rem;
                animation: nfcOrbit 5s ease-in-out infinite;
                display: block;
                margin-bottom: 1.5rem;
                filter: drop-shadow(0 0 20px rgba(138, 43, 226, 0.5));
            }
            
            @keyframes nfcOrbit {
                0%, 100% { transform: rotate(0deg) scale(1); }
                25% { transform: rotate(5deg) scale(1.1); }
                75% { transform: rotate(-5deg) scale(1.1); }
            }
            
            /* Controles NFC centrados */
            .nfc-controls {
                display: flex;
                gap: 1rem;
                justify-content: center;
                margin: 2rem auto;
                max-width: 400px;
            }
            
            /* Footer centrado */
            .cosmic-footer {
                text-align: center;
                margin-top: 4rem;
                padding-top: 2.5rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.6);
                font-size: 0.9rem;
                letter-spacing: 1px;
            }
            
            /* Partículas de fondo */
            .particles-container {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: -1;
            }
            
            .particle {
                position: absolute;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 50%;
                animation: particleFloat 8s infinite linear;
            }
            
            @keyframes particleFloat {
                0% { 
                    transform: translateY(100vh) rotate(0deg) scale(0);
                    opacity: 0;
                }
                10% { 
                    opacity: 1;
                    transform: translateY(90vh) rotate(0deg) scale(1);
                }
                90% { 
                    opacity: 1;
                    transform: translateY(10vh) rotate(360deg) scale(1);
                }
                100% { 
                    opacity: 0;
                    transform: translateY(0vh) rotate(720deg) scale(0);
                }
            }
            
            /* Responsive design mejorado */
            @media (max-width: 768px) {
                .stApp {
                    padding-top: 2vh !important;
                    align-items: flex-start !important;
                }
                
                .holographic-card {
                    margin: 1rem;
                    padding: 3rem 2rem;
                    border-radius: 20px;
                }
                
                .quantum-title {
                    font-size: 2.2rem;
                }
                
                .logo-orbital {
                    font-size: 4.5rem;
                }
                
                .method-grid {
                    grid-template-columns: 1fr;
                    gap: 1rem;
                }
                
                .stButton > button {
                    height: 85px !important;
                }
            }
            
            @media (max-width: 480px) {
                .holographic-card {
                    padding: 2.5rem 1.5rem;
                    margin: 0.5rem;
                }
                
                .quantum-title {
                    font-size: 1.8rem;
                }
                
                .nfc-hologram-center {
                    padding: 2.5rem 1.5rem;
                }
            }
        </style>
        
        <!-- Partículas de fondo -->
        <div class="particles-container" id="particles"></div>
        
        <script>
            function createParticles() {
                const container = document.getElementById('particles');
                const particleCount = 25;
                
                for (let i = 0; i < particleCount; i++) {
                    const particle = document.createElement('div');
                    particle.className = 'particle';
                    
                    const size = Math.random() * 4 + 1;
                    const left = Math.random() * 100;
                    const animationDuration = Math.random() * 8 + 6;
                    const animationDelay = Math.random() * 5;
                    
                    particle.style.width = size + 'px';
                    particle.style.height = size + 'px';
                    particle.style.left = left + '%';
                    particle.style.animationDuration = animationDuration + 's';
                    particle.style.animationDelay = animationDelay + 's';
                    particle.style.background = `rgba(${Math.random() * 100 + 155}, ${Math.random() * 100 + 155}, 255, ${Math.random() * 0.3 + 0.1})`;
                    
                    container.appendChild(particle);
                }
            }
            
            document.addEventListener('DOMContentLoaded', createParticles);
        </script>
    """, unsafe_allow_html=True)

    if "modo_login" not in st.session_state:
        st.session_state.modo_login = None

    # Contenedor principal centrado en la parte superior
    st.markdown('<div class="cosmic-main">', unsafe_allow_html=True)
    st.markdown('<div class="holographic-card">', unsafe_allow_html=True)
    
    # Header centrado
    st.markdown('<div class="quantum-header">', unsafe_allow_html=True)
    st.markdown('<div class="logo-orbital">🌐</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="quantum-title">QUANTUM ACCESS</h1>', unsafe_allow_html=True)
    st.markdown('<p class="quantum-subtitle">Portal de Autenticación Segura</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- SELECTOR DE MÉTODO DE LOGIN ---
    if st.session_state.modo_login is None:
        st.markdown('<div class="method-grid-container">', unsafe_allow_html=True)
        st.markdown('<div class="method-grid">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("""
                👤
                Credenciales
                Digitales
            """, key="btn_password", use_container_width=True):
                st.session_state.modo_login = "password"
                st.rerun()
        
        with col2:
            if st.button("""
                📡
                NFC
                Biométrico
            """, key="btn_nfc", use_container_width=True):
                st.session_state.modo_login = "nfc"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Info de seguridad centrada
        st.markdown("""
            <div style='
                background: linear-gradient(135deg, rgba(138, 43, 226, 0.1), rgba(0, 212, 255, 0.05));
                border: 1px solid rgba(138, 43, 226, 0.3);
                border-radius: 15px;
                padding: 2rem;
                text-align: center;
                margin: 2rem auto;
                max-width: 400px;
                backdrop-filter: blur(10px);
            '>
                <div style='font-size: 2.5rem; margin-bottom: 1rem;'>🛡️</div>
                <div style='color: rgba(255, 255, 255, 0.95); font-weight: 700; font-size: 1.1rem;'>
                    Seguridad de Nivel Cuántico
                </div>
                <div style='color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-top: 0.8rem; line-height: 1.5;'>
                    Autenticación avanzada con encriptación de última generación
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # --- LOGIN CON CREDENCIALES ---
    elif st.session_state.modo_login == "password":
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input(
                "🔐 IDENTIDAD DIGITAL", 
                key="login_user", 
                placeholder="Ingresa tu usuario único"
            )
            
            clave = st.text_input(
                "🗝️ CLAVE DE ACCESO", 
                type="password", 
                key="login_pass", 
                placeholder="••••••••••"
            )
            
            # Opciones centradas
            col_opciones = st.columns([1, 1])
            with col_opciones[0]:
                st.checkbox("💾 Recordar identidad", value=False, key="remember")
            with col_opciones[1]:
                st.markdown("""
                    <div style='text-align: right; padding-top: 0.8rem;'>
                        <a href='#' style='color: #00D4FF; text-decoration: none; font-size: 0.9rem; font-weight: 600;'>
                            🔓 ¿Acceso perdido?
                        </a>
                    </div>
                """, unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 INICIAR SESIÓN SEGURA", type="primary", use_container_width=True):
                if not usuario or not clave:
                    st.error("❌ Se requieren ambos campos de acceso")
                else:
                    usuarios = cargar_usuarios()
                    if usuario in usuarios and usuarios[usuario]["clave"] == clave:
                        st.session_state.update({
                            "autenticado": True,
                            "usuario": usuario,
                            "usuario_id": usuario,
                            "rol": usuarios[usuario]["rol"]
                        })
                        st.success(f"✅ ¡Acceso concedido, {usuario}!")
                        st.rerun()
                    else:
                        st.error("❌ Identidad o clave inválida")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("↶ Volver al selector", key="back_pass", use_container_width=True):
            st.session_state.modo_login = None
            st.rerun()
    
    # --- LOGIN CON NFC ---
    elif st.session_state.modo_login == "nfc":
        # Scanner NFC centrado
        st.markdown('<div class="nfc-hologram-center">', unsafe_allow_html=True)
        st.markdown('<span class="nfc-icon-orbital">💎</span>', unsafe_allow_html=True)
        st.markdown('<h3 style="color: white; margin-bottom: 0.5rem; font-size: 1.4rem;">ESCÁNER NFC ACTIVADO</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: rgba(255, 255, 255, 0.8); font-size: 1rem;">Acerca tu dispositivo de identificación al lector</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Controles centrados
        st.markdown('<div class="nfc-controls">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 INICIAR ESCANEO", key="scan_nfc", use_container_width=True):
                st.session_state.escanenado_nfc = True
                st.rerun()
        
        with col2:
            if st.button("⏹️ DETENER", key="cancel_nfc", use_container_width=True):
                st.session_state.escanenado_nfc = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Estado del escaneo
        if st.session_state.get("escanenado_nfc", False):
            with st.spinner("🔍 Escaneando campo biométrico..."):
                uid = leer_uid_pn532()
                
                if uid:
                    usuarios = cargar_usuarios()
                    usuario_encontrado = False
                    for usuario, datos in usuarios.items():
                        if datos.get("nfc_uid") == uid:
                            st.success(f"✅ Identidad verificada: {usuario}")
                            st.session_state.update({
                                "autenticado": True,
                                "usuario": usuario,
                                "rol": datos["rol"]
                            })
                            usuario_encontrado = True
                            st.rerun()
                    
                    if not usuario_encontrado:
                        st.error("❌ Dispositivo no registrado en el sistema")
                else:
                    st.warning("⚠️ No se detectó señal biométrica. Intenta nuevamente")
        
        if st.button("↶ Volver al selector", key="back_nfc", use_container_width=True):
            st.session_state.modo_login = None
            st.session_state.escanenado_nfc = False
            st.rerun()
    
    # Footer centrado
    st.markdown('<div class="cosmic-footer">', unsafe_allow_html=True)
    st.markdown('''
        <div style="font-weight: 700; letter-spacing: 2px; margin-bottom: 0.5rem;">QUANTUM ACCESS SYSTEM v5.0</div>
        <div style="font-size: 0.8rem; opacity: 0.8;">
            Tecnología de autenticación cuántica © 2024
        </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Cierre holographic-card
    st.markdown('</div>', unsafe_allow_html=True)  # Cierre cosmic-main
    
    if not st.session_state.get("autenticado", False):
        st.stop()

# --- CERRAR SESIÓN ---
def logout():
    st.session_state.clear()
    st.success("🌌 Sesión cerrada - Sistema seguro")
    st.rerun()