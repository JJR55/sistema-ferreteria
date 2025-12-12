import sys
from pathlib import Path
from datetime import datetime
import threading

# Añadir el directorio raíz del proyecto al sys.path
ROOT_PATH = Path(__file__).parent.parent # Subimos un nivel para apuntar a la carpeta 'Sistema'
sys.path.append(str(ROOT_PATH))

from flask import Flask, jsonify, render_template, request, send_file
from flask import session, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from bson import ObjectId
from database.database import *
from gui.security import check_password # Importamos la función para verificar contraseñas
from functools import wraps # Para crear el decorador de login
import csv
from io import StringIO
from fpdf import FPDF
import io
import re
from urllib.parse import quote
import base64
import unicodedata

# Conectar a la base de datos INMEDIATAMENTE después del import para que las colecciones se inicialicen
db = conectar_db()
print("✅ Inicialización de base de datos completada en server.py")
from PIL import Image
import numpy as np

# Inicializar la aplicación Flask
app = Flask(__name__, template_folder=str(Path(__file__).parent / 'templates'), static_folder=str(Path(__file__).parent / 'static'))
app.secret_key = 'una-clave-secreta-muy-segura-y-dificil-de-adivinar' # Necesario para usar sesiones

# Inicializar SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Import opcional de opencv (cv2)
try:
    import cv2
    OPENCV_AVAILABLE = True
    print("OpenCV disponible: funcionalidad avanzada de imágenes activa.")
except ImportError:
    cv2 = None
    OPENCV_AVAILABLE = False
    print("Advertencia: OpenCV no está disponible. Funcionalidad de procesamiento avanzado de imágenes limitada.")

# Import opcional de pyzbar
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
    print("Pyzbar disponible: escaneo de imágenes desde servidor activo.")
except ImportError:
    pyzbar_decode = None
    PYZBAR_AVAILABLE = False
    print("Advertencia: Pyzbar no está disponible. El escaneo de imágenes desde el servidor no funcionará.")

# Import opcional de pytesseract
try:
    import pytesseract
    # Configurar la ruta de Tesseract para Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    PYTESSERACT_AVAILABLE = True
    print("✅ Pytesseract disponible: escaneo de facturas activo.")
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False
    print("❌ Advertencia: Pytesseract no está disponible. El escaneo de facturas (OCR) no funcionará. Para activarlo, instale Tesseract-OCR en el sistema y luego ejecute 'pip install pytesseract'.")

# --- Decorador para requerir inicio de sesión ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- FUNCIONES DE NOTIFICACIONES EN TIEMPO REAL ---
def notify_sale_registered(sale_id, total):
    """Notifica cuando se registra una venta."""
    try:
        notification = {
            'type': 'sale_registered',
            'title': 'Nueva Venta Registrada',
            'message': f'Venta #{sale_id} registrada por RD$ {total:.2f}',
            'sale_id': sale_id,
            'priority': 'low',
            'timestamp': datetime.now().isoformat()
        }
        socketio.emit('notification', notification)
    except Exception as e:
        print(f"Error enviando notificación de venta: {e}")

def notify_low_stock(producto):
    """Notifica cuando un producto tiene stock bajo."""
    try:
        notification = {
            'type': 'low_stock',
            'title': 'Producto con Stock Bajo',
            'message': f'El producto "{producto.get("nombre", "N/A")}" tiene stock bajo.',
            'product_id': str(producto.get('_id')),
            'priority': 'high',
            'timestamp': datetime.now().isoformat()
        }
        socketio.emit('notification', notification)
    except Exception as e:
        print(f"Error enviando notificación de stock bajo: {e}")

def notify_overdue_payment(factura):
    """Notifica sobre pagos vencidos."""
    try:
        notification = {
            'type': 'overdue_payment',
            'title': 'Pago Vencido',
            'message': f'Factura {factura.get("numero_factura", "N/A")} de {factura.get("proveedor_nombre", "Proveedor")} está vencida.',
            'factura_id': str(factura.get('_id')),
            'priority': 'critical',
            'timestamp': datetime.now().isoformat()
        }
        socketio.emit('notification', notification)
    except Exception as e:
        print(f"Error enviando notificación de pago vencido: {e}")

# --- Rutas de Authentication ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Usuario y contraseña son requeridos.', 'danger')
            return redirect(url_for('login'))

        # Buscar usuario en la base de datos
        user = obtener_usuario_por_nombre(username)

        if user and check_password(user['hash_contrasena'], password):
            # Guardar información del usuario en la sesión
            session['user_id'] = str(user['_id'])
            session['username'] = user['nombre_usuario']
            session['role'] = user.get('rol', 'Usuario')
            flash(f'Bienvenido, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
            return redirect(url_for('login'))

    # Si ya está logueado, redirigir al dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('login'))

# --- Rutas de la Interfaz Web (Frontend) ---

@app.route('/')
@login_required
def dashboard():
    """Muestra el panel de control principal."""
    return render_template('dashboard.html')

@login_required
@app.route('/scanner')
def scanner_page():
    """Muestra la página del escáner de códigos de barras."""
    return render_template('scanner.html')

@login_required
@app.route('/quotations')
def quotations_page():
    """Muestra la página para crear cotizaciones."""
    return render_template('quotation.html')

@login_required
@app.route('/pos')
def pos_page():
    """Muestra la página del Punto de Venta web."""
    return render_template('pos.html')

@login_required
@app.route('/inventory')
def inventory_page():
    """Muestra la página de gestión de inventario web."""
    return render_template('inventory.html')

@login_required
@app.route('/accounts_payable')
def accounts_payable_page():
    """Muestra la página de Cuentas por Pagar."""
    return render_template('accounts_payable.html')

@login_required
@app.route('/accounts_receivable')
def accounts_receivable_page():
    """Muestra la página de Cuentas por Cobrar."""
    print(f"Acceso a Cuentas por Cobrar por usuario: {session.get('user_id')}")
    return render_template('accounts_receivable.html')

@login_required
@app.route('/sales_reports')
def sales_reports_page():
    """Muestra la página de reportes de ventas."""
    return render_template('sales_reports.html')

@login_required
@app.route('/sales')
def sales_page():
    """Muestra la página de ventas POS."""
    return render_template('sales.html')

@login_required
@app.route('/clients')
def clients_page():
    """Muestra la página de gestión de clientes."""
    return render_template('clients.html')

@app.route('/automations')
@login_required
def automations_page():
    """Muestra la página de Automatizaciones y Sugerencias."""
    return render_template('automations.html')

@app.route('/cash_closing')
@login_required
def cash_closing_page():
    """Muestra la página de Cierre de Caja."""
    return render_template('cash_closing.html')

@app.route('/sales_history')
@login_required
def sales_history_page():
    """Muestra la página del historial de ventas."""
    return render_template('sales_history.html')

# --- Rutas de la API (Backend para el Frontend) ---

@app.route('/api/products')
def get_products():
    """Devuelve la lista de todos los productos en formato JSON."""
    productos = obtener_productos() # Esta función ya devuelve una lista de diccionarios
    # Convertir ObjectId a string para el campo 'id' que usa el frontend
    for p in productos:
        if '_id' in p:
            p['id'] = str(p['_id'])
            # Opcional: eliminar _id si no se necesita en el frontend
    return jsonify(productos)

@app.route('/api/stats')
def get_stats():
    """Devuelve estadísticas clave del negocio."""
    stats = obtener_estadisticas()
    if stats:
        return jsonify({"success": True, "stats": stats})
    else:
        return jsonify({"success": False, "error": "No se pudieron obtener las estadísticas."}), 500

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

         # La función agregar_producto devuelve el ID del nuevo producto
        try:
            new_product_id = agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida)
            # Buscar el producto recién creado para devolverlo completo
            new_product = buscar_producto_por_id(new_product_id)
            if new_product:
                new_product['id'] = str(new_product['_id'])
                return jsonify({"success": True, "message": "Producto agregado correctamente.", "product": new_product})
            return jsonify({"success": True, "message": "Producto agregado, pero no se pudo recuperar."})
        except Exception as e:
            return jsonify({"success": False, "error": f"No se pudo agregar el producto. Causa probable: Código de barras duplicado. ({str(e)})"}), 500

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

@app.route('/api/products/bulk_update_department', methods=['POST'])
@login_required
def bulk_update_department():
    """Actualiza el departamento para una lista de IDs de productos."""
    data = request.get_json()
    product_ids = data.get('ids', [])
    new_department = data.get('department')

    if not product_ids or not new_department:
        return jsonify({"success": False, "error": "Se requieren IDs de producto y un departamento."}), 400

    try:
        # La función en database.py se encargará de la lógica
        updated_count = actualizar_departamento_masivo(product_ids, new_department)
        return jsonify({"success": True, "updated_count": updated_count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/inventory/clean_duplicates', methods=['POST'])
@login_required
def clean_inventory_duplicates():
    """
    Busca y elimina productos con códigos de barras duplicados, conservando uno.
    """
    if session.get('role') != 'Administrador':
        return jsonify({"success": False, "error": "No tienes permisos para realizar esta acción."}), 403

    try:
        todos_los_productos = obtener_productos()
        
        codigos_vistos = {}  # { 'codigo_barras': producto_a_conservar }
        duplicados_a_eliminar = []  # Lista de IDs a eliminar

        for producto in todos_los_productos:
            codigo = producto.get('codigo_barras')
            if not codigo or not codigo.strip():
                continue

            if codigo in codigos_vistos:
                producto_existente = codigos_vistos[codigo]
                # Criterio: Conservar el que tenga más stock. Si es igual, el más reciente (mayor ID).
                if producto.get('stock', 0) > producto_existente.get('stock', 0):
                    duplicados_a_eliminar.append(producto_existente['id'])
                    codigos_vistos[codigo] = producto
                else:
                    duplicados_a_eliminar.append(producto['id'])
            else:
                codigos_vistos[codigo] = producto

        for prod_id in duplicados_a_eliminar:
            eliminar_producto(prod_id)

        return jsonify({"success": True, "deleted_count": len(duplicados_a_eliminar)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/suppliers/add', methods=['POST'])
def add_supplier():
    """Agrega un nuevo proveedor."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No se recibieron datos"}), 400

    try:
        nombre = data.get('nombre')
        rnc = data.get('rnc')
        telefono = data.get('telefono')

        if not nombre:
            return jsonify({"success": False, "error": "El nombre del proveedor es obligatorio"}), 400

        # Para evitar duplicados, verificar si ya existe
        existing_supplier = None
        try:
            existing_supplier = obtener_proveedor_por_nombre(nombre)
        except:
            pass

        if existing_supplier:
            return jsonify({"success": False, "error": "Ya existe un proveedor con este nombre"}), 400

        # Agregar el proveedor
        agregar_proveedor(nombre, rnc, telefono)

        # Obtener el ID del proveedor recién agregado
        # Como MongoDB asigna ObjectId automáticamente, necesitamos buscarlo
        supplier = obtener_proveedor_por_nombre(nombre)
        if supplier:
            supplier_id = str(supplier['_id'])
            return jsonify({
                "success": True,
                "message": f"Proveedor '{nombre}' agregado exitosamente",
                "supplier_id": supplier_id
            })
        else:
            return jsonify({"success": False, "error": "Error al obtener el proveedor recién creado"}), 500

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
        # Normalizar monto: aceptar formatos con comas de miles como "11,500.00"
        monto_raw = data.get('monto')
        try:
            monto = float(str(monto_raw).replace(',', '').strip())
        except Exception:
            return jsonify({"success": False, "error": "Formato de monto inválido"}), 400

        notas = data.get('notas') # Obtener notas, puede ser None
        agregar_factura_compra(data['proveedor_id'], data['numero_factura'], data['fecha_emision'], data['fecha_vencimiento'], monto, data['moneda'], notas)
        return jsonify({"success": True, "message": "Factura agregada correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable')
def get_accounts_payable():
    """Devuelve la lista de cuentas por pagar pendientes."""
    try:
        cuentas = obtener_cuentas_por_pagar()
        return jsonify(cuentas)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/accounts_payable/search')
def search_accounts_payable():
    """Busca facturas por texto en proveedor o número de factura (diagnóstico)."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"success": False, "error": "Parámetro 'q' requerido"}), 400
    try:
        resultados = buscar_facturas_por_texto(q)
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable/paid')
def get_accounts_payable_paid():
    """Devuelve facturas pagadas en los últimos 90 días por defecto."""
    try:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=90)
        facturas = obtener_facturas_pagadas(inicio, hoy)
        return jsonify(facturas)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable/update/<factura_id>', methods=['POST'])
@login_required
def update_account_payable(factura_id):
    """Actualiza una cuenta por pagar existente."""
    data = request.get_json()
    try:
        # Reutilizamos la función de la base de datos para actualizar
        # Normalizar monto para aceptar formatos con comas
        monto_raw = data.get('monto')
        try:
            monto = float(str(monto_raw).replace(',', '').strip())
        except Exception:
            return jsonify({"success": False, "error": "Formato de monto inválido"}), 400

        notas = data.get('notas') # Obtener notas para la actualización
        actualizar_factura_compra(factura_id, data['proveedor_id'], data['numero_factura'], data['fecha_emision'], data['fecha_vencimiento'], monto, data['moneda'], notas)
        return jsonify({"success": True, "message": "Factura actualizada correctamente."})
    except Exception as e:
        print(f"Error actualizando factura: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable/pay/<factura_id>', methods=['POST'])
def pay_account_payable(factura_id):
    """Marca una cuenta por pagar como pagada."""
    try:
        marcar_factura_como_pagada(factura_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/accounts_payable/delete/<factura_id>', methods=['POST'])
@login_required
def delete_account_payable(factura_id):
    """Elimina una cuenta por pagar."""
    try:
        eliminar_factura_compra(factura_id)
        return jsonify({"success": True, "message": "Factura eliminada correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sales_chart_data')
def get_sales_chart_data():
    """Devuelve los datos de ventas para el gráfico del dashboard."""
    datos_brutos = obtener_datos_grafico_ventas()
    # Convertir a un formato más amigable para JavaScript
    datos_procesados = [{"dia": fila[0], "total": fila[1]} for fila in datos_brutos]
    return jsonify(datos_procesados)

@app.route('/api/sales_by_department')
@login_required
def get_sales_by_department():
    """Devuelve el total de ventas agrupado por departamento."""
    try:
        pipeline = [
            # Unir ventas_detalle con productos para obtener el departamento
            {
                "$lookup": {
                    "from": "productos",
                    "localField": "producto_id",
                    "foreignField": "_id",
                    "as": "producto_info"
                }
            },
            {"$unwind": "$producto_info"},
            # Agrupar por departamento y sumar el subtotal de cada item
            {
                "$group": {
                    "_id": "$producto_info.departamento",
                    "total_vendido": {"$sum": {"$multiply": ["$cantidad", "$precio_unitario"]}}
                }
            },
            # Proyectar para renombrar el campo _id
            {
                "$project": {
                    "_id": 0,
                    "departamento": "$_id",
                    "total": "$total_vendido"
                }
            }
        ]
        datos = list(ventas_detalle_collection.aggregate(pipeline))
        return jsonify({"success": True, "data": datos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/api/scan_image', methods=['POST'])
def api_scan_image():
    """
    Recibe una imagen, la procesa con OpenCV y Pyzbar para encontrar un código de barras,
    y devuelve la información del producto si lo encuentra.
    """
    if not OPENCV_AVAILABLE or not PYZBAR_AVAILABLE:
        return jsonify({"success": False, "error": "El servidor no tiene instaladas las librerías para procesar imágenes (OpenCV/Pyzbar)."}), 500

    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No se recibió ninguna imagen."}), 400

    file = request.files['image']
    try:
        # Leer la imagen en un formato que OpenCV pueda manejar
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        image_data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({"success": False, "error": "No se pudo decodificar la imagen."}), 400

        # Decodificar códigos de barras en la imagen
        barcodes = pyzbar_decode(image)

        if not barcodes:
            return jsonify({"success": False, "error": "No se detectaron códigos de barras."}), 404

        # Usar el primer código de barras encontrado
        barcode_data = barcodes[0].data.decode('utf-8')

        # Buscar el producto en la base de datos
        producto = buscar_producto_por_codigo(barcode_data)

        if producto:
            return jsonify({"success": True, "product": producto, "barcode": barcode_data})
        else:
            return jsonify({"success": False, "error": f"Producto no encontrado para el código '{barcode_data}'.", "barcode": barcode_data}), 404

    except Exception as e:
        print(f"Error procesando imagen en el servidor: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno del servidor al procesar la imagen: {e}"}), 500

@app.route('/api/scan_invoice_image', methods=['POST'])
@login_required
def api_scan_invoice_image():
    """
    Recibe la imagen de una factura, extrae texto con OCR mejorado y parsea productos y precios.
    Incluye preprocesamiento de imagen y mejor parsing.
    """
    if not PYTESSERACT_AVAILABLE:
        return jsonify({"success": False, "error": "El servidor no tiene Pytesseract instalado para leer facturas."}), 500

    if 'invoice_image' not in request.files:
        return jsonify({"success": False, "error": "No se recibió ninguna imagen."}), 400

    file = request.files['invoice_image']
    try:
        # Leer la imagen con PIL
        image = Image.open(file.stream)

        # --- PREPROCESAMIENTO MEJORADO DE IMAGEN ---
        # Convertir a escala de grises si no lo está
        if image.mode != 'L':
            image = image.convert('L')

        # Mejorar contraste y nitidez usando filtros
        from PIL import ImageFilter, ImageEnhance

        # Aplicar filtro de nitidez
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

        # Mejorar contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Aplicar filtro de reducción de ruido
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Binarización adaptativa para mejor OCR
        import numpy as np
        img_array = np.array(image)

        # Aplicar threshold adaptativo
        from scipy import ndimage
        img_array = ndimage.grey_erosion(img_array, size=(2,2))
        img_array = ndimage.grey_dilation(img_array, size=(2,2))

        # Convertir de vuelta a PIL Image
        image = Image.fromarray(img_array)

        # --- CONFIGURACIÓN MEJORADA DE TESSERACT ---
        # Configuración personalizada para mejor reconocimiento
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚÑáéíóúñ.,RD$()[]/- '

        # Extraer texto usando Tesseract con configuración optimizada
        text = pytesseract.image_to_string(image, lang='spa', config=custom_config)

        # Limpiar texto extraído
        text = text.strip()
        text = re.sub(r'\n\s*\n', '\n', text)  # Remover líneas vacías múltiples

        # --- PARSING MEJORADO DE FACTURAS ---
        items = []

        # Patrones más flexibles para diferentes formatos de facturas dominicanas
        # Patrón para precios: RD$ 1,500.00 o 1500.00 o 1,500.00 o 1500 o RD$1500
        price_patterns = [
            re.compile(r'RD\$\s*(\d{1,3}(?:,\d{3})*\.?\d{0,2})'),  # RD$ 1,500.00 o RD$1500
            re.compile(r'(\d{1,3}(?:,\d{3})*\.?\d{0,2})\s*RD\$'),  # 1,500.00 RD$ o 1500RD$
            re.compile(r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b'),          # Solo números con decimales obligatorios
            re.compile(r'\b(\d{1,3}(?:,\d{3})*)\b(?!\.)'),          # Números enteros sin decimales (siempre que no sigan con punto)
        ]

        # Patrón para cantidad: números al inicio de línea, más flexible
        quantity_pattern = re.compile(r'^(\d+(?:\.\d+)?)\s+')

        # Procesar línea por línea
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue

            # Buscar precios en la línea usando todos los patrones
            found_prices = []
            for pattern in price_patterns:
                matches = pattern.findall(line)
                if matches:
                    # Limpiar formato de precio
                    for match in matches:
                        price_str = match.replace(',', '').strip()
                        try:
                            price_val = float(price_str)
                            if 0.01 <= price_val <= 999999.99:  # Rango razonable para precios
                                found_prices.append(price_val)
                        except ValueError:
                            continue

            if not found_prices:
                continue

            # Tomar el último precio encontrado (generalmente el más relevante)
            price_val = found_prices[-1]

            # Buscar cantidad al inicio de la línea
            quantity = 1
            quantity_match = quantity_pattern.match(line)
            if quantity_match:
                try:
                    quantity = float(quantity_match.group(1))
                    if quantity > 1000:  # Probablemente no es cantidad
                        quantity = 1
                except ValueError:
                    quantity = 1

            # Extraer nombre del producto
            name = line

            # Remover precios encontrados
            for pattern in price_patterns:
                name = pattern.sub('', name)

            # Remover cantidad del inicio
            name = quantity_pattern.sub('', name)

            # Limpiar nombre: remover caracteres especiales, números sueltos, espacios extra
            name = re.sub(r'[^\w\sÁÉÍÓÚÑáéíóúñ-]', ' ', name)  # Solo letras, números, espacios y guiones
            name = re.sub(r'\b\d+\b', '', name)  # Remover números que son palabras completas
            name = re.sub(r'\s+', ' ', name).strip()  # Espacios múltiples a uno solo

            # Filtros adicionales para nombres válidos
            if len(name) < 2 or len(name) > 100:  # Nombre demasiado corto o largo
                continue

            # Evitar nombres que son solo números o símbolos
            if re.match(r'^[^a-zA-ZÁÉÍÓÚÑáéíóúñ]*$', name):
                continue

            # Verificar que no sea un duplicado cercano (por nombre y precio)
            is_duplicate = False
            for existing_item in items:
                if (existing_item['nombre'].lower().strip() == name.lower().strip() and
                    abs(existing_item['costo'] - price_val) < 0.01):
                    is_duplicate = True
                    break

            if not is_duplicate:
                items.append({
                    "nombre": name,
                    "costo": price_val,
                    "cantidad": quantity
                })

        # --- VALIDACIÓN Y CORRECCIÓN FINAL ---
        # Remover items con nombres muy similares pero precios muy diferentes
        if len(items) > 1:
            items_to_remove = []
            for i, item1 in enumerate(items):
                for j, item2 in enumerate(items[i+1:], i+1):
                    # Si nombres son similares (>80% similitud) pero precios muy diferentes (>50%)
                    name1 = item1['nombre'].lower()
                    name2 = item2['nombre'].lower()
                    similarity = len(set(name1.split()) & set(name2.split())) / max(len(set(name1.split())), len(set(name2.split())))
                    price_diff = abs(item1['costo'] - item2['costo']) / max(item1['costo'], item2['costo'])

                    if similarity > 0.8 and price_diff > 0.5:
                        # Mantener el que tenga nombre más largo (más descriptivo)
                        if len(item1['nombre']) < len(item2['nombre']):
                            items_to_remove.append(i)
                        else:
                            items_to_remove.append(j)

            # Remover duplicados marcados
            for index in sorted(set(items_to_remove), reverse=True):
                if index < len(items):
                    items.pop(index)

        # Limitar a máximo 50 items para evitar sobrecarga
        items = items[:50]

        # Información de depuración
        debug_info = {
            "total_lines": len(lines),
            "extracted_text_length": len(text),
            "found_items": len(items)
        }

        return jsonify({
            "success": True,
            "items": items,
            "debug_info": debug_info,
            "raw_text_preview": text[:500] + "..." if len(text) > 500 else text
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error procesando imagen de factura: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({
            "success": False,
            "error": f"Error interno del servidor: {str(e)}",
            "details": "Verifica que la imagen sea legible y no esté borrosa"
        }), 500

@app.route('/api/products/bulk_add', methods=['POST'])
@login_required
def api_bulk_add_products():
    """Agrega múltiples productos nuevos a la base de datos."""
    data = request.get_json()
    products = data.get('products', [])
    if not products:
        return jsonify({"success": False, "error": "No se recibieron productos."}), 400
    
    try:
        count = agregar_productos_en_masa(products)
        return jsonify({"success": True, "message": f"Se agregaron {count} productos nuevos al inventario."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
            io.BytesIO(output.getvalue().encode('utf-8-sig')), # Usar utf-8-sig para compatibilidad con Excel
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
                # Asumir orden: codigo, nombre, costo, precio, stock, stock_minimo, departamento
                if len(row) < 7:
                    fallidos += 1
                    continue

                codigo = row[0]
                nombre = row[1]
                costo = float(row[2]) if row[2] else 0.0
                precio = float(row[3]) if row[3] else 0.0
                stock = int(float(row[4])) if row[4] else 0
                stock_minimo = int(float(row[5])) if row[5] else 0
                departamento = row[6] if row[6] else 'Ferretería'

                # Agregar producto completo
                agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento)
                exitosos += 1

            except Exception as e:
                print(f"Error procesando fila: {row[:7]}, Error: {e}")
                fallidos += 1

        return jsonify({"success": True, "message": f"Importados: {exitosos}, Fallidos: {fallidos}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/export/pdf')
def export_products_pdf():
    """Exporta el reporte de inventario a PDF."""
    try:
        productos = obtener_productos()
        
        class PDF(FPDF):
            def header(self):
                logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
                if logo_path.exists():
                    self.image(str(logo_path), 10, 8, 33)
                self.set_font('Arial', 'B', 15)
                self.cell(80)
                self.cell(30, 10, 'Reporte de Inventario', 0, 0, 'C')
                self.ln(5)
                self.set_font('Arial', '', 10)
                self.cell(80)
                self.cell(30, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 0, 'C')
                self.ln(20)

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.cell(0, 10, 'Pagina ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("Arial", "B", 9)

        # Cabeceras de la tabla
        headers = ["Codigo", "Nombre", "Costo", "Precio", "Stock", "Departamento"]
        col_widths = [30, 75, 20, 20, 15, 30]
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, "C")
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for prod in productos:
            if pdf.get_y() > 270:
                pdf.add_page()
                pdf.set_font("Arial", "B", 9)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 10, header, 1, 0, "C")
                pdf.ln()
                pdf.set_font("Arial", "", 9)

            pdf.cell(col_widths[0], 8, str(prod.get('codigo_barras', '')).encode('latin-1', 'replace').decode('latin-1'), 1)
            pdf.cell(col_widths[1], 8, str(prod.get('nombre', '')).encode('latin-1', 'replace').decode('latin-1')[:45], 1)
            pdf.cell(col_widths[2], 8, f"{prod.get('costo', 0):.2f}", 1, 0, 'R')
            pdf.cell(col_widths[3], 8, f"{prod.get('precio', 0):.2f}", 1, 0, 'R')
            pdf.cell(col_widths[4], 8, str(prod.get('stock', 0)), 1, 0, 'C')
            pdf.cell(col_widths[5], 8, str(prod.get('departamento', '')).encode('latin-1', 'replace').decode('latin-1')[:18], 1)
            pdf.ln()

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

@app.route('/api/clients')
@login_required
def get_clients():
    """Obtiene todos los clientes."""
    try:
        clientes = obtener_todos_los_clientes()
        return jsonify({"success": True, "clients": clientes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/client/add', methods=['POST'])
@login_required
def add_client():
    """Agrega un nuevo cliente."""
    data = request.get_json()
    try:
        agregar_cliente(data['nombre'], data.get('rnc_cedula'), data.get('telefono'), data.get('email'), data.get('direccion'))
        return jsonify({"success": True, "message": "Cliente agregado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/client/update/<client_id>', methods=['POST'])
@login_required
def update_client(client_id):
    """Actualiza un cliente existente."""
    data = request.get_json()
    try:
        actualizar_cliente(client_id, data['nombre'], data.get('rnc_cedula'), data.get('telefono'), data.get('email'), data.get('direccion'))
        return jsonify({"success": True, "message": "Cliente actualizado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quotation/save', methods=['POST'])
def save_quotation():
    """Guarda una cotización en la base de datos."""
    data = request.get_json()
    items = data.get('items', [])
    client_id = data.get('client_id')
    validez_dias = data.get('validez_dias', 15) # Default a 15 días si no se especifica

    if not items:
        return jsonify({"success": False, "error": "No hay productos en la cotización."}), 400

    try:
        # Pasamos los días de validez a la función que guarda en la BD
        cotizacion_id = guardar_cotizacion(items, client_id, validez_dias)
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
        # Asegurar que no haya ObjectId en la estructura antes de serializar
        def _make_serializable(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            if isinstance(obj, dict):
                return {k: _make_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_make_serializable(v) for v in obj]
            return obj

        serializable = _make_serializable(cuentas)
        return jsonify(serializable)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/accounts_receivable/paid')
@login_required
def get_paid_accounts_receivable():
    """Devuelve la lista de cuentas por cobrar que ya han sido pagadas."""
    try:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=90) # Historial de los últimos 90 días
        cuentas = obtener_cuentas_cobradas(inicio, hoy)
        return jsonify(cuentas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/diagnose_sales', methods=['GET'])
def diagnose_sales():
    """Endpoint de diagnóstico: muestra todas las ventas sin filtros para investigación."""
    try:
        from database.database import ventas_collection
        if ventas_collection is None:
            return jsonify({"error": "Colección de ventas no inicializada"}), 500
        
        # Obtener todas las ventas sin filtros
        todas_ventas = list(ventas_collection.find({}).sort("fecha", -1).limit(20))
        
        # Convertir ObjectIds a strings para serialización JSON
        for v in todas_ventas:
            v['_id'] = str(v['_id'])
            if 'usuario_id' in v and v['usuario_id']:
                v['usuario_id'] = str(v['usuario_id'])
            if 'cliente_id' in v and v['cliente_id']:
                v['cliente_id'] = str(v['cliente_id'])
            if 'fecha' in v and isinstance(v['fecha'], datetime):
                v['fecha'] = v['fecha'].isoformat()
        
        print(f"DEBUG diagnose_sales -> Total de ventas en BD (últimas 20): {len(todas_ventas)}")
        
        # Agrupar por estado
        por_estado = {}
        for v in todas_ventas:
            estado = v.get('estado', 'SIN_ESTADO')
            if estado not in por_estado:
                por_estado[estado] = []
            por_estado[estado].append(v)
            print(f"  Venta: id={v['_id']}, estado={v.get('estado')}, tipo_pago={v.get('tipo_pago')}, saldo={v.get('saldo_pendiente')}, cliente_temp={v.get('temp_cliente_nombre')}")
        
        return jsonify({
            "total_sales_shown": len(todas_ventas),
            "sales_by_status": {k: len(v) for k, v in por_estado.items()},
            "sales": todas_ventas
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

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
@login_required
def api_register_sale():
    """Registra una venta realizada desde la interfaz web."""
    data = request.get_json()
    items = data.get('items', [])
    client_id = data.get('client_id') # Puede ser null
    payments = data.get('payments', [])
    discount = float(data.get('discount', 0.0))
    # Nuevo campo para el nombre temporal del cliente
    temp_client_name = data.get('temp_client_name')

    # Usar el usuario actualmente logueado
    user_id = session.get('user_id')

    if not items:
        return jsonify({"success": False, "error": "No hay productos en la venta."}), 400

    # Recalcular totales en el servidor para garantizar la integridad de los datos
    ITBIS_RATE = 0.18
    subtotal_bruto = sum(item['cantidad'] * item['precio'] for item in items)
    subtotal_descontado = subtotal_bruto - discount
    total = subtotal_descontado
    itbis_incluido = subtotal_descontado - (subtotal_descontado / (1 + ITBIS_RATE))

    # Determinar el tipo de pago principal (el primero en la lista de pagos)
    tipo_pago = payments[0]['method'] if payments and len(payments) > 0 else 'Efectivo'
    # Normalizar (sin acentos, minúsculas) para uso interno si es necesario
    def _normalize(s):
        if not s:
            return ''
        return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).lower()
    tipo_pago_norm = _normalize(tipo_pago)

    try:
        # Log de debug
        print(f"DEBUG - Items recibidos: {items}")
        print(f"DEBUG - Client ID: {client_id}")
        print(f"DEBUG - Tipo Pago: {tipo_pago} (norm: {tipo_pago_norm})")
        print(f"DEBUG - Temp Client Name: {temp_client_name}")
        # Si no hay conexión con la DB, guardar la venta localmente para sincronizar luego
        if not is_db_connected():
            sale_data = {
                'items': items,
                'total': total,
                'itbis': itbis_incluido,
                'descuento': discount,
                'usuario_id': user_id,
                'tipo_pago': tipo_pago,
                'cliente_id': client_id,
                'temp_client_name': temp_client_name,
                'created_at': datetime.now().isoformat()
            }
            local_id = guardar_venta_local(sale_data)
            return jsonify({
                "success": True,
                "message": "Venta guardada localmente (sincronizar cuando haya conexión).",
                "sale_id": f"local-{local_id}",
                "local_id": local_id
            })

        venta_id = registrar_venta(items, total, itbis_incluido, discount, user_id, tipo_pago, client_id, temp_client_name)

        # Emitir notificación en tiempo real
        notify_sale_registered(venta_id, total)

        return jsonify({
            "success": True,
            "message": f"Venta #{venta_id} registrada correctamente.",
            "sale_id": venta_id
        })
    except Exception as e:
        # Log del error en el servidor para depuración
        import traceback
        trace = traceback.format_exc()
        print(f"Error al registrar venta desde la web: {e}")
        print(f"Traceback: {trace}")
        # Devolver traceback en la respuesta para depuración en entorno controlado
        return jsonify({"success": False, "error": f"No se pudo registrar la venta: {str(e)}", "traceback": trace}), 500

@app.route('/api/sales_history')
@login_required
def api_get_sales_history():
    """Obtiene el historial de las últimas ventas."""
    try:
        sales = obtener_historial_ventas(limit=100) # Obtener las últimas 100 ventas
        return jsonify({"success": True, "sales": sales})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pos/update_sale_client', methods=['POST'])
@login_required
def api_update_sale_client():
    """
    Actualiza el cliente de una venta a crédito que fue registrada sin cliente.
    Permite asociar un cliente después de que la venta ya fue completada.
    """
    data = request.get_json()
    sale_id = data.get('sale_id')
    client_id = data.get('client_id')

    if not sale_id or not client_id:
        return jsonify({"success": False, "error": "Sale ID y Client ID son requeridos"}), 400

    try:
        from bson.objectid import ObjectId
        # Actualizar la venta con el nuevo cliente
        result = ventas_collection.update_one(
            {"_id": ObjectId(sale_id)},
            {
                "$set": {
                    "cliente_id": ObjectId(client_id),
                    "temp_cliente_nombre": None  # Limpiar el nombre temporal
                }
            }
        )

        if result.matched_count == 0:
            return jsonify({"success": False, "error": "Venta no encontrada"}), 404

        return jsonify({
            "success": True,
            "message": "Cliente asociado exitosamente a la venta"
        })
    except Exception as e:
        print(f"Error al actualizar cliente de venta: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pos/print_ticket/<sale_id>')
def print_ticket_web(sale_id):
    """
    Genera una página HTML optimizada para impresión de ticket desde la web.
    """
    try:
        # Recuperar la venta y sus detalles para mostrar todos los artículos
        venta, detalles = buscar_venta_por_id(sale_id)

        if not venta:
            return f"<h1>Venta {sale_id} no encontrada</h1>", 404

        # Obtener nombre del cliente (si existe) o usar nombre temporal
        cliente_nombre = venta.get('temp_cliente_nombre')
        if venta.get('cliente_id'):
            cliente_doc = clientes_collection.find_one({"_id": venta.get('cliente_id')})
            if cliente_doc:
                cliente_nombre = cliente_doc.get('nombre', cliente_nombre)

        # Construir filas de items
        items_html = ""
        total_calc = 0
        for d in detalles:
            # producto_id puede ser ObjectId
            prod = None
            try:
                prod = productos_collection.find_one({"_id": d.get('producto_id')})
            except Exception:
                prod = None

            nombre = prod.get('nombre') if prod else d.get('producto_id')
            cantidad = d.get('cantidad', 0)
            precio = d.get('precio_unitario', 0)
            subtotal = cantidad * precio
            total_calc += subtotal
            items_html += f"<tr><td>{nombre}</td><td style='text-align:center;'>{cantidad}</td><td style='text-align:right;'>{precio:.2f}</td><td style='text-align:right;'>{subtotal:.2f}</td></tr>"

        fecha_str = venta.get('fecha').strftime('%d/%m/%Y %H:%M:%S') if venta.get('fecha') else datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Ticket Venta #{sale_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 10px; }}
                .ticket {{ max-width: 480px; margin: 0 auto; border: 1px solid #000; padding: 10px; }}
                h2 {{ text-align: center; margin: 0 0 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border-bottom: 1px dashed #666; padding: 6px 4px; font-size: 14px; }}
                th {{ text-align: left; }}
                .right {{ text-align: right; }}
                .totals {{ font-weight: bold; font-size: 16px; }}
                .actions {{ text-align: center; margin-top: 10px; }}
                button {{ padding: 8px 14px; margin: 4px; font-size: 14px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="ticket">
                <h2>Ticket de Venta</h2>
                <div><strong>ID:</strong> {sale_id}</div>
                <div><strong>Fecha:</strong> {fecha_str}</div>
                <div><strong>Cliente:</strong> {cliente_nombre or 'Cliente no asignado'}</div>

                <table>
                    <thead>
                        <tr><th>Artículo</th><th style='text-align:center;'>Cant</th><th style='text-align:right;'>P.Unit</th><th style='text-align:right;'>Subtotal</th></tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <div style="margin-top:8px; text-align:right;" class="totals">Total: {venta.get('total', 0):.2f}</div>
                <div style="margin-top:4px; text-align:right;">Saldo pendiente: {venta.get('saldo_pendiente', 0):.2f}</div>

                <div class="actions">
                    <button onclick="window.print()">🖨️ Imprimir</button>
                    <button onclick="window.close()">Cerrar</button>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        print(f"Error generando ticket: {e}")
        return f"<h1>Error: {e}</h1>", 500


@app.route('/api/pos/print_ticket_pdf/<sale_id>')
def print_ticket_pdf(sale_id):
    """Genera un PDF del ticket de venta, lo guarda en `static/tickets/` y lo devuelve para descarga."""
    try:
        # Recuperar la venta y sus detalles
        venta, detalles = buscar_venta_por_id(sale_id)
        if not venta:
            return jsonify({"success": False, "error": "Venta no encontrada"}), 404

        # Preparar directorio de salida
        tickets_dir = Path(__file__).parent / 'static' / 'tickets'
        tickets_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = tickets_dir / f'ticket_{sale_id}.pdf'

        # Crear PDF
        pdf = FPDF('P', 'mm', (80, 200))
        pdf.set_auto_page_break(auto=True, margin=5)
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 6, 'Ticket de Venta', 0, 1, 'C')
        pdf.ln(2)
        pdf.set_font('Arial', '', 9)
        fecha_str = venta.get('fecha').strftime('%d/%m/%Y %H:%M:%S') if venta.get('fecha') else datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        cliente_nombre = venta.get('temp_cliente_nombre') or 'Cliente no asignado'
        if venta.get('cliente_id'):
            cliente_doc = clientes_collection.find_one({"_id": venta.get('cliente_id')})
            if cliente_doc:
                cliente_nombre = cliente_doc.get('nombre', cliente_nombre)

        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, f'ID: {sale_id}', 0, 1)
        pdf.cell(0, 5, f'Fecha: {fecha_str}', 0, 1)
        pdf.cell(0, 5, f'Cliente: {cliente_nombre}', 0, 1)
        pdf.ln(2)

        # Encabezados de tabla
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(40, 5, 'Articulo', 0, 0)
        pdf.cell(10, 5, 'Cant', 0, 0, 'C')
        pdf.cell(20, 5, 'P.Unit', 0, 0, 'R')
        pdf.cell(20, 5, 'Sub', 0, 1, 'R')
        pdf.set_font('Arial', '', 9)

        total_calc = 0
        for d in detalles:
            prod = None
            try:
                prod = productos_collection.find_one({"_id": d.get('producto_id')})
            except Exception:
                prod = None
            nombre = (prod.get('nombre')[:28] if prod else str(d.get('producto_id')))
            cantidad = d.get('cantidad', 0)
            precio = d.get('precio_unitario', 0)
            subtotal = cantidad * precio
            total_calc += subtotal

            pdf.cell(40, 5, nombre, 0, 0)
            pdf.cell(10, 5, str(cantidad), 0, 0, 'C')
            pdf.cell(20, 5, f'{precio:.2f}', 0, 0, 'R')
            pdf.cell(20, 5, f'{subtotal:.2f}', 0, 1, 'R')

        pdf.ln(2)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(70, 6, 'Total:', 0, 0, 'R')
        pdf.cell(0, 6, f'{venta.get("total", 0):.2f}', 0, 1, 'R')
        pdf.cell(70, 6, 'Saldo Pendiente:', 0, 0, 'R')
        pdf.cell(0, 6, f'{venta.get("saldo_pendiente", 0):.2f}', 0, 1, 'R')

        # Guardar PDF en disco
        pdf.output(str(pdf_path))

        # Devolver como descarga
        return send_file(
            str(pdf_path),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'ticket_{sale_id}.pdf'
        )
    except Exception as e:
        import traceback
        print(f"Error generando PDF del ticket: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pos/process_return', methods=['POST'])
@login_required
def api_process_return():
    """Procesa una devolución de productos."""
    data = request.get_json()
    items = data.get('items', [])
    reason = data.get('reason', 'Sin especificar')
    original_sale_id = data.get('original_sale_id') # Opcional
    user_id = session.get('user_id')

    if not items:
        return jsonify({"success": False, "error": "No hay productos para devolver."}), 400

    try:
        # La función en database.py se encarga de la lógica de stock
        devolucion_id = registrar_devolucion(items, user_id, reason, original_sale_id)
        return jsonify({
            "success": True,
            "message": f"Devolución #{devolucion_id} procesada correctamente. El stock ha sido actualizado.",
            "return_id": devolucion_id
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/print_test')
def print_test():
    """Página de prueba para impresión de tickets."""
    return render_template('print_ticket.html')

# --- Rutas adicionales para nueva funcionalidad ---
@app.route('/api/reports/sales/<report_type>', methods=['GET'])
def get_sales_report(report_type):
    """Genera reportes de ventas por tipo (daily, weekly, monthly)."""
    try:
        date_param = request.args.get('date')

        if report_type == 'daily':
            if not date_param:
                date_param = datetime.now().date().isoformat()
            ventas = obtener_ventas_del_dia(date_param)
            chart_data = obtener_grafico_ventas('daily', date_param)

        elif report_type == 'weekly':
            # Para semanal, se usa la fecha como el último día de la semana
            if not date_param:
                date_param = datetime.now().date().isoformat()
            fecha = datetime.fromisoformat(date_param).date()
            inicio_semana = fecha - timedelta(days=fecha.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            ventas = obtener_ventas_por_periodo(
                datetime.combine(inicio_semana, datetime.min.time()),
                datetime.combine(fin_semana, datetime.max.time())
            )
            chart_data = obtener_grafico_ventas('weekly', date_param)

        elif report_type == 'monthly':
            if not date_param:
                ahora = datetime.now()
                date_param = f"{ahora.year}-{ahora.month:02d}"
            fecha_mes = datetime.fromisoformat(date_param + "-01")
            inicio_mes = fecha_mes.replace(day=1)
            fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            ventas = obtener_ventas_por_periodo(inicio_mes, fin_mes)
            chart_data = obtener_grafico_ventas('monthly', date_param)

        else:
            return jsonify({"success": False, "error": "Tipo de reporte inválido"}), 400

        if not ventas:
            return jsonify({"success": True, "data": None})

        # Calcular estadísticas
        summary = calcular_estadisticas_ventas(ventas)
        breakdown = obtener_estadisticas_pago_ventas(ventas)

        # Obtener top productos (sólo si hay ventas)
        top_products_data = []
        if ventas:
            first_sale = min(ventas, key=lambda x: x.get('fecha', datetime.max))
            last_sale = max(ventas, key=lambda x: x.get('fecha', datetime.min))
            inicio_periodo = first_sale.get('fecha').date() if first_sale.get('fecha') else datetime.now().date()
            fin_periodo = last_sale.get('fecha').date() if last_sale.get('fecha') else datetime.now().date()

            top_products_raw = obtener_productos_mas_vendidos(
                inicio_periodo.isoformat(),
                fin_periodo.isoformat()
            )

            for codigo, nombre, cantidad in top_products_raw[:10]:
                top_products_data.append({
                    "codigo_barras": codigo,
                    "nombre": nombre,
                    "total_vendido": cantidad
                })

        # Formatear ventas para respuesta
        formatted_ventas = []
        for venta in ventas:
            formatted_ventas.append({
                "id": str(venta.get("id", "")),
                "fecha": venta.get("fecha"),
                "total": venta.get("total", 0),
                "itbis": venta.get("itbis", 0),
                "descuento": venta.get("descuento", 0),
                "tipo_pago": venta.get("tipo_pago", "Sin especificar")
            })

        # Formatear breakdown para respuesta
        formatted_breakdown = {}
        for method_data in breakdown:
            method_name = method_data["method"].lower()
            formatted_breakdown[f"{method_name}_sales"] = method_data["amount"]
            formatted_breakdown[f"{method_name}_percentage"] = round(method_data["percentage"], 2)

        response_data = {
            "summary": {
                "total_sales": summary["total_sales"],
                "total_transactions": summary["total_transactions"],
                "avg_sale": summary["avg_sale"],
                "total_profit": summary["total_profit"]  # Estimación simplificada
            },
            "breakdown": formatted_breakdown,
            "chart_labels": chart_data["labels"],
            "chart_data": chart_data["data"],
            "details": formatted_ventas,
            "top_products": top_products_data
        }

        return jsonify({"success": True, "data": response_data})

    except Exception as e:
        print(f"Error generando reporte de ventas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# --- RUTAS DE NOTIFICACIONES EN TIEMPO REAL ---
@app.route('/api/notifications')
def get_notifications():
    """Obtiene todas las notificaciones activas del sistema."""
    try:
        # Obtener diferentes tipos de notificaciones
        low_stock = obtener_notificaciones_stock_bajo()
        overdue_payments = obtener_notificaciones_pagos_vencidos()
        expiring_products = obtener_notificaciones_productos_por_vencer()
        due_soon_invoices = obtener_notificaciones_facturas_por_vencer()
        overdue_receivables = obtener_notificaciones_cuentas_por_cobrar_vencidas()

        all_notifications = []
        all_notifications.extend(low_stock)
        all_notifications.extend(due_soon_invoices)
        all_notifications.extend(overdue_payments)
        all_notifications.extend(expiring_products)
        all_notifications.extend(overdue_receivables)

        # Ordenar por prioridad y fecha
        notification_priority = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        all_notifications.sort(key=lambda x: (
            notification_priority.get(x.get('priority', 'low'), 1),
            x.get('created_at', datetime.min)
        ), reverse=True)

        return jsonify({"success": True, "notifications": all_notifications})

    except Exception as e:
        print(f"Error obteniendo notificaciones: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/notifications/dismiss/<notification_id>', methods=['POST'])
def dismiss_notification(notification_id):
    """Marca una notificación como leída/descartada."""
    try:
        # En este caso, como no tenemos tabla de notificaciones,
        # simplemente devolvemos éxito (simulado)
        return jsonify({"success": True, "message": "Notificación descartada"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- RUTAS DE AUTOMATIZACIONES ---
@app.route('/api/automations/reorder_suggestions')
def get_reorder_suggestions():
    """Obtiene sugerencias inteligentes de reordenamiento."""
    try:
        suggestions = obtener_sugerencias_reordenamiento()
        return jsonify({"success": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/automations/apply_reorder/<product_id>', methods=['POST'])
def apply_reorder_suggestion(product_id):
    """Aplica una sugerencia de reordenamiento automáticamente."""
    try:
        data = request.get_json()
        cantidad = data.get('cantidad', 0)

        if cantidad <= 0:
            return jsonify({"success": False, "error": "Cantidad inválida"}), 400

        # Aumentar stock del producto
        sumar_stock_producto(product_id, cantidad)

        # Registrar la acción en logs (simulado)
        return jsonify({"success": True, "message": f"Reorden aplicado: +{cantidad} unidades"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/automations/generate_po_pdf', methods=['POST'])
@login_required
def generate_purchase_order_pdf():
    """Genera un PDF de Orden de Compra para un proveedor y productos específicos."""
    data = request.get_json()
    products = data.get('products', [])
    supplier_name = data.get('supplier_name', 'Proveedor no especificado')

    if not products:
        return jsonify({"success": False, "error": "No hay productos para generar la orden."}), 400

    try:
        pdf = FPDF()
        pdf.add_page()

        # Encabezado
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ORDEN DE COMPRA", 0, 1, "C")
        pdf.ln(10)

        # Información del Pedido
        pdf.set_font("Arial", "B", 11)
        pdf.cell(40, 8, "Proveedor:")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, supplier_name, 0, 1)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(40, 8, "Fecha:")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, datetime.now().strftime('%d/%m/%Y'), 0, 1)
        pdf.ln(10)

        # Tabla de Productos
        pdf.set_font("Arial", "B", 10)
        pdf.cell(100, 8, "Producto", 1, 0, "C")
        pdf.cell(30, 8, "Cantidad Sug.", 1, 0, "C")
        pdf.cell(30, 8, "Costo Unit.", 1, 0, "C")
        pdf.cell(30, 8, "Subtotal", 1, 1, "C")

        pdf.set_font("Arial", "", 9)
        total_pedido = 0
        for prod in products:
            subtotal = prod.get('suggested_quantity', 0) * prod.get('costo', 0)
            total_pedido += subtotal
            pdf.cell(100, 8, str(prod.get('product_name', 'N/A'))[:50], 1)
            pdf.cell(30, 8, str(prod.get('suggested_quantity', 0)), 1, 0, "C")
            pdf.cell(30, 8, f"RD$ {prod.get('costo', 0):.2f}", 1, 0, "R")
            pdf.cell(30, 8, f"RD$ {subtotal:.2f}", 1, 1, "R")

        # Total
        pdf.set_font("Arial", "B", 12)
        pdf.cell(160, 10, "TOTAL ESTIMADO:", 0, 0, "R")
        pdf.cell(30, 10, f"RD$ {total_pedido:.2f}", 1, 1, "R")

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return send_file(io.BytesIO(pdf_output), mimetype='application/pdf', as_attachment=True, download_name=f'Orden_Compra_{supplier_name.replace(" ", "_")}.pdf')
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- RUTAS PARA CIERRE DE CAJA WEB ---
@app.route('/api/cash_closing/summary', methods=['POST'])
@login_required
def get_cash_closing_summary():
    """Obtiene el resumen de ventas por método de pago para un rango de fechas."""
    data = request.get_json()
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        
        summary = obtener_resumen_ventas_por_metodo(start_date, end_date)
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cash_closing/finalize', methods=['POST'])
@login_required
def finalize_cash_closing():
    """Guarda un registro de cierre de caja."""
    data = request.get_json()
    
    # Añadir información del usuario que realiza el cierre
    data['usuario_id'] = session.get('user_id')
    data['usuario_nombre'] = session.get('username')
    data['fecha_cierre'] = datetime.now()

    try:
        registrar_cierre_caja(data)
        return jsonify({"success": True, "message": "Cierre de caja guardado exitosamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/automations/bulk_price_update', methods=['POST'])
def bulk_price_update():
    """Actualización masiva de precios basada en reglas."""
    try:
        data = request.get_json()
        rule_type = data.get('rule_type')
        percentage = data.get('percentage', 0)
        department = data.get('department')

        if rule_type == 'percentage':
            productos_afectados = actualizar_precios_por_porcentaje(percentage, department)
        elif rule_type == 'inflation':
            # Ajuste por inflación (ejemplo)
            productos_afectados = actualizar_precios_por_porcentaje(5.0, department)
        else:
            return jsonify({"success": False, "error": "Tipo de regla inválida"}), 400

        return jsonify({
            "success": True,
            "message": f"Precios actualizados: {productos_afectados} productos afectados",
            "affected_products": productos_afectados
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/automations/create_backup', methods=['POST'])
def create_backup():
    """Crea un backup automático de la base de datos (simulado)."""
    try:
        # Aquí iría la lógica real de backup
        # Por ahora solo simulamos
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Simular tiempo de procesamiento
        import time
        time.sleep(1)

        return jsonify({
            "success": True,
            "message": "Backup creado exitosamente",
            "backup_id": backup_id,
            "backup_date": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/automations/sales_prediction/<days>')
def get_sales_prediction(days):
    """Predice ventas futuras basado en datos históricos."""
    try:
        days = int(days)
        if days not in [7, 30, 90]:
            return jsonify({"success": False, "error": "Días inválidos. Use 7, 30 o 90"}), 400

        prediction = obtener_prediccion_ventas(days)

        return jsonify({
            "success": True,
            "prediction": prediction,
            "period_days": days
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- GESTIÓN DE USUARIOS WEB ---

@app.route('/users')
@login_required
def users_page():
    """Muestra la página de gestión de usuarios."""
    # Solo administradores pueden acceder
    if session.get('role') != 'Administrador':
        flash('No tienes permisos para acceder a esta sección.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('users.html')

@app.route('/api/users')
@login_required
def get_users():
    """Obtiene la lista de usuarios (solo para administradores)."""
    if session.get('role') != 'Administrador':
        return jsonify({"success": False, "error": "No tienes permisos"}), 403

    try:
        usuarios = obtener_todos_los_usuarios()
        # Agregar ID como string para JSON
        for usuario in usuarios:
            usuario["_id"] = str(usuario["_id"])
        return jsonify({"success": True, "users": usuarios})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/users/create', methods=['POST'])
@login_required
def create_user():
    """Crea un nuevo usuario (solo administradores)."""
    if session.get('role') != 'Administrador':
        return jsonify({"success": False, "error": "No tienes permisos"}), 403

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not username or not password or not role:
        return jsonify({"success": False, "error": "Todos los campos son requeridos"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "La contraseña debe tener al menos 6 caracteres"}), 400

    if role not in ['Administrador', 'Vendedor', 'Almacenista']:
        return jsonify({"success": False, "error": "Rol inválido"}), 400

    try:
        crear_usuario(username, password, role)
        return jsonify({"success": True, "message": f"Usuario '{username}' creado exitosamente"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error al crear usuario: {str(e)}"}), 500

@app.route('/api/users/delete/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Elimina un usuario (solo administradores)."""
    if session.get('role') != 'Administrador':
        return jsonify({"success": False, "error": "No tienes permisos"}), 403

    # Evitar que un admin se borre a si mismo
    if user_id == session.get('user_id'):
        return jsonify({"success": False, "error": "No puedes eliminarte a ti mismo"}), 400

    try:
        # Verificar que existe al menos otro administrador
        usuarios = obtener_todos_los_usuarios()
        admin_count = sum(1 for u in usuarios if u.get('rol') == 'Administrador')

        if admin_count <= 1:
            return jsonify({"success": False, "error": "Debe existir al menos un administrador"}), 400

        eliminar_usuario(user_id)
        return jsonify({"success": True, "message": "Usuario eliminado exitosamente"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error al eliminar usuario: {str(e)}"}), 500

@app.route('/api/users/password/change', methods=['POST'])
@login_required
def change_password():
    """Cambia la contraseña del usuario actual."""
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"success": False, "error": "Todos los campos son requeridos"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "error": "La contraseña debe tener al menos 6 caracteres"}), 400

    # Verificar contraseña actual
    user = obtener_usuario_por_nombre(session.get('username'))
    if not user or not check_password(current_password, user['hash_contrasena']):
        return jsonify({"success": False, "error": "Contraseña actual incorrecta"}), 400

    try:
        actualizar_contrasena(user['_id'], new_password)
        return jsonify({"success": True, "message": "Contraseña cambiada exitosamente"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error al cambiar contraseña: {str(e)}"}), 500

# --- AUTORIZACIÓN PARA PROVEEDORES ---
@app.route('/api/supplier/orders/send', methods=['POST'])
@login_required
def send_supplier_order():
    """Envía un pedido automático a un proveedor."""
    data = request.get_json()
    proveedor_id = data.get('proveedor_id')
    productos = data.get('productos', [])  # [{"producto_id": "id", "cantidad": 10, "precio_unitario": 100}]

    if not proveedor_id or not productos:
        return jsonify({"success": False, "error": "Proveedor y productos son requeridos"}), 400

    try:
        # Obtener información del proveedor
        proveedor = proveedores_collection.find_one({"_id": ObjectId(proveedor_id)})
        if not proveedor:
            return jsonify({"success": False, "error": "Proveedor no encontrado"}), 404

        # Crear pedido
        pedido = {
            "proveedor_id": ObjectId(proveedor_id),
            "productos": productos,
            "fecha_pedido": datetime.now(),
            "estado": "Enviado",
            "total": sum(p['cantidad'] * p['precio_unitario'] for p in productos),
            "usuario_id": ObjectId(session['user_id']),
            "referencia_pedido": f"PED-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }

        # Guardar en colección de pedidos a proveedores
        pedidos_proveedores_collection = db["pedidos_proveedores"]
        result = pedidos_proveedores_collection.insert_one(pedido)
        pedido_id = str(result.inserted_id)

        # Aquí se podría integrar con API del proveedor si tiene una
        # Por ejemplo, enviar email al proveedor con el pedido

        return jsonify({
            "success": True,
            "message": f"Pedido enviado a {proveedor['nombre']}",
            "pedido_id": pedido_id,
            "referencia": pedido['referencia_pedido']
        })

    except Exception as e:
        print(f"Error enviando pedido a proveedor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/supplier/orders')
@login_required
def get_supplier_orders():
    """Obtiene histórico de pedidos a proveedores."""
    try:
        pedidos = list(db["pedidos_proveedores"].aggregate([
            {"$lookup": {
                "from": "proveedores",
                "localField": "proveedor_id",
                "foreignField": "_id",
                "as": "proveedor"
            }},
            {"$unwind": "$proveedor"},
            {"$lookup": {
                "from": "usuarios",
                "localField": "usuario_id",
                "foreignField": "_id",
                "as": "usuario"
            }},
            {"$unwind": {"path": "$usuario", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "_id": 1,
                "proveedor_nombre": "$proveedor.nombre",
                "estado": 1,
                "total": 1,
                "fecha_pedido": 1,
                "referencia_pedido": 1,
                "usuario": {"$ifNull": ["$usuario.nombre_usuario", "Sistema"]}
            }},
            {"$sort": {"fecha_pedido": -1}}
        ]))

        for pedido in pedidos:
            pedido["_id"] = str(pedido["_id"])

        return jsonify(pedidos)

    except Exception as e:
        print(f"Error obteniendo pedidos a proveedores: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# --- SISTEMA DE BACKUPS AUTOMÁTICOS ---
import schedule
import time
import threading
import subprocess
import os

backup_jobs = {}
backup_request_queue = []

@app.route('/api/backup/create', methods=['POST'])
@login_required
def create_manual_backup():
    """Crea un backup manual de la base de datos."""
    try:
        if session.get('role') != 'Administrador':
            return jsonify({"success": False, "error": "Solo administradores pueden crear backups"}), 403

        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = f"backups/{backup_id}"

        # Crear directorio si no existe
        os.makedirs("backups", exist_ok=True)

        # Comando para crear backup de MongoDB
        cmd = [
            "mongodump",
            "--db", DB_NAME,
            "--out", backup_path,
            "--uri", MONGODB_URI.replace("mongodb+srv://", "").split("@")[0]  # Extraer credenciales si es necesario
        ]

        # Ejecutar backup
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Registrar backup en colección
            backup_info = {
                "backup_id": backup_id,
                "tipo": "manual",
                "fecha": datetime.now(),
                "ruta": backup_path,
                "tamaño": "Calculando...",
                "estado": "Completado",
                "usuario_creador": session['user_id']
            }

            db["backups"].insert_one(backup_info)

            return jsonify({
                "success": True,
                "message": f"Backup creado exitosamente: {backup_id}",
                "backup_id": backup_id
            })
        else:
            return jsonify({"success": False, "error": f"Error en mongodump: {result.stderr}"}), 500

    except Exception as e:
        print(f"Error creando backup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backup/list')
@login_required
def list_backups():
    """Lista todos los backups disponibles."""
    try:
        if session.get('role') != 'Administrador':
            return jsonify({"success": False, "error": "Solo administradores pueden ver backups"}), 403

        backups = list(db["backups"].find({}, {"_id": 0}).sort("fecha", -1))

        # Calcular tamaño de archivos si existen
        for backup in backups:
            try:
                backup_path = backup.get("ruta")
                if backup_path and os.path.exists(backup_path):
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(backup_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            total_size += os.path.getsize(fp)
                    backup["tamaño"] = f"{total_size / (1024*1024):.2f} MB"
                else:
                    backup["tamaño"] = "No encontrado"
            except Exception as e:
                backup["tamaño"] = "Error calculando"

        return jsonify(backups)

    except Exception as e:
        print(f"Error listando backups: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backup/restore/<backup_id>', methods=['POST'])
@login_required
def restore_backup(backup_id):
    """Restaura un backup específico."""
    try:
        if session.get('role') != 'Administrador':
            return jsonify({"success": False, "error": "Solo administradores pueden restaurar backups"}), 403

        # Buscar backup
        backup = db["backups"].find_one({"backup_id": backup_id})
        if not backup:
            return jsonify({"success": False, "error": "Backup no encontrado"}), 404

        backup_path = backup.get("ruta")
        if not backup_path or not os.path.exists(backup_path):
            return jsonify({"success": False, "error": "Archivo de backup no encontrado"}), 404

        # Comando para restaurar
        cmd = [
            "mongorestore",
            "--db", DB_NAME,
            "--drop",
            backup_path + "/" + DB_NAME
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": f"Backup {backup_id} restaurado exitosamente"
            })
        else:
            return jsonify({"success": False, "error": f"Error en mongorestore: {result.stderr}"}), 500

    except Exception as e:
        print(f"Error restaurando backup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def schedule_automatic_backups():
    """Programa backups automáticos diarios."""
    def daily_backup():
        # Asegurar la conexión a la base de datos en este hilo
        if not is_db_connected():
            conectar_db()
        
        if not is_db_connected():
            print("Error en backup automático: No se pudo conectar a la base de datos para iniciar el proceso.")
            return
        try:
            backup_id = f"auto_backup_{datetime.now().strftime('%Y%m%d')}"

            # Evitar duplicados del día
            existing = db["backups"].find_one({
                "backup_id": backup_id,
                "tipo": "automatico"
            })

            if not existing:
                backup_path = f"backups/{backup_id}"
                os.makedirs("backups", exist_ok=True)

                cmd = ["mongodump", "--db", DB_NAME, "--out", backup_path]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    backup_info = {
                        "backup_id": backup_id,
                        "tipo": "automatico",
                        "fecha": datetime.now(),
                        "ruta": backup_path,
                        "estado": "Completado",
                        "programado": True
                    }
                    db["backups"].insert_one(backup_info)
                    print(f"Backup automático creado: {backup_id}")

        except Exception as e:
            print(f"Error en backup automático: {e}")

    # Programar backup diario a las 2 AM
    schedule.every().day.at("02:00").do(daily_backup)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    # Ejecutar scheduler en hilo separado
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# Inicializar backups automáticos cuando el servidor inicia
schedule_automatic_backups()

@app.route('/api/system/health')
@login_required
def system_health():
    """Verifica el estado del sistema (para debugging)."""
    try:
        health_check = {
            "database": {
                "status": "online",
                "last_backup": None,
                "connection": "ok"
            },
            "backups_enabled": True,
            "scheduler_active": len(schedule.jobs) > 0,
            "timestamp": datetime.now().isoformat()
        }

        # Obtener último backup
        last_backup = db["backups"].find_one(sort=[("fecha", -1)])
        if last_backup:
            health_check["database"]["last_backup"] = last_backup["fecha"].isoformat()

        return jsonify({"success": True, "health": health_check})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- MODALES PARA BACKUPS EN PANEL DE ADMINISTRACIÓN ---
@login_required
@app.route('/backups')
def backups_page():
    """Página de gestión de backups."""
    if session.get('role') != 'Administrador':
        flash('No tienes permisos para acceder a esta sección.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('backups.html')

# --- RUTAS PARA HISTORIAL DE LISTA DE COMPRAS URGENTE ---
@app.route('/api/shopping_list', methods=['GET'])
@login_required
def get_shopping_list():
    """Obtiene la lista de compras urgente MÁS RECIENTE desde la base de datos."""
    try:
        # Busca en la colección de historial, ordena por fecha descendente y toma la primera.
        latest_list_doc = db.shopping_lists.find_one(sort=[("saved_at", -1)])
        if latest_list_doc:
            return jsonify({"success": True, "shopping_list": latest_list_doc.get("list", {})})
        else:
            return jsonify({"success": True, "shopping_list": {}}) # Si no hay historial, devuelve una lista vacía
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/shopping_list/save', methods=['POST'])
@login_required
def save_shopping_list_api():
    """Guarda una NUEVA entrada en el historial de la lista de compras."""
    data = request.get_json()
    current_list = data.get('shopping_list', {})
    
    # No guardar si la lista está vacía para no llenar el historial con nada
    if not current_list:
        return jsonify({"success": True, "message": "No se guarda la lista vacía."})

    try:
        # Insertar un nuevo documento en lugar de actualizar uno existente
        db.shopping_lists.insert_one({
            "list": current_list,
            "saved_at": datetime.now(),
            "item_count": len(current_list)
        })
        return jsonify({"success": True, "message": "Versión de la lista guardada en el historial."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/shopping_lists/history', methods=['GET'])
@login_required
def get_shopping_list_history():
    """Obtiene el historial de todas las listas de compras guardadas."""
    try:
        history = list(db.shopping_lists.find({}, {"list": 0}).sort("saved_at", -1))
        for item in history:
            item['_id'] = str(item['_id'])
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/shopping_list/<list_id>', methods=['GET'])
@login_required
def get_specific_shopping_list(list_id):
    """Obtiene una lista de compras específica del historial por su ID."""
    try:
        shopping_list_doc = db.shopping_lists.find_one({"_id": ObjectId(list_id)})
        if shopping_list_doc:
            return jsonify({"success": True, "shopping_list": shopping_list_doc.get("list", {})})
        else:
            return jsonify({"success": False, "error": "Lista no encontrada"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Configuración para Render.com y producción
    import os

    # Detectar si estamos en Render.com
    is_render = os.environ.get('RENDER') == 'true'

    if is_render:
        # Configuración optimizada para Render.com
        port = int(os.environ.get('PORT', 5000))

        # Ejecutar con configuración de producción
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        # Configuración de desarrollo local
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
