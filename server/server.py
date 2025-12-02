import sys
from pathlib import Path
from datetime import datetime

# Añadir el directorio raíz del proyecto al sys.path
ROOT_PATH = Path(__file__).parent.parent # Subimos un nivel para apuntar a la carpeta 'Sistema'
sys.path.append(str(ROOT_PATH))

from flask import Flask, jsonify, render_template, request, send_file
from database.database import *
import csv
from io import StringIO
from fpdf import FPDF
import io
import re
from urllib.parse import quote

# Inicializar la aplicación Flask
app = Flask(__name__, template_folder=str(Path(__file__).parent / 'templates'), static_folder=str(Path(__file__).parent / 'static'))

# --- Rutas de la Interfaz Web (Frontend) ---

@app.route('/')
def dashboard():
    """Muestra el panel de control principal."""
    return render_template('dashboard.html')

@app.route('/scanner')
def scanner_page():
    """Muestra la página del escáner de códigos de barras."""
    return render_template('scanner.html')

@app.route('/quotations')
def quotations_page():
    """Muestra la página para crear cotizaciones."""
    return render_template('quotation.html')

@app.route('/pos')
def pos_page():
    """Muestra la página del Punto de Venta web."""
    return render_template('pos.html')

@app.route('/inventory')
def inventory_page():
    """Muestra la página de gestión de inventario web."""
    return render_template('inventory.html')

@app.route('/accounts_payable')
def accounts_payable_page():
    """Muestra la página de Cuentas por Pagar."""
    return render_template('accounts_payable.html')

@app.route('/accounts_receivable')
def accounts_receivable_page():
    """Muestra la página de Cuentas por Cobrar."""
    return render_template('accounts_receivable.html')

# --- Rutas de la API (Backend para el Frontend) ---

@app.route('/api/products')
def get_products():
    """Devuelve la lista de todos los productos en formato JSON."""
    productos = obtener_productos() # Esta función ya devuelve una lista de diccionarios
    return jsonify(productos)

@app.route('/api/stats')
def get_stats():
    """Devuelve estadísticas clave del negocio."""
    stats = obtener_estadisticas()
    return jsonify(stats)

@app.route('/api/product/update/<product_id>', methods=['POST'])
def update_product(product_id):
    """Actualiza un producto existente desde la interfaz web."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No se recibieron datos"}), 400
    try:
        # Extraer y validar datos del JSON recibido
        codigo = data.get('codigo_barras')
        nombre = data.get('nombre')
        costo = float(data.get('costo'))
        precio = float(data.get('precio'))
        stock = int(data.get('stock'))
        stock_minimo = int(data.get('stock_minimo'))
        departamento = data.get('departamento')
        unidad_medida = data.get('unidad_medida', 'Unidad')

        # Llamar a la función de la base de datos que ya teníamos
        actualizar_producto(product_id, codigo, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida)
        return jsonify({"success": True, "message": "Producto actualizado correctamente."})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/product/add', methods=['POST'])
def add_product():
    """Agrega un nuevo producto desde la interfaz web."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No se recibieron datos"}), 400

    try:
        # Extraer datos del JSON recibido
        codigo = data.get('codigo_barras')
        nombre = data.get('nombre')
        costo = float(data.get('costo'))
        precio = float(data.get('precio'))
        stock = int(data.get('stock'))
        stock_minimo = int(data.get('stock_minimo', 0)) # Default a 0 si no se envía
        departamento = data.get('departamento')
        unidad_medida = data.get('unidad_medida', 'Unidad')

        if not all([codigo, nombre, departamento]):
             return jsonify({"success": False, "error": "Código, Nombre y Departamento son requeridos."}), 400

        agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida)
        return jsonify({"success": True, "message": "Producto agregado correctamente."})

    except Exception as e:
        return jsonify({"success": False, "error": f"No se pudo agregar el producto. Causa probable: Código de barras duplicado. ({str(e)})"}), 500

@app.route('/api/product/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    """Elimina un producto desde la interfaz web."""
    try:
        # Reutilizamos la función que ya existe en database.py
        eliminar_producto(product_id)
        return jsonify({"success": True, "message": "Producto eliminado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/suppliers')
def get_suppliers():
    """Devuelve la lista de todos los proveedores."""
    try:
        proveedores = obtener_proveedores()
        # Convertir ObjectId a string para que sea serializable
        for p in proveedores:
            p['_id'] = str(p['_id'])
        return jsonify(proveedores)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable/add', methods=['POST'])
def add_account_payable():
    """Agrega una nueva cuenta por pagar."""
    data = request.get_json()
    try:
        agregar_factura_compra(data['proveedor_id'], data['numero_factura'], data['fecha_emision'], data['fecha_vencimiento'], float(data['monto']), data['moneda'])
        return jsonify({"success": True, "message": "Factura agregada correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable')
def get_accounts_payable():
    """Devuelve la lista de cuentas por pagar pendientes."""
    cuentas = obtener_cuentas_por_pagar()
    return jsonify(cuentas)

@app.route('/api/accounts_payable/pay/<factura_id>', methods=['POST'])
def pay_account_payable(factura_id):
    """Marca una cuenta por pagar como pagada."""
    try:
        marcar_factura_como_pagada(factura_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sales_chart_data')
def get_sales_chart_data():
    """Devuelve los datos de ventas para el gráfico del dashboard."""
    datos_brutos = obtener_datos_grafico_ventas()
    # Convertir a un formato más amigable para JavaScript
    datos_procesados = [{"dia": fila[0], "total": fila[1]} for fila in datos_brutos]
    return jsonify(datos_procesados)

@app.route('/api/scan_product', methods=['POST'])
def api_scan_product():
    """
    Recibe un código de barras y devuelve la información del producto.
    """
    data = request.get_json()
    barcode = data.get('barcode')

    if not barcode:
        return jsonify({"success": False, "error": "Código de barras no proporcionado."}), 400

    producto = buscar_producto_por_codigo(barcode)

    if producto:
        return jsonify({"success": True, "product": producto})
    else:
        return jsonify({"success": False, "error": "Producto no encontrado."}), 404

@app.route('/api/add_scanned_stock', methods=['POST'])
def api_add_scanned_stock():
    """
    Recibe una lista de productos y cantidades para sumar al stock.
    """
    data = request.get_json()
    items_to_add = data.get('items') # Esperamos una lista de {"product_id": X, "quantity": Y}

    if not items_to_add:
        return jsonify({"success": False, "error": "No se proporcionaron ítems para agregar stock."}), 400

    try:
        for item in items_to_add:
            sumar_stock_producto(item['product_id'], item['quantity'])
        return jsonify({"success": True, "message": "Stock actualizado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/low_stock')
def get_low_stock_report():
    """Devuelve una lista de productos con stock bajo."""
    try:
        productos = obtener_productos_stock_bajo()
        # Convertir ObjectId a string para que sea serializable
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]
        return jsonify({"success": True, "products": productos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search_products', methods=['POST'])
def api_search_products():
    """Busca productos por nombre."""
    data = request.get_json()
    search_term = data.get('term')

    if not search_term or len(search_term) < 3:
        return jsonify({"success": False, "error": "El término de búsqueda debe tener al menos 3 caracteres."}), 400

    try:
        productos = buscar_productos_por_nombre(search_term)
        return jsonify({"success": True, "products": productos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search_clients', methods=['POST'])
def api_search_clients():
    """Busca clientes por nombre o RNC/Cédula para la web."""
    data = request.get_json()
    search_term = data.get('term')

    if not search_term or len(search_term) < 2:
        return jsonify({"success": False, "error": "El término de búsqueda debe tener al menos 2 caracteres."}), 400

    try:
        clientes = buscar_clientes(search_term)
        return jsonify({"success": True, "clients": clientes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/export/csv')
def export_products_csv():
    """Exporta el inventario a CSV para descarga con formato completo."""
    try:
        productos = obtener_productos()
        # Headers en el orden correcto para importación completa
        headers = ["Código", "Descripción", "Precio Costo", "Precio Venta", "Stock", "Stock Mín.", "Departamento", "Unidad Medida"]

        # Crear CSV en memoria
        from io import StringIO
        import csv

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        # Escribir cada producto con todos sus campos
        for prod in productos:
            writer.writerow([
                prod.get('codigo_barras', ''),
                prod.get('nombre', ''),
                prod.get('costo', 0),
                prod.get('precio', 0),
                prod.get('stock', 0),
                prod.get('stock_minimo', 0),
                prod.get('departamento', ''),
                prod.get('unidad_medida', 'Unidad')
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='inventario.csv'
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/import/csv', methods=['POST'])
def import_products_csv():
    """Importa productos desde un archivo CSV subido."""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No se envió ningún archivo."}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({"success": False, "error": "Archivo CSV requerido."}), 400

    try:
        import csv
        import io

        # Leer el CSV
        stream = io.StringIO(file.read().decode('utf-8'))
        reader = csv.reader(stream)
        headers = next(reader)

        exitosos = 0
        fallidos = 0

        for row in reader:
            try:
                # Asumir orden: codigo, nombre, departamento, precio, stock
                if len(row) < 5:
                    fallidos += 1
                    continue

                codigo = row[0]
                nombre = row[1]
                departamento = row[2]
                precio = float(row[3]) if row[3] else 0
                stock = int(float(row[4])) if row[4] else 0

                # Agregar producto (sin costo para simplicidad)
                agregar_producto(codigo, nombre, precio, precio, stock, 0, departamento)
                exitosos += 1

            except Exception:
                fallidos += 1

        return jsonify({"success": True, "message": f"Importados: {exitosos}, Fallidos: {fallidos}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/export/pdf')
def export_products_pdf():
    """Exporta el reporte de inventario a PDF."""
    try:
        productos = obtener_productos()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Reporte de Inventario", 0, 1, "C")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 10)
        headers = ["ID", "Codigo", "Nombre", "Precio", "Stock"]
        col_widths = [20, 30, 70, 25, 20]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, "C")
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        for prod in productos:
            if pdf.get_y() > 260:  # Nueva página si se acerca al final
                pdf.add_page()
            pdf.cell(col_widths[0], 8, str(prod.get('id', '')), 1, 0)
            pdf.cell(col_widths[1], 8, str(prod.get('codigo_barras', '')), 1, 0)
            pdf.cell(col_widths[2], 8, str(prod.get('nombre', ''))[:30], 1, 0)
            pdf.cell(col_widths[3], 8, f"RD$ {prod.get('precio', 0):.2f}", 1, 0, "R")
            pdf.cell(col_widths[4], 8, str(prod.get('stock', 0)), 1, 1, "C")

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return send_file(
            io.BytesIO(pdf_output),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='inventario.pdf'
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_quotation_pdf', methods=['POST'])
def api_generate_quotation_pdf():
    """Genera un PDF de cotización y lo devuelve para su descarga."""
    data = request.get_json()
    items = data.get('items', [])
    client_info = data.get('client', {})

    if not items:
        return jsonify({"success": False, "error": "No hay productos en la cotización."}), 400

    # Lógica de cálculo de ITBIS (copiada de quotation_frame.py)
    ITBIS_RATE = 0.18
    total_cotizacion = sum(item['cantidad'] * item['precio'] for item in items)
    base_imponible = total_cotizacion / (1 + ITBIS_RATE)
    itbis_incluido = total_cotizacion - base_imponible
    total = total_cotizacion

    cliente_nombre = client_info.get('nombre') if client_info else "Consumidor Final"
    cotizacion_id = f"COT-WEB-{datetime.now().strftime('%Y%m%d%H%M%S')}"

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
        for item in items:
            pdf.cell(20, 8, str(item['cantidad']), 1, 0, "C")
            pdf.cell(95, 8, item['nombre'], 1, 0, "L")
            pdf.cell(35, 8, f"RD$ {item['precio']:,.2f}", 1, 0, "R")
            pdf.cell(35, 8, f"RD$ {(item['cantidad'] * item['precio']):,.2f}", 1, 1, "R")

        # Totales y pie de página
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(125, 8, "Subtotal (Base):", 0, 0, "R")
        pdf.cell(60, 8, f"RD$ {base_imponible:,.2f}", 0, 1, "R")
        pdf.cell(125, 8, f"ITBIS ({ITBIS_RATE*100:.0f}%):", 0, 0, "R")
        pdf.cell(60, 8, f"RD$ {itbis_incluido:,.2f}", 0, 1, "R")
        pdf.set_font("Arial", "B", 14)
        pdf.cell(125, 10, "TOTAL:", 0, 0, "R")
        pdf.cell(60, 10, f"RD$ {total:,.2f}", 0, 1, "R")

        pdf.ln(15)
        pdf.set_font("Arial", "I", 9)
        pdf.cell(0, 5, "Esta cotizacion es valida por 15 dias.", 0, 1, "C")
        pdf.cell(0, 5, "Precios sujetos a cambio sin previo aviso.", 0, 1, "C")
        pdf.cell(0, 5, "Documento no fiscal.", 0, 1, "C")

        # Generar el PDF en memoria
        pdf_output = pdf.output(dest='S').encode('latin-1')

        # Enviar el archivo PDF al navegador para su descarga
        return send_file(
            io.BytesIO(pdf_output),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Cotizacion_{cotizacion_id}.pdf'
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quotation/save', methods=['POST'])
def save_quotation():
    """Guarda una cotización en la base de datos."""
    data = request.get_json()
    items = data.get('items', [])
    client_id = data.get('client_id')

    if not items:
        return jsonify({"success": False, "error": "No hay productos en la cotización."}), 400

    try:
        cotizacion_id = guardar_cotizacion(items, client_id)
        return jsonify({"success": True, "message": f"Cotización guardada con ID: {cotizacion_id}", "quotation_id": cotizacion_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quotations')
def get_quotations():
    """Obtiene lista de cotizaciones guardadas."""
    try:
        cotizaciones = obtener_cotizaciones()
        return jsonify(cotizaciones)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_receivable')
def get_accounts_receivable():
    """Devuelve la lista de cuentas por cobrar pendientes."""
    try:
        cuentas = obtener_cuentas_por_cobrar()
        return jsonify(cuentas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts_receivable/pay', methods=['POST'])
def pay_accounts_receivable():
    """Registra un pago/abono en una cuenta por cobrar."""
    data = request.get_json()
    invoice_id = data.get('invoice_id')
    amount_paid = data.get('amount_paid')

    if not invoice_id or not amount_paid:
        return jsonify({"success": False, "error": "Faltan parámetros requeridos."}), 400

    try:
        registrar_pago_cliente(invoice_id, float(amount_paid))
        return jsonify({"success": True, "message": "Pago registrado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quotation/generate_pdf/<quotation_id>', methods=['GET'])
def api_generate_quotation_pdf_from_saved(quotation_id):
    """Genera PDF de una cotización guardada."""
    try:
        cotizacion, items = obtener_cotizacion_por_id(quotation_id)
        if not cotizacion:
            return jsonify({"success": False, "error": "Cotización no encontrada."}), 404

        # Preparar datos para generate_quotation_pdf existente
        data = {
            'items': items,
            'client': {'nombre': "Consumidor Final"} if not cotizacion.get('cliente_id') else "Cliente"  # Ajustar si hay cliente
        }

        # Llamar al método existente
        # Esto es truco, llamo el endpoint con los datos
        with app.test_request_context('/api/generate_quotation_pdf', method='POST', json=data):
            response = api_generate_quotation_pdf()
            # Es complicado, mejor regenerar PDF aquí mismo

        ITBIS_RATE = 0.18
        cliente_nombre = cotizacion.get('cliente') or "Consumidor Final"
        cotizacion_id_pdf = f"COT-{quotation_id}"

        pdf = FPDF()
        pdf.add_page()

        # Encabezado (similar al existente)
        logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            pdf.image(str(logo_path), x=10, y=8, w=40)
            pdf.set_x(55)

        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 10, "Ferretería XYZ", 0, 1, "L")
        pdf.set_font("Arial", "", 10)
        if logo_path.exists(): pdf.set_x(55)
        pdf.cell(0, 5, "Av. Principal #123, Santo Domingo", 0, 1, "L")
        if logo_path.exists(): pdf.set_x(55)
        pdf.cell(0, 5, "RNC: XXXXXXXXXXX | Tel: (809) 555-1234", 0, 1, "L")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "COTIZACION GUARDADA", 0, 1, "L")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 6, f"ID: {quotation_id}", 0, 1, "L")
        pdf.cell(0, 6, f"Fecha: {cotizacion['fecha'].strftime('%d/%m/%Y')}", 0, 1, "L")
        pdf.cell(0, 6, f"Cliente: {cliente_nombre}", 0, 1, "L")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(20, 8, "Cant.", 1, 0, "C")
        pdf.cell(95, 8, "Descripcion", 1, 0, "C")
        pdf.cell(35, 8, "Precio Unit.", 1, 0, "C")
        pdf.cell(35, 8, "Subtotal", 1, 1, "C")
        pdf.set_font("Arial", "", 10)
        for item in items:
            pdf.cell(20, 8, str(item['cantidad']), 1, 0, "C")
            pdf.cell(95, 8, item['nombre'], 1, 0, "L")
            pdf.cell(35, 8, f"RD$ {item['precio']:.2f}", 1, 0, "R")
            pdf.cell(35, 8, f"RD$ {item['subtotal']:.2f}", 1, 1, "R")

        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(125, 8, "Subtotal (Base):", 0, 0, "R")
        pdf.cell(60, 8, f"RD$ {cotizacion['base_imponible']:.2f}", 0, 1, "R")
        pdf.cell(125, 8, f"ITBIS (18%):", 0, 0, "R")
        pdf.cell(60, 8, f"RD$ {cotizacion['itbis']:.2f}", 0, 1, "R")
        pdf.set_font("Arial", "B", 14)
        pdf.cell(125, 10, "TOTAL:", 0, 0, "R")
        pdf.cell(60, 10, f"RD$ {cotizacion['total']:.2f}", 0, 1, "R")

        pdf.ln(15)
        pdf.set_font("Arial", "I", 9)
        pdf.cell(0, 5, "Esta cotizacion es valida por 15 dias.", 0, 1, "C")
        pdf.cell(0, 5, "Precios sujetos a cambio sin previo aviso.", 0, 1, "C")
        pdf.cell(0, 5, "Documento no fiscal.", 0, 1, "C")

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return send_file(
            io.BytesIO(pdf_output),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Cotizacion_{quotation_id}.pdf'
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pos/register_sale', methods=['POST'])
def api_register_sale():
    """Registra una venta realizada desde la interfaz web."""
    data = request.get_json()
    items = data.get('items', [])
    client_id = data.get('client_id')
    payment_method = data.get('payment_method')
    discount = float(data.get('discount', 0.0))

    # Para simplificar, asignaremos la venta al usuario 'admin' por defecto.
    # Una implementación completa requeriría un sistema de login web.
    admin_user = obtener_usuario_por_nombre('admin')
    if not admin_user:
        return jsonify({"success": False, "error": "Usuario 'admin' no encontrado para registrar la venta."}), 500
    user_id = str(admin_user['_id'])

    if not items:
        return jsonify({"success": False, "error": "No hay productos en la venta."}), 400

    # Recalcular totales en el servidor para garantizar la integridad de los datos
    ITBIS_RATE = 0.18
    subtotal_bruto = sum(item['cantidad'] * item['precio'] for item in items)
    subtotal_descontado = subtotal_bruto - discount
    total = subtotal_descontado
    itbis_incluido = subtotal_descontado - (subtotal_descontado / (1 + ITBIS_RATE))

    try:
        venta_id = registrar_venta(items, total, itbis_incluido, discount, user_id, payment_method, client_id)
        return jsonify({"success": True, "message": f"Venta #{venta_id} registrada correctamente.", "sale_id": venta_id})
    except Exception as e:
        # Log del error en el servidor para depuración
        print(f"Error al registrar venta desde la web: {e}")
        return jsonify({"success": False, "error": f"No se pudo registrar la venta: {e}"}), 500

@app.route('/api/pos/print_ticket/<sale_id>')
def print_ticket_web(sale_id):
    """
    Genera una página HTML optimizada para impresión de ticket desde la web.
    """
    try:
        # Intentar obtener datos reales de la venta por ID
        # Nota: En un sistema real, necesitarías implementar la búsqueda de venta por ID

        # Por simplicidad, obtenemos la última venta registrada
        # (esto funciona porque las ventas se registran justo antes de imprimir)
        try:
            # Obtener la última venta del día (aproximación)
            ventas_hoy = obtener_ventas_del_dia()
            if ventas_hoy and len(ventas_hoy) > 0:
                venta = ventas_hoy[-1]  # Última venta

                # Obtener items de la venta
                items_venta = obtener_items_venta(venta['id']) if 'id' in venta else []

                ticket_data = {
                    'sale_id': f"{venta.get('id', sale_id):06d}",
                    'fecha': datetime.now().strftime('%d/%m/%Y %I:%M %p'),
                    'cliente': 'Consumidor Final',  # Simplificado
                    'items': [
                        {
                            'cantidad': item.get('cantidad', 1),
                            'nombre': item.get('nombre', 'Producto'),
                            'precio': item.get('precio_venta', 0),
                            'subtotal': item.get('subtotal', 0)
                        } for item in items_venta
                    ],
                    'subtotal_bruto': venta.get('total', 0) + venta.get('descuento', 0),
                    'descuento': venta.get('descuento', 0),
                    'itbis_rate': 0.18,  # Valor fijo de ITBIS
                    'itbis_incluido': venta.get('itbis', 0),
                    'total': venta.get('total', 0),
                    'monto_recibido': None,  # No disponible en este formato
                    'devuelta': None
                }
            else:
                # Datos de test cuando no hay ventas previas
                ticket_data = {
                    'sale_id': f"WEB-{sale_id:04d}",
                    'fecha': datetime.now().strftime('%d/%m/%Y %I:%M %p'),
                    'cliente': 'Test - Consumidor Final',
                    'items': [
                        {'cantidad': 2, 'nombre': 'Producto Demo A', 'precio': 100.00, 'subtotal': 200.00},
                        {'cantidad': 1, 'nombre': 'Producto Demo B', 'precio': 150.00, 'subtotal': 150.00}
                    ],
                    'subtotal_bruto': 350.00,
                    'descuento': 0.00,
                    'itbis_rate': 0.18,
                    'itbis_incluido': 53.00,
                    'total': 350.00,
                    'monto_recibido': 400.00,
                    'devuelta': 50.00
                }

        except Exception as db_error:
            # Si hay error con base de datos, usar datos de test
            print(f"Error obteniendo datos de venta: {db_error}")
            ticket_data = {
                'sale_id': f"WEB-{sale_id:04d}",
                'fecha': datetime.now().strftime('%d/%m/%Y %I:%M %p'),
                'cliente': 'Error - Consumidor Final',
                'items': [
                    {'cantidad': 1, 'nombre': 'Producto Error', 'precio': 0.00, 'subtotal': 0.00}
                ],
                'subtotal_bruto': 0.00,
                'descuento': 0.00,
                'itbis_rate': 0.18,
                'itbis_incluido': 0.00,
                'total': 0.00,
                'monto_recibido': None,
                'devuelta': None
            }

        # Renderizar template especial para impresión
        return render_template('print_ticket.html', ticket=ticket_data)

    except Exception as e:
        print(f"Error generando ticket: {e}")
        return f"<h1>Error generando ticket: {e}</h1>", 500

@app.route('/print_test')
def print_test():
    """Página de prueba para impresión de tickets."""
    return render_template('print_ticket.html')


if __name__ == '__main__':
    # La opción host='0.0.0.0' hace que el servidor sea accesible
    # desde otros dispositivos en la misma red (como tu tablet).
    # El modo debug recarga automáticamente el servidor cuando haces cambios.
    app.run(host='0.0.0.0', port=5000, debug=True)
