import customtkinter as ctk
from tkinter import ttk, messagebox
import database.database as database
from datetime import date, datetime, timedelta
from utils.currency import get_usd_to_dop_rate
import threading

class AccountsPayableFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.pack(fill="both", expand=True)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_view.add("Cuentas por Pagar")
        self.tab_view.add("Proveedores")

        self.proveedores_map = {}
        self.exchange_rate = None

        self.setup_accounts_payable_tab()
        self.setup_suppliers_tab()

        # Cargar la tasa de cambio en segundo plano para no congelar la app
        self.actualizar_tasa_async()

    def setup_suppliers_tab(self):
        tab = self.tab_view.tab("Proveedores")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # --- Formulario para agregar proveedor ---
        form_frame = ctk.CTkFrame(tab)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        ctk.CTkLabel(form_frame, text="Gestionar Proveedor", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(form_frame, text="Nombre:").pack(anchor="w", padx=10)
        self.supplier_name_entry = ctk.CTkEntry(form_frame, width=250)
        self.supplier_name_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(form_frame, text="RNC:").pack(anchor="w", padx=10)
        self.supplier_rnc_entry = ctk.CTkEntry(form_frame)
        self.supplier_rnc_entry.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(form_frame, text="Teléfono:").pack(anchor="w", padx=10)
        self.supplier_phone_entry = ctk.CTkEntry(form_frame)
        self.supplier_phone_entry.pack(padx=10, pady=(0, 20), fill="x")

        ctk.CTkButton(form_frame, text="Agregar Proveedor", command=self.agregar_proveedor).pack(pady=10, padx=10, fill="x")

        # --- Lista de proveedores ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.suppliers_tree = ttk.Treeview(tree_frame, columns=("ID", "Nombre", "RNC", "Teléfono"), show='headings')
        self.suppliers_tree.heading("ID", text="ID")
        self.suppliers_tree.heading("Nombre", text="Nombre")
        self.suppliers_tree.heading("RNC", text="RNC")
        self.suppliers_tree.heading("Teléfono", text="Teléfono")
        self.suppliers_tree.column("ID", width=50)
        self.suppliers_tree.grid(row=0, column=0, sticky="nsew")
        self.cargar_proveedores()

    def setup_accounts_payable_tab(self):
        tab = self.tab_view.tab("Cuentas por Pagar")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1) # Ajustar para el nuevo frame de acciones

        # --- Formulario para agregar factura ---
        form_frame = ctk.CTkFrame(tab)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(form_frame, text="Proveedor:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_supplier_menu = ctk.CTkOptionMenu(form_frame, values=["Cargando..."])
        self.invoice_supplier_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="No. Factura:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.invoice_number_entry = ctk.CTkEntry(form_frame)
        self.invoice_number_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Fecha Emisión (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.invoice_date_entry = ctk.CTkEntry(form_frame)
        self.invoice_date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.invoice_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Fecha Vencimiento (YYYY-MM-DD):").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.invoice_due_date_entry = ctk.CTkEntry(form_frame)
        self.invoice_due_date_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Monto:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.invoice_amount_entry = ctk.CTkEntry(form_frame)
        self.invoice_amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Moneda:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.invoice_currency_menu = ctk.CTkOptionMenu(form_frame, values=["DOP", "USD"])
        self.invoice_currency_menu.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

        # --- Tasa de Cambio ---
        rate_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        rate_frame.grid(row=2, column=4, padx=(20, 5), pady=5, sticky="w")
        self.rate_label = ctk.CTkLabel(rate_frame, text="Tasa USD: Cargando...", font=ctk.CTkFont(size=12))
        self.rate_label.pack(side="left")
        self.refresh_rate_button = ctk.CTkButton(rate_frame, text="Actualizar", width=80, command=self.actualizar_tasa_async)
        self.refresh_rate_button.pack(side="left", padx=5)

        ctk.CTkButton(form_frame, text="Agregar Factura Pendiente", command=self.agregar_factura).grid(row=3, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # --- Frame de Acciones ---
        actions_frame = ctk.CTkFrame(tab)
        actions_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.mark_paid_button = ctk.CTkButton(actions_frame, text="Marcar Factura Seleccionada como Pagada", command=self.marcar_como_pagada)
        self.mark_paid_button.pack(side="left", padx=5)

        # --- Lista de cuentas por pagar ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.payable_tree = ttk.Treeview(tree_frame, columns=("ID", "Proveedor", "Factura", "Emisión", "Vencimiento", "Monto", "Moneda", "Monto (DOP)"), show='headings')
        self.payable_tree.heading("ID", text="ID")
        self.payable_tree.heading("Proveedor", text="Proveedor")
        self.payable_tree.heading("Factura", text="No. Factura")
        self.payable_tree.heading("Emisión", text="Fecha Emisión")
        self.payable_tree.heading("Vencimiento", text="Fecha Vencimiento")
        self.payable_tree.heading("Monto", text="Monto")
        self.payable_tree.heading("Moneda", text="Moneda")
        self.payable_tree.heading("Monto (DOP)", text="Equivalente en DOP")
        self.payable_tree.column("ID", width=40)
        self.payable_tree.column("Monto", anchor="e")
        self.payable_tree.column("Monto (DOP)", anchor="e")
        self.payable_tree.column("Moneda", width=60, anchor="center")
        self.payable_tree.grid(row=0, column=0, sticky="nsew")

        # Configurar tags para resaltar filas
        self.payable_tree.tag_configure('overdue', background='#8B0000') # Rojo oscuro para vencidas
        self.payable_tree.tag_configure('due_soon', background='#FF8C00') # Naranja para prontas a vencer

        self.cargar_cuentas_por_pagar()

    def cargar_proveedores(self):
        for item in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(item)
        
        proveedores = database.obtener_proveedores()
        self.proveedores_map = {p['nombre']: p['_id'] for p in proveedores} # Nombre -> ID
        
        if proveedores:
            nombres_proveedores = list(self.proveedores_map.keys())
            self.invoice_supplier_menu.configure(values=nombres_proveedores)
            self.invoice_supplier_menu.set(nombres_proveedores[0])
        else:
            self.invoice_supplier_menu.configure(values=["No hay proveedores"])
            self.invoice_supplier_menu.set("No hay proveedores")

        for p in proveedores:
            # Corregido: Insertar valores en el orden correcto
            valores = (
                p.get('_id', ''),
                p.get('nombre', ''),
                p.get('rnc', ''),
                p.get('telefono', '')
            )
            self.suppliers_tree.insert("", "end", values=valores)

    def agregar_proveedor(self):
        nombre = self.supplier_name_entry.get()
        rnc = self.supplier_rnc_entry.get()
        telefono = self.supplier_phone_entry.get()
        if not nombre:
            messagebox.showerror("Error", "El nombre del proveedor es obligatorio.", parent=self)
            return
        try:
            database.agregar_proveedor(nombre, rnc, telefono)
            self.supplier_name_entry.delete(0, "end")
            self.supplier_rnc_entry.delete(0, "end")
            self.supplier_phone_entry.delete(0, "end")
            self.cargar_proveedores()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el proveedor. Causa probable: ya existe.\n{e}", parent=self)

    def cargar_cuentas_por_pagar(self):
        for item in self.payable_tree.get_children():
            self.payable_tree.delete(item)
        cuentas = database.obtener_cuentas_por_pagar()
        
        for c in cuentas:
            # Corregido: Acceder a los datos por clave de diccionario
            monto = c.get('monto', 0)
            moneda = c.get('moneda', 'DOP')
            monto_dop_str = ""
            if moneda == 'USD' and self.exchange_rate:
                monto_dop = monto * self.exchange_rate
                monto_dop_str = f"RD$ {monto_dop:,.2f}"
            elif moneda == 'DOP':
                monto_dop_str = f"RD$ {monto:,.2f}"
            
            # Lógica para resaltar facturas
            tag = ''
            fecha_vencimiento_str = c.get('fecha_vencimiento', '')
            if fecha_vencimiento_str:
                try:
                    # Usamos datetime.strptime para manejar el formato 'YYYY-MM-DD'
                    fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
                    hoy = date.today()
                    diferencia = (fecha_vencimiento - hoy).days
                    if diferencia < 0:
                        tag = 'overdue'
                    elif 0 <= diferencia <= 7:
                        tag = 'due_soon'
                except (ValueError, TypeError):
                    pass # Si la fecha es inválida, no se aplica tag

            # Corregido: Insertar valores en el orden correcto
            valores = (
                c.get('_id', ''),
                c.get('proveedor_nombre', ''),
                c.get('numero_factura', ''),
                c.get('fecha_emision', ''),
                c.get('fecha_vencimiento', ''),
                f"{monto:,.2f}",
                moneda,
                monto_dop_str
            )
            self.payable_tree.insert("", "end", values=valores, tags=(tag,))

    def agregar_factura(self):
        proveedor_nombre = self.invoice_supplier_menu.get()
        proveedor_id = self.proveedores_map.get(proveedor_nombre)
        # ... (resto de la lógica para agregar factura)
        num_factura = self.invoice_number_entry.get()
        fecha_emision = self.invoice_date_entry.get()
        fecha_vencimiento = self.invoice_due_date_entry.get()
        monto = self.invoice_amount_entry.get()
        moneda = self.invoice_currency_menu.get()

        # Validaciones
        if not all([proveedor_id, num_factura, fecha_emision, fecha_vencimiento, monto]):
            messagebox.showerror("Error", "Todos los campos son obligatorios.", parent=self)
            return
        try:
            monto_val = float(monto)
            date.fromisoformat(fecha_emision)
            date.fromisoformat(fecha_vencimiento)
        except ValueError:
            messagebox.showerror("Error de Formato", "El monto debe ser un número y las fechas deben tener el formato YYYY-MM-DD.", parent=self)
            return

        database.agregar_factura_compra(proveedor_id, num_factura, fecha_emision, fecha_vencimiento, monto_val, moneda)
        self.cargar_cuentas_por_pagar()
        messagebox.showinfo("Éxito", "Factura pendiente agregada correctamente.", parent=self)

    def marcar_como_pagada(self):
        selected_item = self.payable_tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione una factura de la lista para marcarla como pagada.", parent=self)
            return

        item_data = self.payable_tree.item(selected_item[0])['values']
        factura_id = str(item_data[0]) # Asegurarse de que es un string
        proveedor = str(item_data[1])
        num_factura = str(item_data[2])

        if messagebox.askyesno("Confirmar Pago", f"¿Está seguro de que desea marcar la factura #{num_factura} del proveedor '{proveedor}' como pagada?", parent=self):
            database.marcar_factura_como_pagada(str(factura_id))
            self.cargar_cuentas_por_pagar() # Recargar la lista
            messagebox.showinfo("Éxito", "La factura ha sido marcada como pagada y eliminada de la lista de pendientes.", parent=self)

    def actualizar_tasa_async(self):
        """Inicia la carga de la tasa de cambio en un hilo separado."""
        self.rate_label.configure(text="Tasa USD: Cargando...")
        self.refresh_rate_button.configure(state="disabled")
        thread = threading.Thread(target=self.worker_actualizar_tasa)
        thread.start()

    def worker_actualizar_tasa(self):
        """Función que se ejecuta en el hilo para obtener la tasa."""
        rate = get_usd_to_dop_rate()
        self.exchange_rate = rate
        if rate:
            self.rate_label.configure(text=f"Tasa USD: RD$ {rate:.4f}")
        else:
            self.rate_label.configure(text="Tasa USD: Error")
        self.refresh_rate_button.configure(state="normal")
        self.cargar_cuentas_por_pagar() # Recargar la tabla con la nueva tasa