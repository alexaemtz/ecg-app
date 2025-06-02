import customtkinter as ctk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import threading
import time
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import csv
from PIL import Image
from CTkToolTip import *

class CsvLoaderGUI(ctk.CTkFrame):
    def __init__(self, parent, sampling_rate=250, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.sampling_rate = sampling_rate
        self.window_duration = 5
        self.current_index = 0
        self.signal_data = []
        self.filtered_data = []
        self.annotations = []
        
        self.title_font = ctk.CTkFont(family="Poppins SemiBold", size=24)
        self.subtitle_font = ctk.CTkFont(family="Poppins Medium Italic", size=14)
        self.text_font = ctk.CTkFont(family="Poppins Medium", size=14)

        self.start_selection = None
        self.end_selection = None
        
        self.load_button_image = ctk.CTkImage(Image.open("assets/icons/upload.png"))
        self.load_button = ctk.CTkButton(self, text="Seleccionar archivo CSV", command=self.load_csv, image=self.load_button_image, font=self.text_font, compound="left")
        self.load_button.pack(pady=10)
        
        self.load_tooltip = CTkToolTip(self.load_button, delay=1, message="Elige un archivo CSV con los datos de la señal ECG.")
        
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(pady=10, fill="x")
        
        self.pause_button_image = ctk.CTkImage(Image.open("assets/icons/pause.png"))
        self.pause_button = ctk.CTkButton(self.control_frame, text="Pausar", command=self.toggle_animation, image=self.pause_button_image, font=self.text_font, compound="left")
        self.pause_button.pack(side="left", padx=5)

        self.start_entry = ctk.CTkEntry(self.control_frame, placeholder_text="Inicio (s)", width=100)
        self.start_entry.pack(side="left", padx=5)
        self.end_entry = ctk.CTkEntry(self.control_frame, placeholder_text="Fin (s)", width=100)
        self.end_entry.pack(side="left", padx=5)
        
        self.analyze_button_image = ctk.CTkImage(Image.open("assets/icons/search.png"))
        self.analyze_button = ctk.CTkButton(self.control_frame, text="Analizar", command=self.analyze_segment, image=self.analyze_button_image, font=self.text_font, compound="left")
        self.analyze_button.pack(side="left", padx=5)
        
        self.analyze_tooltip = CTkToolTip(self.analyze_button, delay=1, message="Obtiene las características (mínimo, máximo, media, desv. estándar) del segmento de tiempo seleccionado.")

        self.filter_button_image = ctk.CTkImage(Image.open("assets/icons/filter.png"))
        self.filter_button = ctk.CTkButton(self.control_frame, text="Filtrar señal", command=self.apply_filters, image=self.filter_button_image, font=self.text_font, compound="left")
        self.filter_button.pack(side="left", padx=5)
        
        self.filter_tooltip = CTkToolTip(self.filter_button, delay=1, message="Aplica filtros de banda y de banda de corte para reducir ruidos y mejorar la señal ECG.")

        self.normalize_button_image = ctk.CTkImage(Image.open("assets/icons/norm.png"))
        self.normalize_button = ctk.CTkButton(self.control_frame, text="Normalizar y detectar picos R", command=self.normalize_and_detect_r, image=self.normalize_button_image, font=self.text_font, compound="left")
        self.normalize_button.pack(side="left", padx=5)
        
        self.normalize_tooltip = CTkToolTip(self.normalize_button, delay=1, message="Calcula el valor máximo de la señal ECG y divide por él para normalizar la señal.")

        self.stats_label = ctk.CTkLabel(self, text="", justify="left")
        self.stats_label.pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.ax.set_title("Señal ECG")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel("Amplitud")
        self.line, = self.ax.plot([], [], lw=1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(pady=10, fill="both", expand=True)

        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("button_release_event", self.on_release)

        # Anotación
        self.annotation_frame = ctk.CTkFrame(self)
        self.annotation_frame.pack(pady=10, fill="x")

        self.label_option = ctk.CTkOptionMenu(self.annotation_frame, values=["NSR", "AF", "AFL", "APB", "PVC", "Otro", "??"])
        self.label_option.set("NSR")
        self.label_option.pack(side="left", padx=5)

        self.save_annotation_button_image = ctk.CTkImage(Image.open("assets/icons/pen.png"))
        self.save_annotation_button = ctk.CTkButton(self.annotation_frame, text="Anotar", command=self.save_annotation, font=self.text_font, compound="left")
        self.save_annotation_button.pack(side="left", padx=5)
        
        self.save_annotation_tooltip = CTkToolTip(self.save_annotation_button, delay=1, message="Realiza anotaciones en la señal y guarda en un archivo CSV.")

        self.animating = False

    def load_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
            column = df.columns[0]
            self.signal_data = df[column].values
            self.filtered_data = self.signal_data.copy()
            self.current_index = 0
            self.animating = True

            self.ax.set_xlim(0, self.window_duration)
            self.ax.set_ylim(min(self.signal_data), max(self.signal_data))
            threading.Thread(target=self.animate_plot, daemon=True).start()
        except Exception as e:
            print("Error al cargar CSV:", e)

    def animate_plot(self):
        while self.animating and self.current_index + self.window_duration * self.sampling_rate < len(self.filtered_data):
            start = self.current_index
            end = start + self.window_duration * self.sampling_rate
            x_data = [i / self.sampling_rate for i in range(start, end)]
            y_data = self.filtered_data[start:end]

            self.line.set_data(x_data, y_data)
            self.ax.set_xlim(x_data[0], x_data[-1])
            self.ax.set_ylim(min(y_data), max(y_data))
            self.canvas.draw()
            self.current_index += 1
            time.sleep(0.01)

    def toggle_animation(self):
        self.animating = not self.animating
        self.pause_button.configure(text="▶ Reanudar" if not self.animating else "⏸ Pausar")
        if self.animating:
            threading.Thread(target=self.animate_plot, daemon=True).start()

    def analyze_segment(self):
        try:
            start_sec = float(self.start_entry.get())
            end_sec = float(self.end_entry.get())
            self.start_idx = int(start_sec * self.sampling_rate)
            self.end_idx = int(end_sec * self.sampling_rate)
            segment = self.filtered_data[self.start_idx:self.end_idx]

            if len(segment) == 0:
                self.stats_label.configure(text="⚠️ Rango vacío.")
                return

            stats = {
                "Mínimo": np.min(segment),
                "Máximo": np.max(segment),
                "Media": np.mean(segment),
                "Desv. Estándar": np.std(segment)
            }

            stats_text = "\n".join([f"{k}: {v:.2f}" for k, v in stats.items()])
            self.stats_label.configure(text=f"📊 Características del segmento:\n{stats_text}")

            x_data = [i / self.sampling_rate for i in range(self.start_idx, self.end_idx)]
            self.line.set_data(x_data, segment)
            self.ax.set_xlim(x_data[0], x_data[-1])
            self.ax.set_ylim(min(segment), max(segment))
            self.canvas.draw()

        except Exception as e:
            self.stats_label.configure(text=f"Error al analizar: {e}")

    def apply_filters(self):
        try:
            nyq = 0.5 * self.sampling_rate
            low = 0.5 / nyq
            high = 40 / nyq
            b, a = butter(2, [low, high], btype='band')
            notch_freq = 60.0
            q = 30.0
            b_notch, a_notch = butter(2, [notch_freq - 1, notch_freq + 1], btype='bandstop', fs=self.sampling_rate)
            temp = filtfilt(b, a, self.signal_data)
            self.filtered_data = filtfilt(b_notch, a_notch, temp)
            self.current_index = 0
            self.animating = True
            threading.Thread(target=self.animate_plot, daemon=True).start()
        except Exception as e:
            self.stats_label.configure(text=f"Error al filtrar: {e}")

    def normalize_and_detect_r(self):
        try:
            # Normalización de la señal
            norm = (self.filtered_data - np.min(self.filtered_data)) / (np.max(self.filtered_data) - np.min(self.filtered_data))

            # Detección de picos R
            peaks, _ = find_peaks(norm, distance=0.2*self.sampling_rate, height=0.5)

            # Calcular BPM
            time_between_peaks = np.diff(peaks) / self.sampling_rate  # Intervalos entre picos R en segundos
            bpm = 60 / np.mean(time_between_peaks) if len(time_between_peaks) > 0 else 0  # Promedio de los intervalos convertidos a BPM

            # Mostrar BPM en la interfaz
            self.stats_label.configure(text=f"🫀 BPM estimado: {bpm:.2f} BPM")

            # Graficar la señal normalizada y los picos R
            self.ax.clear()
            self.ax.plot(np.arange(len(norm)) / self.sampling_rate, norm, label="Normalizado")
            self.ax.plot(peaks / self.sampling_rate, norm[peaks], "rx", label="Picos R")
            self.ax.set_title("Normalización + Picos R")
            self.ax.set_xlabel("Tiempo (s)")
            self.ax.set_ylabel("Amplitud")
            self.ax.legend()
            self.canvas.draw()
            
        except Exception as e:
            self.stats_label.configure(text=f"Error en picos R: {e}")

    def on_press(self, event):
        if event.inaxes != self.ax:
            return
        self.start_selection = event.xdata

    def on_release(self, event):
        if event.inaxes != self.ax:
            return
        self.end_selection = event.xdata
        self.ax.axvspan(self.start_selection, self.end_selection, color='orange', alpha=0.3)
        self.canvas.draw()

    def save_annotation(self):
        if self.start_selection is None or self.end_selection is None:
            self.stats_label.configure(text="❌ Selecciona un intervalo sobre la gráfica primero.")
            return

        etiqueta = self.label_option.get()
        start_time = min(self.start_selection, self.end_selection)
        end_time = max(self.start_selection, self.end_selection)

        self.annotations.append({
            "Inicio (s)": start_time,
            "Fin (s)": end_time,
            "Etiqueta": etiqueta
        })

        # Guardar en CSV
        with open("anotaciones.csv", "w", newline="") as csvfile:
            fieldnames = ["Inicio (s)", "Fin (s)", "Etiqueta"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.annotations)

        self.stats_label.configure(text=f"✅ Anotación guardada: {etiqueta} [{start_time:.2f}s - {end_time:.2f}s]")

