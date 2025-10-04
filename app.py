from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
import os
import json
import uuid
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

# Inicializar aplicación Flask
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "zero_secret_key")
app.config['UPLOAD_FOLDER'] = 'user_uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    groq_enabled = bool(GROQ_API_KEY)
    return render_template(
        'index.html',
        usuario=session.get('usuario'),
        rol=session.get('rol'),
        groq_enabled=groq_enabled
    )

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/x-icon')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        clave = request.form.get('clave')
        
        # Manejo de acceso rápido
        if clave == 'acceso_rapido':
            # Verificar si el usuario existe en la base de datos
            user_info = db.get_user_by_username(usuario)
            if user_info:
                session['usuario'] = usuario
                session['user_id'] = user_info['id']
                session['rol'] = user_info['rol']
                return redirect(url_for('index'))
        # Autenticación normal con contraseña
        elif verificar_login(usuario, clave):
            # Obtener información del usuario desde la base de datos
            user_info = db.get_user_by_username(usuario)
            if user_info:
                session['usuario'] = usuario
                session['user_id'] = user_info['id']
                session['rol'] = user_info['rol']
                return redirect(url_for('index'))
        
        flash('Credenciales inválidas', 'error')
    
    # Contar usuarios para mostrar en la página de login
    user_count = db.get_user_count() if hasattr(db, 'get_user_count') else '?'
    
    return render_template('login.html', user_count=user_count, login_mode=None)

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
def logout_route():
    logout()
    return redirect(url_for('login'))

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
        if response.status_code != 200:
            return jsonify({'error': f'Error en la API: {response.status_code}'}), 500

        result = response.json()
        ai_response = result['choices'][0]['message']['content']

        # Guardar mensajes en DB
        db.add_message(chat_id, "user", user_message)
        db.add_message(chat_id, "assistant", ai_response)

        return jsonify({'response': ai_response, 'chat_id': chat_id})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

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

# Iniciar la aplicación
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