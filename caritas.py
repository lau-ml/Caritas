import tkinter as tk
from tkinter import font as tkfont
import platform
import os
import sys

# --- REQUISITO: INSTALAR PILLOW (pip install pillow) ---
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PARA VER EL FONDO: pip install pillow")

# Sonido
try:
    import winsound
    SOUND_AVAILABLE = False
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False
    SOUND_AVAILABLE = False


def resource_path(relative_path):
    """ Obtiene la ruta absoluta del recurso, funciona para dev y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FocusTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Temporizador")
        # Tamaño inicial equilibrado
        self.width = 450
        self.height = 350
        
        # POSICIONAR EN ESQUINA SUPERIOR DERECHA
        self.position_top_right(self.width, self.height)
        
        #Es tamaño redimensionable
        self.root.resizable(True, True)
        
        # Translucidez (0.0 = Foto pura, 1.0 = Negro puro)
        self.TRANSLUCENCY_FACTOR = 0.7

        self.BG_MAIN    = "#101010" 
        self.FG_TEXT    = "#FFFFFF" 
        
        self.C_FLOW     = "#00E676" # Verde
        self.C_FOCUS    = "#FFD600" # Amarillo
        self.C_URGENT   = "#FF3D00" # Rojo
        self.C_DONE     = "#AAAAAA" # Gris
        self.C_OVERTIME = "#FF00FF" # Magenta
    
        self.root.configure(bg=self.BG_MAIN)

        # --- TAMAÑOS DE FUENTE (Ajustados a tu gusto) ---
        self.base_font_size_timer = 45  
        self.base_font_size_icon = 70   
        
        self.font_input = ("Helvetica", 30) 
        self.font_ui_title = ("Helvetica", 10, "bold")
        self.font_ui_instr = ("Helvetica", 9)
        self.font_close = ("Arial", 14)
        
        self.emoji_font_family = "Segoe UI Emoji" if IS_WINDOWS else "Noto Color Emoji"

        self.total_seconds = 0; self.remaining = 0; self.running = False
        self.blinking = False; self.timer_id = None
        self.current_color = self.C_FLOW
        self.bg_image_original = None
        self.resize_job = None

        # ===================================================================
        # CANVAS PRINCIPAL
        # ===================================================================
        self.canvas = tk.Canvas(root, highlightthickness=0, bg=self.BG_MAIN)
        self.canvas.pack(fill="both", expand=True)

        # 1. IMAGEN DE FONDO
        ruta_imagen = resource_path("background.jpg")
        if PIL_AVAILABLE and os.path.exists(ruta_imagen):
            try:
                self.bg_image_original = Image.open(ruta_imagen).convert("RGB")
            except:
                pass
        
        self.bg_photo_id = self.canvas.create_image(0, 0, anchor="nw", tags="bg_img")

        # 2. SETUP UI (Configuración)
        # Botón cerrar
        self.btn_close = self.canvas.create_text(0, 0, text="✕", font=self.font_close, 
                                                 fill="#CCCCCC", anchor="ne", tags="setup_ui")
        self.canvas.tag_bind(self.btn_close, "<Button-1>", self.close_app)
        
        # Título y línea
        self.lbl_setup_title = self.canvas.create_text(0, 0, text="M I N U T O S",
                                font=self.font_ui_title, fill="#EEEEEE", tags="setup_ui")
        
        self.lbl_setup_instr = self.canvas.create_text(0, 0, text="[Enter] Iniciar  |  [Esc] Parar | [Espacio] Pausar",
                                font=self.font_ui_instr, fill="#AAAAAA", tags="setup_ui")

        self.setup_line = self.canvas.create_line(0,0,0,0, fill=self.C_FLOW, width=3, tags="setup_ui")

        # --- INPUT CORRECTO ---
        # Usamos el mismo color de fondo que BG_MAIN para que no parezca un parche
        self.entry = tk.Entry(root, font=self.font_input, width=4, justify="center", bd=0, 
                              bg=self.BG_MAIN, fg=self.FG_TEXT, insertbackground=self.C_FLOW)
        self.entry.insert(0, "25")
        self.entry.bind("<Return>", self.start_timer)
        # Se posiciona con .place() más abajo

        # 3. TIMER UI (Reloj)
        self.icon_id = self.canvas.create_text(0, 0, text="😌",
                                               font=(self.emoji_font_family, self.base_font_size_icon), 
                                               fill=self.C_FLOW, tags="timer_ui")
        
        self.time_id = self.canvas.create_text(0, 0, text="00:00",
                                               font=("Helvetica", self.base_font_size_timer, "bold"), 
                                               fill=self.FG_TEXT, tags="timer_ui")

        # Eventos
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<Escape>", self.stop_timer)
        self.root.bind("<Key-space>", self.pause_timer)
        self.canvas.tag_bind("timer_ui", "<Button-1>", self.stop_timer)

        # ARRANQUE
        self.show_setup()
        
        # Forzar foco y repintado
        self.root.after(10, self.reposition_ui_elements)
        self.root.after(100, self.entry.focus_set)


    # --- POSICIONAMIENTO TOP-RIGHT ---
    def position_top_right(self, width, height):
        try:
            screen_width = self.root.winfo_screenwidth()
            # screen_height no es necesario para alinear arriba
            
            # Margen derecho e inferior (para barra de tareas gnome/kde)
            margin_x = 0
            margin_y = 0 

            x = screen_width - width - margin_x
            y = margin_y

            self.root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        except:
            pass

    # --- RESPONSIVE LOGIC ---
    def on_resize(self, event):
        self.width = event.width
        self.height = event.height
        
        self.reposition_ui_elements()
        
        if self.resize_job: self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self.resize_background_image)

    def reposition_ui_elements(self):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if w < 10: w, h = self.width, self.height

        cx = w / 2
        cy = h / 2

        # --- SETUP UI ---
        self.canvas.coords(self.btn_close, w-20, 20)
        self.canvas.coords(self.lbl_setup_title, cx, cy - 50)
        self.canvas.coords(self.setup_line, cx-30, cy+30, cx+30, cy+30)
        self.canvas.coords(self.lbl_setup_instr, cx, h - 40)

        # --- TIMER UI (Posiciones extremas) ---
        icon_y = h * 0.2 
        time_y = h * 0.9 
        
        # Escala suave
        scale_factor = min(w, h) / 350 
        new_icon_size = int(self.base_font_size_icon * scale_factor)
        new_time_size = int(self.base_font_size_timer * scale_factor)
        
        # Límites
        new_icon_size = max(40, min(new_icon_size, 120))
        new_time_size = max(30, min(new_time_size, 90))

        self.canvas.itemconfig(self.icon_id, font=(self.emoji_font_family, new_icon_size))
        self.canvas.coords(self.icon_id, cx, icon_y)
        
        self.canvas.itemconfig(self.time_id, font=("Helvetica", new_time_size, "bold"))
        self.canvas.coords(self.time_id, cx, time_y)


    def resize_background_image(self):
        if not self.bg_image_original or not PIL_AVAILABLE: return
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w < 10: w, h = self.width, self.height

            resized_img = self.bg_image_original.resize((w, h), Image.Resampling.LANCZOS)
            black_overlay = Image.new("RGB", resized_img.size, "black")
            blended_img = Image.blend(resized_img, black_overlay, self.TRANSLUCENCY_FACTOR)
            
            self.bg_photo = ImageTk.PhotoImage(blended_img)
            self.canvas.itemconfig(self.bg_photo_id, image=self.bg_photo)
            self.canvas.tag_lower("bg_img")
        except: pass

    # --- UI HELPERS ---
    def show_setup(self):
        self.canvas.itemconfigure("setup_ui", state="normal")
        self.canvas.itemconfigure("timer_ui", state="hidden")
        # Usamos PLACE con coordenadas relativas (Centro absoluto)
        self.entry.place(relx=0.5, rely=0.5, anchor="center")
        self.entry.focus_set()
        
    def show_timer(self):
        self.canvas.itemconfigure("setup_ui", state="hidden")
        self.canvas.itemconfigure("timer_ui", state="normal")
        self.entry.place_forget()
        self.update_ui(self.C_FLOW, "😌")

    def close_app(self, event=None): self.root.destroy()

    # --- TIMER LOGIC ---
    def start_timer(self, event=None):
        try:
            minutes = int(self.entry.get())
            self.total_seconds = minutes * 60
            self.remaining = self.total_seconds
            self.running = True
            self.blinking = False
            self.show_timer()
            self.tick()
        except ValueError: pass

    def tick(self):
        if not self.running: return
        
        # Formateo que soporta números negativos
        abs_seconds = abs(self.remaining)
        m, s = divmod(abs_seconds, 60)
        sign = "-" if self.remaining < 0 else ""
        self.canvas.itemconfig(self.time_id, text=f"{sign}{m:02}:{s:02}")

        # Lógica de estados según el tiempo restante
        if self.remaining > 0:
            percent = self.remaining / self.total_seconds
            if percent > 0.5:   self.check_update(self.C_FLOW, "😌")
            elif percent > 0.2: self.check_update(self.C_FOCUS, "😐")
            else:               self.check_update(self.C_URGENT, "😰")
        elif self.remaining == 0:
            self.trigger_alarm() # Se activa el parpadeo
        else:
            # Estado de Tiempo Extra (Overtime)
            self.check_update(self.C_OVERTIME, "💀")

        self.remaining -= 1 # Sigue restando por debajo de cero
        self.timer_id = self.root.after(1000, self.tick)
            

    def check_update(self, color, icon):
        if self.current_color != color: self.update_ui(color, icon)

    def update_ui(self, color, icon):
        self.current_color = color
        self.canvas.itemconfig(self.icon_id, text=icon, fill=color)

    def trigger_alarm(self):
        # Ya no ponemos self.running = False para que no se detenga
        self.blinking = True
        self.blink_loop()

    def blink_loop(self):
        if not self.blinking: return        
        # Parpadeo rápido solo al llegar a cero (primeros 5 segundos)
        if abs(self.remaining) < 5:
            current_fill = self.canvas.itemcget(self.icon_id, "fill")
            next_c = self.C_DONE if current_fill == self.C_URGENT else self.C_URGENT
            self.canvas.itemconfig(self.icon_id, fill=next_c)
            self.timer_id = self.root.after(500, self.blink_loop)
        else:
            self.blinking = False # Detener parpadeo, pero el tick sigue

    def stop_timer(self, event=None):
        self.running = False; self.blinking = False
        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.show_setup()
        
    def pause_timer(self, event=None):
        if (self.running):
            self.running= False;
            self.root.after_cancel(self.timer_id);
        else:
            self.running = True;
            self.timer_id = self.root.after(1000, self.tick)

if __name__ == "__main__":
    root = tk.Tk()
    app = FocusTimer(root)
    root.mainloop()
    
    
