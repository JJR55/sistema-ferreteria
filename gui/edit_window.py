import customtkinter as ctk
from tkinter import messagebox
import database.database as database
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .inventory_frame import InventoryFrame

class EditWindow(ctk.CTkToplevel):
    def __init__(self, master, product_data, inventory_frame: "InventoryFrame"):
        super().__init__(master)

        self.product_data = product_data
        self.inventory_frame = inventory_frame # Para poder recargar la tabla

        # Obtener el producto completo de la base de datos para tener unidad_medida
        product_id = self.product_data[0]
        self.producto_completo = None
        try:
            # Buscar por ID convirtiendo a ObjectId si es necesario
            productos = database.obtener_productos()
            for prod in productos:
                if prod.get('id') == product_id:
                    self.producto_completo = prod
                    break
        except Exception as e:
            print(f"Error obteniendo producto completo: {e}")

        self.title("Editar Producto")
        self.geometry("450x450")  # Aumentamos el tamaño para el nuevo campo
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

        self.departamentos = ["Ferretería", "Repuestos", "Hogar", "Electricidad", "Plomería"]
        self.departamento_menu = ctk.CTkOptionMenu(self, values=self.departamentos, width=300)
        self.departamento_menu.set(self.product_data[7])
        self.departamento_menu.pack(pady=5)

        # Unidad de Medida
        self.unidad_medidas = ["Unidad", "Par", "Libra", "Kilogramo", "Pies", "Metro", "Metros", "Litro", "Galón", "Caja", "Paquete", "Rollo"]
        self.unidad_medida_menu = ctk.CTkOptionMenu(self, values=self.unidad_medidas, width=300)
        # Obtener el valor actual de unidad_medida del producto
        current_unidad = self.producto_completo.get('unidad_medida', 'Unidad') if self.producto_completo else 'Unidad'
        self.unidad_medida_menu.set(current_unidad)
        self.unidad_medida_menu.pack(pady=5)

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
        unidad_medida = self.unidad_medida_menu.get()

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
            database.actualizar_producto(id_producto, codigo, nombre, costo_val, precio_val, stock_val, stock_minimo_val, departamento, unidad_medida)
            messagebox.showinfo("Éxito", "Producto actualizado correctamente.", parent=self)

            # Recargar la tabla en la ventana principal y cerrar esta ventana
            self.inventory_frame.cargar_productos()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error en la Base de Datos", f"No se pudo actualizar el producto: {e}", parent=self)
