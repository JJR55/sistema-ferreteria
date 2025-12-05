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
        self.geometry("450x500")  # Aumentamos el tamaño para el nuevo layout
        self.grab_set() # Hace que esta ventana sea modal (bloquea la principal)

        # Frame principal para padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)
        main_frame.grid_columnconfigure(1, weight=1)

        # --- Widgets ---
        ctk.CTkLabel(main_frame, text="Código de Barras:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.codigo_entry = ctk.CTkEntry(main_frame)
        self.codigo_entry.insert(0, self.product_data[1])
        self.codigo_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Nombre del Producto:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
        self.nombre_entry = ctk.CTkEntry(main_frame)
        self.nombre_entry.insert(0, self.product_data[2])
        self.nombre_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Precio Costo:").grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
        self.costo_entry = ctk.CTkEntry(main_frame)
        self.costo_entry.insert(0, self.product_data[3])
        self.costo_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Precio Venta:").grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")
        self.precio_entry = ctk.CTkEntry(main_frame)
        self.precio_entry.insert(0, self.product_data[4])
        self.precio_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Stock Actual:").grid(row=4, column=0, padx=(0, 10), pady=5, sticky="w")
        self.stock_entry = ctk.CTkEntry(main_frame)
        self.stock_entry.insert(0, self.product_data[5])
        self.stock_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Stock Mínimo:").grid(row=5, column=0, padx=(0, 10), pady=5, sticky="w")
        self.stock_minimo_entry = ctk.CTkEntry(main_frame)
        self.stock_minimo_entry.insert(0, self.product_data[6])
        self.stock_minimo_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(main_frame, text="Departamento:").grid(row=6, column=0, padx=(0, 10), pady=5, sticky="w")
        self.departamentos = ["Ferretería", "Repuestos", "Hogar", "Electricidad", "Plomería"]
        self.departamento_menu = ctk.CTkOptionMenu(main_frame, values=self.departamentos)
        self.departamento_menu.set(self.product_data[7])
        self.departamento_menu.grid(row=6, column=1, padx=5, pady=5, sticky="ew")

        # Unidad de Medida
        ctk.CTkLabel(main_frame, text="Unidad de Medida:").grid(row=7, column=0, padx=(0, 10), pady=5, sticky="w")
        self.unidad_medidas = ["Unidad", "Par", "Libra", "Kilogramo", "Pies", "Metro", "Metros", "Litro", "Galón", "Caja", "Paquete", "Rollo"]
        self.unidad_medida_menu = ctk.CTkOptionMenu(main_frame, values=self.unidad_medidas)
        # Obtener el valor actual de unidad_medida del producto
        current_unidad = self.producto_completo.get('unidad_medida', 'Unidad') if self.producto_completo else 'Unidad'
        self.unidad_medida_menu.set(current_unidad)
        self.unidad_medida_menu.grid(row=7, column=1, padx=5, pady=5, sticky="ew")

        # Botón de guardar
        self.save_button = ctk.CTkButton(main_frame, text="Guardar Cambios", command=self.guardar_cambios, height=40)
        self.save_button.grid(row=8, column=0, columnspan=2, padx=5, pady=20, sticky="ew")

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
