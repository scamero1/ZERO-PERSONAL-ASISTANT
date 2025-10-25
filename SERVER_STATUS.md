# ZERO Personal Assistant – Estado del Servidor

Este documento resume la verificación y puesta en marcha realizada para que el proyecto funcione en el servidor actual.

## Entorno
- Entorno virtual: `.venv` creado con `python3 -m venv .venv`.
- Dependencias instaladas: `pip install -r requirements.txt`. Se añadió `Flask-Cors` por import faltante.

## Servicios levantados
- Backend Flask (Waitress): `0.0.0.0:8000` sirviendo `app:app`.
- Frontend Streamlit: `0.0.0.0:8501` sirviendo `Zero.py`.

Comandos usados:
```
. .venv/bin/activate
waitress-serve --host=0.0.0.0 --port=8000 app:app
streamlit run Zero.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

## Validación de rutas
- `/` responde `302` y redirige a `/login` cuando no hay sesión.
- `/login` responde `200` y carga la plantilla `templates/newlogin/index.html`.
- Estáticos responden `200`: `/static/css/index.css` y `/favicon.ico`.

## Variables de entorno relevantes
- `SECRET_KEY`: clave de sesión Flask.
- `GROQ_API_KEY`: requerida para `/api/chat` y análisis con Groq.
- Opcionales: `PUBLIC_APP_URL`, `PUBLIC_SITE_URL` para redirecciones.

Ajuste recomendado:
- Si se sirve sobre HTTP sin TLS, considerar `SESSION_COOKIE_SECURE=False` para evitar que el navegador no acepte la cookie de sesión (actualmente está en `True`). En producción con HTTPS, mantener `True`.

## Nginx
Archivo `nginx.conf` actual proxy a nombres de host de contenedor:
```
location / { proxy_pass http://flask:8000; }
location /app/ { proxy_pass http://streamlit:8501/app/; }
```
Esto asume despliegue en Docker (upstreams `flask` y `streamlit`).

Opciones:
1) Despliegue con Docker (ver sección siguiente).
2) Para despliegue sin Docker, usar `localhost`:
```
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /app/ {
        proxy_pass http://127.0.0.1:8501/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    client_max_body_size 64M;
}
```

## Servicio `zero.service` (systemd)
Archivo actual:
```
WorkingDirectory=/opt/zero
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=deploy
```
Esto requiere:
- Un `docker-compose.yml` en `/opt/zero` con servicios `flask` y `streamlit` (y opcionalmente `nginx`).
- Usuario `deploy` existente y permisos.

No se encontró `docker-compose.yml` en el repositorio. Opciones:
- Crear un `docker-compose.yml` que levante Flask (waitress), Streamlit y Nginx.
- O bien, usar dos servicios systemd simples sin Docker que ejecuten los comandos de Waitress y Streamlit mostrados arriba.

### Ejemplo mínimo de `docker-compose.yml` (referencial)
```
services:
  flask:
    build: .
    command: ["waitress-serve", "--host=0.0.0.0", "--port=8000", "app:app"]
    ports: ["8000:8000"]
  streamlit:
    build: .
    command: ["streamlit", "run", "Zero.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
    ports: ["8501:8501"]
  nginx:
    image: nginx:stable
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports: ["80:80"]
    depends_on: [flask, streamlit]
```
> Nota: Requiere crear `Dockerfile` acorde y manejar `.venv`/dependencias dentro de la imagen.

## Cloudflared (Windows)
- El proyecto incluye `cloudflared.exe` y `cloudflared.yml` orientados a Windows. En Linux, usar `cloudflared` nativo y ajustar paths/credenciales.

## Observaciones de seguridad
- Las contraseñas en `usuarios.json` no están hasheadas en todos los flows. En `app.py` se aplica hash al crear usuarios desde login; revisar consistencia.
- Asegurar `GROQ_API_KEY` vía `.env` o variables del sistema.

## Próximos pasos
- Definir estrategia de despliegue: Docker + Nginx (recomendada) o Systemd + Nginx.
- Configurar Nginx para proxy a `localhost` o a contenedores según lo elegido.
- Proveer `GROQ_API_KEY` en entorno productivo.
- (Opcional) Habilitar HTTPS en Nginx para mantener `SESSION_COOKIE_SECURE=True`.

## Resumen
El proyecto funciona localmente con Flask y Streamlit corriendo y rutas validadas. Para producción, ajustar Nginx y el método de orquestación (Docker/systemd) y definir variables de entorno.