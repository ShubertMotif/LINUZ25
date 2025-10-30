from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import serial
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Dati globali
sensor_data = {'temp': 0, 'hum': 0, 'timestamp': 0}
running = True


def read_serial():
    try:
        ser = serial.Serial('COM3', 115200, timeout=1)
        print("✅ Connesso a COM3")
    except:
        print("❌ Errore COM3")
        return

    while running:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            print(f"📡 Ricevuto: {line}")

            # Parse "Temp: 25.3,Hum: 60.5"
            if 'Temp:' in line and 'Hum:' in line:
                parts = line.split(',')
                temp = parts[0].split(':')[1].strip()
                hum = parts[1].split(':')[1].strip()

                sensor_data['temp'] = float(temp)
                sensor_data['hum'] = float(hum)
                sensor_data['timestamp'] = time.time()

                # Invia via WebSocket
                socketio.emit('sensor_update', sensor_data)

        time.sleep(0.1)


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/data')
def get_data():
    return jsonify(sensor_data)


if __name__ == '__main__':
    thread = threading.Thread(target=read_serial, daemon=True)
    thread.start()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)