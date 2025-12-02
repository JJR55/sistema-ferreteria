from escpos.printer import Usb
from tkinter import messagebox
from datetime import datetime

# --- CONFIGURACIÓN DE LA IMPRESORA ---
# Debes encontrar el idVendor y idProduct de tu impresora.
# En Windows, puedes encontrarlos en el "Administrador de dispositivos":
# 1. Busca tu impresora de tickets.
# 2. Clic derecho -> Propiedades.
# 3. Pestaña "Detalles".
# 4. En el menú desplegable "Propiedad", selecciona "Id. de hardware".
# 5. Verás algo como "USB\VID_04B8&PID_0202".
#    - idVendor es el número después de VID_, en este caso 0x04b8.
#    - idProduct es el número después de PID_, en este caso 0x0202.
#
# ¡¡¡DEBES CAMBIAR ESTOS VALORES POR LOS DE TU IMPRESORA!!!
PRINTER_VENDOR_ID = 0x04b8   # Ejemplo para una impresora Epson
PRINTER_PRODUCT_ID = 0x0202  # Ejemplo para una impresora Epson

def imprimir_ticket(venta_id, items_venta, subtotal_base, itbis_incluido, descuento, total, monto_recibido, devuelta):
    """
    Genera y envía el ticket de venta a la impresora térmica.
    """
    try:
        # Inicializar la conexión con la impresora
        p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID, 0)

        # --- Encabezado del Ticket ---
        p.set(align='center', text_type='B')
        p.text("Ferretería XYZ\n")
        p.set(align='center')
        p.text("RNC: XXXXXXXXXXX\n")
        p.text("Av. Principal #123, Santo Domingo\n")
        p.text("Tel: (809) 555-1234\n")
        p.text("--------------------------------\n")

        # --- Información de la Venta ---
        p.set(align='left')
        p.text(f"Factura No: {venta_id:06d}\n")
        p.text(f"Fecha: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}\n")
        p.text("--------------------------------\n")

        # --- Cuerpo del Ticket (Items) ---
        p.text("Cant. Producto         P.Unit  Subt.\n")
        for item in items_venta:
            nombre = item['nombre']
            # Acortar nombre si es muy largo
            if len(nombre) > 18:
                nombre = nombre[:17] + "."
            
            cantidad = f"{item['cantidad']}x"
            precio = f"{item['precio']:>7.2f}"
            subtotal_item = f"{(item['cantidad'] * item['precio']):>7.2f}"

            linea = f"{cantidad:<5} {nombre:<18} {precio} {subtotal_item}\n"
            p.text(linea)

        # --- Totales ---
        p.text("--------------------------------\n")
        p.set(align='right')
        p.text(f"Subtotal: RD$ {(subtotal_base + itbis_incluido + descuento):,.2f}\n")
        if descuento > 0:
            p.text(f"Descuento: - RD$ {descuento:,.2f}\n")
        p.text(f"ITBIS Incluido: RD$ {itbis_incluido:,.2f}\n")
        p.set(text_type='B', height=2, width=2)
        p.text(f"TOTAL: RD$ {total:,.2f}\n\n")

        if monto_recibido > 0:
            p.set(align='right', text_type='normal')
            p.text(f"Efectivo Recibido: RD$ {monto_recibido:,.2f}\n")
            p.text(f"Devuelta: RD$ {devuelta:,.2f}\n\n")

        # --- Pie de Página ---
        p.set(align='center', text_type='normal')
        p.text("¡Gracias por su compra!\n\n")

        # Cortar el papel
        p.cut()

        p.close()

    except Exception as e:
        error_msg = f"No se pudo imprimir el ticket. Verifique la conexión de la impresora y la configuración.\n\nError: {e}"
        messagebox.showerror("Error de Impresión", error_msg)

def imprimir_cotizacion(cotizacion_id, cliente_nombre, items, subtotal, itbis, total):
    """
    Genera y envía una cotización a la impresora térmica.
    """
    try:
        p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID, 0)

        # --- Encabezado ---
        p.set(align='center', text_type='B', width=2, height=2)
        p.text("COTIZACION\n")
        p.set(text_type='normal')
        p.text("--------------------------------\n")
        p.set(align='center', text_type='B')
        p.text("Ferretería XYZ\n")
        p.set(align='center')
        p.text("RNC: XXXXXXXXXXX\n")
        p.text("Av. Principal #123, Santo Domingo\n")
        p.text("Tel: (809) 555-1234\n")
        p.text("--------------------------------\n")

        # --- Información del Cliente y Documento ---
        p.set(align='left')
        p.text(f"Cotizacion No: {cotizacion_id}\n")
        p.text(f"Fecha: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}\n")
        p.text(f"Cliente: {cliente_nombre}\n")
        p.text("--------------------------------\n")

        # --- Cuerpo (Items) ---
        p.text("Cant. Producto         P.Unit  Subt.\n")
        for item in items:
            nombre = item['nombre']
            if len(nombre) > 18: nombre = nombre[:17] + "."
            cantidad = f"{item['cantidad']}x"
            precio = f"{item['precio']:>7.2f}"
            subtotal_item = f"{(item['cantidad'] * item['precio']):>7.2f}"
            linea = f"{cantidad:<5} {nombre:<18} {precio} {subtotal_item}\n"
            p.text(linea)

        # --- Totales ---
        p.text("--------------------------------\n")
        p.set(align='right')
        p.text(f"Subtotal (Base): RD$ {subtotal_base:,.2f}\n")
        p.text(f"ITBIS Incluido: RD$ {itbis_incluido:,.2f}\n")
        p.set(text_type='B', height=2, width=2)
        p.text(f"TOTAL: RD$ {total:,.2f}\n\n")

        # --- Pie de Página ---
        p.set(align='center', text_type='normal')
        p.text("Esta cotizacion es valida por 15 dias.\n")
        p.text("Documento no fiscal.\n\n")

        p.cut()
        p.close()

    except Exception as e:
        # Reutilizamos el mismo manejo de error, pero lanzamos la excepción
        # para que el frame que llama pueda mostrar el mensaje.
        raise e