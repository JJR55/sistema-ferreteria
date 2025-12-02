import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import database.database as database

from gui.printer import imprimir_ticket

class PosFrame(ctk.CTkFrame):
    def __init__(self, master, current_user, **kwargs):
        super().__init__(master, **kwargs)

        # Constante para el ITBIS (18% en RD)
        self.ITBIS_RATE = 0.18
        self.current_user = current_user
        self.current_sale_items = {} # Usaremos un diccionario para agrupar productos
        self.selected_client = None # Para guardar el cliente seleccionado
        self.client_search_results = [] # Para el popup de búsqueda
        self.product_search_results = [] # Para el popup de búsqueda de productos
        self.descuento_aplicado = 0.0 # Para almacenar el descuento de la venta actual

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=3) # Columna de la tabla más ancha
        self.grid_columnconfigure(1, weight=1) # Columna de totales más estrecha
        self.grid_rowconfigure(0, weight=1)

        # --- Columna Izquierda (Tabla de Venta y entrada de código) ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # Frame para búsqueda de producto y cliente
        top_bar_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        top_bar_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        top_bar_frame.grid_columnconfigure((0, 1, 2), weight=1) # Tres columnas de igual peso

        # Entrada de código de barras
        self.barcode_entry = ctk.CTkEntry(top_bar_frame, placeholder_text="Escanear o escribir código de barras y presionar Enter...")
        self.barcode_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.barcode_entry.bind("<Return>", self.agregar_producto_por_codigo)

        # Búsqueda de producto por nombre
        self.product_search_entry = ctk.CTkEntry(top_bar_frame, placeholder_text="Buscar Producto por Nombre...")
        self.product_search_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.product_search_entry.bind("<KeyRelease>", self.buscar_producto_popup)

        # Búsqueda de cliente
        self.client_search_entry = ctk.CTkEntry(top_bar_frame, placeholder_text="Buscar Cliente (Nombre/Cédula)")
        self.client_search_entry.grid(row=0, column=2, sticky="ew", padx=(5, 0))
        self.client_search_entry.bind("<KeyRelease>", self.buscar_cliente_popup)

        # Tabla para los items de la venta
        self.sale_tree = self.crear_tabla_venta(left_frame)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Frame para indicadores de resumen (Mejora C)
        summary_indicators_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        summary_indicators_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.total_items_label = ctk.CTkLabel(summary_indicators_frame, text="Total Ítems: 0", font=ctk.CTkFont(size=14))
        self.total_items_label.pack(side="left", padx=10)
        self.total_units_label = ctk.CTkLabel(summary_indicators_frame, text="Total Unidades: 0", font=ctk.CTkFont(size=14))
        self.total_units_label.pack(side="left", padx=10)

        # --- Columna Derecha (Totales y Acciones) ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        # Label para mostrar cliente seleccionado
        self.client_label = ctk.CTkLabel(right_frame, text="Cliente: Consumidor Final", font=ctk.CTkFont(size=16), wraplength=250)
        self.client_label.pack(pady=10, padx=10, anchor="w")
        self.clear_client_button = ctk.CTkButton(right_frame, text="Limpiar Cliente", width=100, command=self.limpiar_cliente, fg_color="gray")

# Frame para botones de modificar/eliminar item
        item_actions_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        item_actions_frame.pack(pady=10, padx=10, fill="x")
        item_actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.edit_qty_button = ctk.CTkButton(item_actions_frame, text="Modificar Cantidad", command=self.modificar_cantidad_seleccionada)
        self.edit_qty_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.delete_item_button = ctk.CTkButton(item_actions_frame, text="Eliminar Item", command=self.eliminar_item_seleccionado, fg_color="#E53935", hover_color="#C62828")
        self.delete_item_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Botón de Descuento (Mejora A)
        self.discount_button = ctk.CTkButton(right_frame, text="Aplicar Descuento", command=self.aplicar_descuento)
        self.discount_button.pack(pady=10, padx=10, fill="x")

        # Labels para totales
        font_totales = ctk.CTkFont(size=18, weight="bold")
        self.subtotal_label = ctk.CTkLabel(right_frame, text="Subtotal (Base): RD$ 0.00", font=font_totales)
        self.subtotal_label.pack(pady=10, padx=10, anchor="w")

        self.discount_label = ctk.CTkLabel(right_frame, text="Descuento: RD$ 0.00", font=font_totales) # Etiqueta para mostrar el descuento
        self.discount_label.pack(pady=10, padx=10, anchor="w")

        self.itbis_label = ctk.CTkLabel(right_frame, text=f"ITBIS ({self.ITBIS_RATE*100:.0f}%): RD$ 0.00", font=font_totales)
        self.itbis_label.pack(pady=10, padx=10, anchor="w")

        font_gran_total = ctk.CTkFont(size=24, weight="bold")
        self.total_label = ctk.CTkLabel(right_frame, text="TOTAL: RD$ 0.00", font=font_gran_total, text_color="#3484F0")
        self.total_label.pack(pady=20, padx=10, anchor="w")

        # Método de pago
        ctk.CTkLabel(right_frame, text="Método de Pago:", font=font_totales).pack(pady=(20, 5), padx=10, anchor="w")
        self.payment_method_menu = ctk.CTkOptionMenu(right_frame, values=["Efectivo", "Tarjeta", "Crédito"], command=self.verificar_metodo_pago)
        self.payment_method_menu.pack(pady=5, padx=10, fill="x")
        self.payment_method_menu.set("Efectivo")


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

    def agregar_producto_por_codigo(self, event=None):
        codigo = self.barcode_entry.get()
        if not codigo:
            return
        producto = database.buscar_producto_por_codigo(codigo)
        self.barcode_entry.delete(0, "end")
        if not producto:
            messagebox.showwarning("No encontrado", f"No se encontró ningún producto con el código '{codigo}'.")
            return
        self.agregar_producto_a_venta(producto)

    def agregar_producto_a_venta(self, producto):
        prod_id = producto['id']
        nombre = producto['nombre']
        precio = producto['precio']
        costo = producto['costo']
        stock = producto['stock']
        
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

    def buscar_producto_popup(self, event):
        termino = self.product_search_entry.get()
        if len(termino) < 3:
            if hasattr(self, 'product_popup') and self.product_popup.winfo_exists():
                self.product_popup.destroy()
            return

        self.product_search_results = database.buscar_productos_por_nombre(termino)

        if not hasattr(self, 'product_popup') or not self.product_popup.winfo_exists():
            self.product_popup = ctk.CTkToplevel(self)
            self.product_popup.title("Resultados de Búsqueda de Productos")
            self.product_popup.transient(self)
            self.product_popup.attributes("-topmost", True)
            self.product_listbox = ctk.CTkListbox(self.product_popup, command=self.seleccionar_producto_de_lista)
            self.product_listbox.pack(fill="both", expand=True)
        
        self.product_listbox.delete("all")
        for producto in self.product_search_results:
            self.product_listbox.insert("END", f"{producto['nombre']} (Stock: {producto['stock']})")

    def seleccionar_producto_de_lista(self, selected_value):
        index = self.product_listbox.curselection()
        if index is not None:
            producto_seleccionado = self.product_search_results[index]
            self.agregar_producto_a_venta(producto_seleccionado)
        
        if hasattr(self, 'product_popup') and self.product_popup.winfo_exists():
            self.product_popup.destroy()
        self.product_search_entry.delete(0, "end")

    def buscar_cliente_popup(self, event):
        termino = self.client_search_entry.get()
        if len(termino) < 2:
            if hasattr(self, 'client_popup') and self.client_popup.winfo_exists():
                self.client_popup.destroy()
            return

        self.client_search_results = database.buscar_clientes(termino)

        if not hasattr(self, 'client_popup') or not self.client_popup.winfo_exists():
            self.client_popup = ctk.CTkToplevel(self)
            self.client_popup.title("Resultados de Búsqueda de Clientes")
            self.client_popup.transient(self)
            self.client_popup.attributes("-topmost", True)

            self.client_listbox = ctk.CTkListbox(self.client_popup, command=self.seleccionar_cliente_de_lista)
            self.client_listbox.pack(fill="both", expand=True)
        
        self.client_listbox.delete("all")
        for cliente in self.client_search_results:
            self.client_listbox.insert("END", f"{cliente['nombre']} ({cliente['rnc_cedula']})")

    def seleccionar_cliente_de_lista(self, selected_value):
        index = self.client_listbox.curselection()
        if index is not None:
            self.selected_client = self.client_search_results[index]
            self.client_label.configure(text=f"Cliente: {self.selected_client['nombre']}")
            self.clear_client_button.pack(pady=5, padx=10, anchor="w") # Mostrar botón
            self.verificar_metodo_pago() # Re-validar método de pago
        
        if hasattr(self, 'client_popup') and self.client_popup.winfo_exists():
            self.client_popup.destroy()
        self.client_search_entry.delete(0, "end")

    def limpiar_cliente(self):
        self.selected_client = None
        self.client_label.configure(text="Cliente: Consumidor Final")
        self.clear_client_button.pack_forget() # Ocultar botón
        self.verificar_metodo_pago()

    def verificar_metodo_pago(self, metodo_seleccionado=None):
        """Verifica si se puede usar el método de pago 'Crédito'."""
        if metodo_seleccionado is None:
            metodo_seleccionado = self.payment_method_menu.get()

        if metodo_seleccionado == "Crédito" and self.selected_client is None:
            messagebox.showwarning("Cliente Requerido", "Para ventas a crédito, primero debe seleccionar un cliente.", parent=self)
            self.payment_method_menu.set("Efectivo") # Volver a un método válido
            return False
        return True
    
    def actualizar_tabla_y_totales(self):
        # Limpiar tabla
        for item in self.sale_tree.get_children():
            self.sale_tree.delete(item)
        
        subtotal_bruto = 0.0

        # Llenar tabla y calcular total
        for prod_id, item in self.current_sale_items.items():
            cantidad = item['cantidad']
            nombre = item['nombre']
            precio = item['precio']
            subtotal_item = cantidad * precio
            subtotal_bruto += subtotal_item

            # Usamos el ID del producto como iid para poder identificarlo fácilmente
            self.sale_tree.insert("", "end", iid=prod_id, values=(f"{cantidad}x", nombre, f"RD$ {precio:,.2f}", f"RD$ {subtotal_item:,.2f}"))

        # --- Lógica de Desglose de ITBIS ---
        # El subtotal bruto es la suma de los precios (que ya incluyen ITBIS)
        subtotal_descontado = subtotal_bruto - self.descuento_aplicado
        base_imponible = subtotal_descontado / (1 + self.ITBIS_RATE)
        itbis_incluido = subtotal_descontado - base_imponible
        total = subtotal_descontado

        # Actualizar labels
        self.subtotal_label.configure(text=f"Subtotal (Base): RD$ {base_imponible:,.2f}")
        self.discount_label.configure(text=f"Descuento: - RD$ {self.descuento_aplicado:,.2f}")
        self.itbis_label.configure(text=f"ITBIS ({self.ITBIS_RATE*100:.0f}%): RD$ {itbis_incluido:,.2f}")
        self.total_label.configure(text=f"TOTAL: RD$ {total:,.2f}")

        # Actualizar indicadores de resumen (Mejora C)
        total_items = len(self.current_sale_items)
        total_unidades = sum(item['cantidad'] for item in self.current_sale_items.values())
        self.total_items_label.configure(text=f"Total Ítems: {total_items}")
        self.total_units_label.configure(text=f"Total Unidades: {total_unidades}")

    def finalizar_venta(self):
        if not self.current_sale_items:
            messagebox.showwarning("Venta Vacía", "No hay productos en la venta actual.")
            return

        # Usamos la misma lógica de desglose para registrar la venta
        subtotal_bruto = sum(item['cantidad'] * item['precio'] for item in self.current_sale_items.values())
        subtotal_descontado = subtotal_bruto - self.descuento_aplicado
        base_imponible = subtotal_descontado / (1 + self.ITBIS_RATE)
        itbis_incluido = subtotal_descontado - base_imponible
        total = subtotal_descontado
        tipo_pago = self.payment_method_menu.get()

        if not self.verificar_metodo_pago(tipo_pago):
            return

        # Mejora B: Cálculo de devuelta
        monto_recibido = 0
        if tipo_pago == "Efectivo":
            monto_recibido = simpledialog.askfloat("Pago en Efectivo", f"Total a pagar: RD$ {total:,.2f}\n\nIngrese el monto recibido del cliente:", parent=self, minvalue=total)
            if monto_recibido is None: # El usuario canceló
                return

        if not messagebox.askyesno("Confirmar Venta", f"El total de la venta es RD$ {total:,.2f}. ¿Desea finalizarla?", parent=self):
            return

        devuelta = monto_recibido - total if tipo_pago == "Efectivo" else 0

        try:
            items = list(self.current_sale_items.values())
            cliente_id = self.selected_client['_id'] if self.selected_client else None

            venta_id = database.registrar_venta(items, total, itbis_incluido, self.descuento_aplicado, self.current_user['id'], tipo_pago, cliente_id)
            messagebox.showinfo("Éxito", f"Venta #{venta_id} registrada correctamente.")
            
            imprimir_ticket(venta_id, items, base_imponible, itbis_incluido, self.descuento_aplicado, total, monto_recibido, devuelta)

            self.cancelar_venta() # Limpia la pantalla para la siguiente venta
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo registrar la venta: {e}")

    def cancelar_venta(self):
            if self.current_sale_items:
                if not messagebox.askyesno("Confirmar", "¿Está seguro de que desea cancelar la venta actual? Se perderán todos los productos agregados."):
                    return
            
            self.current_sale_items = {}
            self.descuento_aplicado = 0.0
            self.limpiar_cliente()
            self.actualizar_tabla_y_totales()
            self.barcode_entry.focus() # Poner el cursor de nuevo en la entrada de código

    def on_show(self):
        """Se llama cuando el frame se muestra. Pone el foco y activa los atajos de teclado."""
        self.barcode_entry.focus()
        # Vincular la tecla F12 a la función de finalizar venta
        # Vincular la tecla Escape a la función de cancelar venta
        # Usamos winfo_toplevel() para que el atajo funcione en toda la ventana
        self.winfo_toplevel().bind("<F12>", self.finalizar_venta_event)
        self.winfo_toplevel().bind("<Escape>", self.cancelar_venta_event)

    def finalizar_venta_event(self, event=None):
        """Wrapper para llamar a finalizar_venta desde un evento de teclado."""
        self.finalizar_venta()

    def cancelar_venta_event(self, event=None):
        """Wrapper para llamar a cancelar_venta desde un evento de teclado."""
        self.cancelar_venta()

           

        
            
            

            