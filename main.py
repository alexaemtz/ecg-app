import customtkinter as ctk
import datetime
from PIL import Image
from modules.com import ComunicationGUI
from modules.csv_loader import CsvLoaderGUI

# Seleccion del tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("themes/medical.json")

# ----------- Crear ventana principal -------------
class MainWindow():
    def __init__(self):
        """Constructor de la ventana principal"""
        super().__init__()
        self.root = ctk.CTk()
        self.root.title("Monitor de ECG")
        self.root.geometry("1900x1010")
        self.root.iconbitmap("assets/icons/ecg.ico")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.title_font = ctk.CTkFont(family="Poppins SemiBold", size=24)
        self.subtitle_font = ctk.CTkFont(family="Poppins Medium Italic", size=14)
        self.text_font = ctk.CTkFont(family="Poppins Medium", size=14)

        self.sidebar_expanded = True
        self.sidebar_width = 220
        self.sidebar_collapsed_width = 80

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar (usando pack)
        self.sidebar = ctk.CTkFrame(self.main_frame, width=self.sidebar_width, fg_color="#434E5A", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Botón colapsar
        self.toggle_image = ctk.CTkImage(Image.open("assets/icons/menu.png"), size=(32, 32))
        self.toggle_button = ctk.CTkButton(self.sidebar, text=" Menú", width=40, height=40, command=self.toggle_sidebar, fg_color="transparent", anchor="w", 
                                           image=self.toggle_image, compound="left", font=self.text_font)
        self.toggle_button.pack(padx=10, pady=(10, 20), anchor="w")

        # Cargar íconos
        self.icon_home = ctk.CTkImage(Image.open("assets/icons/home.png"), size=(32, 32))
        self.icon_graph = ctk.CTkImage(Image.open("assets/icons/graph.png"), size=(32, 32))
        self.icon_play = ctk.CTkImage(Image.open("assets/icons/play.png"), size=(32, 32))
        self.icon_annotate = ctk.CTkImage(Image.open("assets/icons/pen.png"), size=(32, 32))
        self.icon_upload = ctk.CTkImage(Image.open("assets/icons/upload.png"), size=(32, 32))
        self.icon_save = ctk.CTkImage(Image.open("assets/icons/save.png"), size=(32, 32))
        self.icon_filter = ctk.CTkImage(Image.open("assets/icons/filter.png"), size=(32, 32))

        # Botones del menú
        self.menu_info = [
            (self.icon_home, "Inicio", self.load_home_page),
            (self.icon_graph, "ECG en tiempo real", self.load_ecg_page),
            (self.icon_upload, "Cargar señal", self.csv_loader)
        ]
        
        self.menu_buttons = []
        for icon, label, command in self.menu_info:
            btn = ctk.CTkButton(self.sidebar, text=label, image=icon, compound="left", anchor="w", height=40, fg_color="transparent", font=self.text_font, command=command)
            btn.pack(fill="x", padx=10, pady=5)
            self.menu_buttons.append(btn)

        # Área de contenido
        self.content_area = ctk.CTkFrame(self.main_frame)
        self.content_area.pack(side="left", fill="both", expand=True)

        # Switch tema
        self.theme_var = ctk.StringVar(value="Oscuro")
        self.theme_combobox = ctk.CTkComboBox(self.sidebar, values=["Claro", "Oscuro"], command=self.theme_event, font=self.text_font, variable=self.theme_var)
        self.theme_combobox.pack(padx=10, pady=20, side="top", anchor="w")
        
        self.load_home_page()
        
    def clear_content_area(self):
        """Limpia el área de contenido"""
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def toggle_sidebar(self):
        """Cambia el estado de la barra lateral. Permite expandir o colapsar."""
        self.sidebar_expanded = not self.sidebar_expanded
        new_width = self.sidebar_width if self.sidebar_expanded else self.sidebar_collapsed_width
        self.sidebar.configure(width=new_width)

        # Cambia texto de botones según estado
        for i, btn in enumerate(self.menu_buttons):
            icon, label, command = self.menu_info[i]
            btn.configure(text=label if self.sidebar_expanded else "")

        # Cambia texto del botón de menú
        self.toggle_button.configure(text=" Menú" if self.sidebar_expanded else "", anchor="w")
        self.sidebar.update_idletasks()

    def theme_event(self, choice):
        """Cambia el tema de la aplicación según la selección del usuario."""
        choice = self.theme_var.get()
        if choice == "Claro":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    def load_home_page(self):
        """Carga la página de inicio con información y estado del sistema."""
        self.clear_content_area()
        try:
            if self.theme_var.get() == "Claro":
                home_img = ctk.CTkImage(Image.open("assets/icons/heart-blue.png"), size=(120, 120))
            else:
                home_img = ctk.CTkImage(Image.open("assets/icons/heartbeat.png"), size=(120, 120))
            img_label = ctk.CTkLabel(self.content_area, image=home_img, text="")
            img_label.image = home_img
            img_label.pack(pady=(40, 10))
        except Exception as e:
            print("Error cargando imagen:", e)
            
        # Home Frame
        home_frame = ctk.CTkFrame(self.content_area, corner_radius=10)
        home_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Título
        title_gui = ctk.CTkLabel(home_frame, text="Bienvenido a ECG Pro 1D", font=self.title_font)
        title_gui.pack(pady=(20, 10))
        
        # Subtítulo
        subtitle_label = ctk.CTkLabel(home_frame, text="Monitoreo de ECG en tiempo real con filtros y anotaciones clínicas", font=self.subtitle_font)
        subtitle_label.pack(pady=(0, 30))
        
        # Estado del sistema
        status_frame = ctk.CTkFrame(home_frame, corner_radius=8)
        status_frame.pack(pady=10, padx=40, fill="x")
        
        status_label = ctk.CTkLabel(status_frame, text="📡 Dispositivo: No conectado", anchor="w")
        status_label.pack(pady=5, padx=20, fill="x")
        
        mode_label = ctk.CTkLabel(status_frame, text="⚙️ Modo actual: Esperando", anchor="w")
        mode_label.pack(pady=5, padx=20, fill="x")
        
        file_label = ctk.CTkLabel(status_frame, text=f"📁 Última sesión: {datetime.date.today().strftime('%d/%m/%Y')}", anchor="w")
        file_label.pack(pady=5, padx=20, fill="x")
        
        # Consejos útiles
        tip_label = ctk.CTkLabel(home_frame, text="💡 Consejo: Verifica la conexión antes de iniciar la adquisición.", font=self.subtitle_font)
        tip_label.pack(pady=(30, 10))

        # Botón de inicio
        start_button = ctk.CTkButton(home_frame, text="Iniciar monitoreo", image=self.icon_play, compound="left", font=self.subtitle_font, command=self.load_ecg_page)
        start_button.pack(pady=20)

        # Footer
        footer_label = ctk.CTkLabel(home_frame, text="Versión 1.0.0   |   Desarrollado por BioHer")
        footer_label.pack(side="bottom", pady=10)

    def load_ecg_page(self):
        self.clear_content_area()
        self.title_gui = ctk.CTkLabel(self.content_area, text="Monitor de electrocardiograma", font=self.title_font)
        self.title_gui.pack(padx=10, pady=10, anchor="w")
        self.com_gui = ComunicationGUI(self.content_area)
        self.com_gui.pack(padx=10, pady=10)
        
    #def load_csv_page(self):
    #    self.clear_content_area()
    #    self.title_gui = ctk.CTkLabel(self.content_area, text="Anotaciones de señal", font=self.title_font)
    #    self.title_gui.pack(padx=10, pady=10, anchor="w")
    #    self.csv_gui = CsvLoaderGUI(self.content_area)
    #    self.csv_gui.pack(padx=10, pady=10)
        
    def csv_loader(self):
        self.clear_content_area()
        self.title_gui = ctk.CTkLabel(self.content_area, text="Anotaciones de señal", font=self.title_font)
        self.title_gui.pack(padx=10, pady=10, anchor="w")
        self.csv_loader_gui = CsvLoaderGUI(self.content_area)
        self.csv_loader_gui.pack(padx=10, pady=10)
        
    def place_holder_function(self):
        self.clear_content_area()
        label = ctk.CTkLabel(self.content_area, text="Función en desarrollo...", font=self.text_font)
        label.pack(padx=10, pady=10, expand=True)
        
    def on_closing(self):
        self.root.destroy()
        
if __name__ == "__main__":
    main = MainWindow()
    main.root.mainloop()
    