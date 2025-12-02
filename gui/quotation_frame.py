import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import database.database as database
from fpdf import FPDF
from pathlib import Path
from datetime import datetime

class QuotationFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.ITBIS_RATE = 0.18
        self.current_quotation_items = {}
        self.selected_client = None
        self.client_search_results = []

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Columna Izquierda (Tabla y búsqueda) ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        top_bar_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        top_bar_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        top_bar_frame.grid_columnconfigure(0, weight=2)
        top_bar_frame.grid_columnconfigure(1, weight=1)

        self.barcode_entry = ctk.CTkEntry(top_bar_frame, placeholder_text="Escanear o escribir código de barras y presionar Enter...")
        self.barcode_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.barcode_entry.bind("<Return>", self.agregar_producto)

        self.client_search_entry = ctk.CTkEntry(top_bar_frame, placeholder_text="Buscar Cliente (Nombre/Cédula)")
        self.client_search_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.client_search_entry.bind("<KeyRelease>", self.buscar_cliente_popup)

        self.quotation_tree = self.crear_tabla(left_frame)
        self.quotation_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # --- Columna Derecha (Totales y Acciones) ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)

        self.client_label = ctk.CTkLabel(right_frame, text="Cliente: Consumidor Final", font=ctk.CTkFont(size=16), wraplength=250)
        self.client_label.pack(pady=10, padx=10, anchor="w")
        self.clear_client_button = ctk.CTkButton(right_frame, text="Limpiar Cliente", width=100, command=self.limpiar_cliente, fg_color="gray")

        font_totales = ctk.CTkFont(size=18, weight="bold")
        self.subtotal_label = ctk.CTkLabel(right_frame, text="Subtotal: RD$ 0.00", font=font_totales)
        self.subtotal_label.pack(pady=20, padx=10, anchor="w")

        self.itbis_label = ctk.CTkLabel(right_frame, text=f"ITBIS ({self.ITBIS_RATE*100}%): RD$ 0.00", font=font_totales)
        self.itbis_label.pack(pady=20, padx=10, anchor="w")

        font_gran_total = ctk.CTkFont(size=24, weight="bold")
        self.total_label = ctk.CTkLabel(right_frame, text="TOTAL: RD$ 0.00", font=font_gran_total, text_color="#3484F0")
        self.total_label.pack(pady=30, padx=10, anchor="w")

        self.export_button = ctk.CTkButton(right_frame, text="Exportar a PDF", height=50, command=self.exportar_cotizacion_pdf)
        self.export_button.pack(pady=10, padx=10, fill="x", side="bottom")

        self.clear_button = ctk.CTkButton(right_frame, text="Limpiar Cotización", height=50, fg_color="#D32F2F", hover_color="#B71C1C", command=self.limpiar_cotizacion)
        self.clear_button.pack(pady=10, padx=10, fill="x", side="bottom")

    def crear_tabla(self, parent):
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

    def agregar_producto(self, event=None):
        codigo = self.barcode_entry.get()
        if not codigo: return

        producto = database.buscar_producto_por_codigo(codigo)
        self.barcode_entry.delete(0, "end")

        if not producto:
            messagebox.showwarning("No encontrado", f"No se encontró ningún producto con el código '{codigo}'.", parent=self)
            return

        prod_id = producto['id']
        if prod_id in self.current_quotation_items:
            self.current_quotation_items[prod_id]['cantidad'] += 1
        else:
            self.current_quotation_items[prod_id] = {
                'id': prod_id,
                'nombre': producto['nombre'],
                'precio': producto['precio'],
                'cantidad': 1
            }
        self.actualizar_tabla_y_totales()

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
            self.clear_client_button.pack(pady=5, padx=10, anchor="w")
        
        if hasattr(self, 'client_popup') and self.client_popup.winfo_exists():
            self.client_popup.destroy()
        self.client_search_entry.delete(0, "end")

    def limpiar_cliente(self):
        self.selected_client = None
        self.client_label.configure(text="Cliente: Consumidor Final")
        self.clear_client_button.pack_forget()

    def actualizar_tabla_y_totales(self):
        for item in self.quotation_tree.get_children():
            self.quotation_tree.delete(item)

        total_cotizacion = 0.0
        for prod_id, item in self.current_quotation_items.items():
            subtotal_item = item['cantidad'] * item['precio']
            total_cotizacion += subtotal_item
            self.quotation_tree.insert("", "end", values=(f"{item['cantidad']}x", item['nombre'], f"RD$ {item['precio']:,.2f}", f"RD$ {subtotal_item:,.2f}"))

        # --- Lógica de Desglose de ITBIS ---
        # El total es la suma de los precios (que ya incluyen ITBIS)
        # Calculamos la base imponible (subtotal) y el ITBIS a partir del total.
        base_imponible = total_cotizacion / (1 + self.ITBIS_RATE)
        itbis_incluido = total_cotizacion - base_imponible
        total = total_cotizacion # El total es el mismo que la suma de los precios

        self.subtotal_label.configure(text=f"Subtotal (Base): RD$ {base_imponible:,.2f}")
        self.itbis_label.configure(text=f"ITBIS ({self.ITBIS_RATE*100:.0f}%): RD$ {itbis_incluido:,.2f}")
        self.total_label.configure(text=f"TOTAL: RD$ {total:,.2f}")

    def exportar_cotizacion_pdf(self):
        if not self.current_quotation_items:
            messagebox.showwarning("Vacía", "No hay productos para cotizar.", parent=self)
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
            initialfile=f"Cotizacion_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        if not filepath:
            return

        # Reutilizamos la misma lógica de desglose para el PDF
        total_cotizacion = sum(item['cantidad'] * item['precio'] for item in self.current_quotation_items.values())
        base_imponible = total_cotizacion / (1 + self.ITBIS_RATE)
        itbis_incluido = total_cotizacion - base_imponible
        total = total_cotizacion

        cliente_nombre = self.selected_client['nombre'] if self.selected_client else "Consumidor Final"
        cotizacion_id = f"COT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            pdf = FPDF()
            pdf.add_page()
            
            # --- Logo y Encabezado ---
            # Asumimos que el logo está en una carpeta 'assets' en la raíz del proyecto
            logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
            if logo_path.exists():
                # Colocamos el logo en la esquina superior izquierda
                pdf.image(str(logo_path), x=10, y=8, w=40)
                # Movemos el cursor a la derecha del logo para el texto
                pdf.set_x(55)
            
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "Ferretería XYZ", 0, 1, "L")
            pdf.set_font("Arial", "", 10)
            if logo_path.exists(): pdf.set_x(55)
            pdf.cell(0, 5, "Av. Principal #123, Santo Domingo", 0, 1, "L")
            if logo_path.exists(): pdf.set_x(55)
            pdf.cell(0, 5, "RNC: XXXXXXXXXXX | Tel: (809) 555-1234", 0, 1, "L")
            pdf.ln(10)

            # Título y datos del cliente
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "COTIZACION", 0, 1, "L")
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 6, f"Numero: {cotizacion_id}", 0, 1, "L")
            pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, "L")
            pdf.cell(0, 6, f"Cliente: {cliente_nombre}", 0, 1, "L")
            pdf.ln(10)

            # Tabla de productos
            pdf.set_font("Arial", "B", 10)
            pdf.cell(20, 8, "Cant.", 1, 0, "C")
            pdf.cell(95, 8, "Descripcion", 1, 0, "C")
            pdf.cell(35, 8, "Precio Unit.", 1, 0, "C")
            pdf.cell(35, 8, "Subtotal", 1, 1, "C")
            pdf.set_font("Arial", "", 10)
            for item in self.current_quotation_items.values():
                pdf.cell(20, 8, str(item['cantidad']), 1, 0, "C")
                pdf.cell(95, 8, item['nombre'], 1, 0, "L")
                pdf.cell(35, 8, f"RD$ {item['precio']:,.2f}", 1, 0, "R")
                pdf.cell(35, 8, f"RD$ {(item['cantidad'] * item['precio']):,.2f}", 1, 1, "R")
            
            # Totales y pie de página
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(125, 8, "Subtotal (Base):", 0, 0, "R")
            pdf.cell(60, 8, f"RD$ {base_imponible:,.2f}", 0, 1, "R")
            pdf.cell(125, 8, f"ITBIS ({self.ITBIS_RATE*100:.0f}%):", 0, 0, "R")
            pdf.cell(60, 8, f"RD$ {itbis_incluido:,.2f}", 0, 1, "R")
            pdf.set_font("Arial", "B", 14)
            pdf.cell(125, 10, "TOTAL:", 0, 0, "R")
            pdf.cell(60, 10, f"RD$ {total:,.2f}", 0, 1, "R")

            pdf.ln(15)
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 5, "Esta cotizacion es valida por 15 dias.", 0, 1, "C")
            pdf.cell(0, 5, "Precios sujetos a cambio sin previo aviso.", 0, 1, "C")
            pdf.cell(0, 5, "Documento no fiscal.", 0, 1, "C")

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Cotización guardada como PDF en:\n{filepath}", parent=self)
            self.limpiar_cotizacion(confirm=False)
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo generar el archivo PDF.\n\nError: {e}", parent=self)

    def limpiar_cotizacion(self, confirm=True):
        if confirm:
            if not messagebox.askyesno("Confirmar", "¿Está seguro de que desea limpiar la cotización actual?", parent=self):
                return
        
        self.current_quotation_items = {}
        self.limpiar_cliente()
        self.actualizar_tabla_y_totales()
        self.barcode_entry.focus()

    def on_show(self):
        """Se llama cuando el frame se muestra para poner el foco en la entrada de código."""
        self.barcode_entry.focus()