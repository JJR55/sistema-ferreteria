import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from fpdf import FPDF
import database.database as database
from datetime import date, timedelta
from utils.currency import get_usd_to_dop_rate
import threading

class ReportsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.pack(fill="both", expand=True)

        # Crear un sistema de pestañas
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_view.add("Inventario Bajo")
        self.tab_view.add("Más Vendidos")
        self.tab_view.add("Reporte de Ventas")
        self.tab_view.add("Facturas Pagadas") # Nueva pestaña

        self.exchange_rate = None

        # Configurar el contenido de cada pestaña
        self.setup_low_stock_tab()
        self.setup_best_sellers_tab()
        self.setup_sales_report_tab()
        self.setup_paid_invoices_tab() # Configurar la nueva pestaña

        self.actualizar_tasa_async()

    def setup_low_stock_tab(self):
        tab = self.tab_view.tab("Inventario Bajo")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # --- Controles del Reporte de Inventario Bajo ---
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Este reporte muestra los productos cuyo stock actual es igual o menor a su stock mínimo definido.", font=ctk.CTkFont(size=14)).pack(side="left", padx=10)

        generate_button = ctk.CTkButton(controls_frame, text="Actualizar Reporte", command=self.generar_reporte_stock_bajo)
        generate_button.pack(side="left", padx=10)

        export_button = ctk.CTkButton(controls_frame, text="Exportar a PDF", command=self.exportar_stock_bajo_pdf)
        export_button.pack(side="left", padx=10)

        # --- Tabla para el Reporte de Inventario Bajo ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.low_stock_tree = ttk.Treeview(tree_frame, columns=("Código", "Nombre", "Departamento", "Stock Actual", "Stock Mínimo"), show='headings')
        self.low_stock_tree.heading("Código", text="Código de Barras")
        self.low_stock_tree.heading("Nombre", text="Nombre del Producto")
        self.low_stock_tree.heading("Departamento", text="Departamento")
        self.low_stock_tree.heading("Stock Actual", text="Stock Actual")
        self.low_stock_tree.heading("Stock Mínimo", text="Stock Mínimo")
        self.low_stock_tree.column("Stock Actual", width=120, anchor="center")
        self.low_stock_tree.column("Stock Mínimo", width=120, anchor="center")
        self.low_stock_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.low_stock_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.low_stock_tree.configure(yscrollcommand=scrollbar.set)

        self.generar_reporte_stock_bajo()

    def generar_reporte_stock_bajo(self):
        for item in self.low_stock_tree.get_children():
            self.low_stock_tree.delete(item)

        productos = database.obtener_productos_stock_bajo()
        for producto in productos:
            # Aseguramos el orden correcto de los valores para la tabla
            valores = (
                producto.get('codigo_barras', 'N/A'),
                producto.get('nombre', 'N/A'),
                producto.get('departamento', 'N/A'),
                producto.get('stock', 0),
                producto.get('stock_minimo', 0)
            )
            self.low_stock_tree.insert("", "end", values=valores)

    def exportar_stock_bajo_pdf(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                  filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            productos = database.obtener_productos_stock_bajo()
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            
            pdf.cell(0, 10, "Reporte de Productos con Inventario Bajo", 0, 1, "C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 10)
            headers = ["Código", "Nombre", "Departamento", "Stock Actual", "Stock Mínimo"]
            col_widths = [40, 80, 30, 20, 20]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, "C")
            pdf.ln()

            pdf.set_font("Arial", "", 9)
            for producto in productos:
                linea = [str(producto.get(k, '')) for k in ['codigo_barras', 'nombre', 'departamento', 'stock', 'stock_minimo']]
                for i, item in enumerate(linea):
                    pdf.cell(col_widths[i], 10, item, 1, 0)
                pdf.ln()

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo PDF: {e}", parent=self)
    def setup_best_sellers_tab(self):
        tab = self.tab_view.tab("Más Vendidos")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # --- Controles del Reporte de Más Vendidos ---
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Desde:").pack(side="left", padx=(10, 5))
        self.start_date_entry = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(controls_frame, text="Hasta:").pack(side="left", padx=(20, 5))
        self.end_date_entry = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.pack(side="left", padx=5)

        # Valores por defecto: último mes
        today = date.today()
        first_day_of_month = today.replace(day=1)
        self.start_date_entry.insert(0, first_day_of_month.strftime("%Y-%m-%d"))
        self.end_date_entry.insert(0, today.strftime("%Y-%m-%d"))

        generate_button = ctk.CTkButton(controls_frame, text="Generar Reporte", command=self.generar_reporte_mas_vendidos)
        generate_button.pack(side="left", padx=20)

        export_button = ctk.CTkButton(controls_frame, text="Exportar a PDF", command=self.exportar_mas_vendidos_pdf)
        export_button.pack(side="left", padx=5)

        # --- Tabla para el Reporte de Más Vendidos ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.best_sellers_tree = ttk.Treeview(tree_frame, columns=("Código", "Nombre", "Total Vendido"), show='headings')
        self.best_sellers_tree.heading("Código", text="Código de Barras")
        self.best_sellers_tree.heading("Nombre", text="Nombre del Producto")
        self.best_sellers_tree.heading("Total Vendido", text="Unidades Vendidas")
        self.best_sellers_tree.column("Total Vendido", width=150, anchor="center")
        self.best_sellers_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.best_sellers_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.best_sellers_tree.configure(yscrollcommand=scrollbar.set)

        self.generar_reporte_mas_vendidos()

    def generar_reporte_mas_vendidos(self):
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        # Validación simple de formato
        try:
            date.fromisoformat(start_date)
            date.fromisoformat(end_date)
        except ValueError:
            messagebox.showerror("Formato de Fecha Inválido", "Por favor, use el formato YYYY-MM-DD para las fechas.", parent=self)
            return

        for item in self.best_sellers_tree.get_children():
            self.best_sellers_tree.delete(item)

        productos = database.obtener_productos_mas_vendidos(start_date, end_date)
        
        if not productos:
            messagebox.showinfo("Sin Datos", "No se encontraron ventas en el rango de fechas especificado.", parent=self)
        else:
            for producto in productos:
                self.best_sellers_tree.insert("", "end", values=producto)

    def exportar_mas_vendidos_pdf(self):
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                  filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            productos = database.obtener_productos_mas_vendidos(start_date, end_date)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            
            pdf.cell(0, 10, f"Reporte de Productos Más Vendidos", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Período: {start_date} al {end_date}", 0, 1, "C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 10)
            headers = ["Código de Barras", "Nombre del Producto", "Unidades Vendidas"]
            col_widths = [50, 100, 40]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, "C")
            pdf.ln()

            pdf.set_font("Arial", "", 10)
            for producto in productos:
                for i, item in enumerate(producto):
                    pdf.cell(col_widths[i], 10, str(item), 1, 0)
                pdf.ln()

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo PDF: {e}", parent=self)

    def setup_sales_report_tab(self):
        tab = self.tab_view.tab("Reporte de Ventas")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1) # Para las tarjetas de resumen
        tab.grid_rowconfigure(2, weight=3) # Para la tabla

        # --- Controles ---
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Desde:").pack(side="left", padx=(10, 5))
        self.sales_start_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.sales_start_date.pack(side="left", padx=5)

        ctk.CTkLabel(controls_frame, text="Hasta:").pack(side="left", padx=(20, 5))
        self.sales_end_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.sales_end_date.pack(side="left", padx=5)

        today = date.today()
        first_day_of_month = today.replace(day=1)
        self.sales_start_date.insert(0, first_day_of_month.strftime("%Y-%m-%d"))
        self.sales_end_date.insert(0, today.strftime("%Y-%m-%d"))

        generate_button = ctk.CTkButton(controls_frame, text="Generar Reporte", command=self.generar_reporte_ventas)
        generate_button.pack(side="left", padx=20)

        # --- Tarjetas de Resumen ---
        summary_frame = ctk.CTkFrame(tab)
        summary_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.total_vendido_label = ctk.CTkLabel(summary_frame, text="Total Vendido:\nRD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_vendido_label.grid(row=0, column=0, padx=10, pady=10)
        self.total_itbis_label = ctk.CTkLabel(summary_frame, text="Total ITBIS:\nRD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_itbis_label.grid(row=0, column=1, padx=10, pady=10)
        self.ganancia_bruta_label = ctk.CTkLabel(summary_frame, text="Ganancia Bruta:\nRD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.ganancia_bruta_label.grid(row=0, column=2, padx=10, pady=10)
        self.num_ventas_label = ctk.CTkLabel(summary_frame, text="Facturas Emitidas:\n0", font=ctk.CTkFont(size=16, weight="bold"))
        self.num_ventas_label.grid(row=0, column=3, padx=10, pady=10)

        # --- Tabla de Ventas ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.sales_tree = ttk.Treeview(tree_frame, columns=("Factura No.", "Fecha y Hora", "Monto Total", "Ganancia"), show='headings')
        self.sales_tree.heading("Factura No.", text="Factura No.")
        self.sales_tree.heading("Fecha y Hora", text="Fecha y Hora")
        self.sales_tree.heading("Monto Total", text="Monto Total (RD$)")
        self.sales_tree.heading("Ganancia", text="Ganancia (RD$)")
        self.sales_tree.grid(row=0, column=0, sticky="nsew")

        self.generar_reporte_ventas()

    def generar_reporte_ventas(self):
        start_date = self.sales_start_date.get()
        end_date = self.sales_end_date.get()

        # Actualizar tarjetas de resumen
        resumen = database.obtener_resumen_ventas(start_date, end_date)
        self.total_vendido_label.configure(text=f"Total Vendido:\nRD$ {resumen['total_vendido']:,.2f}")
        self.total_itbis_label.configure(text=f"Total ITBIS:\nRD$ {resumen['total_itbis']:,.2f}")
        self.ganancia_bruta_label.configure(text=f"Ganancia Bruta:\nRD$ {resumen['ganancia_bruta']:,.2f}")
        self.num_ventas_label.configure(text=f"Facturas Emitidas:\n{resumen['num_ventas']}")

        # Actualizar tabla de ventas
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        
        ventas = database.obtener_ventas_por_rango(start_date, end_date)
        for venta in ventas:
            self.sales_tree.insert("", "end", values=venta)

    def setup_paid_invoices_tab(self):
        tab = self.tab_view.tab("Facturas Pagadas")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # --- Controles ---
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Desde Fecha Pago:").pack(side="left", padx=(10, 5))
        self.paid_invoices_start_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.paid_invoices_start_date.pack(side="left", padx=5)

        ctk.CTkLabel(controls_frame, text="Hasta Fecha Pago:").pack(side="left", padx=(20, 5))
        self.paid_invoices_end_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.paid_invoices_end_date.pack(side="left", padx=5)

        today = date.today()
        first_day_of_month = today.replace(day=1)
        self.paid_invoices_start_date.insert(0, first_day_of_month.strftime("%Y-%m-%d"))
        self.paid_invoices_end_date.insert(0, today.strftime("%Y-%m-%d"))

        generate_button = ctk.CTkButton(controls_frame, text="Generar Reporte", command=self.generar_reporte_facturas_pagadas)
        generate_button.pack(side="left", padx=20)

        self.paid_invoices_rate_label = ctk.CTkLabel(controls_frame, text="Tasa USD: Cargando...")
        self.paid_invoices_rate_label.pack(side="left", padx=10)

        export_button = ctk.CTkButton(controls_frame, text="Exportar a PDF", command=self.exportar_facturas_pagadas_pdf)
        export_button.pack(side="left", padx=5)

        # --- Tabla de Facturas Pagadas ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.paid_invoices_tree = ttk.Treeview(tree_frame, columns=("ID", "Proveedor", "Factura", "Emisión", "Vencimiento", "Fecha Pago", "Monto", "Moneda", "Monto (DOP)"), show='headings')
        self.paid_invoices_tree.heading("ID", text="ID")
        self.paid_invoices_tree.heading("Proveedor", text="Proveedor")
        self.paid_invoices_tree.heading("Factura", text="No. Factura")
        self.paid_invoices_tree.heading("Emisión", text="Fecha Emisión")
        self.paid_invoices_tree.heading("Vencimiento", text="Fecha Vencimiento")
        self.paid_invoices_tree.heading("Fecha Pago", text="Fecha Pago")
        self.paid_invoices_tree.heading("Monto", text="Monto")
        self.paid_invoices_tree.heading("Moneda", text="Moneda")
        self.paid_invoices_tree.heading("Monto (DOP)", text="Equivalente en DOP")
        self.paid_invoices_tree.column("ID", width=40)
        self.paid_invoices_tree.column("Monto", anchor="e")
        self.paid_invoices_tree.column("Monto (DOP)", anchor="e")
        self.paid_invoices_tree.column("Moneda", width=60, anchor="center")
        self.paid_invoices_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.paid_invoices_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.paid_invoices_tree.configure(yscrollcommand=scrollbar.set)

        self.generar_reporte_facturas_pagadas()

    def generar_reporte_facturas_pagadas(self):
        start_date = self.paid_invoices_start_date.get()
        end_date = self.paid_invoices_end_date.get()

        try:
            date.fromisoformat(start_date)
            date.fromisoformat(end_date)
        except ValueError:
            messagebox.showerror("Formato de Fecha Inválido", "Por favor, use el formato YYYY-MM-DD para las fechas.", parent=self)
            return

        for item in self.paid_invoices_tree.get_children():
            self.paid_invoices_tree.delete(item)
        
        facturas = database.obtener_facturas_pagadas(start_date, end_date)
        
        for factura in facturas:
            monto = factura[6]
            moneda = factura[7]
            monto_dop_str = ""
            if moneda == 'USD' and self.exchange_rate:
                monto_dop = monto * self.exchange_rate
                monto_dop_str = f"RD$ {monto_dop:,.2f}"
            elif moneda == 'DOP':
                monto_dop_str = f"RD$ {monto:,.2f}"

            self.paid_invoices_tree.insert("", "end", values=(*factura, monto_dop_str))

    def exportar_facturas_pagadas_pdf(self):
        start_date = self.paid_invoices_start_date.get()
        end_date = self.paid_invoices_end_date.get()

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            facturas = database.obtener_facturas_pagadas(start_date, end_date)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Reporte de Facturas Pagadas", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Período de Pago: {start_date} al {end_date}", 0, 1, "C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 8)
            headers = ["ID", "Proveedor", "Factura", "Emisión", "Venc.", "Pago", "Monto", "Moneda", "Monto DOP"]
            col_widths = [8, 30, 22, 18, 18, 18, 20, 15, 25] # Ajustar anchos
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 7, header, 1, 0, "C")
            pdf.ln()

            pdf.set_font("Arial", "", 8)
            for factura in facturas:
                monto = factura[6]
                moneda = factura[7]
                monto_dop_str = ""
                if moneda == 'USD' and self.exchange_rate:
                    monto_dop = monto * self.exchange_rate
                    monto_dop_str = f"{monto_dop:,.2f}"
                elif moneda == 'DOP':
                    monto_dop_str = f"{monto:,.2f}"

                linea = (*factura, monto_dop_str)
                for i, item in enumerate(factura):
                    pdf.cell(col_widths[i], 7, str(linea[i]), 1, 0)
                pdf.ln()

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo PDF: {e}", parent=self)

    def actualizar_tasa_async(self):
        thread = threading.Thread(target=self.worker_actualizar_tasa_reportes)
        thread.start()

    def worker_actualizar_tasa_reportes(self):
        rate = get_usd_to_dop_rate()
        self.exchange_rate = rate
        if rate:
            self.paid_invoices_rate_label.configure(text=f"Tasa USD: RD$ {rate:.4f}")
        else:
            self.paid_invoices_rate_label.configure(text="Tasa USD: Error")
        self.generar_reporte_facturas_pagadas()
        productos = database.obtener_productos_mas_vendidos(start_date, end_date)
        
        if not productos:
            messagebox.showinfo("Sin Datos", "No se encontraron ventas en el rango de fechas especificado.", parent=self)
        else:
            for producto in productos:
                self.best_sellers_tree.insert("", "end", values=producto)

    def exportar_mas_vendidos_pdf(self):
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                  filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            productos = database.obtener_productos_mas_vendidos(start_date, end_date)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            
            pdf.cell(0, 10, f"Reporte de Productos Más Vendidos", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Período: {start_date} al {end_date}", 0, 1, "C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 10)
            headers = ["Código de Barras", "Nombre del Producto", "Unidades Vendidas"]
            col_widths = [50, 100, 40]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, "C")
            pdf.ln()

            pdf.set_font("Arial", "", 10)
            for producto in productos:
                for i, item in enumerate(producto):
                    pdf.cell(col_widths[i], 10, str(item), 1, 0)
                pdf.ln()

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a {filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo PDF: {e}", parent=self)

    def setup_sales_report_tab(self):
        tab = self.tab_view.tab("Reporte de Ventas")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1) # Para las tarjetas de resumen
        tab.grid_rowconfigure(2, weight=3) # Para la tabla

        # --- Controles ---
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Desde:").pack(side="left", padx=(10, 5))
        self.sales_start_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.sales_start_date.pack(side="left", padx=5)

        ctk.CTkLabel(controls_frame, text="Hasta:").pack(side="left", padx=(20, 5))
        self.sales_end_date = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.sales_end_date.pack(side="left", padx=5)

        today = date.today()
        first_day_of_month = today.replace(day=1)
        self.sales_start_date.insert(0, first_day_of_month.strftime("%Y-%m-%d"))
        self.sales_end_date.insert(0, today.strftime("%Y-%m-%d"))

        generate_button = ctk.CTkButton(controls_frame, text="Generar Reporte", command=self.generar_reporte_ventas)
        generate_button.pack(side="left", padx=20)

        # --- Tarjetas de Resumen ---
        summary_frame = ctk.CTkFrame(tab)
        summary_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.total_vendido_label = ctk.CTkLabel(summary_frame, text="Total Vendido:\nRD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_vendido_label.grid(row=0, column=0, padx=10, pady=10)
        self.total_itbis_label = ctk.CTkLabel(summary_frame, text="Total ITBIS:\nRD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_itbis_label.grid(row=0, column=1, padx=10, pady=10)
        self.num_ventas_label = ctk.CTkLabel(summary_frame, text="Facturas Emitidas:\n0", font=ctk.CTkFont(size=16, weight="bold"))
        self.num_ventas_label.grid(row=0, column=2, padx=10, pady=10)

        # --- Tabla de Ventas ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.sales_tree = ttk.Treeview(tree_frame, columns=("Factura No.", "Fecha y Hora", "Monto Total"), show='headings')
        self.sales_tree.heading("Factura No.", text="Factura No.")
        self.sales_tree.heading("Fecha y Hora", text="Fecha y Hora")
        self.sales_tree.heading("Monto Total", text="Monto Total (RD$)")
        self.sales_tree.grid(row=0, column=0, sticky="nsew")

        self.generar_reporte_ventas()

    def generar_reporte_ventas(self):
        start_date = self.sales_start_date.get()
        end_date = self.sales_end_date.get()

        # Actualizar tarjetas de resumen
        resumen = database.obtener_resumen_ventas(start_date, end_date)
        self.total_vendido_label.configure(text=f"Total Vendido:\nRD$ {resumen['total_vendido']:,.2f}")
        self.total_itbis_label.configure(text=f"Total ITBIS:\nRD$ {resumen['total_itbis']:,.2f}")
        self.num_ventas_label.configure(text=f"Facturas Emitidas:\n{resumen['num_ventas']}")

        # Actualizar tabla de ventas
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        
        ventas = database.obtener_ventas_por_rango(start_date, end_date)
        for venta in ventas:
            self.sales_tree.insert("", "end", values=venta)
