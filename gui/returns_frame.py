import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import database.database as database

class ReturnsFrame(ctk.CTkFrame):
    def __init__(self, master, current_user, **kwargs):
        super().__init__(master, **kwargs)

        self.current_user = current_user
        self.current_sale_details = []
        self.current_sale_id = None

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Frame de Búsqueda ---
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(search_frame, text="Número de Factura:").pack(side="left", padx=10)
        self.sale_id_entry = ctk.CTkEntry(search_frame)
        self.sale_id_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.sale_id_entry.bind("<Return>", self.buscar_venta)

        self.search_button = ctk.CTkButton(search_frame, text="Buscar Venta", command=self.buscar_venta)
        self.search_button.pack(side="left", padx=10)

        # --- Frame de Información de la Venta ---
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.info_label = ctk.CTkLabel(self.info_frame, text="Busque una factura para ver sus detalles.", font=ctk.CTkFont(size=14))
        self.info_label.pack(pady=10)

        # --- Tabla de Detalles de la Venta ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.details_tree = ttk.Treeview(tree_frame, columns=("ID Producto", "Nombre", "Cant. Vendida", "Precio Unit."), show='headings')
        self.details_tree.heading("ID Producto", text="ID")
        self.details_tree.heading("Nombre", text="Producto")
        self.details_tree.heading("Cant. Vendida", text="Cant. Vendida")
        self.details_tree.heading("Precio Unit.", text="Precio Unitario")
        self.details_tree.column("ID Producto", width=50)
        self.details_tree.grid(row=0, column=0, sticky="nsew")

        # --- Botón de Acción ---
        self.process_return_button = ctk.CTkButton(self, text="Procesar Devolución de Productos Seleccionados", height=40, command=self.procesar_devolucion)
        self.process_return_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.process_return_button.configure(state="disabled")

    def buscar_venta(self, event=None):
        sale_id_str = self.sale_id_entry.get()
        if not sale_id_str:
            return

        try:
            sale_id = int(sale_id_str)
            venta, detalles = database.buscar_venta_por_id(sale_id)

            # Limpiar estado anterior
            for item in self.details_tree.get_children():
                self.details_tree.delete(item)
            self.process_return_button.configure(state="disabled")

            if not venta:
                messagebox.showerror("No encontrada", f"No se encontró ninguna venta con el ID de factura {sale_id}.", parent=self)
                self.info_label.configure(text="Busque una factura para ver sus detalles.")
                return

            self.current_sale_id = venta[0]
            self.current_sale_details = detalles

            # Mostrar información y llenar tabla
            self.info_label.configure(text=f"Mostrando detalles de la Factura #{venta[0]}  |  Fecha: {venta[1]}  |  Total Original: RD$ {venta[2]:,.2f}")
            for detalle in detalles:
                self.details_tree.insert("", "end", values=detalle)
            
            self.process_return_button.configure(state="normal")

        except ValueError:
            messagebox.showerror("ID Inválido", "El número de factura debe ser un número entero.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al buscar la venta: {e}", parent=self)

    def procesar_devolucion(self):
        selected_items = self.details_tree.selection()
        if not selected_items:
            messagebox.showwarning("Sin selección", "Por favor, seleccione al menos un producto de la lista para devolver.", parent=self)
            return

        items_a_devolver = []
        total_devuelto = 0.0

        for selected_item in selected_items:
            item_data = self.details_tree.item(selected_item)['values']
            producto_id, nombre, cant_vendida, precio_unit = item_data

            # Preguntar cuántos se devuelven
            cantidad_a_devolver = simpledialog.askinteger("Cantidad a Devolver", 
                                                          f"¿Cuántas unidades de '{nombre}' desea devolver?\n(Máximo: {cant_vendida})",
                                                          parent=self, minvalue=1, maxvalue=int(cant_vendida))

            if cantidad_a_devolver is None: # El usuario presionó Cancelar
                continue

            items_a_devolver.append({
                "producto_id": producto_id,
                "cantidad_a_devolver": cantidad_a_devolver
            })
            total_devuelto += cantidad_a_devolver * float(precio_unit)

        if not items_a_devolver:
            return # No se procesa nada si no se especificaron cantidades

        if not messagebox.askyesno("Confirmar Devolución", 
                                   f"Se devolverá un total de RD$ {total_devuelto:,.2f}.\n"
                                   f"El stock de los productos seleccionados será ajustado.\n\n"
                                   f"¿Desea continuar?", parent=self):
            return

        try:
            database.registrar_devolucion(self.current_sale_id, items_a_devolver, total_devuelto, self.current_user['id'])
            messagebox.showinfo("Éxito", "La devolución ha sido registrada correctamente y el stock ha sido actualizado.", parent=self)
            # Limpiar la pantalla
            self.sale_id_entry.delete(0, "end")
            self.info_label.configure(text="Busque una factura para ver sus detalles.")
            for item in self.details_tree.get_children():
                self.details_tree.delete(item)
            self.process_return_button.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar la devolución: {e}", parent=self)
