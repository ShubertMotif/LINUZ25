import tkinter as tk
import serial
import threading
import time


class SensorGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("STWIN - Temp & Humidity")
        self.window.geometry("400x200")

        # Labels
        tk.Label(self.window, text="Temperatura:", font=("Arial", 16)).pack(pady=10)
        self.temp_label = tk.Label(self.window, text="-- °C", font=("Arial", 24, "bold"))
        self.temp_label.pack()

        tk.Label(self.window, text="Umidità:", font=("Arial", 16)).pack(pady=10)
        self.hum_label = tk.Label(self.window, text="-- %", font=("Arial", 24, "bold"))
        self.hum_label.pack()

        # Seriale
        self.ser = None
        self.running = True

    def connect(self, port='COM3', baud=115200):
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            print(f"Connesso a {port}")
        except:
            print(f"Errore connessione {port}")

    def read_data(self):
        while self.running:
            if self.ser and self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8').strip()
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) == 2:
                        temp = parts[0]
                        hum = parts[1]
                        self.temp_label.config(text=f"{temp} °C")
                        self.hum_label.config(text=f"{hum} %")
            time.sleep(0.1)

    def run(self, port='COM3'):
        self.connect(port)
        thread = threading.Thread(target=self.read_data, daemon=True)
        thread.start()
        self.window.mainloop()
        self.running = False


if __name__ == "__main__":
    gui = SensorGUI()
    gui.run('COM3')  # Cambia COM3 con la tua porta