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

    st.markdown("""
        <style>
            /* Estilos generales */
            .login-container {
                max-width: 500px;
                margin: 0 auto;
                padding: 2rem;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
            }
            
            .dark-mode .login-container {
                background: linear-gradient(145deg, #1a1a2e, #16213e);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            }
            
            .login-title {
                text-align: center;
                margin-bottom: 2rem;
                color: #2c3e50;
                font-size: 2rem;
                font-weight: 600;
            }
            
            .dark-mode .login-title {
                color: #f8f9fa;
            }
            
            .login-logo {
                font-size: 3rem;
                margin-bottom: 1rem;
                text-align: center;
                color: #6A0DAD;
            }
            
            /* Botones de opción */
            .login-option-btn {
                background-color: #6A0DAD;
                color: white;
                border: none;
                padding: 1rem;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .login-option-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
                background-color: #4B0082;
            }
            
            /* Formularios */
            .login-input {
                margin-bottom: 1.5rem;
            }
            
            .login-input label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
                color: #2c3e50;
            }
            
            .dark-mode .login-input label {
                color: #f8f9fa;
            }
            
            .login-input input {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #ced4da;
                border-radius: 8px;
                font-size: 1rem;
                transition: all 0.3s;
            }
            
            .login-input input:focus {
                border-color: #6A0DAD;
                box-shadow: 0 0 0 3px rgba(106, 13, 173, 0.25);
                outline: none;
            }
            
            /* Botones de acción */
            .login-action-btn {
                background-color: #6A0DAD;
                color: white;
                border: none;
                padding: 0.75rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s;
                width: 100%;
                margin-top: 1rem;
            }
            
            .login-action-btn:hover {
                background-color: #4B0082;
            }
            
            .login-back-btn {
                background-color: transparent;
                color: #6A0DAD;
                border: 1px solid #6A0DAD;
                padding: 0.75rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s;
                width: 100%;
                margin-top: 1rem;
            }
            
            .dark-mode .login-back-btn {
                color: #B57EDC;
                border-color: #B57EDC;
            }
            
            .login-back-btn:hover {
                background-color: rgba(106, 13, 173, 0.1);
            }
            
            /* Mensajes */
            .login-message {
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                font-weight: 500;
            }
            
            .login-error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .dark-mode .login-error {
                background-color: #3a1d23;
                color: #f8b3bb;
                border-color: #4d232a;
            }
            
            .login-success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .dark-mode .login-success {
                background-color: #1d3a24;
                color: #b3f8c3;
                border-color: #234d2d;
            }
            
            /* Spinner */
            .login-spinner {
                display: inline-block;
                width: 1.5rem;
                height: 1.5rem;
                border: 3px solid rgba(106, 13, 173, 0.3);
                border-radius: 50%;
                border-top-color: #6A0DAD;
                animation: spin 1s ease-in-out infinite;
                margin-right: 0.5rem;
                vertical-align: middle;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    """, unsafe_allow_html=True)

    if "modo_login" not in st.session_state:
        st.session_state.modo_login = None

    # Contenedor principal del login
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Logo y título
        st.markdown('<div class="login-logo">🔐</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">Acceso al Sistema</h1>', unsafe_allow_html=True)
        
        # --- OPCIÓN DE MÉTODO DE LOGIN ---
        if st.session_state.modo_login is None:
            col1, col2 = st.columns([1, 1], gap="large")
            with col1:
                if st.button("👤 Usuario y contraseña", key="btn_password", 
                            help="Accede con tus credenciales de usuario", 
                            use_container_width=True, 
                            type="primary"):
                    st.session_state.modo_login = "password"
                    st.rerun()
            with col2:
                if st.button("📶 Tarjeta NFC", key="btn_nfc", 
                           help="Accede con tu tarjeta NFC registrada", 
                           use_container_width=True, 
                           type="primary"):
                    st.session_state.modo_login = "nfc"
                    st.rerun()
        
        # --- LOGIN CON USUARIO Y CONTRASEÑA ---
        elif st.session_state.modo_login == "password":
            with st.form("login_form"):
                st.markdown('<div class="login-input">', unsafe_allow_html=True)
                usuario = st.text_input("Usuario", key="login_user")
                clave = st.text_input("Contraseña", type="password", key="login_pass")
                st.markdown('</div>', unsafe_allow_html=True)
                
                submit = st.form_submit_button("➡️ Iniciar sesión", type="primary", 
                                             use_container_width=True)
                
                if submit:
                    usuarios = cargar_usuarios()
                    if usuario in usuarios and usuarios[usuario]["clave"] == clave:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario"] = usuario
                        st.session_state["usuario_id"] = usuario
                        st.session_state["rol"] = usuarios[usuario]["rol"]
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
            
            if st.button("🔙 Volver", key="back_pass", use_container_width=True):
                st.session_state.modo_login = None
                st.rerun()
        
        # --- LOGIN CON TARJETA NFC ---
        elif st.session_state.modo_login == "nfc":
            if st.button("📡 Escanear tarjeta NFC", key="scan_nfc", 
                        use_container_width=True, 
                        type="primary"):
                with st.spinner("Esperando tarjeta NFC..."):
                    uid = leer_uid_pn532()
                
                if uid:
                    usuarios = cargar_usuarios()
                    usuario_encontrado = False
                    
                    for usuario, datos in usuarios.items():
                        if datos.get("nfc_uid") == uid:
                            st.success(f"✅ Bienvenido, {usuario}")
                            st.session_state["autenticado"] = True
                            st.session_state["usuario"] = usuario
                            st.session_state["rol"] = datos["rol"]
                            usuario_encontrado = True
                            st.rerun()
                    
                    if not usuario_encontrado:
                        st.error("❌ Tarjeta no registrada.")
                else:
                    st.error("⚠️ No se pudo leer la tarjeta.")
            
            if st.button("🔙 Volver", key="back_nfc", use_container_width=True):
                st.session_state.modo_login = None
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# --- CERRAR SESIÓN ---
def logout():
    st.session_state.clear()
    st.success("🚪 Has cerrado sesión correctamente.")
    st.rerun()