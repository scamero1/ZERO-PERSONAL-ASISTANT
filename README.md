# ZERO - Asistente Virtual

Este proyecto es un asistente virtual avanzado desarrollado en Python, diseñado para integrarse con Streamlit y ofrecer funcionalidades de reconocimiento de voz, autenticación, procesamiento de archivos, búsqueda web y gestión de usuarios. El sistema está pensado para ser colaborativo y escalable, ideal para grupos de programadores.

## Estructura del Proyecto

- **Zero.py**: Interfaz principal en Streamlit. Gestiona la interacción con el usuario, autenticación, subida y análisis de archivos, y comunicación con otros módulos.
- **base.py**: Funciones base y utilidades para la interfaz y lógica de la aplicación.
- **Login.py**: Registro, login y gestión de usuarios (incluye soporte para tarjetas NFC).
- **auth_jwt.py**: Autenticación basada en JWT y gestión de sesiones seguras.
- **database.py**: Acceso y gestión de la base de datos SQLite para usuarios y registros.
- **file_processor.py**: Procesamiento y extracción de texto de archivos PDF, Word, Excel, imágenes, etc.
- **lector_nfc.py**: Lectura de UID de tarjetas NFC para autenticación física.
- **websearch.py**: Búsqueda contextual en la web usando APIs externas.
- **requirements.txt**: Lista de dependencias del proyecto.
- **usuarios.json**: Almacena los usuarios registrados.
- **active_tokens.json**: Tokens JWT activos para sesiones.
- **zero.db**: Base de datos SQLite del sistema.
- **storage/**: Carpeta para archivos de administración y documentos de referencia.
- **uploads/**: Archivos subidos por los usuarios.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu_usuario/ZERO-PERSONAL-ASISTANT.git
   cd ZERO-PERSONAL-ASISTANT
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura las variables de entorno necesarias (por ejemplo, `GROQ_API_KEY`, `JWT_SECRET`).
4. Ejecuta la aplicación principal:
   ```bash
   streamlit run Zero.py
   ```

## Funcionalidades principales

- **Reconocimiento de voz y video**
- **Autenticación segura (JWT, NFC, login tradicional)**
- **Procesamiento de archivos (PDF, Word, Excel, imágenes, texto)**
- **Búsqueda web contextual**
- **Gestión de usuarios y roles**
- **Interfaz web moderna con Streamlit**

## Colaboradores

Este proyecto está abierto a la colaboración. Siéntete libre de crear issues, pull requests o sugerencias.

---

¡Bienvenido al equipo de desarrollo de ZERO!