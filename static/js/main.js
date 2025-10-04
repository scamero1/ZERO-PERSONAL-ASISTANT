// Estado global simple
let currentChatId = null;
let chatsCache = [];

// Utilidades de UI
function el(id) { return document.getElementById(id); }
function qs(selector) { return document.querySelector(selector); }
function qsa(selector) { return Array.from(document.querySelectorAll(selector)); }

function showSection(section) {
    const sections = {
        chat: el('chat-section'),
        files: el('files-section'),
        images: el('images-section'),
    };
    Object.values(sections).forEach(s => s.style.display = 'none');
    sections[section].style.display = 'block';
}

function createMessageBubble(role, content) {
    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'msg msg-user' : 'msg msg-assistant';

    const bubble = document.createElement('div');
    bubble.className = role === 'user' ? 'bubble bubble-user' : 'bubble bubble-assistant';
    bubble.textContent = content;

    wrapper.appendChild(bubble);
    return wrapper;
}

function scrollChatToEnd() {
    const container = el('chat-container');
    container.scrollTop = container.scrollHeight;
}

function setLoading(loading) {
    const sendBtn = el('send-btn');
    sendBtn.disabled = loading;
    sendBtn.textContent = loading ? '⏳' : '📤';
}

// Cargar lista de chats
async function loadChats() {
    try {
        const res = await fetch('/api/chats');
        if (!res.ok) return;

        const data = await res.json();
        chatsCache = data.chats || [];

        const list = el('chat-list');
        list.innerHTML = '';
        chatsCache.forEach(chat => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '#';
            a.className = 'chat-link';
            a.textContent = chat.title || chat.chat_id || 'Chat';
            a.addEventListener('click', (e) => {
                e.preventDefault();
                loadChatMessages(chat.chat_id || chat.id);
            });
            li.appendChild(a);
            list.appendChild(li);
        });
    } catch (err) {
        console.warn('No se pudo cargar chats:', err);
    }
}

// Cargar mensajes de un chat
async function loadChatMessages(chatId) {
    if (!chatId) return;
    try {
        const res = await fetch(`/api/chat/${encodeURIComponent(chatId)}`);
        if (!res.ok) return;

        const data = await res.json();
        currentChatId = data.chat_id || chatId;

        const container = el('chat-container');
        container.innerHTML = '';

        // Mensaje de bienvenida solo si el chat está vacío
        const msgs = data.messages || [];
        if (msgs.length === 0) {
            renderWelcome();
        } else {
            msgs.forEach(m => {
                const role = (m.role || '').toLowerCase();
                const content = m.content || '';
                container.appendChild(createMessageBubble(role, content));
            });
            scrollChatToEnd();
        }
        showSection('chat');
    } catch (err) {
        console.warn('No se pudo cargar mensajes:', err);
    }
}

// Render de bienvenida
function renderWelcome() {
    const container = el('chat-container');
    container.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">⚡</div>
            <h2>Bienvenido a ZERO</h2>
            <p>Asistente de IA avanzado con capacidades de análisis de documentos,<br>
            procesamiento de imágenes y soporte para ecuaciones matemáticas.</p>
            <div class="feature-cards">
                <div class="feature-card">
                    <div class="feature-icon">💬</div>
                    <div class="feature-title">Chat Inteligente</div>
                    <div class="feature-desc">Conversaciones naturales y contextuales</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📁</div>
                    <div class="feature-title">Análisis de Archivos</div>
                    <div class="feature-desc">Procesa documentos e imágenes</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🧮</div>
                    <div class="feature-title">Soporte Matemático</div>
                    <div class="feature-desc">Ecuaciones y análisis avanzado</div>
                </div>
            </div>
        </div>
    `;
}

// Enviar mensaje al backend
async function sendMessage(text) {
    setLoading(true);
    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: text, chat_id: currentChatId })
        });

        const data = await res.json();
        if (res.status === 401) {
            alert('No autenticado. Por favor inicia sesión.');
            return;
        }
        if (data.error) {
            alert(data.error);
            return;
        }

        // Actualizar chat_id para conservar el hilo
        currentChatId = data.chat_id || currentChatId;

        // Render respuesta del asistente
        el('chat-container').appendChild(createMessageBubble('assistant', data.response));
        scrollChatToEnd();

        // Refrescar lista de chats
        loadChats();
    } catch (err) {
        console.error('Error al enviar mensaje:', err);
        alert('Error al enviar el mensaje.');
    } finally {
        setLoading(false);
    }
}

// Subir y analizar documento/imagen
async function uploadAndAnalyze(file) {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);

    // Muestra indicador simple en chat
    const container = el('chat-container');
    const uploading = document.createElement('div');
    uploading.className = 'bubble bubble-assistant';
    uploading.textContent = `Analizando "${file.name}"...`;
    container.appendChild(uploading);
    scrollChatToEnd();

    try {
        const res = await fetch('/api/analyze-document', {
            method: 'POST',
            body: form
        });
        const data = await res.json();

        if (!data.success && data.error) {
            alert(data.error);
            return;
        }

        const analysisText = data.analysis || `Archivo "${file.name}" procesado.`;
        container.appendChild(createMessageBubble('assistant', analysisText));
        scrollChatToEnd();

        // Refrescar chats por si se guardó contexto
        loadChats();
    } catch (err) {
        console.error('Error analizando documento:', err);
        alert('Error analizando el archivo.');
    } finally {
        uploading.remove();
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    // Navegación de herramientas
    qsa('.tool-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tool = link.dataset.tool;
            showSection(tool);
        });
    });

    // Nuevo chat
    const newChatBtn = qs('.new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            currentChatId = null;
            el('chat-container').innerHTML = '';
            renderWelcome();
            showSection('chat');
        });
    }

    // Envío del formulario de chat
    const chatForm = el('chat-form');
    const chatInput = el('chat-input');
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = (chatInput.value || '').trim();
        if (!text) return;

        // Render mensaje del usuario
        el('chat-container').appendChild(createMessageBubble('user', text));
        scrollChatToEnd();

        // Limpiar y enviar
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendMessage(text);
    });

    // Auto-expand del textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = `${chatInput.scrollHeight}px`;
    });

    // Botón subir archivo en sección chat
    const uploadBtn = el('upload-btn');
    const fileUploadInput = el('file-upload');
    uploadBtn.addEventListener('click', () => fileUploadInput.click());
    fileUploadInput.addEventListener('change', () => {
        const file = fileUploadInput.files[0];
        if (file) {
            showSection('chat');
            uploadAndAnalyze(file);
        }
        fileUploadInput.value = '';
    });

    // Sección archivos: botón grande
    const fileUploadArea = el('file-upload-area');
    const uploadBtnLarge = qs('.upload-btn-large');
    uploadBtnLarge.addEventListener('click', () => fileUploadArea.click());
    fileUploadArea.addEventListener('change', () => {
        const file = fileUploadArea.files[0];
        if (file) {
            showSection('files');
            uploadAndAnalyze(file);
        }
        fileUploadArea.value = '';
    });

    // Sección imágenes: preview y analizar
    const imageUpload = el('image-upload');
    const previewContainer = el('image-preview-container');
    const previewImage = el('preview-image');
    const analyzeImageBtn = el('analyze-image-btn');

    imageUpload.addEventListener('change', () => {
        const file = imageUpload.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
    });

    analyzeImageBtn.addEventListener('click', () => {
        const file = imageUpload.files[0];
        if (file) {
            showSection('images');
            uploadAndAnalyze(file);
        } else {
            alert('Primero selecciona una imagen.');
        }
    });

    // Estado inicial
    renderWelcome();
    showSection('chat');
    loadChats();
});