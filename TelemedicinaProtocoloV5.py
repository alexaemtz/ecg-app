import socket
import threading
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer, QObject, pyqtSlot, pyqtSignal
import pyqtgraph as pg
import sys
import struct
from collections import deque
import sounddevice as sd  # Para reproducir audio del estetoscopio





class MedicalMonitor(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configuración de datos con buffer para autoajuste
        self.ecg_data = {
            1: {
                'data': np.zeros(250*10),  # Aumentamos el buffer para mejor visualización
                'index': 0, 
                'color': 'b', 
                'title': 'ECG1 - Dispositivo 1',
                'buffer': deque(maxlen=250*3),
                'auto_range': True,
                'min_val': -2000,
                'max_val': 2000,
                'ptr': 0  # Puntero para el desplazamiento
            },
            2: {
                'data': np.zeros(250*10), 
                'index': 0, 
                'color': 'r', 
                'title': 'ECG2 - Dispositivo 2',
                'buffer': deque(maxlen=250*3),
                'auto_range': True,
                'min_val': -2000,
                'max_val': 2000,
                'ptr': 0
            }
        }
        
        # Datos para SPO2
        self.spo2_data = {
            'data': np.zeros(250*10),
            'index': 0,
            'color': 'g',
            'title': 'SPO2',
            'value': 98,
            'buffer': deque(maxlen=250*3),
            'auto_range': True,
            'min_val': 80,
            'max_val': 100,
            'ptr': 0
        
        }
        
        self.image_data = {
            1: {'image': None, 'title': 'Imágenes - Cliente 1'},
            2: {'image': None, 'title': 'Imágenes - Cliente 2'}
        }
        
        # Datos de pacientes
        self.patient_data = {
            1: {
                'id': 1,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            2: {
                'id': 2,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            3: {
                'id': 3,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            4: {
                'id': 4,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            5: {
                'id': 5,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            6: {
                'id': 6,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            },
            7: {
                'id': 7,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            }
            
        }
        
        # Audio del estetoscopio
        self.stethoscope_audio = None
        
        self.initUI()
        self.setup_auto_adjust_timer()


    
    def initUI(self):
        self.setWindowTitle('Monitor Médico Avanzado')
        self.setGeometry(100, 100, 1200, 1200)
        
        # Widget central
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # ===== BARRA DE HERRAMIENTAS =====
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)
        
        # Botón para limpiar datos de pacientes
        clear_btn = QtWidgets.QAction('Limpiar Datos de Pacientes', self)
        clear_btn.triggered.connect(self.clear_patient_data)
        toolbar.addAction(clear_btn)
        
        # ===== SECCIÓN ECG =====
        ecg_group = QtWidgets.QGroupBox("Monitoreo ECG (Autoajuste activado)")
        ecg_layout = QtWidgets.QHBoxLayout(ecg_group)
        
        # Gráficos ECG
        for client_id, info in self.ecg_data.items():
            frame = QtWidgets.QFrame()
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame_layout = QtWidgets.QVBoxLayout(frame)
            
            # Título con botón de autoajuste
            title_layout = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(info['title'])
            label.setStyleSheet('font-size: 14px; font-weight: bold;')
            
            auto_btn = QtWidgets.QPushButton("Autoajuste: ON")
            auto_btn.setCheckable(True)
            auto_btn.setChecked(True)
            auto_btn.setStyleSheet("QPushButton { padding: 2px 5px; font-size: 12px; }")
            auto_btn.clicked.connect(lambda _, cid=client_id: self.toggle_auto_adjust(cid))
            
            title_layout.addWidget(label)
            title_layout.addStretch()
            title_layout.addWidget(auto_btn)
            frame_layout.addLayout(title_layout)
            
            # Widget de gráfico
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setYRange(info['min_val'], info['max_val'])
            plot_widget.setXRange(0, 5)
            
            # Configurar el plot para desplazamiento continuo
            plot_widget.setLimits(xMin=0, xMax=10)  # 10 segundos de visualización
            plot_widget.setXRange(0, 5)  # Mostrar los últimos 5 segundos inicialmente
            plot_widget.enableAutoRange('y', True)
            
            info['plot'] = plot_widget  # Guardar referencia al plot
            info['curve'] = plot_widget.plot(pen=pg.mkPen(info['color'], width=2))
            
            frame_layout.addWidget(plot_widget)
            ecg_layout.addWidget(frame)
        
        main_layout.addWidget(ecg_group)
        
        # ===== SECCIÓN SPO2 =====
        spo2_group = QtWidgets.QGroupBox("Monitoreo SPO2")
        spo2_layout = QtWidgets.QHBoxLayout(spo2_group)
        
        # Gráfico SPO2
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame_layout = QtWidgets.QVBoxLayout(frame)
        
        # Título con botón de autoajuste
        title_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(self.spo2_data['title'])
        label.setStyleSheet('font-size: 14px; font-weight: bold;')
        
        auto_btn = QtWidgets.QPushButton("Autoajuste: ON")
        auto_btn.setCheckable(True)
        auto_btn.setChecked(True)
        auto_btn.setStyleSheet("QPushButton { padding: 2px 5px; font-size: 12px; }")
        auto_btn.clicked.connect(self.toggle_spo2_auto_adjust)
        
        title_layout.addWidget(label)
        title_layout.addStretch()
        title_layout.addWidget(auto_btn)
        frame_layout.addLayout(title_layout)
        
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setLimits(xMin=0, xMax=10)  # 10 segundos de visualización
        plot_widget.setXRange(0, 5)  # Mostrar los últimos 5 segundos inicialmente
        plot_widget.enableAutoRange('y', True)
        
        self.spo2_data['plot'] = plot_widget
        self.spo2_data['curve'] = plot_widget.plot(pen=pg.mkPen(self.spo2_data['color'], width=2))
        
        frame_layout.addWidget(plot_widget)
        spo2_layout.addWidget(frame)
        
        # Valor numérico de SPO2
        value_frame = QtWidgets.QFrame()
        value_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        value_layout = QtWidgets.QVBoxLayout(value_frame)
        
        value_label = QtWidgets.QLabel("Oxigenación (%):")
        value_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        value_layout.addWidget(value_label)
        
        self.spo2_value_display = QtWidgets.QLCDNumber()
        self.spo2_value_display.setDigitCount(3)
        self.spo2_value_display.setSegmentStyle(QtWidgets.QLCDNumber.Filled)
        self.spo2_value_display.display(self.spo2_data['value'])
        value_layout.addWidget(self.spo2_value_display)
        
        spo2_layout.addWidget(value_frame)
        main_layout.addWidget(spo2_group)
        
        # ===== SECCIÓN IMAGENES =====
        img_group = QtWidgets.QGroupBox("Visualización de Imágenes")
        img_layout = QtWidgets.QHBoxLayout(img_group)
        
        # Botones para imágenes
        for client_id, info in self.image_data.items():
            frame = QtWidgets.QFrame()
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame_layout = QtWidgets.QVBoxLayout(frame)
            
            btn = QtWidgets.QPushButton(info['title'])
            btn.setStyleSheet('font-size: 14px; font-weight: bold;')
            btn.clicked.connect(lambda _, cid=client_id: self.show_image(cid))
            frame_layout.addWidget(btn)
            
            img_layout.addWidget(frame)
        
        main_layout.addWidget(img_group)
        
        # ===== SECCIÓN PACIENTES =====
        patient_group = QtWidgets.QGroupBox("Información de Pacientes")
        patient_layout = QtWidgets.QHBoxLayout(patient_group)
        
        # Botón para mostrar información de pacientes
        patient_btn = QtWidgets.QPushButton("Mostrar Información de Pacientes")
        patient_btn.setStyleSheet('font-size: 14px; font-weight: bold;')
        patient_btn.clicked.connect(self.show_patient_info)
        patient_layout.addWidget(patient_btn)
        
        # Botón para estetoscopio
        stethoscope_btn = QtWidgets.QPushButton("Reproducir Estetoscopio")
        stethoscope_btn.setStyleSheet('font-size: 14px; font-weight: bold;')
        stethoscope_btn.clicked.connect(self.play_stethoscope)
        patient_layout.addWidget(stethoscope_btn)
        
        main_layout.addWidget(patient_group)
        
        # Barra de estado
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Servidor listo. Autoajuste ECG activado.")
        
        # Timers para actualización
        self.ecg_timer = QTimer()
        self.ecg_timer.timeout.connect(self.update_ecg)
        self.ecg_timer.start(50)  # 50ms para ECG
        
        self.img_timer = QTimer()
        self.img_timer.timeout.connect(self.update_images)
        self.img_timer.start(100)  # 100ms para imágenes



        
    def setup_auto_adjust_timer(self):
        """Timer para ajuste automático de rango vertical"""
        self.auto_adjust_timer = QTimer()
        self.auto_adjust_timer.timeout.connect(self.adjust_ranges)
        self.auto_adjust_timer.start(2000)  # Ajustar cada 2 segundos

    def toggle_auto_adjust(self, client_id):
        """Activa/desactiva autoajuste para un cliente ECG"""
        client = self.ecg_data[client_id]
        client['auto_range'] = not client['auto_range']
        
        btn = self.sender()
        if client['auto_range']:
            btn.setText("Autoajuste: ON")
            self.status_bar.showMessage(f"Autoajuste activado para Cliente {client_id}")
        else:
            btn.setText("Autoajuste: OFF")
            self.status_bar.showMessage(f"Autoajuste desactivado para Cliente {client_id}")

    def toggle_spo2_auto_adjust(self):
        """Activa/desactiva autoajuste para SPO2"""
        self.spo2_data['auto_range'] = not self.spo2_data['auto_range']
        
        btn = self.sender()
        if self.spo2_data['auto_range']:
            btn.setText("Autoajuste: ON")
            self.status_bar.showMessage("Autoajuste SPO2 activado")
        else:
            btn.setText("Autoajuste: OFF")
            self.status_bar.showMessage("Autoajuste SPO2 desactivado")

    def adjust_ranges(self):
        """Ajusta automáticamente los rangos Y basado en los datos recientes"""
        # Ajustar ECG
        for client_id, client in self.ecg_data.items():
            if client['auto_range'] and len(client['buffer']) > 0:
                data = np.array(client['buffer'])
                q10 = np.percentile(data, 10)
                q90 = np.percentile(data, 90)
                
                margin = (q90 - q10) * 0.2
                min_val = q10 - margin
                max_val = q90 + margin
                
                min_val = max(min_val, -5000)
                max_val = min(max_val, 5000)
                
                if abs(min_val - client['min_val']) > 100 or abs(max_val - client['max_val']) > 100:
                    client['min_val'] = min_val
                    client['max_val'] = max_val
                    client['plot'].setYRange(min_val, max_val, padding=0.1)
        
        # Ajustar SPO2
        if self.spo2_data['auto_range'] and len(self.spo2_data['buffer']) > 0:
            data = np.array(self.spo2_data['buffer'])
            q10 = np.percentile(data, 10)
            q90 = np.percentile(data, 90)
            
            margin = (q90 - q10) * 0.2
            min_val = q10 - margin
            max_val = q90 + margin
            
            # Limitar rango SPO2 entre 70 y 100
            min_val = max(min_val, 70)
            max_val = min(max_val, 100)
            
            if abs(min_val - self.spo2_data['min_val']) > 1 or abs(max_val - self.spo2_data['max_val']) > 1:
                self.spo2_data['min_val'] = min_val
                self.spo2_data['max_val'] = max_val
                self.spo2_data['plot'].setYRange(min_val, max_val, padding=0.1)

    def show_image(self, client_id):
        """Muestra la imagen en una ventana separada"""
        if client_id in self.image_data and self.image_data[client_id]['image'] is not None:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Imagen del Dispositivo {client_id}")
            
            layout = QtWidgets.QVBoxLayout(dialog)
            
            image_label = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap.fromImage(self.image_data[client_id]['image'])
            image_label.setPixmap(pixmap)
            
            layout.addWidget(image_label)
            dialog.exec_()

    def show_patient_info(self):
        """Muestra la información de los pacientes en una ventana"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Información de Pacientes")
        dialog.setMinimumSize(600, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        tab_widget = QtWidgets.QTabWidget()
        
        for client_id, data in self.patient_data.items():
            tab = QtWidgets.QWidget()
            tab_layout = QtWidgets.QFormLayout(tab)
            
            tab_layout.addRow(QtWidgets.QLabel(f"<b>Paciente del Dispositivo {client_id}</b>"))
            tab_layout.addRow(QtWidgets.QLabel(""))  # Espacio
            
            # Campos de información
            fields = [
                ("Identificador:", str(data['id'])),
                ("Primer Nombre:", data['nombre1']),
                ("Segundo Nombre:", data['nombre2']),
                ("Apellido Paterno:", data['apellido_paterno']),
                ("Apellido Materno:", data['apellido_materno']),
                ("CURP:", data['curp']),
                ("Fecha:", data['fecha'])
            ]
            
            for label, value in fields:
                label_widget = QtWidgets.QLabel(label)
                value_widget = QtWidgets.QLabel(value)
                value_widget.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
                tab_layout.addRow(label_widget, value_widget)
            
            tab_widget.addTab(tab, f"Dispositivo {client_id}")
        
        layout.addWidget(tab_widget)
        dialog.exec_()

    def play_stethoscope(self):
        """Reproduce el audio del estetoscopio"""
        if self.stethoscope_audio is not None:
            try:
                sd.play(self.stethoscope_audio, samplerate=44100)
                self.status_bar.showMessage("Reproduciendo audio del estetoscopio...")
            except Exception as e:
                self.status_bar.showMessage(f"Error reproduciendo audio: {str(e)}")
        else:
            self.status_bar.showMessage("No hay audio del estetoscopio disponible")

    @pyqtSlot(int, list)
    def add_ecg_data(self, client_id, samples):
        if client_id in self.ecg_data:
            client = self.ecg_data[client_id]
            for sample in samples:
                client['data'][client['ptr']] = sample
                client['buffer'].append(sample)
                client['ptr'] += 1
                if client['ptr'] >= len(client['data']):
                    client['ptr'] = 0
                    # Desplazar la vista cuando llegamos al final
                    client['plot'].setXRange(client['ptr']/250, (client['ptr']/250)+5)
            
            self.status_bar.showMessage(f"Datos ECG recibidos del cliente {client_id}")

    @pyqtSlot(list)
    def add_spo2_data(self, samples):
        for sample in samples:
            self.spo2_data['data'][self.spo2_data['ptr']] = sample
            self.spo2_data['buffer'].append(sample)
            self.spo2_data['ptr'] += 1
            if self.spo2_data['ptr'] >= len(self.spo2_data['data']):
                self.spo2_data['ptr'] = 0
                # Desplazar la vista cuando llegamos al final
                self.spo2_data['plot'].setXRange(self.spo2_data['ptr']/250, (self.spo2_data['ptr']/250)+5)

        # Actualizar valor numérico
        if len(self.spo2_data['buffer']) > 0:
            last_values = list(self.spo2_data['buffer'])[-10:]
            self.spo2_data['value'] = round(sum(last_values) / len(last_values), 1)
            self.spo2_value_display.display(self.spo2_data['value'])
        
        self.status_bar.showMessage("Datos SPO2 actualizados")

    @pyqtSlot(int, bytes)
    def add_image_data(self, client_id, image_bytes):
        if client_id in self.image_data:
            try:
                image = QtGui.QImage()
                image.loadFromData(image_bytes)
                
                if not image.isNull():
                    self.image_data[client_id]['image'] = image
                    self.status_bar.showMessage(f"Imagen recibida del cliente {client_id}")
                else:
                    print(f"Error: Imagen del cliente {client_id} no válida")
            except Exception as e:
                print(f"Error procesando imagen del cliente {client_id}: {e}")

    @pyqtSlot(dict)
    def add_patient_data(self, data):
        client_id = data.get('id', 0)
        if client_id in self.patient_data:
            self.patient_data[client_id].update(data)
            self.status_bar.showMessage(f"Datos del paciente {client_id} actualizados")

    @pyqtSlot(bytes)
    def add_stethoscope_data(self, audio_data):
        try:
            # Convertir bytes a array numpy para reproducción
            self.stethoscope_audio = np.frombuffer(audio_data, dtype=np.int16)
            self.status_bar.showMessage("Audio del estetoscopio recibido y listo para reproducir")
        except Exception as e:
            self.status_bar.showMessage(f"Error procesando audio: {str(e)}")

    def update_ecg(self):
        for client_id, client in self.ecg_data.items():
            if client['ptr'] > 0:
                # Calcular el rango de tiempo actual
                start_time = max(0, (client['ptr']/250)-5)
                end_time = start_time + 5
                
                # Crear array de tiempo
                x = np.linspace(start_time, end_time, len(client['data']))
                
                # Reorganizar los datos para mostrar correctamente
                data = np.roll(client['data'], -client['ptr'])
                
                # Actualizar la curva
                client['curve'].setData(x, data)
                
                # Actualizar el rango de visualización si está en modo auto-desplazamiento
                if client['auto_range']:
                    client['plot'].setXRange(start_time, end_time)
        
        # Actualizar SPO2 de manera similar
        if self.spo2_data['ptr'] > 0:
            start_time = max(0, (self.spo2_data['ptr']/250)-5)
            end_time = start_time + 5
            x = np.linspace(start_time, end_time, len(self.spo2_data['data']))
            data = np.roll(self.spo2_data['data'], -self.spo2_data['ptr'])
            self.spo2_data['curve'].setData(x, data)
            
            if self.spo2_data['auto_range']:
                self.spo2_data['plot'].setXRange(start_time, end_time)
                
    def update_images(self):
        pass  # Ya no necesitamos actualizar imágenes automáticamente

    def clear_patient_data(self):
        """Limpia todos los datos de pacientes"""
        for device_id in self.patient_data:
            self.patient_data[device_id] = {
                'id': device_id,
                'nombre1': '',
                'nombre2': '',
                'apellido_paterno': '',
                'apellido_materno': '',
                'curp': '',
                'fecha': ''
            }
        self.status_bar.showMessage("Datos de pacientes limpiados correctamente")
        print("Datos de pacientes limpiados")    

class IntegratedServer(QObject):
    new_ecg_data = pyqtSignal(int, list)
    new_spo2_data = pyqtSignal(list)
    new_image_data = pyqtSignal(int, bytes)
    new_patient_data = pyqtSignal(dict)
    new_stethoscope_data = pyqtSignal(bytes)
    
    def __init__(self):
        super().__init__()
        self.running = False
    
    def start(self, port=5000):
        self.running = True
        threading.Thread(target=self.run_server, args=(port,), daemon=True).start()
    
    def run_server(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            s.listen()
            print(f"Servidor integrado iniciado en puerto {port}")
            
            while self.running:
                conn, addr = None, None
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error aceptando conexión: {e}")
    
    def handle_client(self, conn, addr):
        try:
            # Recibir tipo de cliente (4 bytes exactos)
            client_type = conn.recv(4)
            if len(client_type) != 4:
                print(f"Cliente {addr} envió cabecera inválida")
                return
            
            client_type = client_type.decode('ascii').strip()
            print(f"Cliente {addr} tipo: {client_type}")
        
            if client_type == "ECG":
                self.handle_ecg_client(conn, addr)
            elif client_type == "IMG":
                self.handle_image_client(conn, addr)
            elif client_type == "PAT":
                self.handle_patient_client(conn, addr)
            elif client_type == "SPO2":
                self.handle_spo2_client(conn, addr)
            elif client_type == "STET":
                self.handle_stethoscope_client(conn, addr)
            else:
                print(f"Tipo de cliente desconocido: {client_type}")
            
        except Exception as e:
            print(f"Error con cliente {addr}: {e}")
        finally:
            conn.close()

    def handle_ecg_client(self, conn, addr):
        buffer = bytearray()
        client_id = None
        header_received = False
        
        try:
            # Recibir cabecera ECG (16 bytes)
            header = conn.recv(16)
            if len(header) == 16:
                client_id, client_type, sampling_rate, num_channels = struct.unpack('<I4sII', header)
                client_type = client_type.decode('ascii').strip('\x00')
                print(f"ECG Client {client_id} connected from {addr}")
                
                while self.running:
                    data = conn.recv(4096)
                    if not data:
                        break
                    
                    # Procesar datos ECG (2 bytes por muestra)
                    samples = []
                    for i in range(0, len(data), 2):
                        if i+2 <= len(data):
                            sample = int.from_bytes(data[i:i+2], 'little', signed=True)
                            samples.append(sample)
                    
                    if samples:
                        self.new_ecg_data.emit(client_id, samples)
                        
        except Exception as e:
            print(f"Error con ECG client {client_id}: {e}")

    def handle_image_client(self, conn, addr):
        try:
            # Recibir ID de cliente (4 bytes)
            client_id = int.from_bytes(conn.recv(4), byteorder='big')
            
            # Recibir tamaño de imagen (4 bytes)
            img_size = int.from_bytes(conn.recv(4), byteorder='big')
            print(f"Image Client {client_id} connected from {addr}, receiving {img_size} bytes")
            
            # Recibir datos de imagen
            img_data = bytearray()
            remaining = img_size
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining))
                if not chunk:
                    break
                img_data.extend(chunk)
                remaining -= len(chunk)
            
            if len(img_data) == img_size:
                self.new_image_data.emit(client_id, bytes(img_data))
            else:
                print(f"Error: Imagen incompleta del cliente {client_id}")
                
        except Exception as e:
            print(f"Error recibiendo imagen: {e}")

    def handle_patient_client(self, conn, addr):
        try:
            # Recibir datos del paciente (formato: ID|NOM1|NOM2|AP_PAT|AP_MAT|CURP|FECHA)
            data = conn.recv(1024).decode('utf-8')
            fields = data.split('|')
            
            if len(fields) >= 7:
                patient_info = {
                    'id': int(fields[0]),
                    'nombre1': fields[1],
                    'nombre2': fields[2],
                    'apellido_paterno': fields[3],
                    'apellido_materno': fields[4],
                    'curp': fields[5],
                    'fecha': fields[6]
                }
                self.new_patient_data.emit(patient_info)
                print(f"Datos del paciente {fields[0]} recibidos")
            else:
                print("Datos del paciente incompletos")
                
        except Exception as e:
            print(f"Error recibiendo datos del paciente: {e}")

    def handle_spo2_client(self, conn, addr):
        try:
            print(f"SPO2 Client connected from {addr}")
            
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                
                # Procesar datos SPO2 (2 bytes por muestra)
                samples = []
                for i in range(0, len(data), 2):
                    if i+2 <= len(data):
                        sample = int.from_bytes(data[i:i+2], 'little', signed=False)
                        samples.append(sample)
                
                if samples:
                    self.new_spo2_data.emit(samples)
                    
        except Exception as e:
            print(f"Error con SPO2 client: {e}")

    def handle_stethoscope_client(self, conn, addr):
        try:
            # Recibir tamaño del audio (4 bytes)
            audio_size = int.from_bytes(conn.recv(4), byteorder='big')
            print(f"Stethoscope Client connected from {addr}, receiving {audio_size} bytes")
            
            # Recibir datos de audio
            audio_data = bytearray()
            remaining = audio_size
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining))
                if not chunk:
                    break
                audio_data.extend(chunk)
                remaining -= len(chunk)
            
            if len(audio_data) == audio_size:
                self.new_stethoscope_data.emit(bytes(audio_data))
                print("Audio del estetoscopio recibido correctamente")
            else:
                print("Error: Audio del estetoscopio incompleto")
                
        except Exception as e:
            print(f"Error recibiendo audio del estetoscopio: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    
    # Crear interfaz
    monitor = MedicalMonitor()
    server = IntegratedServer()
    
    # Conectar señales
    server.new_ecg_data.connect(monitor.add_ecg_data)
    server.new_spo2_data.connect(monitor.add_spo2_data)
    server.new_image_data.connect(monitor.add_image_data)
    server.new_patient_data.connect(monitor.add_patient_data)
    server.new_stethoscope_data.connect(monitor.add_stethoscope_data)
    
    # Iniciar
    monitor.show()
    server.start()
    
    sys.exit(app.exec_())

    print(f"Recibido: {client_type} (bytes: {[b for b in client_type]})")