import customtkinter as ctk
from tkinter import ttk, messagebox
import database.database as database

class UserManagementFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Frame para Agregar Usuario (Izquierda) ---
        add_user_frame = ctk.CTkFrame(self)
        add_user_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="ns")

        ctk.CTkLabel(add_user_frame, text="Agregar Usuario", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        ctk.CTkLabel(add_user_frame, text="Nombre de Usuario:").pack(anchor="w", padx=10)
        self.username_entry = ctk.CTkEntry(add_user_frame)
        self.username_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(add_user_frame, text="Contraseña:").pack(anchor="w", padx=10)
        self.password_entry = ctk.CTkEntry(add_user_frame, show="*")
        self.password_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(add_user_frame, text="Rol:").pack(anchor="w", padx=10)
        self.role_menu = ctk.CTkOptionMenu(add_user_frame, values=["Cajero", "Administrador"])
        self.role_menu.pack(padx=10, pady=(0, 20), fill="x")

        self.add_button = ctk.CTkButton(add_user_frame, text="Agregar Usuario", command=self.agregar_usuario)
        self.add_button.pack(pady=10, padx=10, fill="x")

        # --- Frame para Lista de Usuarios (Derecha) ---
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        # Botones de acción para la lista
        action_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.change_pass_button = ctk.CTkButton(action_frame, text="Cambiar Contraseña", command=self.cambiar_contrasena_seleccionado)
        self.change_pass_button.pack(side="left", padx=5)

        self.delete_button = ctk.CTkButton(action_frame, text="Eliminar Seleccionado", fg_color="#D32F2F", hover_color="#B71C1C", command=self.eliminar_usuario_seleccionado)
        self.delete_button.pack(side="left", padx=5)

        # Tabla de usuarios
        self.user_tree = ttk.Treeview(list_frame, columns=("ID", "Nombre de Usuario", "Rol"), show='headings')
        self.user_tree.heading("ID", text="ID")
        self.user_tree.heading("Nombre de Usuario", text="Nombre de Usuario")
        self.user_tree.heading("Rol", text="Rol")
        self.user_tree.column("ID", width=50)
        self.user_tree.grid(row=1, column=0, sticky="nsew")

        self.cargar_usuarios()

    def cargar_usuarios(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        
        usuarios = database.obtener_todos_los_usuarios()
        for usuario in usuarios:
            self.user_tree.insert("", "end", values=usuario)

    def agregar_usuario(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = self.role_menu.get()

        if not username or not password:
            messagebox.showerror("Error", "Nombre de usuario y contraseña son requeridos.", parent=self)
            return

        try:
            database.crear_usuario(username, password, role)
            messagebox.showinfo("Éxito", "Usuario creado correctamente.", parent=self)
            self.username_entry.delete(0, "end")
            self.password_entry.delete(0, "end")
            self.cargar_usuarios()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el usuario. Causa probable: el nombre de usuario ya existe.\n\nError: {e}", parent=self)

    def eliminar_usuario_seleccionado(self):
        selected_item = self.user_tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un usuario de la lista.", parent=self)
            return

        user_data = self.user_tree.item(selected_item[0])['values']
        user_id = user_data[0]
        username = user_data[1]

        if username == 'admin':
            messagebox.showerror("Acción no permitida", "No se puede eliminar al usuario 'admin' principal.", parent=self)
            return

        if messagebox.askyesno("Confirmar", f"¿Está seguro de que desea eliminar al usuario '{username}'?", parent=self):
            database.eliminar_usuario(user_id)
            self.cargar_usuarios()

    def cambiar_contrasena_seleccionado(self):
        selected_item = self.user_tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un usuario de la lista.", parent=self)
            return

        user_data = self.user_tree.item(selected_item[0])['values']
        user_id = user_data[0]
        username = user_data[1]

        dialog = ctk.CTkInputDialog(text=f"Ingrese la nueva contraseña para '{username}':", title="Cambiar Contraseña")
        new_password = dialog.get_input()

        if new_password:
            try:
                database.actualizar_contrasena(user_id, new_password)
                messagebox.showinfo("Éxito", f"La contraseña para '{username}' ha sido actualizada.", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar la contraseña.\n\nError: {e}", parent=self)
