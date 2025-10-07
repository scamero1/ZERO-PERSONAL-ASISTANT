// Módulo para detectar inactividad y ejecutar una acción tras timeout (por defecto 2h).

import { exec } from 'child_process';

export type IdleOptions = {
	timeoutMs?: number; // tiempo de inactividad para cerrar sesión (por defecto 2h)
	onTimeout?: () => void; // callback a ejecutar al expirar el timeout
	runNativeLock?: boolean; // si true eyecta un comando nativo para bloquear/salir (Windows)
	nativeLockCmd?: string; // comando nativo opcional (overrides por defecto)
};

let timer: ReturnType<typeof setTimeout> | null = null;
let started = false;
let optsGlobal: IdleOptions = {};

function defaultNativeCmd() {
	// comando por defecto para Windows: bloquear estación de trabajo
	if (process.platform === 'win32') {
		// Usa rundll32 para bloquear
		return 'rundll32 user32.dll,LockWorkStation';
	}
	// macOS: lock screen
	if (process.platform === 'darwin') {
		return `osascript -e 'tell application "System Events" to keystroke "q" using {control down, command down}'`;
	}
	// Linux: intentar gnome-screensaver-command o loginctl lock-session
	return 'loginctl lock-session || gnome-screensaver-command -l || dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock';
}

function clearExistingTimer() {
	if (timer) {
		clearTimeout(timer);
		timer = null;
	}
}

function scheduleTimeout() {
	clearExistingTimer();
	const ms = optsGlobal.timeoutMs ?? 2 * 60 * 60 * 1000; // 2 horas por defecto
	timer = setTimeout(async () => {
		try {
			if (optsGlobal.onTimeout) {
				optsGlobal.onTimeout();
			}
			if (optsGlobal.runNativeLock) {
				const cmd = optsGlobal.nativeLockCmd ?? defaultNativeCmd();
				exec(cmd, (err) => {
					// Silenciar errores; el caller puede manejar logout desde onTimeout
				});
			}
		} finally {
			// Detener listeners tras timeout
			stopIdleLogout();
		}
	}, ms);
}

function activityHandler() {
	// Reinicia el temporizador en cualquier actividad
	if (!started) return;
	scheduleTimeout();
}

function visibilityHandler() {
	// Si la pestaña vuelve visible, reiniciamos timer
	if (document.visibilityState === 'visible') {
		activityHandler();
	}
}

export function startIdleLogout(options: IdleOptions = {}) {
	if (started) {
		// actualizar opciones y reiniciar timer
		optsGlobal = { ...optsGlobal, ...options };
		scheduleTimeout();
		return;
	}
	optsGlobal = { timeoutMs: 2 * 60 * 60 * 1000, ...options };
	started = true;

	// Escuchar eventos de actividad comunes
	if (typeof window !== 'undefined' && typeof document !== 'undefined') {
		window.addEventListener('mousemove', activityHandler, true);
		window.addEventListener('mousedown', activityHandler, true);
		window.addEventListener('keydown', activityHandler, true);
		window.addEventListener('touchstart', activityHandler, true);
		window.addEventListener('wheel', activityHandler, true);
		document.addEventListener('visibilitychange', visibilityHandler, true);
	}
	// Si estamos en entorno Node sin window, el caller debe llamar resetIdle manually.
	scheduleTimeout();
}

export function stopIdleLogout() {
	if (!started) return;
	started = false;
	clearExistingTimer();
	if (typeof window !== 'undefined' && typeof document !== 'undefined') {
		window.removeEventListener('mousemove', activityHandler, true);
		window.removeEventListener('mousedown', activityHandler, true);
		window.removeEventListener('keydown', activityHandler, true);
		window.removeEventListener('touchstart', activityHandler, true);
		window.removeEventListener('wheel', activityHandler, true);
		document.removeEventListener('visibilitychange', visibilityHandler, true);
	}
}

// Utility: permite reiniciar manualmente el temporizador (por ejemplo desde código)
// útil si detectas actividad a nivel de app y no del DOM.
export function resetIdleTimer() {
	if (!started) return;
	scheduleTimeout();
}

// Ejemplo de uso (en tu app):
// import { startIdleLogout } from './utils/idleLogout';
// startIdleLogout({
//   timeoutMs: 2 * 60 * 60 * 1000, // 2 horas
//   onTimeout: () => { /* cerrar sesión en tu app, limpiar credenciales, navegar a login */ },
//   runNativeLock: true // opcional: intenta bloquear la sesión del SO
// });
