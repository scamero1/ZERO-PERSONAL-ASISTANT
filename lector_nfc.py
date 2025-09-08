import serial
import time

def leer_uid_pn532(puerto='COM4', baudios=9600):
    try:
        with serial.Serial(puerto, baudios, timeout=5) as ser:
            time.sleep(2)
            ser.reset_input_buffer()
            linea = ser.readline().decode('utf-8').strip()
            if linea.startswith("UID:"):
                return linea.replace("UID:", "").strip().upper()
    except Exception as e:
        print("Error leyendo UID:", e)
    return None