import customtkinter as ctk
from tkinter import ttk, messagebox
import database.database as database

class ClientsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Formulario para agregar cliente (Izquierda) ---
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        ctk.CTkLabel(form_frame, text="Gestionar Cliente", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        ctk.CTkLabel(form_frame, text="Nombre Completo:").pack(anchor="w", padx=10)
        self.name_entry = ctk.CTkEntry(form_frame, width=250)
        self.name_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(form_frame, text="RNC / Cédula:").pack(anchor="w", padx=10)
        self.rnc_entry = ctk.CTkEntry(form_frame)
        self.rnc_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(form_frame, text="Teléfono:").pack(anchor="w", padx=10)
        self.phone_entry = ctk.CTkEntry(form_frame)
        self.phone_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(form_frame, text="Dirección:").pack(anchor="w", padx=10)
        self.address_entry = ctk.CTkEntry(form_frame)
        self.address_entry.pack(padx=10, pady=(0, 20), fill="x")

        ctk.CTkButton(form_frame, text="Agregar Cliente", command=self.agregar_cliente).pack(pady=10, padx=10, fill="x")

        # --- Lista de clientes (Derecha) ---
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkButton(list_frame, text="Eliminar Seleccionado", fg_color="#D32F2F", hover_color="#B71C1C", command=self.eliminar_cliente_seleccionado).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.clients_tree = ttk.Treeview(list_frame, columns=("ID", "Nombre", "RNC/Cédula", "Teléfono", "Dirección"), show='headings')
        self.clients_tree.heading("ID", text="ID")
        self.clients_tree.heading("Nombre", text="Nombre")
        self.clients_tree.heading("RNC/Cédula", text="RNC/Cédula")
        self.clients_tree.heading("Teléfono", text="Teléfono")
        self.clients_tree.heading("Dirección", text="Dirección")
        self.clients_tree.column("ID", width=50)
        self.clients_tree.column("Nombre", width=200)
        self.clients_tree.column("Dirección", width=250)
        self.clients_tree.grid(row=1, column=0, sticky="nsew")

        self.cargar_clientes()

    def cargar_clientes(self):
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        clientes = database.obtener_clientes()
        for cliente in clientes:
            self.clients_tree.insert("", "end", values=(cliente['_id'], cliente['nombre'], cliente['rnc_cedula'], cliente['telefono'], cliente['direccion']))

    def agregar_cliente(self):
        nombre = self.name_entry.get()
        rnc = self.rnc_entry.get()
        telefono = self.phone_entry.get()
        direccion = self.address_entry.get()

        if not nombre or not rnc:
            messagebox.showerror("Error", "Nombre y RNC/Cédula son obligatorios.", parent=self)
            return
        try:
            database.agregar_cliente(nombre, rnc, telefono, direccion)
            self.name_entry.delete(0, "end")
            self.rnc_entry.delete(0, "end")
            self.phone_entry.delete(0, "end")
            self.address_entry.delete(0, "end")
            self.cargar_clientes()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el cliente. Causa probable: ya existe.\n{e}", parent=self)

    def eliminar_cliente_seleccionado(self):
            selected_item = self.clients_tree.selection()
            if not selected_item:
                messagebox.showwarning("Sin selección", "Por favor, seleccione un cliente de la lista.", parent=self)
                return

            cliente_id = self.clients_tree.item(selected_item[0])['values'][0]
            if messagebox.askyesno("Confirmar", "¿Está seguro de que desea eliminar a este cliente?", parent=self):
                database.eliminar_cliente(cliente_id)
                self.cargar_clientes()