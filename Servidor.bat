@echo off
setlocal

REM Ir al directorio del script
cd /d "%~dp0"

REM Activar venv si existe (opcional)
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [INFO] No se encontró venv. Usando Python del sistema.
)

REM Variables para Flask
set FLASK_APP=app.py
set FLASK_ENV=production

REM Iniciar Flask en puerto 8000
echo [INFO] Iniciando Flask en http://localhost:8000/
start "Flask - ZERO" cmd /c "py -3 -m flask run --host=127.0.0.1 --port=8000"

REM Iniciar Streamlit en puerto 8501
echo [INFO] Iniciando Streamlit en http://localhost:8501/
start "Streamlit - ZERO" cmd /c "py -3 -m streamlit run Zero.py --server.port 8501 --server.address 127.0.0.1"

REM Abrir el navegador en el login
timeout /t 3 /nobreak >nul
start "" "http://localhost:8000/"

endlocal