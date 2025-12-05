import customtkinter as ctk
from tkinter import ttk, messagebox
import database.database as database
from datetime import date, datetime

class CashClosingFrame(ctk.CTkFrame):
    def __init__(self, master, current_user, **kwargs):
        super().__init__(master, **kwargs)

        self.current_user = current_user
        self.current_summary = {}

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Frame de Controles (Fechas) ---
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls_frame, text="Desde:").pack(side="left", padx=(10, 5))
        self.start_date_entry = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(controls_frame, text="Hasta:").pack(side="left", padx=(20, 5))
        self.end_date_entry = ctk.CTkEntry(controls_frame, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.pack(side="left", padx=5)

        # Por defecto, el día de hoy
        today_str = date.today().strftime("%Y-%m-%d")
        self.start_date_entry.insert(0, today_str)
        self.end_date_entry.insert(0, today_str)

        generate_button = ctk.CTkButton(controls_frame, text="Generar Reporte de Cierre", command=self.generar_reporte_cierre)
        generate_button.pack(side="left", padx=20)

        # --- Frame de Resumen y Arqueo ---
        summary_frame = ctk.CTkFrame(self)
        summary_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        summary_frame.grid_columnconfigure((0, 1), weight=1)

        # Columna de Totales Esperados
        expected_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
        expected_frame.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        ctk.CTkLabel(expected_frame, text="Totales del Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        self.total_efectivo_label = ctk.CTkLabel(expected_frame, text="Efectivo Esperado: RD$ 0.00", font=ctk.CTkFont(size=14))
        self.total_efectivo_label.pack(anchor="w", pady=5)
        self.total_tarjeta_label = ctk.CTkLabel(expected_frame, text="Total Tarjeta: RD$ 0.00", font=ctk.CTkFont(size=14))
        self.total_tarjeta_label.pack(anchor="w", pady=5)
        self.total_transferencia_label = ctk.CTkLabel(expected_frame, text="Total Transferencia: RD$ 0.00", font=ctk.CTkFont(size=14))
        self.total_transferencia_label.pack(anchor="w", pady=5)
        self.total_credito_label = ctk.CTkLabel(expected_frame, text="Total Crédito: RD$ 0.00", font=ctk.CTkFont(size=14))
        self.total_credito_label.pack(anchor="w", pady=5)
        ctk.CTkLabel(expected_frame, text="-"*30).pack(anchor="w", pady=5)
        self.total_ventas_label = ctk.CTkLabel(expected_frame, text="Total Ventas: RD$ 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_ventas_label.pack(anchor="w", pady=5)

        # Columna de Arqueo de Caja
        counting_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
        counting_frame.grid(row=0, column=1, padx=10, pady=10, sticky="n")
        ctk.CTkLabel(counting_frame, text="Arqueo de Caja (Efectivo)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        ctk.CTkLabel(counting_frame, text="Monto Contado en Caja:").pack(anchor="w", pady=(10, 0))
        self.counted_cash_entry = ctk.CTkEntry(counting_frame, placeholder_text="0.00")
        self.counted_cash_entry.pack(fill="x", pady=5)
        self.counted_cash_entry.bind("<KeyRelease>", self.calcular_diferencia)

        self.diferencia_label = ctk.CTkLabel(counting_frame, text="Diferencia: RD$ 0.00", font=ctk.CTkFont(size=18, weight="bold"))
        self.diferencia_label.pack(anchor="w", pady=10)

        ctk.CTkLabel(counting_frame, text="Notas del Cierre:").pack(anchor="w", pady=(10, 0))
        self.notes_entry = ctk.CTkTextbox(counting_frame, height=80)
        self.notes_entry.pack(fill="x", pady=5)

        # --- Botón de Finalizar Cierre ---
        self.finalize_button = ctk.CTkButton(self, text="Finalizar y Guardar Cierre de Caja", height=40, command=self.finalizar_cierre)
        self.finalize_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.generar_reporte_cierre()

    def generar_reporte_cierre(self):
        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()

        try:
            # Convertir a objetos datetime para la consulta
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            messagebox.showerror("Formato de Fecha Inválido", "Por favor, use el formato YYYY-MM-DD.", parent=self)
            return

        resumen = database.obtener_resumen_ventas_por_metodo(start_date, end_date)
        self.current_summary = resumen

        total_ventas = sum(resumen.values())

        self.total_efectivo_label.configure(text=f"Efectivo Esperado: RD$ {resumen.get('Efectivo', 0):,.2f}")
        self.total_tarjeta_label.configure(text=f"Total Tarjeta: RD$ {resumen.get('Tarjeta', 0):,.2f}")
        self.total_transferencia_label.configure(text=f"Total Transferencia: RD$ {resumen.get('Transferencia', 0):,.2f}")
        self.total_credito_label.configure(text=f"Total Crédito: RD$ {resumen.get('Crédito', 0):,.2f}")
        self.total_ventas_label.configure(text=f"Total Ventas: RD$ {total_ventas:,.2f}")

        self.calcular_diferencia()

    def calcular_diferencia(self, event=None):
        try:
            contado = float(self.counted_cash_entry.get() or 0)
        except ValueError:
            contado = 0

        esperado = self.current_summary.get('Efectivo', 0)
        diferencia = contado - esperado

        color = "white"
        texto_diferencia = f"Diferencia: RD$ {diferencia:,.2f}"
        if diferencia > 0:
            color = "#28a745" # Verde (sobrante)
            texto_diferencia += " (Sobrante)"
        elif diferencia < 0:
            color = "#D32F2F" # Rojo (faltante)
            texto_diferencia += " (Faltante)"

        self.diferencia_label.configure(text=texto_diferencia, text_color=color)

    def finalizar_cierre(self):
        if not self.current_summary:
            messagebox.showwarning("Sin Datos", "Primero debe generar un reporte de cierre.", parent=self)
            return

        try:
            contado = float(self.counted_cash_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "El monto contado en caja debe ser un número válido.", parent=self)
            return

        esperado = self.current_summary.get('Efectivo', 0)
        diferencia = contado - esperado
        notas = self.notes_entry.get("1.0", "end-1c")

        confirm_message = (
            f"Resumen del Cierre:\n\n"
            f"Efectivo Esperado: RD$ {esperado:,.2f}\n"
            f"Efectivo Contado: RD$ {contado:,.2f}\n"
            f"Diferencia: RD$ {diferencia:,.2f}\n\n"
            f"¿Está seguro de que desea guardar este cierre de caja?"
        )

        if not messagebox.askyesno("Confirmar Cierre", confirm_message, parent=self):
            return

        datos_cierre = {
            "fecha_cierre": datetime.now(),
            "usuario_id": self.current_user['id'],
            "usuario_nombre": self.current_user['username'],
            "fecha_inicio_periodo": self.start_date_entry.get(),
            "fecha_fin_periodo": self.end_date_entry.get(),
            "total_esperado_efectivo": esperado,
            "total_contado_efectivo": contado,
            "diferencia_efectivo": diferencia,
            "total_tarjeta": self.current_summary.get('Tarjeta', 0),
            "total_transferencia": self.current_summary.get('Transferencia', 0),
            "total_credito": self.current_summary.get('Crédito', 0),
            "total_ventas": sum(self.current_summary.values()),
            "notas": notas
        }

        try:
            database.registrar_cierre_caja(datos_cierre)
            messagebox.showinfo("Éxito", "El cierre de caja ha sido guardado correctamente.", parent=self)
            # Limpiar campos para el próximo cierre
            self.counted_cash_entry.delete(0, "end")
            self.notes_entry.delete("1.0", "end")
            self.generar_reporte_cierre() # Recargar con los datos actuales
        except Exception as e:
            messagebox.showerror("Error de Base de Datos", f"No se pudo guardar el cierre de caja: {e}", parent=self)