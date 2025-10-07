import subprocess
import os
import sys
import tkinter as tk
from tkinter import messagebox
from plyer import notification
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Verifica el JSON
try:
    with open("usuarios.json") as f:
        json.load(f)
except Exception as e:
    messagebox.showerror("Error", f"Archivo JSON inválido: {e}")
    exit()

# Rutas
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_SCRIPTS = os.path.join(ROOT_DIR, ".venv", "Scripts")
PIP_EXE = os.path.join(VENV_SCRIPTS, "pip.exe")
WAITRESS_EXE = os.path.join(VENV_SCRIPTS, "waitress-serve.exe")
STREAMLIT_EXE = os.path.join(VENV_SCRIPTS, "streamlit.exe")
CLOUDFLARED_EXE = os.path.join(ROOT_DIR, "cloudflared.exe")
CF_CFG = os.path.join(ROOT_DIR, "cloudflared.yml")

CONTROL_PORT = int(os.getenv("CONTROL_PORT", "8765"))
CONTROL_TOKEN = os.getenv("CONTROL_TOKEN", "cambia-este-token")

# Bandera para ocultar consola en Windows
CREATE_NO_WINDOW = 0x08000000

# Procesos
procs = {
    "flask": None,
    "streamlit": None,
    "cloudflared": None,
}

def start_processes():
    errors = []
    # Intentar auto-instalar si faltan
    if not os.path.exists(WAITRESS_EXE):
        try:
            subprocess.run([PIP_EXE, "install", "waitress"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW)
        except Exception:
            pass
    if not os.path.exists(STREAMLIT_EXE):
        try:
            subprocess.run([PIP_EXE, "install", "streamlit"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW)
        except Exception:
            pass

    # Validar de nuevo y acumular errores si siguen faltando
    if not os.path.exists(WAITRESS_EXE):
        errors.append(f"No existe {WAITRESS_EXE}. Instala dependencias en .venv.")
    if not os.path.exists(STREAMLIT_EXE):
        errors.append(f"No existe {STREAMLIT_EXE}. Instala dependencias en .venv.")
    if not os.path.exists(CLOUDFLARED_EXE):
        errors.append(f"No existe {CLOUDFLARED_EXE}. Copia cloudflared.exe al proyecto.")
    if not os.path.exists(CF_CFG):
        errors.append(f"No existe {CF_CFG}. Crea/configura cloudflared.yml.")

    if errors:
        messagebox.showerror("Error de inicio", "\n".join(errors))
        return False

    try:
        # Flask con Waitress en 0.0.0.0:8000
        procs["flask"] = subprocess.Popen(
            [WAITRESS_EXE, "--host=0.0.0.0", "--port=8000", "app:app"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        # Streamlit en 0.0.0.0:8501
        procs["streamlit"] = subprocess.Popen(
            [STREAMLIT_EXE, "run", os.path.join(ROOT_DIR, "Zero.py"),
             "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        # Cloudflare Tunnel (ZERO)
        procs["cloudflared"] = subprocess.Popen(
            [CLOUDFLARED_EXE, "tunnel", "--config", CF_CFG, "run", "ZERO"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        notification.notify(
            title="ZERO Servidor",
            message="✅ Servidor activo: Flask, Streamlit y Tunnel corriendo.",
            timeout=5
        )
        return True
    except Exception as e:
        messagebox.showerror("Error al iniciar", str(e))
        return False

def stop_processes():
    # Terminar procesos si existen
    for name in ["cloudflared", "streamlit", "flask"]:
        p = procs.get(name)
        if p and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    # Forzar kill si siguen vivos
    for name in ["cloudflared", "streamlit", "flask"]:
        p = procs.get(name)
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass
    notification.notify(
        title="ZERO Servidor",
        message="🛑 Servidor detenido.",
        timeout=5
    )

# Control HTTP para celular
class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        token = (qs.get("token") or [""])[0]

        def ok(text):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(text.encode("utf-8"))

        def bad(text):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(text.encode("utf-8"))

        if parsed.path == "/status":
            status = {
                "flask": (procs["flask"] is not None and procs["flask"].poll() is None),
                "streamlit": (procs["streamlit"] is not None and procs["streamlit"].poll() is None),
                "cloudflared": (procs["cloudflared"] is not None and procs["cloudflared"].poll() is None),
            }
            return ok(json.dumps(status))
        elif parsed.path in ("/start", "/stop"):
            if token != CONTROL_TOKEN:
                return bad("Token inválido")
            if parsed.path == "/start":
                started = start_processes()
                return ok("start: " + ("ok" if started else "error"))
            else:
                stop_processes()
                return ok("stop: ok")
        else:
            self.send_response(404)
            self.end_headers()

def run_control_server():
    try:
        server = HTTPServer(("0.0.0.0", CONTROL_PORT), ControlHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
    except Exception as e:
        # No bloquear si falla; solo informar
        try:
            notification.notify(
                title="Control remoto",
                message=f"No se pudo iniciar control en {CONTROL_PORT}: {e}",
                timeout=5
            )
        except Exception:
            pass

# Interfaz de apagado
def detener_servidor():
    stop_processes()
    root.destroy()

# Servidor de control remoto (para celular) -> iniciar siempre
run_control_server()

# Iniciar procesos principales (no salir si falla; seguir con control)
started = start_processes()
# No hacer sys.exit(1); mostrar notificación si falla
if not started:
    try:
        notification.notify(
            title="ZERO Servidor",
            message="⚠️ Control activo, pero procesos no pudieron iniciar. Usa /start",
            timeout=5
        )
    except Exception:
        pass

# GUI mínima para apagar (local)
root = tk.Tk()
root.title("ZERO en ejecución")
root.geometry("260x140")
tk.Label(root, text="Servidor ejecutándose", font=("Arial", 12)).pack(pady=15)
tk.Button(root, text="Apagar Servidor", command=detener_servidor).pack()
tk.Label(root, text=f"Control: http://localhost:{CONTROL_PORT}", font=("Arial", 8)).pack(pady=10)
root.mainloop()