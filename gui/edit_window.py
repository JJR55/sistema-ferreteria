import customtkinter as ctk
from tkinter import messagebox
import database.database as database

class EditWindow(ctk.CTkToplevel):
    def __init__(self, master, product_data, inventory_frame):
        super().__init__(master)

        self.product_data = product_data
        self.inventory_frame = inventory_frame # Para poder recargar la tabla

        self.title("Editar Producto")
        self.geometry("400x400")
        self.grab_set() # Hace que esta ventana sea modal (bloquea la principal)

        # --- Widgets ---
        self.id_label = ctk.CTkLabel(self, text=f"Editando Producto ID: {self.product_data[0]}")
        self.id_label.pack(pady=10)

        # --- Widgets en el nuevo orden ---
        self.codigo_entry = ctk.CTkEntry(self, width=300)
        self.codigo_entry.insert(0, self.product_data[1])
        self.codigo_entry.pack(pady=5)

        self.nombre_entry = ctk.CTkEntry(self, width=300)
        self.nombre_entry.insert(0, self.product_data[2])
        self.nombre_entry.pack(pady=5)

        self.costo_entry = ctk.CTkEntry(self, width=300)
        self.costo_entry.insert(0, self.product_data[3])
        self.costo_entry.pack(pady=5)

        self.precio_entry = ctk.CTkEntry(self, width=300)
        self.precio_entry.insert(0, self.product_data[4])
        self.precio_entry.pack(pady=5)

        self.stock_entry = ctk.CTkEntry(self, width=300)
        self.stock_entry.insert(0, self.product_data[5])
        self.stock_entry.pack(pady=5)

        self.stock_minimo_entry = ctk.CTkEntry(self, width=300)
        self.stock_minimo_entry.insert(0, self.product_data[6])
        self.stock_minimo_entry.pack(pady=5)

        self.departamentos = ["Ferretería", "Repuestos", "Hogar"]
        self.departamento_menu = ctk.CTkOptionMenu(self, values=self.departamentos, width=300)
        self.departamento_menu.set(self.product_data[7])
        self.departamento_menu.pack(pady=5)

        self.save_button = ctk.CTkButton(self, text="Guardar Cambios", command=self.guardar_cambios)
        self.save_button.pack(pady=20)

    def guardar_cambios(self):
        # Obtener los nuevos valores
        id_producto = self.product_data[0]
        codigo = self.codigo_entry.get()
        nombre = self.nombre_entry.get()
        costo = self.costo_entry.get()
        precio = self.precio_entry.get()
        stock = self.stock_entry.get()
        stock_minimo = self.stock_minimo_entry.get()
        departamento = self.departamento_menu.get()

        # Validaciones
        if not all([codigo, nombre, precio, costo, stock, stock_minimo]):
            messagebox.showerror("Error de validación", "Todos los campos son requeridos.", parent=self)
            return
        try:
            costo_val = float(costo)
            precio_val = float(precio)
            stock_val = int(stock)
            stock_minimo_val = int(stock_minimo)
        except ValueError:
            messagebox.showerror("Error de formato", "Precio, costo, stock e inventario mínimo deben ser números.", parent=self)
            return

        # Confirmación
        if not messagebox.askyesno("Confirmar", "¿Está seguro de que desea guardar los cambios?", parent=self):
            return

        # Llamar a la función de la base de datos
        try:
            database.actualizar_producto(id_producto, codigo, nombre, costo_val, precio_val, stock_val, stock_minimo_val, departamento)
            messagebox.showinfo("Éxito", "Producto actualizado correctamente.", parent=self)
            
            # Recargar la tabla en la ventana principal y cerrar esta ventana
            self.inventory_frame.cargar_productos()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error en la Base de Datos", f"No se pudo actualizar el producto: {e}", parent=self)
