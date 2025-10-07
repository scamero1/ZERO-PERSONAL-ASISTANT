from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
import os
import json
import uuid
import hashlib
import logging
from werkzeug.utils import secure_filename
from base64 import b64encode
import requests
from datetime import datetime
from dotenv import load_dotenv

# Importar módulos existentes
from database import ZeroDatabase
from file_processor import FileProcessor
from auth import verificar_login, logout, registrar_usuario

# Cargar variables de entorno
load_dotenv()

# Configurar logging a archivo
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), 'error.log'),
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Inicializar aplicación Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "zero_secret_key")
app.config['UPLOAD_FOLDER'] = 'user_uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Endurecer cookies de sesión (opcional pero recomendado)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Inicializar base de datos
db = ZeroDatabase()

# Configuración de Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("GROQ_API_KEY no encontrada en las variables de entorno")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

BASE_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}
STREAM_HEADERS = {
    **BASE_HEADERS,
    "Accept": "text/event-stream",
}

# Rutas para la aplicación
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session.get('usuario')

    # Redirigir hacia la app pública (subdominio)
    public_app_url = os.getenv("PUBLIC_APP_URL")
    if public_app_url:
        target = f"{public_app_url.rstrip('/')}/?usuario={usuario}"
    else:
        scheme = 'https' if request.is_secure else 'http'
        host = request.host.split(':')[0]
        target = f"{scheme}://{host}:8501/?usuario={usuario}"

    return redirect(target)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'templates', 'newlogin'),
        'logozero.jpg',
        mimetype='image/jpeg'
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = (request.form.get('usuario') or '').strip()
        clave = (request.form.get('clave') or '').strip()

        if not usuario or not clave:
            flash('Completa usuario y contraseña', 'error')
            return render_template('newlogin/index.html')

        # Admin/admin directo
        if usuario == 'admin' and clave == 'admin':
            user_info = db.get_user_by_username('admin')
            if not user_info:
                pwd_hash = hashlib.sha256('admin'.encode('utf-8')).hexdigest()
                db.create_user('admin', pwd_hash, rol='admin')
                user_info = db.get_user_by_username('admin')
            session['usuario'] = 'admin'
            session['user_id'] = user_info.get('id') if user_info else None
            session['rol'] = 'admin'
            if session.get('user_id'):
                db.update_last_login(session['user_id'])
            return redirect(url_for('index'))

        # Verificación normal
        if verificar_login(usuario, clave):
            # Leer rol desde usuarios.json
            rol_json = 'usuario'
            try:
                with open(os.path.join(app.root_path, 'usuarios.json'), 'r', encoding='utf-8') as f:
                    usuarios = json.load(f)
                if isinstance(usuarios, dict):
                    dato = usuarios.get(usuario)
                    if isinstance(dato, dict):
                        rol_json = dato.get('rol', 'usuario')
                elif isinstance(usuarios, list):
                    for u in usuarios:
                        name = u.get('usuario') or u.get('username')
                        if name == usuario:
                            rol_json = u.get('rol', 'usuario')
                            break
            except Exception:
                pass

            user_info = db.get_user_by_username(usuario)
            if not user_info:
                pwd_hash = hashlib.sha256(clave.encode('utf-8')).hexdigest()
                db.create_user(usuario, pwd_hash, rol=rol_json)
                user_info = db.get_user_by_username(usuario)

            session['usuario'] = usuario
            session['user_id'] = user_info.get('id') if user_info else None
            session['rol'] = user_info.get('rol', rol_json) if user_info else rol_json
            if session.get('user_id'):
                db.update_last_login(session['user_id'])
            return redirect(url_for('index'))

        flash('Credenciales inválidas', 'error')
        return render_template('newlogin/index.html')

    # GET: muestra el nuevo login
    return render_template('newlogin/index.html')

# --- NUEVO: Registro de usuarios desde newlogin ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # Reutiliza la misma página (conmutada por JS) para mostrar el registro
        return render_template('newlogin/index.html')

    # POST: crear usuario
    usuario = (request.form.get('usuario') or '').strip()
    clave = (request.form.get('clave') or '').strip()
    confirmar = (request.form.get('confirmar') or '').strip()
    rol = (request.form.get('rol') or 'usuario').strip()

    if not usuario or not clave or not confirmar:
        flash('Completa todos los campos', 'error')
        return render_template('newlogin/index.html')

    if clave != confirmar:
        flash('Las contraseñas no coinciden', 'error')
        return render_template('newlogin/index.html')

    # Guardar en usuarios.json
    try:
        success, msg = registrar_usuario(usuario, clave, rol)
        if not success:
            flash(msg or 'No se pudo registrar el usuario', 'error')
            return render_template('newlogin/index.html')
    except Exception as e:
        flash(f'Error registrando usuario: {str(e)}', 'error')
        return render_template('newlogin/index.html')

    # Asegurar entrada en la BD (password con hash)
    try:
        pwd_hash = hashlib.sha256(clave.encode('utf-8')).hexdigest()
        user_info = db.get_user_by_username(usuario)
        if not user_info:
            db.create_user(usuario, pwd_hash, rol=rol)
    except Exception:
        # Si la BD falla, el registro en JSON igual se mantiene.
        pass

    flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
    return redirect(url_for('login'))

@app.route('/api/nfc-scan', methods=['POST'])
def nfc_scan():
    if 'usuario' in session:
        return jsonify({'success': True})
    
    # Aquí se implementaría la lógica real de escaneo NFC
    # Por ahora, simulamos un acceso con usuario predeterminado
    usuario = 'invitado'
    
    # Verificar si el usuario existe
    user_info = db.get_user_by_username(usuario)
    if user_info:
        session['usuario'] = usuario
        session['user_id'] = user_info['id']
        session['rol'] = user_info['rol']
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Usuario no encontrado'})

@app.route('/logout')
def flask_logout():
    session.clear()
    # Redirigir al sitio público (raíz)
    public_site_url = os.getenv("PUBLIC_SITE_URL")  # p.ej. https://zero-va.com
    if public_site_url:
        target = public_site_url.rstrip('/') + '/'
    else:
        scheme = 'https' if request.is_secure else 'http'
        host = request.host.split(':')[0]
        target = f"{scheme}://{host}/"
    resp = redirect(target)
    # Borrar cookie de sesión para asegurar cierre
    try:
        cookie_name = app.session_cookie_name
    except Exception:
        cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
    resp.delete_cookie(cookie_name)  # sin dominio (cubre la mayoría)
    resp.delete_cookie(cookie_name, path='/', domain=request.host.split(':')[0])  # con dominio
    return resp

# API para el chat
@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json() or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400
    if not GROQ_API_KEY:
        return jsonify({'error': 'GROQ_API_KEY no configurada'}), 400

    # Gestionar chat_id consistente y crear si no existe
    incoming_chat_id = data.get('chat_id')
    user_id = session.get('user_id')
    chat_id = incoming_chat_id or session.get('current_chat')
    title = user_message[:30] + ('...' if len(user_message) > 30 else '')

    if not chat_id:
        chat_id = db.create_chat(user_id, title)
    else:
        try:
            db.update_chat_title(chat_id, title)
        except Exception:
            pass
    session['current_chat'] = chat_id

    # Mensajes para la IA (incluye pequeño prompt del sistema opcional)
    system_prompt = "Eres un asistente AI llamado Zero. Sé conciso, profesional y útil."
    user_context = db.get_user_context(user_id)
    if user_context:
        context_info = "\n\nContexto personalizado del usuario:\n"
        for ctx in user_context[-5:]:
            context_info += f"- {ctx['context_key']}: {ctx['context_value'][:200]}...\n"
        system_prompt += context_info

    payload = {
        "model": GROQ_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=BASE_HEADERS, json=payload, timeout=60)
        # Registrar cuerpo de error si falla
        if response.status_code != 200:
            try:
                err_json = response.json()
            except Exception:
                err_json = {"raw": response.text[:500]}
            logging.error(f"Groq API error {response.status_code}: {err_json}")
            # Mensaje amigable según código
            if response.status_code == 401:
                return jsonify({'error': 'Clave de API inválida o expirada'}), 500
            if response.status_code == 404:
                return jsonify({'error': f'Modelo no encontrado: {GROQ_TEXT_MODEL}'}), 500
            return jsonify({'error': 'Error en la API de IA'}), 500

        result = response.json()
        ai_response = result['choices'][0]['message']['content']

        # Guardar mensajes en DB
        db.add_message(chat_id, "user", user_message)
        db.add_message(chat_id, "assistant", ai_response)

        return jsonify({'response': ai_response, 'chat_id': chat_id})
    except requests.exceptions.Timeout:
        logging.error("Groq API timeout")
        return jsonify({'error': 'Tiempo de espera agotado con la IA'}), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Groq API request exception: {e}")
        return jsonify({'error': 'Error de conexión con la IA'}), 500
    except Exception as e:
        logging.error(f"Groq API unexpected error: {e}", exc_info=True)
        return jsonify({'error': 'Error inesperado procesando la respuesta'}), 500

# API para análisis de documentos
@app.route('/api/analyze-document', methods=['POST'])
def analyze_document_api():
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    
    # Guardar y procesar el archivo
    try:
        filename = secure_filename(file.filename)
        file_type = filename.split('.')[-1].lower()
        
        # Verificar tipo de archivo
        file_types = {
            'pdf': 'pdf', 'docx': 'word', 'doc': 'word', 'txt': 'text',
            'md': 'markdown', 'xlsx': 'excel', 'xls': 'excel', 'csv': 'csv',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image'
        }
        file_type = file_types.get(file_type, 'unknown')
        
        if file_type == 'unknown':
            return jsonify({'error': 'Tipo de archivo no soportado'}), 400
        
        # Guardar archivo
        user_dir = f"{app.config['UPLOAD_FOLDER']}/{session.get('user_id')}"
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, filename)
        file.save(file_path)
        
        # Procesar archivo
        content = ""
        analysis = ""
        
        if file_type == 'image':
            with open(file_path, 'rb') as img_file:
                image_base64 = b64encode(img_file.read()).decode('utf-8')
            analysis = analyze_image_with_groq(image_base64, filename)
            content = "Imagen procesada para análisis visual"
        else:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            if file_type in ['pdf', 'word']:
                processor = FileProcessor()
                result = processor.process_file(file_content, filename)
                content = result.get('content', '')[:5000]
            else:
                try:
                    content = file_content.decode('utf-8')[:5000]
                except:
                    content = file_content.decode('latin-1')[:5000]
            
            if content and len(content.strip()) > 50:
                analysis = analyze_document_with_groq(content, filename)
            else:
                analysis = f"Documento procesado: {filename}"
        
        # Guardar en la base de datos
        file_id = db.save_file(
            user_id=session.get('user_id'),
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=os.path.getsize(file_path),
            content_extracted=content,
            analysis_summary=analysis[:350]
        )
        
        if analysis:
            context_key = f"Archivo: {filename}"
            db.save_user_context(session.get('user_id'), context_key, analysis, file_id)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'analysis': analysis
        })
    
    except Exception as e:
        return jsonify({'error': f'Error procesando archivo: {str(e)}'}), 500

# Función para analizar documentos con Groq
def analyze_document_with_groq(content, filename):
    """Analiza documentos con Groq"""
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

# Función para analizar imágenes con Groq
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
Describe el contenido de manera detallada

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

@app.route('/newlogin/styles.css')
def newlogin_css():
    css_dir = os.path.join(app.root_path, 'templates', 'newlogin')
    return send_from_directory(css_dir, 'styles.css', mimetype='text/css')

# Iniciar la aplicación
def verificar_login(usuario, clave):
    # Intenta validar con usuarios.json; si no existe, retorna False
    try:
        with open(os.path.join(app.root_path, 'usuarios.json'), 'r', encoding='utf-8') as f:
            usuarios = json.load(f)
        # Formato dict: {"admin": {"clave": "...", "rol": "admin"}, ...}
        if isinstance(usuarios, dict):
            entry = usuarios.get(usuario)
            if isinstance(entry, dict):
                return (entry.get('clave') or entry.get('password')) == clave
            # Soporte de dict plano: {"admin": "clave"}
            return entry == clave
        # Formato lista: [{"usuario": "...", "clave": "...", "rol": "..."}]
        if isinstance(usuarios, list):
            for u in usuarios:
                name = u.get('usuario') or u.get('username')
                if name == usuario and (u.get('clave') or u.get('password')) == clave:
                    return True
    except Exception:
        pass
    return False

if __name__ == '__main__':
    app.run(debug=True, port=8000)


# Agregar después de la ruta /api/analyze-document

# API para obtener la lista de chats
@app.route('/api/chats', methods=['GET'])
def get_chats():
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    user_id = session.get('user_id')
    chats = db.get_user_chats(user_id)
    
    return jsonify({
        'chats': chats
    })

# API para obtener un chat específico
@app.route('/api/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    # Corrige llamada: solo requiere chat_id
    messages = db.get_chat_messages(chat_id)

    return jsonify({
        'chat_id': chat_id,
        'messages': messages
    })