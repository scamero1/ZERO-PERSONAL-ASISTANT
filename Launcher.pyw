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
flask_app_path = "app.py"
python_path = r"C:\Users\Camero\AppData\Local\Programs\Python\Python313\python.exe"

# Bandera para ocultar consola en Windows
CREATE_NO_WINDOW = 0x08000000

# Ejecuta el proceso Flask SIN ventana visible
flask_process = subprocess.Popen([python_path, flask_app_path],
                 stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL,
                 creationflags=CREATE_NO_WINDOW)

# Notificación
notification.notify(
    title="ZERO Servidor",
    message="✅ Servidor iniciado automáticamente en http://localhost:8000",
    timeout=5
)

# Interfaz solo para apagar
def detener_servidor():
    if flask_process.poll() is None:  # Si el proceso sigue en ejecución
        flask_process.terminate()
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