import customtkinter as ctk

from .inventory_frame import InventoryFrame
from .pos_frame import PosFrame
from .reports_frame import ReportsFrame
from .login_frame import LoginFrame
from .user_management_frame import UserManagementFrame
from .returns_frame import ReturnsFrame
from .accounts_payable_frame import AccountsPayableFrame

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Inventario y Ventas")
        self.geometry("1100x580")

        self.current_user = None

        # Configurar el layout principal (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Frame de Navegación (Izquierda) ---
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(6, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="Ferretería XYZ",
                                                   font=ctk.CTkFont(size=20, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.btn_inventario = ctk.CTkButton(self.navigation_frame, text="Inventario", command=self.mostrar_frame_inventario)
        self.btn_inventario.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_punto_venta = ctk.CTkButton(self.navigation_frame, text="Punto de Venta", command=self.mostrar_frame_pos)
        self.btn_punto_venta.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_reportes = ctk.CTkButton(self.navigation_frame, text="Reportes", command=self.mostrar_frame_reportes)
        self.btn_reportes.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_devoluciones = ctk.CTkButton(self.navigation_frame, text="Devoluciones", command=self.mostrar_frame_devoluciones)
        self.btn_devoluciones.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_cuentas_pagar = ctk.CTkButton(self.navigation_frame, text="Cuentas por Pagar", command=self.mostrar_frame_cuentas_pagar)
        self.btn_cuentas_pagar.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.btn_gestion_usuarios = ctk.CTkButton(self.navigation_frame, text="Gestionar Usuarios", command=self.mostrar_frame_gestion_usuarios)
        self.btn_gestion_usuarios.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.logout_button = ctk.CTkButton(self.navigation_frame, text="Cerrar Sesión", fg_color="#D32F2F", hover_color="#B71C1C", command=self.logout)
        self.logout_button.grid(row=7, column=0, padx=20, pady=20, sticky="s")

        # --- Frame Principal (Derecha) ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # --- Frame de Login ---
        self.login_frame = LoginFrame(self, on_login_success=self.on_login_success, fg_color="transparent")
        self.login_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # Ocultar el frame principal al inicio
        self.navigation_frame.grid_remove()
        self.main_frame.grid_remove()

    def on_login_success(self, user_info):
        self.current_user = user_info
        self.login_frame.grid_remove() # Ocultar el frame de login

        # Mostrar los frames principales
        self.navigation_frame.grid()
        self.main_frame.grid()

        # Aplicar permisos
        if self.current_user['role'] == 'Cajero':
            self.btn_inventario.grid_remove()
            self.btn_reportes.grid_remove()
            self.btn_cuentas_pagar.grid_remove()
            self.btn_gestion_usuarios.grid_remove()
        else: # Administrador
            self.btn_inventario.grid()
            self.btn_reportes.grid()
            self.btn_cuentas_pagar.grid()
            self.btn_gestion_usuarios.grid()

        self.mostrar_frame_bienvenida()

    def logout(self):
        self.current_user = None
        # Ocultar frames principales
        self.navigation_frame.grid_remove()
        self.main_frame.grid_remove()
        # Mostrar el frame de login
        self.login_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def mostrar_frame_bienvenida(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        label = ctk.CTkLabel(self.main_frame, text="Seleccione una opción del menú", font=ctk.CTkFont(size=24))
        label.pack(pady=50, padx=50)

    def mostrar_frame_inventario(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.inventory_frame = InventoryFrame(master=self.main_frame)

    def mostrar_frame_pos(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.pos_frame = PosFrame(master=self.main_frame, current_user=self.current_user)
        # Llamar a un método para poner el foco en la entrada de código
        self.pos_frame.on_show()

    def mostrar_frame_reportes(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.reports_frame = ReportsFrame(master=self.main_frame)

    def mostrar_frame_gestion_usuarios(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.user_management_frame = UserManagementFrame(master=self.main_frame)

    def mostrar_frame_devoluciones(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.returns_frame = ReturnsFrame(master=self.main_frame, current_user=self.current_user)

    def mostrar_frame_cuentas_pagar(self):
        # Limpiar el frame principal
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.accounts_payable_frame = AccountsPayableFrame(master=self.main_frame)