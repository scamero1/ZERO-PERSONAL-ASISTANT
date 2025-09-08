import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid

class ZeroDatabase:
    def get_user_id_by_username(self, username: str) -> Optional[int]:
        """Obtiene el ID de usuario por nombre de usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None

    def __init__(self, db_path: str = "zero.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos con todas las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'usuario',
                nfc_uid TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Tabla de chats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id)
            )
        """)
        
        # Tabla de mensajes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats (id)
            )
        """)
        
        # Tabla de archivos subidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archivos (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                file_path TEXT NOT NULL,
                content_extracted TEXT,
                analysis_summary TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id)
            )
        """)
        
        # Tabla de análisis de imágenes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analisis_imagenes (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                archivo_id TEXT,
                image_path TEXT NOT NULL,
                analysis_result TEXT NOT NULL,
                model_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id),
                FOREIGN KEY (archivo_id) REFERENCES archivos (id)
            )
        """)
        
        # Tabla de contexto personalizado por usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contexto_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                context_key TEXT NOT NULL,
                context_value TEXT NOT NULL,
                source_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id),
                FOREIGN KEY (source_file_id) REFERENCES archivos (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    # === MÉTODOS PARA USUARIOS ===
    def create_user(self, username: str, password_hash: str, rol: str = "usuario", nfc_uid: str = None) -> bool:
        """Crea un nuevo usuario"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, rol, nfc_uid) VALUES (?, ?, ?, ?)",
                (username, password_hash, rol, nfc_uid)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene un usuario por nombre de usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'rol': row[3],
                'nfc_uid': row[4],
                'created_at': row[5],
                'last_login': row[6]
            }
        return None
    
    def update_last_login(self, user_id: int):
        """Actualiza la última fecha de login"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    
    # === MÉTODOS PARA CHATS ===
    def create_chat(self, user_id: int, title: str = "Nuevo chat") -> str:
        """Crea un nuevo chat"""
        chat_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (id, user_id, title) VALUES (?, ?, ?)",
            (chat_id, user_id, title)
        )
        conn.commit()
        conn.close()
        return chat_id
    
    def get_user_chats(self, user_id: int) -> List[Dict]:
        """Obtiene todos los chats de un usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM chats WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        chats = []
        for row in rows:
            chats.append({
                'id': row[0],
                'user_id': row[1],
                'title': row[2],
                'created_at': row[3],
                'updated_at': row[4]
            })
        return chats
    
    def update_chat_title(self, chat_id: str, title: str):
        """Actualiza el título de un chat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, chat_id)
        )
        conn.commit()
        conn.close()
    
    # === MÉTODOS PARA MENSAJES ===
    def add_message(self, chat_id: str, role: str, content: str, metadata: Dict = None):
        """Añade un mensaje a un chat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Actualizar timestamp del chat
        cursor.execute(
            "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (chat_id,)
        )
        
        # Insertar mensaje
        metadata_json = json.dumps(metadata) if metadata else None
        cursor.execute(
            "INSERT INTO mensajes (chat_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, metadata_json)
        )
        
        conn.commit()
        conn.close()
    
    def get_chat_messages(self, chat_id: str) -> List[Dict]:
        """Obtiene todos los mensajes de un chat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM mensajes WHERE chat_id = ? ORDER BY timestamp ASC",
            (chat_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            metadata = json.loads(row[5]) if row[5] else None
            messages.append({
                'id': row[0],
                'chat_id': row[1],
                'role': row[2],
                'content': row[3],
                'timestamp': row[4],
                'metadata': metadata
            })
        return messages
    
    # === MÉTODOS PARA ARCHIVOS ===
    def save_file(self, user_id: int, filename: str, file_type: str, file_size: int, 
                  file_path: str, content_extracted: str = None, analysis_summary: str = None) -> str:
        """Guarda información de un archivo subido"""
        file_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO archivos (id, user_id, filename, file_type, file_size, 
               file_path, content_extracted, analysis_summary) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_id, user_id, filename, file_type, file_size, file_path, content_extracted, analysis_summary)
        )
        conn.commit()
        conn.close()
        return file_id
    
    def get_user_files(self, user_id: int) -> List[Dict]:
        """Obtiene todos los archivos de un usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM archivos WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        files = []
        for row in rows:
            files.append({
                'id': row[0],
                'user_id': row[1],
                'filename': row[2],
                'file_type': row[3],
                'file_size': row[4],
                'file_path': row[5],
                'content_extracted': row[6],
                'analysis_summary': row[7],
                'uploaded_at': row[8]
            })
        return files
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Obtiene un archivo por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM archivos WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'filename': row[2],
                'file_type': row[3],
                'file_size': row[4],
                'file_path': row[5],
                'content_extracted': row[6],
                'analysis_summary': row[7],
                'uploaded_at': row[8]
            }
        return None
    
    # === MÉTODOS PARA ANÁLISIS DE IMÁGENES ===
    def save_image_analysis(self, user_id: int, image_path: str, analysis_result: str, 
                           model_used: str, archivo_id: str = None) -> str:
        """Guarda un análisis de imagen"""
        analysis_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO analisis_imagenes (id, user_id, archivo_id, image_path, 
               analysis_result, model_used) VALUES (?, ?, ?, ?, ?, ?)""",
            (analysis_id, user_id, archivo_id, image_path, analysis_result, model_used)
        )
        conn.commit()
        conn.close()
        return analysis_id
    
    def get_user_image_analyses(self, user_id: int) -> List[Dict]:
        """Obtiene todos los análisis de imágenes de un usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM analisis_imagenes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        analyses = []
        for row in rows:
            analyses.append({
                'id': row[0],
                'user_id': row[1],
                'archivo_id': row[2],
                'image_path': row[3],
                'analysis_result': row[4],
                'model_used': row[5],
                'created_at': row[6]
            })
        return analyses
    
    # === MÉTODOS PARA CONTEXTO PERSONALIZADO ===
    def save_user_context(self, user_id: int, context_key: str, context_value: str, source_file_id: str = None):
        """Guarda contexto personalizado del usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contexto_usuario (user_id, context_key, context_value, source_file_id) VALUES (?, ?, ?, ?)",
            (user_id, context_key, context_value, source_file_id)
        )
        conn.commit()
        conn.close()
    
    def get_user_context(self, user_id: int) -> List[Dict]:
        """Obtiene todo el contexto personalizado de un usuario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM contexto_usuario WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        context = []
        for row in rows:
            context.append({
                'id': row[0],
                'user_id': row[1],
                'context_key': row[2],
                'context_value': row[3],
                'source_file_id': row[4],
                'created_at': row[5]
            })
        return context
    
    def delete_file(self, file_id: str, user_id: int) -> bool:
        """Elimina un archivo y sus análisis asociados"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Eliminar análisis de imágenes asociados
            cursor.execute("DELETE FROM analisis_imagenes WHERE archivo_id = ?", (file_id,))
            
            # Eliminar contexto asociado
            cursor.execute("DELETE FROM contexto_usuario WHERE source_file_id = ?", (file_id,))
            
            # Eliminar archivo
            cursor.execute("DELETE FROM archivos WHERE id = ? AND user_id = ?", (file_id, user_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

# Instancia global de la base de datos
db = ZeroDatabase()