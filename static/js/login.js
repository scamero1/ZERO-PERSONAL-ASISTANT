// Función para crear el efecto de lluvia de matriz
function createMatrixRain() {
    const container = document.getElementById('matrixRain');
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    const charCount = Math.floor(window.innerWidth / 20);
    
    for (let i = 0; i < charCount; i++) {
        const char = document.createElement('div');
        char.className = 'code-char';
        char.textContent = chars[Math.floor(Math.random() * chars.length)];
        
        const left = Math.random() * 100;
        const delay = Math.random() * 10;
        const duration = Math.random() * 5 + 3;
        
        char.style.left = left + '%';
        char.style.animationDelay = delay + 's';
        char.style.animationDuration = duration + 's';
        char.style.opacity = Math.random() * 0.5 + 0.1;
        
        container.appendChild(char);
    }
}

// Crear efecto de lluvia de matriz al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    createMatrixRain();
    
    // Botones de selección de método de login
    const btnPassword = document.getElementById('btn-password');
    const btnNfc = document.getElementById('btn-nfc');
    const btnQuickAccess = document.getElementById('btn-quick-access');
    const passwordLogin = document.getElementById('password-login');
    const nfcLogin = document.getElementById('nfc-login');
    const quickAccess = document.getElementById('quick-access');
    const backFromPassword = document.getElementById('back-from-password');
    const backFromNfc = document.getElementById('back-from-nfc');
    const backFromQuick = document.getElementById('back-from-quick');
    const startScan = document.getElementById('start-scan');
    const abortScan = document.getElementById('abort-scan');
    const scanStatus = document.getElementById('scan-status');
    const cyberSelector = document.querySelector('.cyber-selector');
    const warningMessage = document.querySelector('.warning-message');
    
    // Mostrar login con contraseña
    if (btnPassword) {
        btnPassword.addEventListener('click', function() {
            cyberSelector.style.display = 'none';
            warningMessage.style.display = 'none';
            passwordLogin.style.display = 'block';
        });
    }
    
    // Mostrar login con NFC
    if (btnNfc) {
        btnNfc.addEventListener('click', function() {
            cyberSelector.style.display = 'none';
            warningMessage.style.display = 'none';
            nfcLogin.style.display = 'block';
        });
    }
    
    // Mostrar acceso rápido por usuario
    if (btnQuickAccess) {
        btnQuickAccess.addEventListener('click', function() {
            cyberSelector.style.display = 'none';
            warningMessage.style.display = 'none';
            quickAccess.style.display = 'block';
        });
    }
    
    // Volver desde login con contraseña
    if (backFromPassword) {
        backFromPassword.addEventListener('click', function() {
            passwordLogin.style.display = 'none';
            cyberSelector.style.display = 'grid';
            warningMessage.style.display = 'block';
        });
    }
    
    // Volver desde login con NFC
    if (backFromNfc) {
        backFromNfc.addEventListener('click', function() {
            nfcLogin.style.display = 'none';
            cyberSelector.style.display = 'grid';
            warningMessage.style.display = 'block';
            scanStatus.style.display = 'none';
        });
    }
    
    // Volver desde acceso rápido
    if (backFromQuick) {
        backFromQuick.addEventListener('click', function() {
            quickAccess.style.display = 'none';
            cyberSelector.style.display = 'grid';
            warningMessage.style.display = 'block';
        });
    }
    
    // Botones de usuario para acceso rápido
    const userButtons = document.querySelectorAll('.user-button');
    if (userButtons.length > 0) {
        userButtons.forEach(button => {
            button.addEventListener('click', function() {
                const user = this.getAttribute('data-user');
                // Crear un formulario y enviarlo automáticamente
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/login';
                
                // Agregar campo de usuario
                const userInput = document.createElement('input');
                userInput.type = 'hidden';
                userInput.name = 'usuario';
                userInput.value = user;
                form.appendChild(userInput);
                
                // Agregar campo de clave (vacío para acceso rápido)
                const passInput = document.createElement('input');
                passInput.type = 'hidden';
                passInput.name = 'clave';
                passInput.value = 'acceso_rapido';
                form.appendChild(passInput);
                
                // Agregar al documento y enviar
                document.body.appendChild(form);
                form.submit();
            });
        });
    }
    
    // Iniciar escaneo NFC
    if (startScan) {
        startScan.addEventListener('click', function() {
            scanStatus.style.display = 'block';
            
            // Simulación de escaneo NFC (en una aplicación real, esto se conectaría con el backend)
            setTimeout(function() {
                // Aquí se haría una petición al backend para leer el NFC
                fetch('/api/nfc-scan', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = '/';
                    } else {
                        scanStatus.innerHTML = `<p style="color: #ff0080;">🚫 ${data.error || 'Error en el escaneo'}</p>`;
                        setTimeout(() => {
                            scanStatus.style.display = 'none';
                            scanStatus.innerHTML = `
                                <div class="spinner"></div>
                                <p>🔍 SCANNING BIOMETRIC SIGNATURE...</p>
                            `;
                        }, 3000);
                    }
                })
                .catch(error => {
                    scanStatus.innerHTML = `<p style="color: #ff0080;">🚫 Error de conexión</p>`;
                    setTimeout(() => {
                        scanStatus.style.display = 'none';
                        scanStatus.innerHTML = `
                            <div class="spinner"></div>
                            <p>🔍 SCANNING BIOMETRIC SIGNATURE...</p>
                        `;
                    }, 3000);
                });
            }, 2000);
        });
    }
    
    // Abortar escaneo NFC
    if (abortScan) {
        abortScan.addEventListener('click', function() {
            scanStatus.style.display = 'none';
        });
    }
});