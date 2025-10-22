import sqlite3
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
import uuid
import csv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

SAFE_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".txt", ".pptx", ".csv", ".png", ".jpg", ".jpeg"
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB por ejemplo

class ZeroDatabase:
    def __init__(self, db_path: str = "zero.db", upload_root: str = "uploads"):
        self.db_path = db_path
        self.upload_root = upload_root
        os.makedirs(self.upload_root, exist_ok=True)
        self.init_database()

    # --- conexión con PRAGMAs y timeouts
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # PRAGMAs críticos
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")  # 5s
        return conn

    # --- init schema
    def init_database(self):
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Tabla de empresas (multi-tenant)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS empresas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    slug TEXT UNIQUE,
                    settings_json TEXT,
                    groq_api_key TEXT,
                    model_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Tabla de usuarios
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'usuario',
                    nfc_uid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                """
            )

            # Agregar columna empresa_id si no existe
            cur.execute("PRAGMA table_info(usuarios);")
            cols = [r[1] for r in cur.fetchall()]
            if "empresa_id" not in cols:
                cur.execute("ALTER TABLE usuarios ADD COLUMN empresa_id INTEGER;")

            # Tabla de chats
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                );
                """
            )

            # Tabla de mensajes
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
                );
                """
            )

            # Tabla de archivos subidos
            cur.execute(
                """
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
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                );
                """
            )

            # Tabla de análisis de imágenes
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analisis_imagenes (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    archivo_id TEXT,
                    image_path TEXT NOT NULL,
                    analysis_result TEXT NOT NULL,
                    model_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE,
                    FOREIGN KEY (archivo_id) REFERENCES archivos (id) ON DELETE CASCADE
                );
                """
            )

            # Tabla de contexto por usuario
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS contexto_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    context_key TEXT NOT NULL,
                    context_value TEXT NOT NULL,
                    source_file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE,
                    FOREIGN KEY (source_file_id) REFERENCES archivos (id) ON DELETE SET NULL
                );
                """
            )

            # Índices recomendados
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_msgs_chat ON mensajes(chat_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_user ON archivos(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ctx_user ON contexto_usuario(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_img_user ON analisis_imagenes(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_empresa ON usuarios(empresa_id);")

            # Tabla de claves de cifrado por empresa
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS empresa_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    key_ciphertext BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE CASCADE
                );
                """
            )

    # --- helpers de subida/seguridad
    def _safe_filename(self, name: str) -> str:
        # quita caracteres peligrosos, deja letras, números, ., _, -
        name = os.path.basename(name)
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
        return name or f"file_{uuid.uuid4()}"

    def _ensure_user_dir(self, user_id: int) -> str:
        user_dir = os.path.join(self.upload_root, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _check_file_constraints(self, filename: str, file_size: int) -> None:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SAFE_EXTENSIONS:
            raise ValueError(f"Extensión no permitida: {ext}")
        if file_size is not None and file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError("Archivo supera el tamaño máximo permitido")

    # --- USUARIOS
    def get_user_id_by_username(self, username: str) -> Optional[int]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT id FROM usuarios WHERE username = ?;", (username,))
            row = cur.fetchone()
            return row["id"] if row else None

    def create_user(self, username: str, password_hash: str, rol: str = "usuario", nfc_uid: Optional[str] = None) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO usuarios (username, password_hash, rol, nfc_uid) VALUES (?, ?, ?, ?);",
                    (username, password_hash, rol, nfc_uid)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM usuarios WHERE username = ?;", (username,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_users(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM usuarios ORDER BY created_at DESC;")
            return [dict(r) for r in cur.fetchall()]

    def update_last_login(self, user_id: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?;", (user_id,))

    # --- EMPRESAS
    def create_company(self, nombre: str, slug: Optional[str] = None, settings: Optional[Dict] = None,
                       groq_api_key: Optional[str] = None, model_name: Optional[str] = None) -> int:
        settings_json = json.dumps(settings) if settings else None
        with self.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO empresas (nombre, slug, settings_json, groq_api_key, model_name) VALUES (?, ?, ?, ?, ?);",
                (nombre, slug, settings_json, groq_api_key, model_name)
            )
            return cur.lastrowid

    def list_companies(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM empresas ORDER BY created_at DESC;")
            return [dict(r) for r in cur.fetchall()]

    def get_company_by_id(self, empresa_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM empresas WHERE id = ?;", (empresa_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_company_by_slug(self, slug: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM empresas WHERE slug = ?;", (slug,))
            row = cur.fetchone()
            return dict(row) if row else None

    def assign_user_to_company(self, user_id: int, empresa_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute("UPDATE usuarios SET empresa_id = ? WHERE id = ?;", (empresa_id, user_id))
            return True
        except Exception:
            return False

    def get_user_company_id(self, user_id: int) -> Optional[int]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT empresa_id FROM usuarios WHERE id = ?;", (user_id,))
            row = cur.fetchone()
            return row["empresa_id"] if row and row["empresa_id"] is not None else None

    def get_company_settings(self, empresa_id: int) -> Dict:
        empresa = self.get_company_by_id(empresa_id)
        if not empresa:
            return {}
        sj = empresa.get("settings_json")
        try:
            return json.loads(sj) if sj else {}
        except Exception:
            return {}

    def update_company_settings(self, empresa_id: int, updates: Dict) -> bool:
        try:
            current = self.get_company_settings(empresa_id)
            current.update(updates or {})
            settings_json = json.dumps(current)
            with self.get_connection() as conn:
                conn.execute("UPDATE empresas SET settings_json = ? WHERE id = ?;", (settings_json, empresa_id))
            return True
        except Exception:
            return False

    def _get_master_key(self) -> bytes:
        mk_b64 = os.getenv("ZERO_MASTER_KEY")
        if mk_b64:
            try:
                mk = base64.b64decode(mk_b64)
                if len(mk) in (16, 24, 32):
                    if len(mk) != 32:
                        mk = (mk + b"\x00" * 32)[:32]
                    return mk
            except Exception:
                pass
        if not hasattr(self, "_ephemeral_master_key") or self._ephemeral_master_key is None:
            self._ephemeral_master_key = os.urandom(32)
        return self._ephemeral_master_key

    def ensure_empresa_key(self, empresa_id: int) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT version FROM empresa_keys WHERE empresa_id = ? ORDER BY version DESC LIMIT 1;",
                (empresa_id,)
            )
            row = cur.fetchone()
            last_version = row["version"] if row else 0
            cur = conn.execute(
                "SELECT id FROM empresa_keys WHERE empresa_id = ? AND active = 1 LIMIT 1;",
                (empresa_id,)
            )
            active = cur.fetchone()
            if active:
                return last_version or 1
            data_key = os.urandom(32)
            nonce = os.urandom(12)
            aes = AESGCM(self._get_master_key())
            key_ciphertext = aes.encrypt(nonce, data_key, associated_data=str(empresa_id).encode())
            version = (last_version or 0) + 1
            conn.execute(
                """INSERT INTO empresa_keys (empresa_id, version, key_ciphertext, nonce, active)
                   VALUES (?, ?, ?, ?, 1);""",
                (empresa_id, version, key_ciphertext, nonce)
            )
            return version

    def get_active_empresa_key(self, empresa_id: int) -> Optional[bytes]:
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT key_ciphertext, nonce FROM empresa_keys WHERE empresa_id = ? AND active = 1 ORDER BY version DESC LIMIT 1;",
                (empresa_id,)
            )
            row = cur.fetchone()
            if not row:
                self.ensure_empresa_key(empresa_id)
                cur = conn.execute(
                    "SELECT key_ciphertext, nonce FROM empresa_keys WHERE empresa_id = ? AND active = 1 ORDER BY version DESC LIMIT 1;",
                    (empresa_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
            try:
                aes = AESGCM(self._get_master_key())
                data_key = aes.decrypt(row["nonce"], row["key_ciphertext"], associated_data=str(empresa_id).encode())
                return data_key
            except Exception:
                return None

    def rotate_empresa_key(self, empresa_id: int) -> Optional[int]:
        with self.get_connection() as conn:
            conn.execute("UPDATE empresa_keys SET active = 0 WHERE empresa_id = ? AND active = 1;", (empresa_id,))
            cur = conn.execute("SELECT MAX(version) AS v FROM empresa_keys WHERE empresa_id = ?;", (empresa_id,))
            row = cur.fetchone()
            next_version = (row["v"] or 0) + 1
            data_key = os.urandom(32)
            nonce = os.urandom(12)
            aes = AESGCM(self._get_master_key())
            key_ciphertext = aes.encrypt(nonce, data_key, associated_data=str(empresa_id).encode())
            conn.execute(
                """INSERT INTO empresa_keys (empresa_id, version, key_ciphertext, nonce, active)
                   VALUES (?, ?, ?, ?, 1);""",
                (empresa_id, next_version, key_ciphertext, nonce)
            )
            return next_version

    def get_company_users(self, empresa_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM usuarios WHERE empresa_id = ? ORDER BY username ASC;", (empresa_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_company_files(self, empresa_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT a.* FROM archivos a
                JOIN usuarios u ON u.id = a.user_id
                WHERE u.empresa_id = ?
                ORDER BY uploaded_at DESC;
                """,
                (empresa_id,)
            )
            return [dict(r) for r in cur.fetchall()]

    def get_company_context(self, empresa_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT c.* FROM contexto_usuario c
                JOIN usuarios u ON u.id = c.user_id
                WHERE u.empresa_id = ?
                ORDER BY created_at DESC;
                """,
                (empresa_id,)
            )
            return [dict(r) for r in cur.fetchall()]

    def export_company_docs_csv(self, empresa_id: int, output_path: str) -> str:
        files = self.get_company_files(empresa_id)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "file_id", "user_id", "filename", "file_type", "file_size",
                "uploaded_at", "analysis_summary"
            ])
            for doc in files:
                writer.writerow([
                    doc.get("id"), doc.get("user_id"), doc.get("filename"), doc.get("file_type"),
                    doc.get("file_size"), doc.get("uploaded_at"), (doc.get("analysis_summary") or "").replace("\n", " ")
                ])
        return output_path

    # --- CHATS
    def create_chat(self, user_id: int, title: str = "Nuevo chat") -> str:
        chat_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            conn.execute("INSERT INTO chats (id, user_id, title) VALUES (?, ?, ?);", (chat_id, user_id, title))
        return chat_id

    def get_user_chats(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM chats WHERE user_id = ? ORDER BY updated_at DESC;", (user_id,))
            return [dict(r) for r in cur.fetchall()]

    def update_chat_title(self, chat_id: str, title: str):
        with self.get_connection() as conn:
            conn.execute("UPDATE chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (title, chat_id))

    # --- MENSAJES
    def add_message(self, chat_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        metadata_json = json.dumps(metadata) if metadata else None
        with self.get_connection() as conn:
            conn.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (chat_id,))
            conn.execute(
                "INSERT INTO mensajes (chat_id, role, content, metadata) VALUES (?, ?, ?, ?);",
                (chat_id, role, content, metadata_json)
            )

    def get_chat_messages(self, chat_id: str) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM mensajes WHERE chat_id = ? ORDER BY timestamp ASC;", (chat_id,))
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else None
                out.append(d)
            return out

    # --- ARCHIVOS
    def save_file(self, user_id: int, filename: str, file_type: str, file_size: Optional[int],
                  file_path: str, content_extracted: Optional[str] = None, analysis_summary: Optional[str] = None) -> str:
        """
        Registra el archivo ya guardado en disco. Valida extensión/tamaño y existencia del path.
        """
        safe_name = self._safe_filename(filename)
        self._check_file_constraints(safe_name, file_size)

        if not os.path.isfile(file_path):
            raise FileNotFoundError("El archivo no existe en el file_path indicado")

        file_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO archivos (id, user_id, filename, file_type, file_size, file_path, content_extracted, analysis_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                (file_id, user_id, safe_name, file_type, file_size, file_path, content_extracted, analysis_summary)
            )
        return file_id

    def get_user_files(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM archivos WHERE user_id = ? ORDER BY uploaded_at DESC;", (user_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM archivos WHERE id = ?;", (file_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # --- ANÁLISIS DE IMÁGENES
    def save_image_analysis(self, user_id: int, image_path: str, analysis_result: str,
                            model_used: Optional[str], archivo_id: Optional[str] = None) -> str:
        if not os.path.isfile(image_path):
            raise FileNotFoundError("image_path no existe")
        analysis_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO analisis_imagenes (id, user_id, archivo_id, image_path, analysis_result, model_used)
                   VALUES (?, ?, ?, ?, ?, ?);""",
                (analysis_id, user_id, archivo_id, image_path, analysis_result, model_used)
            )
        return analysis_id

    def get_user_image_analyses(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM analisis_imagenes WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
            return [dict(r) for r in cur.fetchall()]

    # --- CONTEXTO
    def save_user_context(self, user_id: int, context_key: str, context_value: str, source_file_id: Optional[str] = None):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO contexto_usuario (user_id, context_key, context_value, source_file_id) VALUES (?, ?, ?, ?);",
                (user_id, context_key, context_value, source_file_id)
            )

    def get_user_context(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM contexto_usuario WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
            return [dict(r) for r in cur.fetchall()]

    # --- BORRADO
    def delete_file(self, file_id: str, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                # borra dependencias (ON DELETE CASCADE ya lo hace, pero mantenemos por claridad)
                conn.execute("DELETE FROM analisis_imagenes WHERE archivo_id = ?;", (file_id,))
                conn.execute("DELETE FROM contexto_usuario WHERE source_file_id = ?;", (file_id,))
                # borra registro del archivo
                conn.execute("DELETE FROM archivos WHERE id = ? AND user_id = ?;", (file_id, user_id))
            return True
        except Exception:
            return False

    def delete_chat(self, chat_id: str, user_id: int) -> bool:
        """
        Elimina un chat y sus mensajes asociados para el usuario dado.
        """
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM mensajes WHERE chat_id = ?;", (chat_id,))
                conn.execute("DELETE FROM chats WHERE id = ? AND user_id = ?;", (chat_id, user_id))
            return True
        except Exception:
            return False
