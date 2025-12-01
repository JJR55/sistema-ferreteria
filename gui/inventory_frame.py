import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import database.database as database
import csv
from fpdf import FPDF

from .edit_window import EditWindow
class InventoryFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # --- Configuración del Layout del Frame Principal ---
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Cambiado a 2 para dar espacio a los nuevos botones

        # --- Frame para Controles (Entradas y Botones) ---
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # --- Widgets de entrada en el nuevo orden ---
        self.codigo_entry = ctk.CTkEntry(controls_frame, placeholder_text="Código de Barras")
        self.codigo_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.nombre_entry = ctk.CTkEntry(controls_frame, placeholder_text="Nombre del Producto")
        self.nombre_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.costo_entry = ctk.CTkEntry(controls_frame, placeholder_text="Precio Costo")
        self.costo_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.precio_entry = ctk.CTkEntry(controls_frame, placeholder_text="Precio Venta")
        self.precio_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.stock_entry = ctk.CTkEntry(controls_frame, placeholder_text="Stock")
        self.stock_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.stock_minimo_entry = ctk.CTkEntry(controls_frame, placeholder_text="Inv. Mínimo")
        self.stock_minimo_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.departamentos = ["Ferretería", "Repuestos", "Hogar"]
        self.departamento_menu = ctk.CTkOptionMenu(controls_frame, values=self.departamentos)
        self.departamento_menu.pack(side="left", padx=5, pady=5)

        self.add_button = ctk.CTkButton(controls_frame, text="Agregar Producto", command=self.agregar_producto)
        self.add_button.pack(side="left", padx=5, pady=5)

        # --- Treeview para mostrar los productos ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#2a2d2e",
                        foreground="white",
                        rowheight=25,
                        fieldbackground="#343638",
                        bordercolor="#343638",
                        borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading",
                        background="#565b5e",
                        foreground="white",
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#3484F0')])

        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew") # Cambiado a fila 2
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Definir columnas en el orden de la base de datos
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Código", "Descripción", "Precio Costo", "Precio Venta", "Stock", "Inv. Mínimo", "Departamento"), show='headings')
        
        # Ocultar la columna ID
        self.tree['displaycolumns'] = ("Código", "Descripción", "Precio Costo", "Precio Venta", "Stock", "Inv. Mínimo", "Departamento")

        self.tree.heading("ID", text="ID")
        self.tree.heading("Código", text="Código")
        self.tree.heading("Descripción", text="Descripción")
        self.tree.heading("Precio Costo", text="Precio Costo (RD$)")
        self.tree.heading("Precio Venta", text="Precio Venta (RD$)")
        self.tree.heading("Stock", text="Stock")
        self.tree.heading("Inv. Mínimo", text="Inv. Mínimo")
        self.tree.heading("Departamento", text="Departamento")

        # Ajustar ancho de columnas
        self.tree.column("Código", width=150)
        self.tree.column("Descripción", width=250, anchor="w")
        self.tree.column("Precio Costo", width=120, anchor="e")
        self.tree.column("Precio Venta", width=120, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.column("Inv. Mínimo", width=80, anchor="center")
        self.tree.column("Departamento", width=100, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Configurar un "tag" para resaltar filas en rojo
        self.tree.tag_configure('low_stock', background='#8B0000') # Un rojo oscuro que se ve bien en el tema

        # --- Frame para botones de acción (Editar, Eliminar) ---
        action_buttons_frame = ctk.CTkFrame(self)
        action_buttons_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")

        self.edit_button = ctk.CTkButton(action_buttons_frame, text="Editar Seleccionado", command=self.editar_producto_seleccionado)
        self.edit_button.pack(side="left", padx=5, pady=5)

        self.delete_button = ctk.CTkButton(action_buttons_frame, text="Eliminar Seleccionado", fg_color="#D32F2F", hover_color="#B71C1C", command=self.eliminar_producto_seleccionado)
        self.delete_button.pack(side="left", padx=5, pady=5)
        
        # Separador visual
        ctk.CTkLabel(action_buttons_frame, text="|").pack(side="left", padx=10)

        self.import_csv_button = ctk.CTkButton(action_buttons_frame, text="Importar desde CSV", command=self.importar_csv)
        self.import_csv_button.pack(side="left", padx=5, pady=5)

        self.export_csv_button = ctk.CTkButton(action_buttons_frame, text="Exportar a CSV", command=self.exportar_csv)
        self.export_csv_button.pack(side="left", padx=5, pady=5)

        self.export_pdf_button = ctk.CTkButton(action_buttons_frame, text="Exportar a PDF", command=self.exportar_pdf)
        self.export_pdf_button.pack(side="left", padx=5, pady=5)


        self.cargar_productos()

    def cargar_productos(self):
        # Limpiar la tabla antes de cargar nuevos datos
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Obtener productos de la BD y mostrarlos
        productos = database.obtener_productos()
        for producto in productos:
            # producto[5] es 'stock', producto[6] es 'stock_minimo'
            stock_actual = producto[5]
            stock_minimo = producto[6]

            # Asignar el tag 'low_stock' si el stock es bajo y se ha definido un mínimo
            if stock_actual <= stock_minimo and stock_minimo > 0:
                self.tree.insert("", "end", values=producto, tags=('low_stock',))
            else:
                self.tree.insert("", "end", values=producto)


    def agregar_producto(self):
        codigo = self.codigo_entry.get()
        nombre = self.nombre_entry.get()
        costo = self.costo_entry.get()
        precio = self.precio_entry.get()
        stock = self.stock_entry.get()
        stock_minimo = self.stock_minimo_entry.get()
        departamento = self.departamento_menu.get()

        # Validaciones básicas
        if not all([codigo, nombre, precio, costo, stock, stock_minimo]):
            messagebox.showerror("Error de validación", "Todos los campos son requeridos.")
            return
        try:
            # Intentar convertir precio y stock a números
            costo_val = float(costo)
            precio_val = float(precio)
            stock_val = int(stock)
            stock_minimo_val = int(stock_minimo)
        except ValueError:
            messagebox.showerror("Error de formato", "Precio, costo, stock e inventario mínimo deben ser números.")
            return

        # Llamar a la función de la base de datos
        try:
            database.agregar_producto(codigo, nombre, costo_val, precio_val, stock_val, stock_minimo_val, departamento)
            messagebox.showinfo("Éxito", "Producto agregado correctamente.")
            self.cargar_productos() # Recargar la lista
            # Limpiar campos de entrada
            self.codigo_entry.delete(0, "end")
            self.nombre_entry.delete(0, "end")
            self.costo_entry.delete(0, "end")
            self.precio_entry.delete(0, "end")
            self.stock_entry.delete(0, "end")
            self.stock_minimo_entry.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Error en la Base de Datos", f"No se pudo agregar el producto: {e}")

    def editar_producto_seleccionado(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un producto de la tabla para editar.")
            return

        # Obtener los datos del item seleccionado
        product_data = self.tree.item(selected_item[0])['values']

        # Abrir la ventana de edición
        EditWindow(self.master, product_data, self)

    def eliminar_producto_seleccionado(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un producto de la tabla para eliminar.")
            return

        product_data = self.tree.item(selected_item[0])['values']
        product_id = product_data[0]

        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de que desea eliminar el producto '{product_data[2]}'?"):
            try:
                database.eliminar_producto(product_id)
                messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
                self.cargar_productos()
            except Exception as e:
                messagebox.showerror("Error en la Base de Datos", f"No se pudo eliminar el producto: {e}")

    def exportar_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            productos = database.obtener_productos()
            headers = ["ID", "Codigo de Barras", "Nombre", "Departamento", "Precio", "Stock"]

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(productos)
            
            messagebox.showinfo("Éxito", f"Datos exportados correctamente a {filepath}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo CSV: {e}")

    def exportar_pdf(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                  filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        try:
            productos = database.obtener_productos()
            headers = ["ID", "Codigo de Barras", "Nombre", "Departamento", "Precio", "Stock"]

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            
            pdf.cell(0, 10, "Reporte de Inventario", 0, 1, "C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 10)
            # Anchos de celda (ajustar según necesidad)
            col_widths = [15, 40, 70, 30, 20, 15]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, "C")
            pdf.ln()

            pdf.set_font("Arial", "", 10)
            for producto in productos:
                for i, item in enumerate(producto):
                    pdf.cell(col_widths[i], 10, str(item), 1, 0)
                pdf.ln()

            pdf.output(filepath)
            messagebox.showinfo("Éxito", f"Datos exportados correctamente a {filepath}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo PDF: {e}")

    def importar_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not filepath:
            return

        if not messagebox.askyesno("Confirmar Importación", "Esto agregará productos desde un archivo CSV. Los productos con códigos de barras duplicados serán omitidos. ¿Desea continuar?"):
            return

        exitosos = 0
        fallidos = 0

        try:
            with open(filepath, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader) # Omitir la cabecera

                for row in reader:
                    try:
                        # Asumiendo el orden: codigo, nombre, depto, precio, stock
                        if len(row) < 5:
                            fallidos += 1
                            continue # Omitir filas incompletas

                        codigo = row[0]
                        nombre = row[1]
                        departamento = row[2]
                        precio = float(row[3])
                        stock = int(row[4])

                        database.agregar_producto(codigo, nombre, departamento, precio, stock)
                        exitosos += 1

                    except ValueError: # Error al convertir precio/stock
                        fallidos += 1
                    except Exception: # Otro error (ej. código duplicado)
                        fallidos += 1
            
            summary_message = f"Importación completada.\n\nProductos agregados: {exitosos}\nFilas omitidas (errores o duplicados): {fallidos}"
            messagebox.showinfo("Resumen de Importación", summary_message)
            self.cargar_productos()

        except Exception as e:
            messagebox.showerror("Error de Importación", f"No se pudo leer el archivo CSV: {e}")
