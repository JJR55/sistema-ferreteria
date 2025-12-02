import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import database.database as database

class AccountsReceivableFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Frame de Acciones ---
        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.pay_button = ctk.CTkButton(actions_frame, text="Registrar Abono/Pago", command=self.registrar_pago)
        self.pay_button.pack(side="left", padx=5)

        self.refresh_button = ctk.CTkButton(actions_frame, text="Actualizar Lista", command=self.cargar_cuentas_por_cobrar)
        self.refresh_button.pack(side="left", padx=5)

        # --- Lista de cuentas por cobrar ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.receivable_tree = ttk.Treeview(tree_frame, columns=("ID", "Fecha", "Cliente", "Total", "Saldo Pendiente"), show='headings')
        self.receivable_tree.heading("ID", text="Factura ID")
        self.receivable_tree.heading("Fecha", text="Fecha")
        self.receivable_tree.heading("Cliente", text="Cliente")
        self.receivable_tree.heading("Total", text="Monto Total")
        self.receivable_tree.heading("Saldo Pendiente", text="Saldo Pendiente")
        self.receivable_tree.column("ID", width=100)
        self.receivable_tree.column("Fecha", width=150)
        self.receivable_tree.column("Cliente", width=250)
        self.receivable_tree.column("Total", anchor="e")
        self.receivable_tree.column("Saldo Pendiente", anchor="e")
        self.receivable_tree.grid(row=0, column=0, sticky="nsew")

        self.cargar_cuentas_por_cobrar()

    def cargar_cuentas_por_cobrar(self):
        for item in self.receivable_tree.get_children():
            self.receivable_tree.delete(item)
        
        cuentas = database.obtener_cuentas_por_cobrar()
        for c in cuentas:
            # Formatear valores para mostrar
            fecha = c['fecha'].strftime("%Y-%m-%d %H:%M")
            total = f"RD$ {c['total']:,.2f}"
            saldo = f"RD$ {c['saldo_pendiente']:,.2f}"
            self.receivable_tree.insert("", "end", values=(c['venta_id'], fecha, c['cliente_nombre'], total, saldo))

    def registrar_pago(self):
        selected_item = self.receivable_tree.selection()
        if not selected_item:
            messagebox.showwarning("Sin selección", "Por favor, seleccione una factura para registrar un pago.", parent=self)
            return

        item_values = self.receivable_tree.item(selected_item[0])['values']
        venta_id = item_values[0]
        saldo_actual_str = item_values[4].replace("RD$ ", "").replace(",", "")
        saldo_actual = float(saldo_actual_str)

        monto_pagado = simpledialog.askfloat("Registrar Pago", 
                                             f"Factura: {venta_id}\nSaldo Actual: RD$ {saldo_actual:,.2f}\n\nIngrese el monto a abonar:",
                                             parent=self, minvalue=0.01, maxvalue=saldo_actual)

        if monto_pagado:
            try:
                database.registrar_pago_cliente(venta_id, monto_pagado)
                messagebox.showinfo("Éxito", "El pago ha sido registrado correctamente.", parent=self)
                self.cargar_cuentas_por_cobrar()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar el pago: {e}", parent=self)