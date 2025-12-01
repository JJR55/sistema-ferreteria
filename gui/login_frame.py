import customtkinter as ctk
from tkinter import messagebox
import database.database as database
from gui.security import hash_password, check_password

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success, **kwargs):
        super().__init__(master, **kwargs)

        self.on_login_success = on_login_success

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(container, text="Inicio de Sesión", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        self.username_entry = ctk.CTkEntry(container, placeholder_text="Usuario", width=250)
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(container, placeholder_text="Contraseña", show="*", width=250)
        self.password_entry.pack(pady=10)
        self.password_entry.bind("<Return>", self.login)

        self.login_button = ctk.CTkButton(container, text="Ingresar", command=self.login, width=250)
        self.login_button.pack(pady=20)

        self.error_label = ctk.CTkLabel(container, text="", text_color="red")
        self.error_label.pack()

    def login(self, event=None):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Usuario y contraseña son requeridos.")
            return

        user_data = database.obtener_usuario_por_nombre(username)

        if user_data and check_password(user_data['hash_contrasena'], password):
            self.error_label.configure(text="")
            user_info = {
                "id": str(user_data['_id']), # MongoDB _id es un ObjectId, lo convertimos a string
                "username": user_data['nombre_usuario'],
                "role": user_data['rol']
            }
            self.on_login_success(user_info)
        else:
            self.error_label.configure(text="Usuario o contraseña incorrectos.")
