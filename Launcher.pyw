import subprocess
import os
import tkinter as tk
from tkinter import messagebox
from plyer import notification
import json

# Verifica el JSON
try:
    with open("usuarios.json") as f:
        json.load(f)
except Exception as e:
    messagebox.showerror("Error", f"Archivo JSON inválido: {e}")
    exit()

# Rutas
cloudflared_path = os.path.expanduser(r"C:\Program Files (x86)\cloudflared\cloudflared.exe")
streamlit_path = "streamlit"
script_path = "zero.py"

# Bandera para ocultar consola en Windows
CREATE_NO_WINDOW = 0x08000000

# Ejecuta los procesos SIN ventana visible
subprocess.Popen([cloudflared_path, "tunnel", "run", "zero"],
                 stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL,
                 creationflags=CREATE_NO_WINDOW)

subprocess.Popen([streamlit_path, "run", script_path],
                 stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL,
                 creationflags=CREATE_NO_WINDOW)

# Notificación
notification.notify(
    title="ZERO Servidor",
    message="✅ Servidor iniciado automáticamente.",
    timeout=5
)

# Interfaz solo para apagar
def detener_servidor():
    os.system("taskkill /f /im streamlit.exe >nul 2>&1")
    os.system("taskkill /f /im cloudflared.exe >nul 2>&1")
    notification.notify(
        title="ZERO Servidor",
        message="🛑 Servidor detenido.",
        timeout=5
    )
    root.destroy()

root = tk.Tk()
root.title("ZERO en ejecución")
root.geometry("250x120")
tk.Label(root, text="Servidor ejecutándose", font=("Arial", 12)).pack(pady=15)
tk.Button(root, text="Detener Servidor", command=detener_servidor).pack()
root.mainloop()