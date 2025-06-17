import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import time
import itertools
import serial
import serial.tools.list_ports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, filtfilt, iirnotch, sosfilt, sosfiltfilt, lfilter, tf2sos
from PIL import Image
import datetime
import csv
from scipy.signal import find_peaks
import socket
import struct
from CTkToolTip import *

plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Tahoma', 'DejaVu Sans',
                               'Lucida Grande', 'Verdana']

class ComunicationGUI(ctk.CTkFrame):
    def __init__(self, root, host='XXX.XXXX.XXX.X', port=5000):
        """Constructur de la ventana de comunicación"""
        super().__init__(master=root, border_width=1, border_color="white", corner_radius=10)
        self.pack(padx=10, pady=10, anchor="nw", fill="both", expand=True)

        self.bpm_font = ctk.CTkFont(family="Poppins SemiBold", size=60)
        self.subtitle_font = ctk.CTkFont(family="Poppins Medium", size=18)
        self.label_font = ctk.CTkFont(family="Poppins Medium Italic", size=14)
        self.text_font = ctk.CTkFont(family="Poppins Medium", size=14)
        self.icon_size = (32, 32)

        self.main_layout = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        self.main_layout.pack(fill="both", expand=True)
        
        self.host = host
        self.port = int(port)
        self.client_socket = None
        self.device_id = 1
        self.fs = 300  # Sampling frequency in Hz
        self.sending_ecg = False
        self.ecg_socket = None

        # ---------- Configuración de puerto COM y Baud rate ----------
        top_frame = ctk.CTkFrame(self.main_layout, fg_color="transparent")
        top_frame.pack(pady=10, padx=10, anchor="w")

        com_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        com_frame.pack(side="left", padx=5)

        self.label_com = ctk.CTkLabel(com_frame, text="Dispositivo:", anchor="w", font=self.label_font)
        self.label_com.pack(side="left", padx=(10, 5))

        self.com_port_combobox = ctk.CTkComboBox(com_frame, values=[], width=150, height=30, font=self.text_font)
        self.com_port_combobox.pack(side="left", padx=(5, 10))

        self.icon_refresh = ctk.CTkImage(Image.open("assets/icons/refresh.png"), size=self.icon_size)
        self.refresh_button = ctk.CTkButton(com_frame, text="Actualizar", command=self.refresh_com_ports, width=80, height=30, font=self.text_font, image=self.icon_refresh)
        self.refresh_button.pack(side="left", padx=(5, 10))

        baud_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        baud_frame.pack(side="left", padx=5)

        #self.label_baud = ctk.CTkLabel(baud_frame, text="Baud rate:", anchor="w", font=self.label_font)
        #self.label_baud.pack(side="left", padx=(10, 5))

        #self.baud_options = ["9600", "19200", "38400", "57600", "115200"]
        #self.baud_combobox = ctk.CTkComboBox(baud_frame, values=self.baud_options, width=130, height=30, font=self.text_font)
        #self.baud_combobox.set("115200")
        #self.baud_combobox.pack(side="left", padx=(5, 10))

        #self.info_button_image = ctk.CTkImage(Image.open("assets/icons/info.png"), size=self.icon_size)
        #self.info_button = ctk.CTkButton(baud_frame, text=" ", width=10, height=10, command=self.show_baud_info, font=self.text_font, image=self.info_button_image, corner_radius=10)
        #self.info_button.pack(side="left", padx=(5, 10))

        self.icon_begin_device = ctk.CTkImage(Image.open("assets/icons/connect.png"), size=self.icon_size)
        self.begin_device_button = ctk.CTkButton(baud_frame, text="Iniciar Dispositivo", command=self.begin_device, width=80, height=30, font=self.text_font, image=self.icon_begin_device)
        self.begin_device_button.pack(side="left", padx=(5, 10))
        
        self.icon_disconnect = ctk.CTkImage(Image.open("assets/icons/unlink.png"), size=self.icon_size)
        self.disconnect_button = ctk.CTkButton(baud_frame, text="Desconectar", command=self.disconnect_com_port, width=80, height=30, font=self.text_font, image=self.icon_disconnect)
        self.disconnect_button.pack(side="left", padx=(5, 10))
        
        self.refresh_com_ports()

        # ---------- Gráfico ----------
        self.graph_frame = ctk.CTkFrame(self.main_layout, corner_radius=10)
        self.graph_frame.pack(pady=10, padx=10, fill="x", expand=False)

        self.arduino = None
        self.streaming = False
        self.ani = None
        # self.saving_data = False
        self.animation_running = False  
        
        # Variables para el guardado continuo de datos
        self.continuos_recording = False
        self.recording_data = []
        self.recording_data_filtered = []
        self.recording_start_time = None

        # Variables para buffer circular
        self.buffer_size =  1000
        self.current_index = 0
        self.buffer_full = False
        
        # Variables para visualizar en tiempo real
        self.display_buffer_size = 1000 # Tamaño del buffer de visualización
        self.display_index = 0 # Indice actual en el display
        self.clearing_window = 15
        self.y_display_data = [0] * self.display_buffer_size
        
        # Crear un frame contenedor para la gráfica y el BPM
        self.plot_container = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        self.plot_container.pack(pady=10, fill="both", expand=True)
        
        # Frame para la gráfica
        self.plot_frame = ctk.CTkFrame(self.plot_container, fg_color="transparent")
        self.plot_frame.pack(side="left", fill="both", expand=True)
        
        # Frame para el BPM a la derecha
        self.bpm_frame = ctk.CTkFrame(self.plot_container, fg_color="transparent", width=250)
        self.bpm_frame.pack(side="right", fill="y", padx=(10, 0))
        self.bpm_frame.pack_propagate(False)  # Mantener el ancho fijo
        
        self.fig, self.ax = plt.subplots(figsize=(11, 7))
        
        # Inicializar arrays con el tamaño del buffer
        self.x_data = list(range(self.buffer_size))  # Eje X fijo de 0 a 199
        self.x_display = list(range(self.display_buffer_size)) # Para visualización
        self.y_data_raw = [0] * self.buffer_size  # Buffer circular para datos crudos
        self.y_data_filtered = [0] * self.buffer_size  # Buffer circular para datos filtrados
        self.y_display_data = [0] * self.display_buffer_size # Buffer para visualización
        
        # Buffer temporal para aplicar filtros (mantiene historial completo)
        self.temp_raw_buffer = []

        # Línea principal del ECG
        self.line_filtered, = self.ax.plot(self.x_data, self.y_data_filtered, label="Señal ECG", color='limegreen', linewidth=2)
        
        # Línea de limpieza
        self.clearing_line, = self.ax.plot([], [], color='#040b14', linewidth=4, alpha=0.1)
        
        # Línea del cursor/indicador de posición actual
        # self.cursor_line, = self.ax.plot([], [], color='red', linewidth=2, alpha=0.8) # Remover cursor

        self.ax.set_title("Monitor ECG - 1D Pro", fontsize=18)
        self.ax.set_xlabel("Muestras", fontsize=14)
        self.ax.set_ylabel("Amplitud (V)", fontsize=14)
        self.ax.set_xlim(0, self.buffer_size - 1)  # Eje X fijo
        self.ax.legend(loc="upper right")
        self.ax.set_facecolor("#040b14")  # Fondo del gráfico
        
        # Configuración de la cuadrícula estilo ECG
        self.ax.set_ylim(-2.2, 2.2)  # Rango completo del ADS1115 con GAIN_TWOTHIRDS

        # Líneas principales (cada 0.5 mV = 0.0005 V)
        self.ax.set_yticks(np.arange(-2.1, 2.1, 0.5))  # Marcas principales cada 0.5V
        self.ax.grid(which='major', color='springgreen', linestyle='-', linewidth=0.8, alpha=0.3)

        # Líneas secundarias (cada 0.1 mV = 0.0001 V)
        self.ax.set_yticks(np.arange(-2.1, 2.1, 0.1), minor=True)  # Marcas menores cada 0.1V
        self.ax.grid(which='minor', color='springgreen', linestyle=':', linewidth=0.3, alpha=0.2)

        # Configuración para el eje X (cada 10 muestras)
        self.ax.set_xticks(np.arange(0, self.buffer_size, 50))  # Marcas principales cada 50 muestras
        self.ax.set_xticks(np.arange(0, self.buffer_size, 10), minor=True)  # Marcas menores cada 10 muestras

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(pady=10)
        
         # ---------- Controles ----------
        self.control_frame = ctk.CTkFrame(self.main_layout, fg_color="transparent")
        self.control_frame.pack(pady=10, padx=10, anchor="w", fill="x")
        
        # Frame interno para centrar los botones horizontalmente
        self.buttons_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.buttons_frame.pack(anchor="center")  # Este centra los botones dentro de control_frame

        self.icon_start = ctk.CTkImage(Image.open("assets/icons/play.png"), size=self.icon_size)
        self.start_button = ctk.CTkButton(self.buttons_frame, text="", command=self.start_animation, font=self.text_font, image=self.icon_start, width=50)
        self.start_button.pack(side="left", padx=10)
        
        self.start_tooltip = CTkToolTip(self.start_button, delay=0.5, message="Inicia la lectura de datos.", text=self.text_font)

        self.icon_pause = ctk.CTkImage(Image.open("assets/icons/pause.png"), size=self.icon_size)
        self.pause_button = ctk.CTkButton(self.buttons_frame, text="", command=self.pause_animation, font=self.text_font, image=self.icon_pause, width=50)
        self.pause_button.pack(side="left", padx=10)
        
        self.pause_tooltip = CTkToolTip(self.pause_button, delay=0.5, message="Pausa la gráfica.", font=self.text_font)

        self.icon_stop = ctk.CTkImage(Image.open("assets/icons/stop.png"), size=self.icon_size)
        self.stop_button = ctk.CTkButton(self.buttons_frame, text="", command=self.stop_animation, font=self.text_font, image=self.icon_stop, width=50)
        self.stop_button.pack(side="left", padx=10)
        
        self.stop_tooltip = CTkToolTip(self.stop_button, delay=0.5, message="Detén la lectura de datos.", font=self.text_font)
        
         # ---------- Filtros ----------
        self.frame_filter = ctk.CTkFrame(self.main_layout, fg_color="transparent")
        self.frame_filter.pack(pady=10, padx=10, anchor="w", fill="x")
        
        # Frame interno centrado para los elementos de filtro
        self.filters_inner_frame = ctk.CTkFrame(self.frame_filter, fg_color="transparent")
        self.filters_inner_frame.pack(anchor="center")  # centra el frame interno

        # Activar filtros por defecto
        self.low_pass_var = ctk.StringVar(value="on")  # Cambiado de "off" a "on"
        self.low_pass_toggle = ctk.CTkCheckBox(self.filters_inner_frame, text="Pasa-bajas (20Hz)", variable=self.low_pass_var, onvalue="on", offvalue="off", font=self.text_font)
        self.low_pass_toggle.pack(side="left", padx=10)

        self.high_pass_var = ctk.StringVar(value="on")  # Cambiado de "off" a "on"
        self.high_pass_toggle = ctk.CTkCheckBox(self.filters_inner_frame, text="Pasa-altas (0.5Hz)", variable=self.high_pass_var, onvalue="on", offvalue="off", font=self.text_font)
        self.high_pass_toggle.pack(side="left", padx=10)

        self.notch_var = ctk.StringVar(value="on")  # Cambiado de "off" a "on"
        self.notch_toggle = ctk.CTkCheckBox(self.filters_inner_frame, text="Notch (60Hz)", variable=self.notch_var, onvalue="on", offvalue="off", font=self.text_font)
        self.notch_toggle.pack(side="left", padx=10)

        # Botón para verificar estado de filtros
        self.filter_status_button = ctk.CTkButton(self.filters_inner_frame, text="Estado Filtros", command=self.show_filter_status,font=self.text_font,width=120)
        self.filter_status_button.pack(side="left", padx=10)
        
        # Agregar BPM label en el frame derecho
        self.bpm_label = ctk.CTkLabel(self.bpm_frame, text="BPM: --", font=self.bpm_font, text_color="white")
        self.bpm_label.pack(anchor="center", pady=5)
        
        self.connection_status_label = ctk.CTkLabel(self.bpm_frame, text="📲 Estado:", font=self.subtitle_font)
        self.connection_status_label.pack(padx=(5, 10))
        self.connected_label = ctk.CTkLabel(self.bpm_frame, text="Desconectado", font=self.subtitle_font, text_color="crimson")
        self.connected_label.pack(padx=(5, 10))
        
        #self.voltage_label = ctk.CTkLabel(self.graph_frame, text="Voltaje: -- V", font=self.text_font)
        #self.voltage_label.pack(side="right", padx=20)

        # ---------- Guardar CSV ----------
        # self.save_frame = ctk.CTkFrame(self.bpm_frame, fg_color="transparent")
        # self.save_frame.pack(pady=10, padx=10, anchor="w", fill="x")

        self.patient_name_entry = ctk.CTkEntry(self.bpm_frame, placeholder_text="Nombre del paciente", width=200, height=30, font=self.text_font)
        self.patient_name_entry.pack(padx=10, pady=10)
        self.patient_id_entry = ctk.CTkEntry(self.bpm_frame, placeholder_text="Curp del paciente", width=300, height=30, font=self.text_font)
        self.patient_id_entry.pack(padx=10, pady=10)
        
        self.icon_save = ctk.CTkImage(Image.open("assets/icons/save.png"), size=self.icon_size)
        self.start_recording_button = ctk.CTkButton(self.bpm_frame, text="Exportar en CSV", command=self.start_continuos_recording, font=self.text_font, image=self.icon_save)
        self.start_recording_button.pack(padx=10, pady=10)
        
        self.icon_stop = ctk.CTkImage(Image.open("assets/icons/stop.png"), size=self.icon_size)
        self.stop_recording_button = ctk.CTkButton(self.bpm_frame, text="Detener guardado", command=self.stop_continuos_recording, font=self.text_font, image=self.icon_stop)
        self.stop_recording_button.pack(padx=10, pady=10)
        
        self.recording_status_label = ctk.CTkLabel(self.bpm_frame, text=" ", font=self.text_font)
        self.recording_status_label.pack(padx=10, pady=10)
        
        # --------------- Enviar información a dispositivo remoto -----------------
        self.label_remote = ctk.CTkLabel(self.bpm_frame, text="📡 Enviar datos:", font=self.subtitle_font)
        self.label_remote.pack(padx=10, pady=10)
        
        self.patient_icon = ctk.CTkImage(Image.open("assets/icons/patient.png"), size=self.icon_size)
        self.save_patient_button = ctk.CTkButton(self.bpm_frame, text="Guardar Paciente", command=self.save_patient_data, font=self.text_font, image=self.patient_icon)
        self.save_patient_button.pack(padx=10, pady=10)
        
        self.icon_share = ctk.CTkImage(Image.open("assets/icons/share.png"), size=self.icon_size)
        self.send_patient_data_button = ctk.CTkButton(self.bpm_frame, text="Enviar Datos", command=lambda: [self.send_patient_data(), self.send_ecg_stream()], font=self.text_font,
                                                      image=self.icon_share)
        self.send_patient_data_button.pack(padx=10, pady=10)
        
    def save_patient_data(self):
        full_name = self.patient_name_entry.get().strip()
        curp = self.patient_id_entry.get().strip().upper()
        
        if not full_name:
            CTkMessagebox(title="Error", message="Debe ingresar el nombre completo del paciente.", icon="cancel")
            return
        if not curp:
            CTkMessagebox(title="Error", message="Debe ingresar el CURP del paciente.", icon="cancel")
            return
        
        split_name = full_name.split()
        nombre1 = split_name[0] if len(split_name) > 0 else ""
        nombre2 = split_name[1] if len(split_name) > 1 else ""
        apellido_paterno = split_name[2] if len(split_name) > 2 else ""
        apellido_materno = split_name[3] if len(split_name) > 3 else ""
        
        self.patient_data = {
            'id': 1, 
            'nombre1': nombre1,
            'nombre2': nombre2,
            'apellido_paterno': apellido_paterno,
            'apellido_materno': apellido_materno,
            'curp': curp,
            'fecha': datetime.datetime.now().strftime("%d/%m/%Y")  # Fecha actual
        }
        
        print("Datos del paciente guardados:")
        for key, value in self.patient_data.items():
            print(f"  {key} ({type(value)}): {value}")
        
        CTkMessagebox(title="Éxito", message="Los datos del paciente se han guardado correctamente", icon="check")
        
    def send_patient_data(self):
        """Envía datos del paciente al servidor"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(b'PAT ')
                
                patient_str = (f"{self.patient_data['id']}|{self.patient_data['nombre1']}|"
                             f"{self.patient_data['nombre2']}|{self.patient_data['apellido_paterno']}|"
                             f"{self.patient_data['apellido_materno']}|{self.patient_data['curp']}|"
                             f"{self.patient_data['fecha']}")
                
                s.sendall(patient_str.encode('utf-8'))
                print(f"Datos paciente {self.patient_data['id']} enviados")
        except Exception as e:
            print(f"Error enviando datos paciente: {e}")
            CTkMessagebox(title="Error", message="No se pudo enviar los datos del paciente al servidor", icon="cancel")
            
    def set_device_id(self, device_id):
        """Establece ID del dispositivo (1 o 2)"""
        if device_id in [1, 2]:
            self.device_id = device_id
            print(f"Dispositivo ECG configurado como ID: {self.device_id}")
        else:
            print("Error: El ID del dispositivo ECG debe ser 1 o 2")
            
    def send_ecg_stream(self):
        try:
            self.ecg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ecg_socket.connect((self.host, self.port))
            self.ecg_socket.sendall(b'ECG ')
            header = struct.pack('<I4sII', self.device_id, b'ECG', self.fs, 1)
            self.ecg_socket.sendall(header)
            self.sending_ecg = True
            print("✅ Conectado al servidor como cliente ECG")
        except Exception as e:
            print(f"❌ Error al conectar con servidor ECG: {e}")
            self.sending_ecg = False
            
    def refresh_com_ports(self):
        """Actualiza la lista de puertos COM disponibles"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.com_port_combobox.configure(values=port_list)
        if port_list:
            self.com_port_combobox.set(port_list[0])

    def disconnect_com_port(self):
        """Desconecta el dispositivo de comunicación"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            self.arduino = None
            CTkMessagebox(title="Desconectado", message="Puerto COM cerrado correctamente", icon="check")

    #def show_baud_info(self):
    #    """Muestra información sobre el baud rate seleccionado"""
    #    CTkMessagebox(title="Información", message="Selecciona el baud rate que coincida con tu dispositivo.", icon="info")

    def show_filter_status(self):
        """Mostrar estado actual de los filtros"""
        status = []
        if self.low_pass_var.get() == "on":
            status.append("✓ Pasa-bajas (20Hz): ACTIVO")
        else:
            status.append("✗ Pasa-bajas (20Hz): INACTIVO")
            
        if self.high_pass_var.get() == "on":
            status.append("✓ Pasa-altas (0.5Hz): ACTIVO")
        else:
            status.append("✗ Pasa-altas (0.5Hz): INACTIVO")
            
        if self.notch_var.get() == "on":
            status.append("✓ Notch (60Hz): ACTIVO")
        else:
            status.append("✗ Notch (60Hz): INACTIVO")
        
        message = "\n".join(status)
        CTkMessagebox(title="Estado de Filtros ECG", message=message, icon="info")
        
    def init_plot(self):
        """Inicializa el gráfico antes de la animación"""
        self.line_filtered.set_data(self.x_display, self.y_display_data)
        self.clearing_line.set_data([], [])
        # self.cursor_line.set_data([], []) # Remove cursor
        return self.line_filtered, self.clearing_line #, self.cursor_line
    
    def begin_device(self):
        """Inicia el dispositivo de comunicación"""
        if self.arduino is None:
            try:
                self.port_device = self.com_port_combobox.get()
                self.baud = int(115200)
                self.arduino = serial.Serial(port=self.port_device, baudrate=self.baud, timeout=1)
                self.connected_label.configure(text="Conectado", text_color="limegreen")
                CTkMessagebox(title="Dispositivo", message="El dispositivo se ha conectado con éxito", icon="check")
            except serial.SerialException:
                CTkMessagebox(title="Error", message="No se pudo iniciar el dispositivo", icon="cancel")
            except ValueError:
                CTkMessagebox(title="Warning", message="Revise los valores de entrada", icon="warning")
            except Exception:
                CTkMessagebox(title="Error", message="Error al conectar con el dispositivo", icon="cancel")
                return
            
    def start_animation(self):
        """Comienza la animación del gráfico"""
        if self.arduino is None or not self.arduino.is_open:
            CTkMessagebox(title="Error", message="Debe conectar el dispositivo primero.", icon="cancel")
            return
        else:
            if self.ani is None:
                self.animacion()  # Inicializa la animación
            elif not self.animation_running:
                self.ani.event_source.start()
                self.animation_running = True
                self.streaming = True

    def pause_animation(self):
        "Pausa la animación del gráfico"
        self.streaming = False
        self.animation_running = False

    def stop_animation(self):
        """Detiene la animación y resetea el gráfico"""
        # Detener guardado continuo si está activo
        if self.continuos_recording:
            self.stop_continuos_recording()

        self.streaming = False    
        if self.ani:
            self.ani.event_source.stop()
            self.animation_running = False
        
        # Resetear buffers
        self.current_index = 0
        self.display_index = 0
        self.buffer_full = False
        self.y_data_raw = [0] * self.buffer_size
        self.y_data_filtered = [0] * self.buffer_size
        self.temp_raw_buffer.clear()
        
        self.line_filtered.set_data(self.x_display, self.y_display_data)
        self.clearing_line.set_data([], [])
        # self.cursor_line.set_data([], []) # Remove cursor
        self.canvas.draw()
        
    def animacion(self):
        """Anima el gráfico en tiempo real"""
        if self.ani is None:
            self.ani = animation.FuncAnimation(self.fig, self.update_plot, frames=itertools.count(), 
                                            init_func=self.init_plot, blit=True, interval=2)
        self.animation_running = True
        self.ani.event_source.start()
        
    def reading(self, signal):
        try:
            self.arduino.write(signal.encode())
            time.sleep(0.00001)
            data = self.arduino.readline().decode().strip()

            if not data:
                # Si está vacío, retornar 0.0 sin error
                return 0.0

            val = float(data)
            return val
        except Exception as e:
            print(f"⚠️ Error al leer dato del puerto: {e} - Dato recibido: {repr(data)}")
            return 0.0

    def apply_filters(self, signal_data):
        """Aplicar filtros de ECG de manera optimizada"""
        if len(signal_data) < 30:  # Necesitamos más datos para filtros estables
            return signal_data[-1] if len(signal_data) > 0 else 0
        
        # Convertir a numpy array
        filtered_signal = np.array(signal_data.copy(), dtype=np.float64)
        
        try:
            # 1. Filtro Notch primero (eliminar interferencia de red 60Hz)
            if self.notch_var.get() == "on":
                b, a = iirnotch(60, Q=60, fs=self.fs)
                sos = tf2sos(b, a)
                filtered_signal = sosfiltfilt(sos, filtered_signal)
            
            # 2. Filtro pasa-altas (eliminar deriva de línea base)
            if self.high_pass_var.get() == "on":
                sos = butter(4, 0.5, btype='highpass', fs=self.fs, output='sos')
                filtered_signal = sosfilt(sos, filtered_signal)
            
            # 3. Filtro pasa-bajas (anti-aliasing y suavizado)
            if self.low_pass_var.get() == "on":
                sos = butter(4, 20, btype='lowpass', fs=self.fs, output='sos')
                filtered_signal = sosfilt(sos, filtered_signal)
            
            return filtered_signal[-1]
            
        except Exception as e:
            print(f"Error aplicando filtros: {e}")
            return signal_data[-1] if len(signal_data) > 0 else 0
        
    def update_plot(self, frame):
        if not self.animation_running:
            return self.line_filtered, self.clearing_line #, self.cursor_line # Remove cursor

        # Leer dato crudo
        raw_value = self.reading("raw") 
        
        # Agregar al buffer temporal para filtros
        self.temp_raw_buffer.append(raw_value)
        
        # Actualizar buffer circular con el nuevo dato raw (para guardado)
        self.y_data_raw[self.current_index] = raw_value
        
        # Calcular voltaje actual del dato crudo
        current_voltage = raw_value 
        #self.voltage_label.configure(text=f"Voltaje: {current_voltage:.3f} V")

        # APLICAR FILTROS MEJORADOS
        filtered_value = self.apply_filters(self.temp_raw_buffer)
        
        # Actualizar buffer circular con el dato filtrado
        self.y_data_filtered[self.current_index] = filtered_value
        
        # Actualizar buffer de visualización
        self.update_display_buffer(filtered_value)
        
        if self.sending_ecg and self.ecg_socket:
            try:
                if isinstance(filtered_value, (int, float)) and not np.isnan(filtered_value):
                    int_val = int(filtered_value * 1000)
                    packed = struct.pack('<h', int_val)
                    self.ecg_socket.sendall(packed)
                else:
                    raise TypeError(f"Valor inválido para enviar: {filtered_value}")
            except Exception as e:
                print(f"❌ Error enviando datos ECG: {e}")
                self.sending_ecg = False
        
        # Guardar en guardado continuo si está habilitado
        if self.continuos_recording:
            self.recording_data_raw.append(raw_value)
            self.recording_data_filtered.append(filtered_value)
            
            if self.recording_start_time:
                current_duration = (datetime.datetime.now() - self.recording_start_time).total_seconds()
                self.recording_status_label.configure(text=f"🔴 Guardando... {current_duration:.1f}s")

        # Detectar picos R y calcular BPM solo en la señal filtrada
        if self.buffer_full or self.current_index > 50:  # Solo calcular si hay suficientes datos
            bpm = self.calculate_bpm(self.y_data_filtered)
            self.update_bpm_label(bpm)

        # Avanzar índice del buffer circular
        self.current_index = (self.current_index + 1) % self.buffer_size
        if self.current_index == 0:
            self.buffer_full = True

        # Limitar el buffer temporal para evitar que crezca indefinidamente
        if len(self.temp_raw_buffer) > 1000:  # Mantener últimos 1000 puntos para filtros
            self.temp_raw_buffer = self.temp_raw_buffer[-1000:]

        # Actualizar solo la línea filtrada en el gráfico
        #self.line_filtered.set_data(self.x_data, self.y_data_filtered)
        self.update_realtime_display()

        return self.line_filtered, self.clearing_line #, self.cursor_line # Remove cursor
    
    def update_realtime_display(self):
        # Actualizar línea principal del ECG
        self.line_filtered.set_data(self.x_display, self.y_display_data)
        
        # Obtener posiciones para efectos visuales
        cursor_pos, clearing_positions = self.get_display_positions()
        
        # Actualizar cursor (línea roja vertical que indica posición actual)
        # y_range = self.ax.get_ylim() # Remove cursor
        # self.cursor_line.set_data([cursor_pos, cursor_pos], [y_range[0], y_range[1]]) # Remove cursor
        
        # Actualizar ventan de limpieza (línea negra que "borra")
        if clearing_positions:
            y_range = self.ax.get_ylim() # Moved y_range here as it's still needed for clearing_line
            clearing_x = clearing_positions
            clearing_y_bottom = [y_range[0]] * len(clearing_positions)
            clearing_y_top = [y_range[1]] * len(clearing_positions) 
            
            # Mostrar solo la primera poisición de limpieza
            first_clear_pos = clearing_positions[0]
            self.clearing_line.set_data([first_clear_pos, first_clear_pos], [y_range[0], y_range[1]])
    
    def calculate_bpm(self, signal):
        # Convertir signal a numpy array si no lo es
        if not isinstance(signal, np.ndarray):
            signal = np.array(signal)
            
        # Solo usar datos no-cero para evitar falsos picos
        non_zero_signal = signal[signal != 0]
        if len(non_zero_signal) < 20:  # Necesitamos suficientes datos
            return 0
            
        # Parámetros mejorados para detección de picos R
        # Altura mínima basada en el rango de la señal
        signal_range = np.max(non_zero_signal) - np.min(non_zero_signal)
        if signal_range == 0:
            return 0
            
        min_height = np.mean(non_zero_signal) + 0.3 * signal_range
        
        # Distancia mínima entre picos (aproximadamente 0.4 segundos)
        min_distance = int(0.4 * self.fs)  # Ajustado para la velocidad de muestreo (self.fs)
        
        try:
            # Detectar picos R
            peaks, properties = find_peaks(non_zero_signal, height=min_height, distance=min_distance, prominence=0.1 * signal_range)

            # Calcular BPM si hay suficientes picos
            if len(peaks) >= 2:
                # Calcular intervalos entre picos (en muestras)
                intervals = np.diff(peaks)
                
                # Convertir a tiempo 
                intervals_seconds = intervals / self.fs # fs = sampling frequency
                
                # Calcular BPM promedio
                avg_interval = np.mean(intervals_seconds)
                if avg_interval > 0:
                    bpm = 60 / avg_interval
                    # Limitar BPM a un rango razonable
                    return max(30, min(200, bpm))
        except Exception as e:
            print(f"Error calculando BPM: {e}")
        
        return 0

    def update_bpm_label(self, bpm):
        # Mostrar BPM
        if bpm > 0:
            self.bpm_label.configure(text=f"BPM: {int(bpm)}")
            
            # Cambiar color según rango normal
            if bpm < 60:
                self.bpm_label.configure(text_color="orange")  # Bradicardia
            elif bpm > 100:
                self.bpm_label.configure(text_color="red")     # Taquicardia
            else:
                self.bpm_label.configure(text_color="lime")    # Normal
        else:
            self.bpm_label.configure(text="BPM: --", text_color="white")
            
    def update_display_buffer(self, new_value):
        self.y_display_data[self.display_index] = new_value
        # Limpiar las muestras que van por delante (efecto ventana)
        #for i in range(1, self.clearing_window + 1): 
        for j in range(1, self.clearing_window + 1):
            clear_index = (self.display_index + j) % self.display_buffer_size
            self.y_display_data[clear_index] = 0
        
        # Avanzar el índice de visualización
        self.display_index = (self.display_index + 1) % self.display_buffer_size
        
    def get_display_positions(self):
        # Posición del cursor (línea roja que indica dónde se está escribiendo)
        cursor_pos = self.display_index
        
        # Posiciones de la ventana de limpieza
        clearing_positions = []
        for i in range(1, self.clearing_window + 1):
            pos = (self.display_index + i) % self.display_buffer_size
            clearing_positions.append(pos)
        
        return cursor_pos, clearing_positions
    
    # Método para personalizar el tamaño de la ventana de limpieza
    def set_clearing_window_size(self, size):
        self.clearing_window = max(5, min(30, size))
            
    def start_continuos_recording(self):
        patient_name = self.patient_name_entry.get().strip()
        patient_id = self.patient_id_entry.get().strip().upper()
        if not patient_name: 
            CTkMessagebox(title="Error", message="Debe ingresar el nombre del paciente.", icon="cancel")
            return
        if not patient_id:
            CTkMessagebox(title="Error", message="Debe ingresar el CURP del paciente.", icon="cancel")
            return
        if not self.animation_running:
            CTkMessagebox(title="Error", message="Debe iniciar la adquisición de datos antes de guardarlos.", icon="cancel")
            return
        
        # Inicializar guardado continuo de datos
        self.continuos_recording = True
        self.recording_data_raw = []
        self.recording_data_filtered = []
        self.recording_start_time = datetime.datetime.now()
        
        # Actualizar botones y etiqueta de guardado en interfaz
        self.start_recording_button.configure(state="disabled")
        self.stop_recording_button.configure(state="normal")
        self.recording_status_label.configure(text="🔴 Guardando datos...")
        
        CTkMessagebox(title="Guardado iniciado", message="El guardado de datos continuo ha comenzado", icon="check")
        
    def stop_continuos_recording(self):
        if not self.continuos_recording:
            return
        
        # Detener el guarado de datos continuo
        self.continuos_recording = False
        recording_end_time = datetime.datetime.now()
        
        # Actualizar botones y etiqueta de guardado en interfaz
        self.start_recording_button.configure(state="normal")
        self.stop_recording_button.configure(state="disabled")
        self.recording_status_label.configure(text=" ")
        
        # Comprobar si hay datos grabados para guardarlos
        if len(self.recording_data_raw) > 0:
            self.save_continuos_recording_data(recording_end_time)
        else:
            CTkMessagebox(title="Sin datos", message="No hay datos para guardar", icon="warning")
            
    def save_continuos_recording_data(self, end_time):
        patient_name = self.patient_name_entry.get().strip()
        patient_id = self.patient_id_entry.get().strip().upper()
        
        duration_seconds = (end_time - self.recording_start_time).total_seconds()
        sampling_rate = self.fs  
        
        # Crear nombre de archivo para el guardado de datos
        filename = f"ECG_{patient_name}_{patient_id}_{self.recording_start_time.strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, mode="w", newline="") as file:
                writer = csv.writer(file)
                
                # Encazabezados con información detallada
                writer.writerow(["Guardado continuo de ECG"])
                writer.writerow([f"Paciente: {patient_name}_({patient_id})"])
                writer.writerow([f"Inicio: {self.recording_start_time.strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([f"Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([f"Duracion: {duration_seconds:.2f} segundos ({len(self.recording_data_raw)} muestras)"])
                writer.writerow([f"Frecuencia de muestreo: {sampling_rate} Hz"])
                
                # Encabezados de datos
                writer.writerow(["Sample", "Time", "Raw signal", "Filtered signal"])
                
                # Escribir todos los datos grabados
                for i, (raw_val, filtered_val) in enumerate(zip(self.recording_data_raw, self.recording_data_filtered)):
                    time_seconds = i / sampling_rate  # Corrected calculation
                    writer.writerow([i, f"{time_seconds:.3f}", raw_val, filtered_val])
                    
            CTkMessagebox(title="Datos guardados", 
                          message=f"Datos guardados correctamente\nArchivo: {filename}\nDuración: {duration_seconds:.2f} segundos\nMuestras: {len(self.recording_data_raw)}", 
                          icon="check")
                
        except Exception as e:
            CTkMessagebox(title="Error", message=f"Error al guardar archivo: {str(e)}", icon="cancel")
