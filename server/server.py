import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
ROOT_PATH = Path(__file__).parent.parent # Subimos un nivel para apuntar a la carpeta 'Sistema'
sys.path.append(str(ROOT_PATH))

from flask import Flask, jsonify, render_template, request
from database.database import *

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

# --- Rutas de la API (Backend para el Frontend) ---

@app.route('/api/products')
def get_products():
    """Devuelve la lista de todos los productos en formato JSON."""
    productos = obtener_productos()
    # Convertir la lista de tuplas a una lista de diccionarios para JSON
    keys = ["id", "codigo_barras", "nombre", "departamento", "precio", "costo", "stock"]
    keys = ["id", "codigo_barras", "nombre", "costo", "precio", "stock", "stock_minimo", "departamento"]
    productos_dict = [dict(zip(keys, prod)) for prod in productos]
    return jsonify(productos_dict)

@app.route('/api/stats')
def get_stats():
    """Devuelve estadísticas clave del negocio."""
    stats = obtener_estadisticas()
    return jsonify(stats)

@app.route('/api/product/update/<int:product_id>', methods=['POST'])
def update_product(product_id):
    """Actualiza un producto existente desde la interfaz web."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No se recibieron datos"}), 400

    try:
        # Extraer y validar datos del JSON recibido
        codigo = data['codigo_barras']
        nombre = data['nombre']
        departamento = data['departamento']
        costo = float(data['costo'])
        precio = float(data['precio'])
        costo = float(data['costo'])
        stock = int(data['stock'])
        stock_minimo = int(data['stock_minimo'])
        departamento = data['departamento']

        # Llamar a la función de la base de datos que ya teníamos
        actualizar_producto(product_id, codigo, nombre, departamento, precio, costo, stock)
        actualizar_producto(product_id, codigo, nombre, costo, precio, stock, stock_minimo, departamento)
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
        departamento = data.get('departamento')
        costo = float(data.get('costo'))
        precio = float(data.get('precio'))
        costo = float(data.get('costo'))
        stock = int(data.get('stock'))
        stock_minimo = int(data.get('stock_minimo', 0)) # Default a 0 si no se envía
        departamento = data.get('departamento')

        if not all([codigo, nombre, departamento]):
             return jsonify({"success": False, "error": "Código, Nombre y Departamento son requeridos."}), 400

        agregar_producto(codigo, nombre, departamento, precio, costo, stock)
        agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento)
        return jsonify({"success": True, "message": "Producto agregado correctamente."})

    except Exception as e:
        return jsonify({"success": False, "error": f"No se pudo agregar el producto. Causa probable: Código de barras duplicado. ({str(e)})"}), 500

@app.route('/api/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Elimina un producto desde la interfaz web."""
    try:
        # Reutilizamos la función que ya existe en database.py
        eliminar_producto(product_id)
        return jsonify({"success": True, "message": "Producto eliminado correctamente."})
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
        keys = ["id", "codigo_barras", "nombre", "departamento", "precio", "costo", "stock"]
        keys = ["id", "codigo_barras", "nombre", "costo", "precio", "stock", "stock_minimo", "departamento"]
        producto_dict = dict(zip(keys, producto))
        return jsonify({"success": True, "product": producto_dict})
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

@app.route('/api/search_products', methods=['POST'])
def api_search_products():
    """
    Busca productos por nombre.
    """
    data = request.get_json()
    search_term = data.get('term')

    if not search_term or len(search_term) < 3:
        return jsonify({"success": False, "error": "El término de búsqueda debe tener al menos 3 caracteres."}), 400

    try:
        productos = buscar_productos_por_nombre(search_term)
        keys = ["id", "codigo_barras", "nombre", "departamento", "precio", "costo", "stock"]
        keys = ["id", "codigo_barras", "nombre", "costo", "precio", "stock", "stock_minimo", "departamento"]
        productos_dict = [dict(zip(keys, prod)) for prod in productos]
        return jsonify({"success": True, "products": productos_dict})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    # La opción host='0.0.0.0' hace que el servidor sea accesible
    # desde otros dispositivos en la misma red (como tu tablet).
    # El modo debug recarga automáticamente el servidor cuando haces cambios.
    app.run(host='0.0.0.0', port=5000, debug=True)
