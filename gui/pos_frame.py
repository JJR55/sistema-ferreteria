import customtkinter as ctk
from tkinter import ttk, messagebox
import database.database as database

from gui.printer import imprimir_ticket
class PosFrame(ctk.CTkFrame):
    def __init__(self, master, current_user, **kwargs):
        super().__init__(master, **kwargs)

        # Constante para el ITBIS (18% en RD)
        self.ITBIS_RATE = 0.18
        self.current_user = current_user
        self.current_sale_items = {} # Usaremos un diccionario para agrupar productos

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=3) # Columna de la tabla más ancha
        self.grid_columnconfigure(1, weight=1) # Columna de totales más estrecha
        self.grid_rowconfigure(0, weight=1)

        # --- Columna Izquierda (Tabla de Venta y entrada de código) ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # Entrada de código de barras
        self.barcode_entry = ctk.CTkEntry(left_frame, placeholder_text="Escanear o escribir código de barras y presionar Enter...")
        self.barcode_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.barcode_entry.bind("<Return>", self.agregar_producto_a_venta)

        # Tabla para los items de la venta
        self.sale_tree = self.crear_tabla_venta(left_frame)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # --- Columna Derecha (Totales y Acciones) ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        # Labels para totales
        font_totales = ctk.CTkFont(size=18, weight="bold")
        self.subtotal_label = ctk.CTkLabel(right_frame, text="Subtotal: RD$ 0.00", font=font_totales)
        self.subtotal_label.pack(pady=20, padx=10, anchor="w")

        self.itbis_label = ctk.CTkLabel(right_frame, text=f"ITBIS ({self.ITBIS_RATE*100}%): RD$ 0.00", font=font_totales)
        self.itbis_label.pack(pady=20, padx=10, anchor="w")

        font_gran_total = ctk.CTkFont(size=24, weight="bold")
        self.total_label = ctk.CTkLabel(right_frame, text="TOTAL: RD$ 0.00", font=font_gran_total, text_color="#3484F0")
        self.total_label.pack(pady=30, padx=10, anchor="w")

        # Botones de acción
        self.complete_sale_button = ctk.CTkButton(right_frame, text="Finalizar Venta", height=50, command=self.finalizar_venta)
        self.complete_sale_button.pack(pady=10, padx=10, fill="x", side="bottom")

        self.cancel_sale_button = ctk.CTkButton(right_frame, text="Cancelar Venta", height=50, fg_color="#D32F2F", hover_color="#B71C1C", command=self.cancelar_venta)
        self.cancel_sale_button.pack(pady=10, padx=10, fill="x", side="bottom")

    def crear_tabla_venta(self, parent):
        tree = ttk.Treeview(parent, columns=("Cantidad", "Nombre", "Precio Unit.", "Subtotal"), show='headings')
        tree.heading("Cantidad", text="Cant.")
        tree.heading("Nombre", text="Producto")
        tree.heading("Precio Unit.", text="Precio Unit.")
        tree.heading("Subtotal", text="Subtotal")

        tree.column("Cantidad", width=60, anchor="center")
        tree.column("Nombre", width=300)
        tree.column("Precio Unit.", width=100, anchor="e")
        tree.column("Subtotal", width=100, anchor="e")
        return tree

    def agregar_producto_a_venta(self, event=None):
        codigo = self.barcode_entry.get()
        if not codigo:
            return

        producto = database.buscar_producto_por_codigo(codigo)
        self.barcode_entry.delete(0, "end")

        if not producto:
            messagebox.showwarning("No encontrado", f"No se encontró ningún producto con el código '{codigo}'.")
            return

        prod_id, _, nombre, _, precio, costo, stock = producto

        if stock <= 0:
            messagebox.showwarning("Sin Stock", f"El producto '{nombre}' no tiene stock disponible.")
            return

        # Si el producto ya está en la venta, incrementa la cantidad
        if prod_id in self.current_sale_items:
            # Verificar si hay stock suficiente para agregar uno más
            if self.current_sale_items[prod_id]['cantidad'] >= stock:
                messagebox.showwarning("Stock Insuficiente", f"No hay más stock disponible para '{nombre}'.")
                return
            self.current_sale_items[prod_id]['cantidad'] += 1
        else:
            self.current_sale_items[prod_id] = {
                'id': prod_id,
                'nombre': nombre,
                'precio': precio,
                'costo': costo,
                'cantidad': 1,
                'stock_disponible': stock
            }
        
        self.actualizar_tabla_y_totales()

    def actualizar_tabla_y_totales(self):
        # Limpiar tabla
        for item in self.sale_tree.get_children():
            self.sale_tree.delete(item)

        subtotal_general = 0.0

        # Llenar tabla y calcular subtotal
        for prod_id, item in self.current_sale_items.items():
            cantidad = item['cantidad']
            nombre = item['nombre']
            precio = item['precio']
            subtotal_item = cantidad * precio
            subtotal_general += subtotal_item

            self.sale_tree.insert("", "end", values=(f"{cantidad}x", nombre, f"RD$ {precio:,.2f}", f"RD$ {subtotal_item:,.2f}"))

        # Calcular totales
        itbis = subtotal_general * self.ITBIS_RATE
        total = subtotal_general + itbis

        # Actualizar labels
        self.subtotal_label.configure(text=f"Subtotal: RD$ {subtotal_general:,.2f}")
        self.itbis_label.configure(text=f"ITBIS ({self.ITBIS_RATE*100:.0f}%): RD$ {itbis:,.2f}")
        self.total_label.configure(text=f"TOTAL: RD$ {total:,.2f}")

    def finalizar_venta(self):
        if not self.current_sale_items:
            messagebox.showwarning("Venta Vacía", "No hay productos en la venta actual.")
            return

        subtotal_general = sum(item['cantidad'] * item['precio'] for item in self.current_sale_items.values())
        itbis = subtotal_general * self.ITBIS_RATE
        total = subtotal_general + itbis

        if not messagebox.askyesno("Confirmar Venta", f"El total de la venta es RD$ {total:,.2f}. ¿Desea finalizarla?"):
            return

        try:
            items = list(self.current_sale_items.values())
            venta_id = database.registrar_venta(items, total, itbis, self.current_user['id'])
            messagebox.showinfo("Éxito", "Venta registrada correctamente.")
            
            imprimir_ticket(venta_id, items, subtotal_general, itbis, total)

            self.cancelar_venta() # Limpia la pantalla para la siguiente venta
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo registrar la venta: {e}")

    def cancelar_venta(self):
        if self.current_sale_items:
            if not messagebox.askyesno("Confirmar", "¿Está seguro de que desea cancelar la venta actual? Se perderán todos los productos agregados."):
                return
        
        self.current_sale_items = {}
        self.actualizar_tabla_y_totales()
        self.barcode_entry.focus() # Poner el cursor de nuevo en la entrada de código

    def on_show(self):
        """Se llama cuando el frame se muestra. Pone el foco en la entrada de código."""
        self.barcode_entry.focus()
