from pymongo import MongoClient
from pathlib import Path
from bson import ObjectId
from datetime import datetime, timedelta
from gui.security import hash_password, check_password
import json
import os 
from pymongo.errors import ConnectionFailure, ConfigurationError
import sqlite3
import unicodedata

CACHE_FILE = "local_cache.json"
LOCAL_DB_FILE = "offline_data.db"

# Define la ruta del proyectoo 
ROOT_PATH = Path(__file__).parent.parent
MONGODB_URI = "mongodb+srv://JJR5:Guacamole97@cluster0.e1gxa7c.mongodb.net/?retryWrites=true&w=majority"

### MongoDB ###c
# Reemplaza con tu cadena de conexión de MongoDB Atlas 
DB_NAME = "ferreteria"  # Nombre de tu base de datos

# Inicializar el cliente de MongoDB
client = None
db = None
IS_CONNECTED = False # Variable global para rastrear el estado de la conexión

# Definir variables globales para las colecciones
productos_collection = None
ventas_collection = None
usuarios_collection = None
proveedores_collection = None
clientes_collection = None
facturas_compra_collection = None
devoluciones_collection = None
ventas_detalle_collection = None
devoluciones_detalle_collection = None
cotizaciones_collection = None
cotizaciones_detalle_collection = None
cierres_caja_collection = None # New


def conectar_db():
    """Establece la conexión con la base de datos MongoDB."""
    global client, db
    global IS_CONNECTED
    if client is None:
        try:
            print("Intentando conectar a MongoDB Atlas...")
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # El siguiente comando fuerza una conexión y verifica si es exitosa.
            client.admin.command('ping')
            db = client[DB_NAME]
            print("✅ Conexión a MongoDB Atlas exitosa.")
            IS_CONNECTED = True

            # --- Inicializar colecciones DESPUÉS de conectar ---
            global productos_collection, ventas_collection, usuarios_collection, proveedores_collection, clientes_collection, facturas_compra_collection, devoluciones_collection, ventas_detalle_collection, devoluciones_detalle_collection, cotizaciones_collection, cotizaciones_detalle_collection, cierres_caja_collection
            productos_collection = db["productos"]
            ventas_collection = db["ventas"]
            usuarios_collection = db["usuarios"]
            proveedores_collection = db["proveedores"]
            clientes_collection = db["clientes"]
            facturas_compra_collection = db["facturas_compra"]
            devoluciones_collection = db["devoluciones"]
            ventas_detalle_collection = db["ventas_detalle"]
            devoluciones_detalle_collection = db["devoluciones_detalle"]
            cotizaciones_collection = db["cotizaciones"]
            cotizaciones_detalle_collection = db["cotizaciones_detalle"]
            cierres_caja_collection = db["cierres_caja"]

        except (ConnectionFailure, ConfigurationError) as e:
            # Capturamos tanto errores de conexión como errores de configuración/DNS (ej. SRV/DNS refusals)
            IS_CONNECTED = False
            print("❌ ERROR AL CONECTAR A MONGODB: La aplicación entrará en modo offline.")
            print("   Posibles causas: sin conexión a internet, DNS bloqueado, o configuración de red que impide resolver el host de MongoDB Atlas.")
            print(f"   Detalles del error: {e}")
            print("   Si esto ocurre en una red corporativa o con firewall, verifica que las consultas DNS (puerto 53) y el acceso saliente a MongoDB Atlas estén permitidos.")
            print("   La aplicación seguirá funcionando en modo offline mientras no haya conexión.")

def is_db_connected():
    """Devuelve el estado actual de la conexión a la base de datos."""
    return IS_CONNECTED

def guardar_datos_en_cache():
    """
    Obtiene los datos principales de MongoDB y los guarda en un archivo JSON local.
    """
    if db is None:
        print("No hay conexión a la base de datos para crear la caché.")
        return

    print("Actualizando caché de datos local...")
    try:
        cache_data = {
            'productos': list(db.productos.find({})),
            'clientes': list(db.clientes.find({})),
            'proveedores': list(db.proveedores.find({})),
            'timestamp': datetime.now().isoformat()
        }
        # Convertir ObjectId a string para que sea serializable en JSON
        for item_list in cache_data.values():
            if isinstance(item_list, list):
                for item in item_list:
                    if '_id' in item:
                        item['_id'] = str(item['_id'])
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        print("Caché local actualizada exitosamente.")
    except Exception as e:
        print(f"Error al guardar la caché local: {e}")

def cargar_datos_de_cache(key):
    """
    Carga una colección de datos desde el archivo de caché JSON.
    """
    print(f"ADVERTENCIA: Cargando datos desde la caché local para '{key}'. La información puede no estar actualizada.")
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get(key, [])
    except (IOError, json.JSONDecodeError):
        return []

def inicializar_db_local():
    """Crea la base de datos SQLite y las tablas necesarias si no existen."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        # Tabla para ventas pendientes de sincronización
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_pendientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                datos_venta TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tablas para almacenar productos, clientes y proveedores localmente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id TEXT PRIMARY KEY,
                codigo_barras TEXT,
                nombre TEXT,
                costo REAL,
                precio REAL,
                stock INTEGER,
                stock_minimo INTEGER,
                departamento TEXT,
                unidad_medida TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id TEXT PRIMARY KEY,
                nombre TEXT,
                rnc_cedula TEXT,
                telefono TEXT,
                direccion TEXT
            )
        """)

        # Tabla para registrar cambios pendientes de sincronización
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cambios_pendientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo TEXT NOT NULL, -- 'producto', 'cliente', etc.
                id_modelo TEXT NOT NULL, -- El ID del objeto
                operacion TEXT NOT NULL, -- 'crear', 'actualizar', 'eliminar'
                datos TEXT, -- JSON con los datos para crear/actualizar
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print("Base de datos local (SQLite) inicializada correctamente.")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos local: {e}")

def inicializar_db():
    """
    No es necesario crear tablas explícitamente en MongoDB.
    Las colecciones se crean automáticamente al insertar el primer documento.
    """    
    conectar_db() # Intentar conectar al iniciar
    print("Inicialización de la base de datos (MongoDB) completada.")

def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos central.")
        productos = list(productos_collection.find({}))
        # Convertir ObjectId a string para que sea serializable en JSON
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]  # Eliminar el ObjectId original para evitar errores de serialización JSON
        return productos
    except ConnectionFailure:
        return cargar_datos_de_cache('productos')

def agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida="Unidad"):
    """Agrega un nuevo producto a la base de datos."""
    try:
        producto = {
            "codigo_barras": codigo,
            "nombre": nombre,
            "costo": costo,
            "precio": precio,
            "stock": stock,
            "stock_minimo": stock_minimo,
            "departamento": departamento,
            "unidad_medida": unidad_medida,
        }
        productos_collection.insert_one(producto)
        # Después de insertar en MongoDB, también lo guardamos/actualizamos en la caché local
        producto['id'] = str(producto.pop('_id'))
        guardar_producto_local(producto)
    except ConnectionFailure:
        # --- Lógica Offline ---
        print("Modo Offline: Guardando nuevo producto localmente.")
        # Generamos un ID temporal localmente
        temp_id = str(ObjectId())
        producto_local = {
            "id": temp_id, # Usamos el ID temporal
            "codigo_barras": codigo, "nombre": nombre, "costo": costo, "precio": precio,
            "stock": stock, "stock_minimo": stock_minimo, "departamento": departamento,
            "unidad_medida": unidad_medida
        }
        guardar_producto_local(producto_local)
        registrar_cambio_local('producto', temp_id, 'crear', producto_local)
    except Exception as e:
        raise e


def agregar_productos_en_masa(products):
    """Agrega múltiples productos a la colección `productos`.
    `products` debe ser una lista de diccionarios con keys como:
    nombre, stock, costo, precio, stock_minimo, departamento, codigo_barras (opc.)
    Devuelve el número de productos insertados.
    """
    try:
        if db is None:
            raise ConnectionFailure("No hay conexión a la base de datos.")

        docs = []
        for p in products:
            try:
                doc = {
                    "codigo_barras": p.get('codigo_barras') or p.get('codigo') or '',
                    "nombre": p.get('nombre', 'Producto Nuevo'),
                    "costo": float(p.get('costo', 0)) if p.get('costo') not in (None, '') else 0.0,
                    "precio": float(p.get('precio', 0)) if p.get('precio') not in (None, '') else 0.0,
                    "stock": int(p.get('stock', 0)) if p.get('stock') not in (None, '') else 0,
                    "stock_minimo": int(p.get('stock_minimo', 1)) if p.get('stock_minimo') not in (None, '') else 1,
                    "departamento": p.get('departamento', 'Sin Asignar'),
                    "unidad_medida": p.get('unidad_medida', 'Unidad'),
                    "is_new": True
                }
                docs.append(doc)
            except Exception:
                # Saltar elementos inválidos pero continuar con el resto
                continue

        if not docs:
            return 0

        result = productos_collection.insert_many(docs)
        return len(result.inserted_ids)
    except Exception as e:
        raise e

def registrar_cambio_local(modelo, id_modelo, operacion, datos=None):
    """Registra una operación en la tabla de cambios pendientes para sincronización."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        datos_json = json.dumps(datos) if datos else None
        cursor.execute(
            "INSERT INTO cambios_pendientes (modelo, id_modelo, operacion, datos) VALUES (?, ?, ?, ?)",
            (modelo, id_modelo, operacion, datos_json)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error al registrar cambio local: {e}")

def actualizar_producto(id_producto, codigo, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida="Unidad"):
    """Actualiza un producto existente en la base de datos."""
    try:
        productos_collection.update_one(
            {"_id": ObjectId(id_producto)},  # Buscar por ObjectId
            {"$set": {
                "codigo_barras": codigo,
                "nombre": nombre,
                "costo": costo,
                "precio": precio,
                "stock": stock,
                "stock_minimo": stock_minimo,
                "departamento": departamento,
                "unidad_medida": unidad_medida,
            }}
        )
        
        # Si tiene éxito, actualiza la copia local
        guardar_producto_local(locals())
    except ConnectionFailure:
        # Si falla la conexión, actualiza localmente y registra el cambio
        print("Modo Offline: Actualizando producto localmente y registrando cambio.")
        guardar_producto_local(locals())
        registrar_cambio_local('producto', id_producto, 'actualizar', locals())
    except Exception as e:
        raise e

def actualizar_departamento_masivo(product_ids, nuevo_departamento):
    """Actualiza el departamento para una lista de productos."""
    try:
        if db is None:
            raise ConnectionFailure("No hay conexión a la base de datos.")
        
        object_ids = [ObjectId(pid) for pid in product_ids]
        
        result = productos_collection.update_many(
            {"_id": {"$in": object_ids}},
            {"$set": {"departamento": nuevo_departamento}}
        )
        return result.modified_count
    except Exception as e:
        raise e

def eliminar_producto(id_producto):
    """Elimina un producto de la base de datos por su ID."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos.")
        productos_collection.delete_one({"_id": ObjectId(id_producto)})  # Buscar por ObjectId
        eliminar_producto_local(id_producto)
    except ConnectionFailure:
        print("Modo Offline: Eliminando producto localmente y registrando cambio.")
        eliminar_producto_local(id_producto)
        registrar_cambio_local('producto', id_producto, 'eliminar')
    except Exception as e:
        raise e

def buscar_producto_por_codigo(codigo):
    """Busca un producto por su código de barras."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos.")
        producto = productos_collection.find_one({"codigo_barras": codigo})
        if producto:
            producto["id"] = str(producto["_id"])
            del producto["_id"]
        return producto
    except ConnectionFailure:
        # Búsqueda en caché
        productos_cache = cargar_datos_de_cache('productos')
        for producto in productos_cache:
            if producto.get('codigo_barras') == codigo:
                # El ID ya viene como string desde la caché
                return producto
        return None


def sumar_stock_producto(producto_id, cantidad_a_sumar):
    """Suma una cantidad específica al stock de un producto."""
    try:
        productos_collection.update_one(
            {"_id": ObjectId(producto_id)},
            {"$inc": {"stock": cantidad_a_sumar}}
        )
    except Exception as e:
        raise e

def buscar_productos_por_nombre(search_term):
    """Busca productos cuyo nombre contenga el término de búsqueda (limitado a 10 resultados)."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos.")
        productos = list(productos_collection.find(
            {"nombre": {"$regex": search_term, "$options": "i"}}  # Búsqueda insensible a mayúsculas
        ).limit(10))
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]  # Eliminar ObjectId para evitar errores de serialización JSON
        return productos
    except ConnectionFailure:
        # Búsqueda en caché
        productos_cache = cargar_datos_de_cache('productos')
        resultados = []
        for producto in productos_cache:
            if search_term.lower() in producto.get('nombre', '').lower():
                resultados.append(producto)
        return resultados[:10] # Limitar a 10 resultados
    
def obtener_productos_stock_bajo():
    """Obtiene todos los productos cuyo stock es igual o menor al stock mínimo."""
    try:
        # Usar $expr para comparar dos campos del mismo documento: stock y stock_minimo
        pipeline = [
            {
                "$match": {
                    "$expr": { "$lte": ["$stock", "$stock_minimo"] }
                }
            }
        ]
        productos = list(productos_collection.aggregate(pipeline))
        # Convertir ObjectId a string para que sea serializable
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]  # Eliminar ObjectId para evitar errores de serialización JSON
        return productos
    except ConnectionFailure:
        # Filtrado en caché
        productos_cache = cargar_datos_de_cache('productos')
        resultados = []
        for producto in productos_cache:
            stock = producto.get('stock', 0)
            stock_minimo = producto.get('stock_minimo', 0)
            if stock <= stock_minimo:
                resultados.append(producto)
        return resultados

# --- Funciones para Clientes (CRM) ---

def agregar_cliente(nombre, rnc_cedula, telefono, direccion):
    """Agrega un nuevo cliente a la base de datos."""
    try:
        cliente = {
            "nombre": nombre,
            "rnc_cedula": rnc_cedula,
            "telefono": telefono,
            "direccion": direccion,
            "fecha_creacion": datetime.now()
        }

        result = clientes_collection.insert_one(cliente)
        # Devolver el id del cliente insertado como string
        return str(result.inserted_id)
    except Exception as e:
        # Si hay fallo por conexión, intentar guardar en caché/local (opcional)
        print(f"Error agregando cliente: {e}")
        raise e

def obtener_clientes():
    """Obtiene todos los clientes de la base de datos."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos central.")
        clientes = list(clientes_collection.find({}))
        for cliente in clientes:
            cliente["_id"] = str(cliente["_id"])
        return clientes
    except ConnectionFailure:

        return cargar_datos_de_cache('clientes')




def buscar_clientes(termino_busqueda):
    """Busca clientes por nombre o RNC/Cédula."""
    try:
        # Busca si el término está en el nombre O en el rnc_cedula
        query = {
            "$or": [
                {"nombre": {"$regex": termino_busqueda, "$options": "i"}},
                {"rnc_cedula": {"$regex": termino_busqueda, "$options": "i"}}
            ]
        }
        clientes = list(clientes_collection.find(query).limit(10))
        for cliente in clientes:
            cliente["_id"] = str(cliente["_id"])
        return clientes
    except ConnectionFailure:
        # Búsqueda en caché
        clientes_cache = cargar_datos_de_cache('clientes')
        resultados = []
        termino = termino_busqueda.lower()
        for cliente in clientes_cache:
            if termino in cliente.get('nombre', '').lower() or \
               termino in cliente.get('rnc_cedula', '').lower():
                resultados.append(cliente)
        return resultados[:10]


def eliminar_cliente(cliente_id):
    """Elimina un cliente por su ID."""
    try:
        clientes_collection.delete_one({"_id": ObjectId(cliente_id)})
        eliminar_cliente_local(cliente_id)
    except ConnectionFailure:
        print("Modo Offline: Eliminando cliente localmente y registrando cambio.")
        eliminar_cliente_local(cliente_id)
        registrar_cambio_local('cliente', cliente_id, 'eliminar')
    except Exception as e:
        raise e


def actualizar_id_producto_local(id_antiguo, id_nuevo):
    """Actualiza el ID de un producto en la base de datos local."""
    with sqlite3.connect(LOCAL_DB_FILE) as conn:
        conn.execute("UPDATE productos SET id = ? WHERE id = ?", (id_nuevo, id_antiguo))

def buscar_venta_por_id(venta_id):
    """Busca una venta y sus detalles por su ID."""
    try:
        # Asegurarse de buscar por ObjectId en la colección de ventas
        venta = ventas_collection.find_one({"_id": ObjectId(venta_id)})
        # En ventas_detalle guardamos venta_id como ObjectId, por lo que usamos ObjectId aquí
        detalles = list(ventas_detalle_collection.find({"venta_id": ObjectId(venta_id)}))
        return venta, detalles
    except Exception as e:
        print(f"Error al buscar venta: {e}")
        return None, None
def guardar_producto_local(producto):
    """Guarda o actualiza un producto en la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO productos (id, codigo_barras, nombre, costo, precio, stock, stock_minimo, departamento, unidad_medida)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            producto.get('id'),
            producto.get('codigo_barras'),
            producto.get('nombre'),
            producto.get('costo'),
            producto.get('precio'),
            producto.get('stock'),
            producto.get('stock_minimo'),
            producto.get('departamento'),
            producto.get('unidad_medida')
        ))
        conn.commit()
        conn.close()
        print(f"Producto {producto.get('nombre')} guardado/actualizado localmente.")
    except sqlite3.Error as e:
        print(f"Error al guardar/actualizar producto localmente: {e}")

def eliminar_producto_local(producto_id):
    """Elimina un producto de la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
        conn.commit()
        conn.close()
        print(f"Producto con ID {producto_id} eliminado localmente.")
    except sqlite3.Error as e:
        print(f"Error al eliminar producto localmente: {e}")

def guardar_cliente_local(cliente):
    """Guarda o actualiza un cliente en la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO clientes (id, nombre, rnc_cedula, telefono, direccion)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cliente.get('id'),
            cliente.get('nombre'),
            cliente.get('rnc_cedula'),
            cliente.get('telefono'),
            cliente.get('direccion')
        ))
        conn.commit()
        conn.close()
        print(f"Cliente {cliente.get('nombre')} guardado/actualizado localmente.")
    except sqlite3.Error as e:
        print(f"Error al guardar/actualizar cliente localmente: {e}")

def eliminar_cliente_local(cliente_id):
    """Elimina un cliente de la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        conn.close()
        print(f"Cliente con ID {cliente_id} eliminado localmente.")
    except sqlite3.Error as e:
        print(f"Error al eliminar cliente localmente: {e}")

def limpiar_tabla_local(table_name):
    """Limpia una tabla en la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
        conn.close()
        print(f"Tabla {table_name} limpiada localmente.")
    except sqlite3.Error as e:
        print(f"Error al limpiar tabla localmente: {e}")

def obtener_ids_productos_local():
    """Obtiene todos los ids de productos guardados localmente."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos")
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ids
    except sqlite3.Error as e:
        print(f"Error al obtener ids de productos localmente: {e}")
        return []

def agregar_proveedor(nombre, rnc, telefono):
    """Agrega un nuevo proveedor."""
    try:
        proveedor = {
            "nombre": nombre,
            "rnc": rnc,
            "telefono": telefono,
        }
        proveedores_collection.insert_one(proveedor)
    except Exception as e:
        raise e

def obtener_proveedor_por_nombre(nombre):
    """Obtiene un proveedor por su nombre."""
    try:
        proveedor = proveedores_collection.find_one({"nombre": nombre})
        return proveedor
    except Exception as e:
        print(f"Error al obtener proveedor por nombre: {e}")
        return None

def obtener_proveedores():
    """Obtiene todos los proveedores."""
    try:
        if db is None: raise ConnectionFailure("No hay conexión a la base de datos.")
        proveedores = list(proveedores_collection.find({}))
        return proveedores
    except ConnectionFailure:
        return cargar_datos_de_cache('proveedores')

def agregar_factura_compra(proveedor_id, num_factura, fecha_emision, fecha_vencimiento, monto, moneda, notas=None):
    """Agrega una nueva factura de compra (cuenta por pagar)."""
    try:
        factura = {
            "proveedor_id": ObjectId(proveedor_id),
            "numero_factura": num_factura,
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "monto": monto,
            "moneda": moneda,
            "estado": "Pendiente",
            "notas": notas
        }  
        facturas_compra_collection.insert_one(factura)
    except Exception as e:
        raise e

def obtener_cuentas_por_pagar():
    """Obtiene todas las facturas pendientes, uniendo con el nombre del proveedor."""
    try:
        # Validar que la colección existe antes de usarla
        if facturas_compra_collection is None:
            print("AVISO CRÍTICO: facturas_compra_collection es None en obtener_cuentas_por_pagar")
            return []
        if db is None:
            print("No hay conexión a la base de datos: obtener_cuentas_por_pagar devuelve lista vacía.")
            return []

        cuentas = list(facturas_compra_collection.aggregate([
            {
                "$lookup": {
                    "from": "proveedores",
                    "localField": "proveedor_id",
                    "foreignField": "_id",
                    "as": "proveedor"
                }
            },
            {
                "$unwind": {"path": "$proveedor", "preserveNullAndEmptyArrays": True}
            },
            {
                "$match": {"estado": "Pendiente"}
            },
            {
                "$project": {
                    "_id": 1,
                    "proveedor_id": 1,
                    "proveedor": "$proveedor.nombre",
                    "numero_factura": 1,
                    "fecha_emision": 1,
                    "fecha_vencimiento": 1,
                    "monto": 1,
                    "moneda": 1,
                    "notas": 1
                }
            }
        ]))

        # Convertir ObjectId a string para que sea serializable en JSON
        for cuenta in cuentas:
            cuenta["_id"] = str(cuenta["_id"])
            if 'proveedor_id' in cuenta:
                cuenta["proveedor_id"] = str(cuenta["proveedor_id"])
            if 'fecha_emision' in cuenta and isinstance(cuenta['fecha_emision'], datetime):
                cuenta['fecha_emision'] = cuenta['fecha_emision'].isoformat()
            if 'fecha_vencimiento' in cuenta and isinstance(cuenta['fecha_vencimiento'], datetime):
                cuenta['fecha_vencimiento'] = cuenta['fecha_vencimiento'].isoformat()

        return cuentas
    except Exception as e:
        print(f"Error al obtener cuentas por pagar: {e}")
        return []

def marcar_factura_como_pagada(factura_id):
    """Cambia el estado de una factura de compra a 'Pagada'."""
    try:    
        # Establecer estado y fecha de pago al momento de marcar como pagada
        facturas_compra_collection.update_one(
            {"_id": ObjectId(factura_id)},
            {"$set": {"estado": "Pagada", "fecha_pago": datetime.now()}}
        )
    except Exception as e:
        raise e

def eliminar_factura_compra(factura_id):
    """Elimina una factura de compra por su ID."""
    try:
        if db is None:
            raise ConnectionFailure("No hay conexión a la base de datos.")
        facturas_compra_collection.delete_one({"_id": ObjectId(factura_id)})
    except Exception as e:
        raise e

def actualizar_factura_compra(factura_id, proveedor_id, num_factura, fecha_emision, fecha_vencimiento, monto, moneda, notas=None):
    """Actualiza una factura de compra existente."""
    try:
        if db is None:
            raise ConnectionFailure("No hay conexión a la base de datos.")

        facturas_compra_collection.update_one(
            {"_id": ObjectId(factura_id)},
            {"$set": {
                "proveedor_id": ObjectId(proveedor_id),
                "numero_factura": num_factura,
                "fecha_emision": fecha_emision,
                "fecha_vencimiento": fecha_vencimiento,
                "monto": monto,
                "moneda": moneda,
                "notas": notas
            }}
        )
    except Exception as e:
        raise e

def obtener_facturas_pagadas(fecha_inicio, fecha_fin):
    """Obtiene todas las facturas pagadas en un rango de fechas, uniendo con el nombre del proveedor."""
    try:
        # Validar que la colección existe antes de usarla
        if facturas_compra_collection is None:
            print("AVISO CRÍTICO: facturas_compra_collection es None en obtener_facturas_pagadas")
            return []
        if db is None:
            print("No hay conexión a la base de datos: obtener_facturas_pagadas devuelve lista vacía.")
            return []

        facturas = list(facturas_compra_collection.aggregate([
            {
                "$lookup": {
                    "from": "proveedores",
                    "localField": "proveedor_id",
                    "foreignField": "_id",
                    "as": "proveedor"
                }
            },
            {
                "$unwind": {"path": "$proveedor", "preserveNullAndEmptyArrays": True}
            },
            {
                "$match": {
                    "estado": "Pagada",
                    "fecha_pago": {"$gte": fecha_inicio, "$lte": fecha_fin}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "proveedor": "$proveedor.nombre",
                    "numero_factura": 1,
                    "fecha_emision": 1,
                    "fecha_vencimiento": 1, # Keep as datetime for now, convert later
                    "fecha_pago": 1, # Keep as datetime for now, convert later
                    "monto": 1,
                    "moneda": 1
                }
            }
        ]))
        # Convertir ObjectId a string y datetime a string ISO para serialización JSON
        for f in facturas:
            if '_id' in f: f['_id'] = str(f['_id'])
            if 'fecha_emision' in f and isinstance(f['fecha_emision'], datetime): f['fecha_emision'] = f['fecha_emision'].isoformat()
            if 'fecha_vencimiento' in f and isinstance(f['fecha_vencimiento'], datetime): f['fecha_vencimiento'] = f['fecha_vencimiento'].isoformat()
            if 'fecha_pago' in f and isinstance(f['fecha_pago'], datetime): f['fecha_pago'] = f['fecha_pago'].isoformat()
        return facturas
    except Exception as e:
        print(f"Error al obtener facturas pagadas: {e}")
        return []


def buscar_facturas_por_texto(texto):
    """Busca facturas por proveedor o número de factura que contengan el texto dado (case-insensitive)."""
    try:
        if facturas_compra_collection is None:
            print("AVISO CRÍTICO: facturas_compra_collection es None en buscar_facturas_por_texto")
            return []
        regex = {"$regex": texto, "$options": "i"}
        pipeline = [
            {
                "$lookup": {
                    "from": "proveedores",
                    "localField": "proveedor_id",
                    "foreignField": "_id",
                    "as": "proveedor"
                }
            },
            {"$unwind": {"path": "$proveedor", "preserveNullAndEmptyArrays": True}},
            {"$match": {"$or": [{"numero_factura": regex}, {"proveedor.nombre": regex}] }},
            {"$project": {"_id": 1, "proveedor": "$proveedor.nombre", "numero_factura": 1, "fecha_emision": 1, "fecha_vencimiento": 1, "fecha_pago": 1, "monto": 1, "moneda": 1, "estado": 1}}
        ]
        resultados = list(facturas_compra_collection.aggregate(pipeline))
        for f in resultados:
            if '_id' in f: f['_id'] = str(f['_id'])
            if 'fecha_emision' in f and isinstance(f['fecha_emision'], datetime): f['fecha_emision'] = f['fecha_emision'].isoformat()
            if 'fecha_vencimiento' in f and isinstance(f['fecha_vencimiento'], datetime): f['fecha_vencimiento'] = f['fecha_vencimiento'].isoformat()
            if 'fecha_pago' in f and isinstance(f['fecha_pago'], datetime): f['fecha_pago'] = f['fecha_pago'].isoformat()
        return resultados
    except Exception as e:
        print(f"Error buscando facturas por texto '{texto}': {e}")
        return []

def crear_admin_por_defecto():
    """Crea un usuario administrador por defecto."""
    try:
        # Siempre asegurar que existe usuario admin, reemplazando si existe
        admin_pass_hash = hash_password("ferreteria123")
        usuarios_collection.replace_one(
            {"nombre_usuario": "ferreteria"},
            {
                "nombre_usuario": "ferreteria",
                "hash_contrasena": admin_pass_hash,
                "rol": "Administrador",
                "activo": True
            },
            upsert=True
        )
        print("Usuario ferreteria/ferreteria123 configurado correctamente.")
    except Exception as e:
        print(f"Error al crear usuario admin por defecto: {e}")

def obtener_usuario_por_nombre(nombre_usuario):
    """Obtiene los datos de un usuario por su nombre de usuario."""
    try:
        usuario = usuarios_collection.find_one({"nombre_usuario": nombre_usuario})
        return usuario
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return None

def obtener_todos_los_usuarios():
    """Obtiene una lista de todos los usuarios (sin la contraseña)."""
    try:
        usuarios = list(usuarios_collection.find({}, {"hash_contrasena": 0}))
        return usuarios
    except Exception as e:
        print(f"Error al obtener todos los usuarios: {e}")
        return []

def crear_usuario(nombre_usuario, password, rol):
    """Crea un nuevo usuario en la base de datos."""
    try:
        password_hash = hash_password(password)
        usuarios_collection.insert_one({
            "nombre_usuario": nombre_usuario,
            "hash_contrasena": password_hash,
            "rol": rol
        })
    except Exception as e:
        raise e

def eliminar_usuario(usuario_id):
    """Elimina un usuario por su ID."""
    try:
        usuarios_collection.delete_one({"_id": ObjectId(usuario_id)})
    except Exception as e:
        raise e

def actualizar_contrasena(usuario_id, nueva_contrasena):
    """Actualiza la contraseña de un usuario."""
    try:
        nuevo_hash = hash_password(nueva_contrasena)
        usuarios_collection.update_one(
            {"_id": ObjectId(usuario_id)},
            {"$set": {"hash_contrasena": nuevo_hash}}
        )
    except Exception as e:
        raise e

def registrar_venta(items_venta, total, itbis, descuento, usuario_id, tipo_pago, cliente_id=None, temp_client_name=None):
    """
    Registra una venta completa en la base de datos, incluyendo el detalle
    y la actualización del stock de los productos.
    
    Args:
        temp_client_name: Nombre temporal del cliente para ventas a crédito sin cliente asignado
    """
    try:
        # Normalizar tipo_pago para detectar "credito" independientemente de mayúsculas o acentos
        def _normalize(s):
            if not s:
                return ''
            return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).lower()

        tipo_pago_norm = _normalize(tipo_pago)
        print(f"DEBUG registrar_venta -> tipo_pago recibido: '{tipo_pago}', normalizado: '{tipo_pago_norm}'")

        es_credito = 'credito' in tipo_pago_norm or 'credit' in tipo_pago_norm
        print(f"DEBUG registrar_venta -> es_credito={es_credito}")

        # Si es crédito sin cliente ni nombre temporal, generar un nombre por defecto
        if es_credito and not cliente_id and not temp_client_name:
            temp_client_name = f"Cliente Temporal - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        venta = {
            "fecha": datetime.now(),
            "total": total,
            "itbis": itbis,
            "descuento": descuento,
            "usuario_id": ObjectId(usuario_id) if usuario_id else None,
            "tipo_pago": tipo_pago,
            "cliente_id": ObjectId(cliente_id) if cliente_id else None,
            "temp_cliente_nombre": temp_client_name,  # Guardar nombre temporal si aplica
            # Si es a crédito, queda pendiente. Si no, se marca como pagada.
            "estado": "Pendiente" if es_credito else "Pagada",
            "saldo_pendiente": total if es_credito else 0
        }
        print(f"DEBUG registrar_venta -> venta document antes de insert: {venta}")
        result = ventas_collection.insert_one(venta)
        venta_id_obj = result.inserted_id  # Guardar como ObjectId
        venta_id = str(venta_id_obj)  # Convertir a string para retornar

        print(f"DEBUG registrar_venta -> venta insertada: id={venta_id}, tipo_pago={tipo_pago}, estado={venta.get('estado')}, saldo={venta.get('saldo_pendiente')}, cliente_id={cliente_id}, temp_name={temp_client_name}")

        for idx, item in enumerate(items_venta):
            # Validaciones y conversiones seguras de IDs
            producto_id = item.get('id')
            cantidad = item.get('cantidad', 0)
            precio_unitario = item.get('precio', 0)
            costo_unitario = item.get('costo', 0)

            # Convertir producto_id a ObjectId si es string
            try:
                if not isinstance(producto_id, ObjectId):
                    producto_obj_id = ObjectId(producto_id)
                else:
                    producto_obj_id = producto_id
            except Exception as conv_err:
                print(f"Error convirtiendo producto_id en item {idx}: {conv_err}")
                raise conv_err

            # Insertar detalle de venta usando ObjectId
            ventas_detalle_collection.insert_one({
                "venta_id": venta_id_obj,
                "producto_id": producto_obj_id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "costo_unitario": costo_unitario
            })

            # Actualizar stock (manejar producto_id como ObjectId)
            try:
                productos_collection.update_one(
                    {"_id": producto_obj_id},
                    {"$inc": {"stock": -cantidad}}
                )
            except Exception as upd_err:
                print(f"Error actualizando stock para producto {producto_id}: {upd_err}")
                raise upd_err

        return venta_id

    except Exception as e:
        print(f"Error al registrar la venta: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise e
        raise e

def obtener_historial_ventas(limit=100):
    """Obtiene un historial de las últimas ventas con información del cliente y vendedor."""
    try:
        pipeline = [
            {"$sort": {"fecha": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "clientes",
                    "localField": "cliente_id",
                    "foreignField": "_id",
                    "as": "cliente_info"
                }
            },
            {"$unwind": {"path": "$cliente_info", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "usuarios",
                    "localField": "usuario_id",
                    "foreignField": "_id",
                    "as": "vendedor_info"
                }
            },
            {"$unwind": {"path": "$vendedor_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "fecha": "$fecha",
                    "cliente_nombre": {"$ifNull": ["$cliente_info.nombre", "$temp_cliente_nombre"]},
                    "vendedor_nombre": "$vendedor_info.nombre_usuario",
                    "total": "$total",
                    "tipo_pago": "$tipo_pago",
                    "estado": "$estado"
                }
            }
        ]
        ventas = list(ventas_collection.aggregate(pipeline))
        return ventas
    except Exception as e:
        print(f"Error al obtener historial de ventas: {e}")
        return []

def guardar_venta_local(sale_data):
    """Guarda los datos de una venta en la base de datos SQLite local."""
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        # Convertimos el diccionario de la venta a un string JSON para guardarlo
        datos_json = json.dumps(sale_data)
        cursor.execute("INSERT INTO ventas_pendientes (datos_venta) VALUES (?)", (datos_json,))
        conn.commit()
        conn.close()
        print(f"Venta guardada localmente. ID local: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error al guardar venta localmente: {e}")
        raise e

# --- Funciones para Cuentas por Cobrar ---

def obtener_cuentas_por_cobrar():
    """Obtiene todas las ventas pendientes de pago, uniendo con el nombre del cliente."""
    try:
        # Incluye ventas pendientes aún sin cliente asignado (usa temp_cliente_nombre)
        pipeline = [
            {"$match": {"estado": "Pendiente"}},
            {
                "$lookup": {
                    "from": "clientes",
                    "localField": "cliente_id",
                    "foreignField": "_id",
                    "as": "cliente_info"
                }
            },
            {"$unwind": {"path": "$cliente_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "venta_id": {"$toString": "$_id"},
                    "fecha": "$fecha",
                    "tipo_pago": "$tipo_pago",
                    "usuario_id": {"$toString": "$usuario_id"},
                    "cliente_id": {"$toString": "$cliente_id"},
                    # Si no hay cliente vinculado, usar el nombre temporal guardado en la venta
                    "cliente_nombre": {"$ifNull": ["$cliente_info.nombre", "$temp_cliente_nombre"]},
                    "total": "$total",
                    "saldo_pendiente": "$saldo_pendiente"
                }
            },
            {"$sort": {"fecha": -1}} # Ordenar por las más recientes primero
        ]
        cuentas = list(ventas_collection.aggregate(pipeline))
        # Asegurar la serialización de la fecha para JSON
        for c in cuentas:
            if 'fecha' in c and isinstance(c['fecha'], datetime):
                c['fecha'] = c['fecha'].isoformat()
            # Convertir None a null en JSON para campos de IDs
            if 'usuario_id' in c and c['usuario_id'] == 'None':
                c['usuario_id'] = None
            if 'cliente_id' in c and c['cliente_id'] == 'None':
                c['cliente_id'] = None
            # Si cliente_nombre está vacío o None, asignar "Sin cliente"
            if not c.get('cliente_nombre') or c['cliente_nombre'] == 'None':
                c['cliente_nombre'] = "(Sin cliente asignado)"
        print(f"DEBUG obtener_cuentas_por_cobrar -> Total de cuentas pendientes: {len(cuentas)}")
        for cuenta in cuentas:
            print(f"  Cuenta: venta_id={cuenta.get('venta_id')}, cliente={cuenta.get('cliente_nombre')}, saldo={cuenta.get('saldo_pendiente')}")
        return cuentas
    except Exception as e:
        print(f"Error al obtener cuentas por cobrar: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

def obtener_cuentas_cobradas(fecha_inicio, fecha_fin):
    """Obtiene todas las ventas pagadas en un rango de fechas."""
    try:
        pipeline = [
            {"$match": {
                "estado": "Pagada",
                "fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}
            }},
            {
                "$lookup": {
                    "from": "clientes",
                    "localField": "cliente_id",
                    "foreignField": "_id",
                    "as": "cliente_info"
                }
            },
            {"$unwind": {"path": "$cliente_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "venta_id": {"$toString": "$_id"},
                    "fecha": "$fecha",
                    "cliente_nombre": {"$ifNull": ["$cliente_info.nombre", "$temp_cliente_nombre", "(Sin cliente)"]},
                    "total": "$total"
                }
            },
            {"$sort": {"fecha": -1}}
        ]
        cuentas = list(ventas_collection.aggregate(pipeline))
        for c in cuentas:
            if 'fecha' in c and isinstance(c['fecha'], datetime):
                c['fecha'] = c['fecha'].isoformat()
        return cuentas
    except Exception as e:
        print(f"Error al obtener cuentas cobradas: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

def registrar_pago_cliente(venta_id, monto_pagado):
    """Registra un abono a una cuenta por cobrar y actualiza el estado si se salda."""
    try:
        # Usamos findOneAndUpdate para obtener el documento antes de la actualización
        venta = ventas_collection.find_one_and_update(
            {"_id": ObjectId(venta_id)},
            {"$inc": {"saldo_pendiente": -monto_pagado}},
            return_document=False # Devuelve el documento ANTES de actualizar
        )

        if not venta:
            raise Exception("Venta no encontrada.")

        nuevo_saldo = venta['saldo_pendiente'] - monto_pagado

        # Si el nuevo saldo es 0 o menos, la factura se marca como pagada
        if nuevo_saldo <= 0:
            ventas_collection.update_one(
                {"_id": ObjectId(venta_id)},
                {"$set": {"estado": "Pagada", "saldo_pendiente": 0}}
            )
    except Exception as e:
        raise e

def obtener_estadisticas():
    """Obtiene estadísticas clave de la base de datos para un dashboard."""
    try:
        if db is None:
            # En modo offline, devolver ceros para evitar errores.
            return {"total_productos": 0, "valor_inventario": 0, "ventas_hoy": 0, "productos_stock_bajo": 0}

        # Total de productos distintos
        total_productos = productos_collection.count_documents({})

        # Valor total del inventario
        pipeline_valor = [
            {"$group": {"_id": None, "valor": {"$sum": {"$multiply": ["$costo", "$stock"]}}}}
        ]
        result_valor = list(productos_collection.aggregate(pipeline_valor))
        valor_inventario = result_valor[0]["valor"] if result_valor else 0

        # Ventas de hoy
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hoy_fin = hoy_inicio + timedelta(days=1)
        pipeline_ventas = [
            {"$match": {"fecha": {"$gte": hoy_inicio, "$lt": hoy_fin}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        result_ventas = list(ventas_collection.aggregate(pipeline_ventas))
        ventas_hoy = result_ventas[0]["total"] if result_ventas else 0

        # Productos con stock bajo
        productos_stock_bajo = len(obtener_productos_stock_bajo())

        return {"total_productos": total_productos, "valor_inventario": valor_inventario, "ventas_hoy": ventas_hoy, "productos_stock_bajo": productos_stock_bajo}
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        return {"total_productos": 0, "valor_inventario": 0, "ventas_hoy": 0, "productos_stock_bajo": 0}

def obtener_datos_grafico_ventas():
    """Obtiene el total de ventas por día de los últimos 7 días."""
    try:
        # MongoDB Aggregation Pipeline
        pipeline = [
            {
                "$match": {
                    "fecha": {"$gte": datetime.now() - timedelta(days=7)}
                }
            },
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$fecha"}},
                    "total_dia": {"$sum": "$total"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        datos = list(ventas_collection.aggregate(pipeline))
        # Formatear los resultados
        resultados = [{"dia": d["_id"], "total": d["total_dia"]} for d in datos]
        return resultados
    except Exception as e:
        print(f"Error al obtener datos del gráfico: {e}")
        return []

### Funciones para el dashboard
def obtener_productos_mas_vendidos(fecha_inicio, fecha_fin):
    """
    Obtiene un ranking de productos más vendidos en un rango de fechas.
    """
    try:
        # MongoDB Aggregation Pipeline
        pipeline = [
            # Join con la colección de productos
            {
                "$lookup": {
                    "from": "productos",
                    "localField": "producto_id",
                    "foreignField": "_id",
                    "as": "producto"
                }
            },
            # Unir los resultados del lookup
            {"$unwind": "$producto"},
            # Filtrar por rango de fechas
            {
                "$match": {
                    "fecha": {"$gte": datetime.fromisoformat(fecha_inicio), "$lte": datetime.fromisoformat(fecha_fin)}
                }
            },
            # Agrupar por producto y sumar las cantidades vendidas
            {
                "$group": {
                    "_id": {"producto_id": "$producto._id", "nombre": "$producto.nombre", "codigo_barras": "$producto.codigo_barras"},
                    "total_vendido": {"$sum": "$cantidad"}
                }
            },
            # Ordenar por total vendido de forma descendente
            {"$sort": {"total_vendido": -1}},
            # Limitar a los 10 productos más vendidos
            {"$limit": 10},
            # Proyectar los resultados al formato deseado
            {
                "$project": {
                    "_id": 0,
                    "codigo_barras": "$_id.codigo_barras",
                    "nombre": "$_id.nombre",
                    "total_vendido": 1
                }
            }
        ]
        # Ejecutar el pipeline y obtener los resultados
        productos = list(ventas_detalle_collection.aggregate(pipeline))
        # Formatear los resultados
        resultados = [(p["codigo_barras"], p["nombre"], p["total_vendido"]) for p in productos]
        return resultados
    except Exception as e:
        print(f"Error al obtener productos más vendidos: {e}")
        return []

def obtener_resumen_ventas(fecha_inicio, fecha_fin):
    """Calcula el resumen de ventas (total vendido, itbis, numero de ventas) en un rango."""
    try:
        # MongoDB Aggregation Pipeline
        pipeline = [
            # Filtrar por rango de fechas
            {
                "$match": {
                    "fecha": {"$gte": datetime.fromisoformat(fecha_inicio), "$lte": datetime.fromisoformat(fecha_fin)}
                }
            },
            # Calcular los totales
            {
                "$group": {
                    "_id": None,
                    "total_vendido": {"$sum": "$total"},
                    "total_itbis": {"$sum": "$itbis"},
                    "num_ventas": {"$sum": 1}
                }
            }
        ]
        # Ejecutar el pipeline y obtener los resultados
        resumen = list(ventas_collection.aggregate(pipeline))
       # Si no hay ventas, el resultado estará vacío
        if not resumen:
            return {"total_vendido": 0, "total_itbis": 0, "num_ventas": 0}
        # Extraer los valores del resultado
        resumen = resumen[0]
        return {"total_vendido": resumen["total_vendido"], "total_itbis": resumen["total_itbis"], "num_ventas": resumen["num_ventas"]}
    except Exception as e:
        print(f"Error al obtener resumen de ventas: {e}")
        return {"total_vendido": 0, "total_itbis": 0, "num_ventas": 0}

def obtener_ventas_por_rango(fecha_inicio, fecha_fin):
    """Obtiene una lista de todas las ventas en un rango de fechas."""
    try:
        # MongoDB Aggregation Pipeline
        pipeline = [
            # Filtrar por rango de fechas
            {
                "$match": {
                    "fecha": {"$gte": datetime.fromisoformat(fecha_inicio), "$lte": datetime.fromisoformat(fecha_fin)}
                }
            },
            # Proyectar los resultados al formato deseado
            {
                "$project": {
                    "_id": 0,
                    "Factura No.": "$id",
                    "Fecha y Hora": {"$dateToString": {"format": "%Y-%m-%d %H:%M:%S", "date": "$fecha"}},
                    "Monto Total": "$total"
                }
            }
        ]
        # Ejecutar el pipeline y obtener los resultados
        ventas = list(ventas_collection.aggregate(pipeline))
        # Formatear los resultados
        resultados = [(v["Factura No."], v["Fecha y Hora"], v["Monto Total"]) for v in ventas]
        return resultados
    except Exception as e:
        print(f"Error al obtener ventas por rango: {e}")
        return []

def guardar_cotizacion(items_cotizacion, cliente_id, usuario_id='admin'):
    """Guarda una cotización en la base de datos."""
    try:
        # Calcular totales
        ITBIS_RATE = 0.18
        total_cotizacion = sum(item['cantidad'] * item['precio'] for item in items_cotizacion)
        base_imponible = total_cotizacion / (1 + ITBIS_RATE)
        itbis_incluido = total_cotizacion - base_imponible

        cotizacion = {
            "cliente_id": ObjectId(cliente_id) if cliente_id else None,
            "usuario_id": usuario_id,
            "fecha": datetime.now(),
            "total": total_cotizacion,
            "base_imponible": base_imponible,
            "itbis": itbis_incluido,
            "estado": "Guardada"
        }
        result = cotizaciones_collection.insert_one(cotizacion)
        cotizacion_id = str(result.inserted_id)

        # Guardar detalles
        for item in items_cotizacion:
            cotizaciones_detalle_collection.insert_one({
                "cotizacion_id": cotizacion_id,
                "producto_id": item['id'],
                "cantidad": item['cantidad'],
                "precio_unitario": item['precio'],
                "subtotal": item['cantidad'] * item['precio']
            })

        return cotizacion_id
    except Exception as e:
        print(f"Error al guardar cotización: {e}")
        raise e

def obtener_cotizaciones():
    """Obtiene todas las cotizaciones guardadas."""
    try:
        cotizaciones = list(cotizaciones_collection.aggregate([
            {
                "$lookup": {
                    "from": "clientes",
                    "localField": "cliente_id",
                    "foreignField": "_id",
                    "as": "cliente"
                }
            },
            {"$unwind": {"path": "$cliente", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 1,
                    "cliente": {"$ifNull": ["$cliente.nombre", "Consumidor Final"]},
                    "fecha": 1,
                    "total": 1,
                    "estado": 1
                }
            },
            {"$sort": {"fecha": -1}}
        ]))
        return cotizaciones
    except Exception as e:
        print(f"Error al obtener cotizaciones: {e}")
        return []

def obtener_cotizacion_por_id(cotizacion_id):
    """Obtiene una cotización y sus detalles por ID."""
    try:
        cotizacion = cotizaciones_collection.find_one({"_id": ObjectId(cotizacion_id)})
        detalles = list(cotizaciones_detalle_collection.aggregate([
            {"$match": {"cotizacion_id": cotizacion_id}},
            {
                "$lookup": {
                    "from": "productos",
                    "localField": "producto_id",
                    "foreignField": "_id",
                    "as": "producto"
                }
            },
            {"$unwind": "$producto"},
            {
                "$project": {
                    "_id": 0,
                    "id": "$producto._id",
                    "nombre": "$producto.nombre",
                    "precio": "$precio_unitario",
                    "cantidad": 1,
                    "subtotal": 1
                }
            }
        ]))
        for detalle in detalles:
            detalle["id"] = str(detalle["id"])

        return cotizacion, detalles
    except Exception as e:
        print(f"Error al obtener cotización: {e}")
        return None, []

def obtener_ventas_del_dia(fecha=None):
    """Obtiene todas las ventas del día específico o del día actual."""
    try:
        if fecha is None:
            fecha = datetime.now().date()
        elif isinstance(fecha, str):
            fecha = datetime.fromisoformat(fecha).date()

        inicio_dia = datetime.combine(fecha, datetime.min.time())
        fin_dia = datetime.combine(fecha, datetime.max.time())

        # Excluir ventas a crédito pendientes (estado == 'Pendiente')
        ventas = list(ventas_collection.find({
            "fecha": {"$gte": inicio_dia, "$lt": fin_dia},
            "estado": {"$ne": "Pendiente"}
        }))

        # Convertir ObjectId a string
        for venta in ventas:
            venta["id"] = str(venta["_id"])
            del venta["_id"]

        return ventas
    except Exception as e:
        print(f"Error al obtener ventas del día: {e}")
        return []

def obtener_items_venta(venta_id):
    """Obtiene los detalles de una venta específica."""
    try:
        # Buscar en la colección de detalles de venta
        detalles = list(ventas_detalle_collection.find({"venta_id": ObjectId(venta_id)}))

        items = []
        for detalle in detalles:
            producto_id = detalle.get("producto_id")
            # Obtener información del producto
            # En ventas_detalle se guarda producto_id como ObjectId
            producto = productos_collection.find_one({"_id": producto_id})
            if producto:
                items.append({
                    'cantidad': detalle.get('cantidad', 0),
                    'nombre': producto.get('nombre', 'Producto desconocido'),
                    'precio': detalle.get('precio_unitario', 0),
                    'costo': detalle.get('costo_unitario', 0),
                    'subtotal': detalle.get('cantidad', 0) * detalle.get('precio_unitario', 0)
                })

        return items
    except Exception as e:
        print(f"Error al obtener items de venta {venta_id}: {e}")
        return []

def obtener_ventas_por_periodo(inicio, fin):
    """Obtiene ventas en un rango de fechas."""
    try:
        ventas = list(ventas_collection.find({
            "fecha": {"$gte": inicio, "$lte": fin}
        }).sort("fecha", 1))

        for venta in ventas:
            venta["id"] = str(venta["_id"])
            del venta["_id"]

        return ventas
    except Exception as e:
        print(f"Error al obtener ventas por periodo: {e}")
        return []

def calcular_estadisticas_ventas(ventas):
    """Calcula estadísticas a partir de una lista de ventas."""
    if not ventas:
        return {
            "total_sales": 0,
            "total_transactions": 0,
            "avg_sale": 0,
            "total_profit": 0
        }

    total_sales = sum(v.get("total", 0) for v in ventas)
    total_transactions = len(ventas)
    avg_sale = total_sales / total_transactions if total_transactions > 0 else 0

    # Calcular utilidad aproximada (ITBIS como aproximación)
    total_itbis = sum(v.get("itbis", 0) for v in ventas)
    # Utilidad aproximada como porcentaje del ITBIS (muy simplificado)
    total_profit = total_itbis * 5  # Estimación simplificada

    return {
        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "avg_sale": avg_sale,
        "total_profit": total_profit
    }

def obtener_estadisticas_pago_ventas(ventas):
    """Obtiene estadísticas de métodos de pago."""
    metodos = {
        'Efectivo': 0,
        'Tarjeta': 0,
        'Crédito': 0,
        'Transferencia': 0
    }

    for venta in ventas:
        metodo = venta.get('tipo_pago', 'Efectivo')
        if metodo in metodos:
            metodos[metodo] += venta.get('total', 0)

    return [
        {"method": "Efectivo", "amount": metodos['Efectivo'], "percentage": (metodos['Efectivo'] / max(sum(metodos.values()), 1)) * 100},
        {"method": "Tarjeta", "amount": metodos['Tarjeta'], "percentage": (metodos['Tarjeta'] / max(sum(metodos.values()), 1)) * 100},
        {"method": "Crédito", "amount": metodos['Crédito'], "percentage": (metodos['Crédito'] / max(sum(metodos.values()), 1)) * 100},
        {"method": "Transferencia", "amount": metodos['Transferencia'], "percentage": (metodos['Transferencia'] / max(sum(metodos.values()), 1)) * 100}
    ]

def obtener_grafico_ventas(periodo, fecha=None):
    """Genera datos para gráfico de ventas según el periodo."""
    try:
        if periodo == "daily":
            # Últimas 24 horas en intervalos de hora
            if fecha is None:
                fecha = datetime.now().date()

            inicio = datetime.combine(fecha, datetime.min.time())
            fin = datetime.combine(fecha, datetime.max.time())

            labels = []
            data = []
            current = inicio
            while current <= fin:
                hora_inicio = current
                hora_fin = current + timedelta(hours=1)

                # Excluir ventas pendientes (a crédito) del total horario
                ventas_hora = list(ventas_collection.find({
                    "fecha": {"$gte": hora_inicio, "$lt": hora_fin},
                    "estado": {"$ne": "Pendiente"}
                }))

                total_hora = sum(v.get("total", 0) for v in ventas_hora)
                labels.append(hora_inicio.strftime("%H:00"))
                data.append(total_hora)

                current = hora_fin

        elif periodo == "weekly":
            # Últimos 7 días
            if fecha is None:
                fecha = datetime.now().date()

            labels = []
            data = []
            for i in range(7):
                dia = fecha - timedelta(days=6-i)
                inicio = datetime.combine(dia, datetime.min.time())
                fin = datetime.combine(dia, datetime.max.time())

                # Excluir ventas pendientes (a crédito) del total diario
                ventas_dia = list(ventas_collection.find({
                    "fecha": {"$gte": inicio, "$lte": fin},
                    "estado": {"$ne": "Pendiente"}
                }))

                total_dia = sum(v.get("total", 0) for v in ventas_dia)
                labels.append(dia.strftime("%d/%m"))
                data.append(total_dia)

        elif periodo == "monthly":
            # Mes actual por semanas
            if fecha is None:
                fecha = datetime.now().date()

            # Usar el primer día del mes como fecha
            if isinstance(fecha, str):
                fecha = datetime.fromisoformat(fecha + "-01").date()

            inicio_mes = fecha.replace(day=1)
            fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            labels = []
            data = []
            current = inicio_mes
            while current <= fin_mes:
                week_start = current
                week_end = min(week_start + timedelta(days=6), fin_mes)

                # Excluir ventas pendientes (a crédito) del total semanal
                ventas_semana = list(ventas_collection.find({
                    "fecha": {"$gte": datetime.combine(week_start, datetime.min.time()),
                             "$lte": datetime.combine(week_end, datetime.max.time())},
                    "estado": {"$ne": "Pendiente"}
                }))

                total_semana = sum(v.get("total", 0) for v in ventas_semana)
                labels.append(f"Sem {len(labels) + 1}")
                data.append(total_semana)

                if current + timedelta(days=7) > fin_mes:
                    break
                current += timedelta(days=7)

        return {"labels": labels, "data": data}
    except Exception as e:
        print(f"Error al generar gráfico: {e}")
        return {"labels": [], "data": []}

# --- FUNCIONES PARA NOTIFICACIONES EN TIEMPO REAL ---
def obtener_notificaciones_stock_bajo():
    """Obtiene notificaciones de productos con stock bajo."""
    try:
        hoy = datetime.now()
        productos_bajo = obtener_productos_stock_bajo()

        notifications = []
        for producto in productos_bajo:
            # Determinar nivel de prioridad basado en stock
            stock_actual = producto.get('stock', 0)
            stock_minimo = producto.get('stock_minimo', 0)

            if stock_actual <= 0:
                priority = 'critical'
                title = '🚨 PRODUCTO AGOTADO'
                message = f"El producto '{producto.get('nombre', 'N/A')}' está completamente agotado"
            elif stock_actual <= stock_minimo * 0.5:
                priority = 'high'
                title = '⚠️ STOCK CRÍTICO'
                message = f"Quedan solo {stock_actual} unidades del producto '{producto.get('nombre', 'N/A')}'"
            else:
                priority = 'medium'
                title = '📉 STOCK BAJO'
                message = f"Quedan {stock_actual} unidades del producto '{producto.get('nombre', 'N/A')}' (mínimo: {stock_minimo})"

            notifications.append({
                'id': f"stock_{producto.get('id', 'unknown')}",
                'type': 'low_stock',
                'title': title,
                'message': message,
                'priority': priority,
                'created_at': hoy,
                'data': {
                    'product_id': producto.get('id'),
                    'product_name': producto.get('nombre'),
                    'current_stock': stock_actual,
                    'min_stock': stock_minimo,
                    'department': producto.get('departamento')
                }
            })

        return notifications

    except Exception as e:
        print(f"Error obteniendo notificaciones de stock bajo: {e}")
        return []

def obtener_notificaciones_pagos_vencidos():
    """Obtiene notificaciones de pagos vencidos."""
    try:
        hoy = datetime.now().date()
        cuentas_por_pagar = obtener_cuentas_por_pagar()

        notifications = []
        for cuenta in cuentas_por_pagar:
            try:
                fecha_vencimiento = cuenta.get('fecha_vencimiento')
                if isinstance(fecha_vencimiento, str):
                    fecha_vencimiento = datetime.fromisoformat(fecha_vencimiento).date()
                elif isinstance(fecha_vencimiento, datetime):
                    fecha_vencimiento = fecha_vencimiento.date()

                dias_vencido = (hoy - fecha_vencimiento).days

                if dias_vencido > 0:
                    if dias_vencido >= 30:
                        priority = 'critical'
                        title = f'🔴 PAGO VENCIDO {dias_vencido} DÍAS'
                    elif dias_vencido >= 15:
                        priority = 'high'
                        title = f'🟠 PAGO VENCIDO {dias_vencido} DÍAS'
                    else:
                        priority = 'medium'
                        title = f'🟡 PAGO VENCIDO {dias_vencido} DÍAS'

                    notifications.append({
                        'id': f"payment_{cuenta.get('_id', 'unknown')}",
                        'type': 'overdue_payment',
                        'title': title,
                        'message': f"Factura de {cuenta.get('proveedor', 'Proveedor desconocido')} por RD${cuenta.get('monto', 0):.2f} vencida desde {fecha_vencimiento.strftime('%d/%m/%Y')}",
                        'priority': priority,
                        'created_at': datetime.now(),
                        'data': cuenta
                    })
            except Exception as e:
                print(f"Error procesando cuenta por pagar: {e}")
                continue

        return notifications

    except Exception as e:
        print(f"Error obteniendo notificaciones de pagos vencidos: {e}")
        return []

def obtener_notificaciones_facturas_por_vencer():
    """Obtiene notificaciones de facturas de compra próximas a vencer (ej. en 7 días)."""
    try:
        hoy = datetime.now()
        limite_vencimiento = hoy + timedelta(days=7)

        pipeline = [
            {
                "$match": {
                    "estado": "Pendiente",
                    "fecha_vencimiento": {"$gte": hoy, "$lte": limite_vencimiento}
                }
            },
            {
                "$lookup": {
                    "from": "proveedores",
                    "localField": "proveedor_id",
                    "foreignField": "_id",
                    "as": "proveedor_info"
                }
            },
            {"$unwind": {"path": "$proveedor_info", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"fecha_vencimiento": 1}}
        ]

        facturas = list(facturas_compra_collection.aggregate(pipeline))
        notifications = []
        for f in facturas:
            dias_restantes = (f['fecha_vencimiento'] - hoy).days
            notifications.append({
                'id': f"due_payment_{str(f['_id'])}",
                'type': 'due_payment',
                'title': f'⚠️ PAGO PRÓXIMO ({dias_restantes} días)',
                'message': f"Factura de {f.get('proveedor_info', {}).get('nombre', 'N/A')} por {f['moneda']}${f['monto']:.2f} vence pronto.",
                'priority': 'medium',
                'created_at': datetime.now(),
                'data': {'factura_id': str(f['_id'])}
            })
        return notifications

    except Exception as e:
        print(f"Error obteniendo notificaciones de facturas por vencer: {e}")
        return []

def obtener_notificaciones_productos_por_vencer():
    """Obtiene notificaciones de productos próximos a vencer (simulado)."""
    # Esta función simula productos con fechas de vencimiento
    # En un sistema real, tendrías una tabla de lotes/fechas de vencimiento
    try:
        notifications = []
        hoy = datetime.now().date()

        # Simular algunos productos próximos a vencer (basado en lógica de negocio)
        productos = obtener_productos()[:5]  # Solo algunos para ejemplo

        for producto in productos:
            # Simular fechas de vencimiento basadas en el ID del producto
            import hashlib
            hash_val = int(hashlib.md5(str(producto.get('id', '')).encode()).hexdigest()[:8], 16)
            dias_para_vencer = hash_val % 90  # Entre 0-90 días

            if dias_para_vencer <= 30:  # Avisar con 30 días de anticipación
                fecha_vencimiento = hoy + timedelta(days=dias_para_vencer)

                if dias_para_vencer <= 7:
                    priority = 'high'
                    title = '⚡ PRODUCTO VENCE PRONTO'
                    message = f"El lote del producto '{producto.get('nombre', 'N/A')}' vence en {dias_para_vencer} días"
                elif dias_para_vencer <= 15:
                    priority = 'medium'
                    title = '📅 PRODUCTO PRÓXIMO A VENCER'
                    message = f"El lote del producto '{producto.get('nombre', 'N/A')}' vence en {dias_para_vencer} días"
                else:
                    priority = 'low'
                    title = '📆 REVISAR FECHA DE VENCIMIENTO'
                    message = f"El lote del producto '{producto.get('nombre', 'N/A')}' vence en {dias_para_vencer} días"

                notifications.append({
                    'id': f"expiry_{producto.get('id', 'unknown')}",
                    'type': 'product_expiring',
                    'title': title,
                    'message': message,
                    'priority': priority,
                    'created_at': datetime.now(),
                    'data': {
                        'product_id': producto.get('id'),
                        'product_name': producto.get('nombre'),
                        'days_to_expiry': dias_para_vencer,
                        'expiry_date': fecha_vencimiento.isoformat()
                    }
                })

        return notifications

    except Exception as e:
        print(f"Error obteniendo notificaciones de productos por vencer: {e}")
        return []

def obtener_notificaciones_cuentas_por_cobrar_vencidas():
    """Obtiene notificaciones de cuentas por cobrar vencidas."""
    try:
        hoy = datetime.now().date()
        cuentas_por_cobrar = obtener_cuentas_por_cobrar()

        notifications = []
        for cuenta in cuentas_por_cobrar:
            # Las cuentas por cobrar ya vienen filtradas como pendientes
            # Aquí solo notificar sobre saldos pendientes con más de 30 días
            try:
                fecha_venta = cuenta.get('fecha')
                if isinstance(fecha_venta, str):
                    fecha_venta = datetime.fromisoformat(fecha_venta).date()
                elif isinstance(fecha_venta, datetime):
                    fecha_venta = fecha_venta.date()

                dias_pendiente = (hoy - fecha_venta).days

                if dias_pendiente >= 30:  # Notificar después de 30 días
                    priority = 'medium' if dias_pendiente < 60 else 'high'
                    title = f'💰 COBRO PENDIENTE ({dias_pendiente} días)'

                    notifications.append({
                        'id': f"receivable_{cuenta.get('venta_id', 'unknown')}",
                        'type': 'overdue_receivable',
                        'title': title,
                        'message': f"Pago pendiente de {cuenta.get('cliente_nombre', 'Cliente desconocido')} por RD${cuenta.get('total', 0):.2f}",
                        'priority': priority,
                        'created_at': datetime.now(),
                        'data': cuenta
                    })
            except Exception as e:
                print(f"Error procesando cuenta por cobrar: {e}")
                continue

        return notifications

    except Exception as e:
        print(f"Error obteniendo notificaciones de cuentas por cobrar: {e}")
        return []

# --- FUNCIONES PARA AUTOMATIZACIONES ---
def obtener_sugerencias_reordenamiento():
    """Obtiene sugerencias inteligentes para reordenamiento de productos."""
    try:
        hoy = datetime.now()
        sugerencias = []

        # Analizar productos con stock bajo
        productos_bajo = obtener_productos_stock_bajo()

        # Obtener todos los proveedores para mapeo rápido
        proveedores_map = {str(p['_id']): p['nombre'] for p in proveedores_collection.find({}, {"nombre": 1})}

        # Crear un pipeline para buscar el último proveedor de cada producto
        pipeline_last_purchase = [
            {"$sort": {"fecha_emision": -1}},
            {"$group": {
                "_id": "$producto_id",
                "last_supplier_id": {"$first": "$proveedor_id"}
            }}
        ]
        # Esta información no está disponible en facturas_compra, así que lo simularemos o asumiremos un proveedor por defecto.
        # Para este ejemplo, asignaremos un proveedor basado en el departamento.

        for producto in productos_bajo:
            stock_actual = producto.get('stock', 0)
            stock_minimo = producto.get('stock_minimo', 0)

            # Calcular cantidad sugerida (mínimo + 20% buffer)
            cantidad_sugerida = max(stock_minimo * 1.2, stock_minimo + 5) - stock_actual
            if cantidad_sugerida < 1:
                continue

            # Calcular urgencia basada en ventas recientes
            urgencia = 'medium'
            if stock_actual <= 0:
                urgencia = 'critical'
            elif stock_actual <= stock_minimo * 0.5:
                urgencia = 'high'

            # Simulación de proveedor basado en departamento (MEJORA A FUTURO: buscar último proveedor real)
            proveedor_nombre_simulado = "Proveedor General"
            if producto.get('departamento') == 'Plomería': proveedor_nombre_simulado = "Ferretería Americana"

            sugerencias.append({
                'id': f"suggestion_{producto.get('id')}",
                'product_id': producto.get('id'),
                'product_name': producto.get('nombre'),
                'department': producto.get('departamento'),
                'current_stock': stock_actual,
                'min_stock': stock_minimo,
                'suggested_quantity': int(cantidad_sugerida),
                'urgency': urgencia,
                'reason': f'Stock actual ({stock_actual}) por debajo del mínimo ({stock_minimo})',
                'costo': producto.get('costo', 0),
                'proveedor_sugerido': proveedor_nombre_simulado, # Dato clave añadido
                'estimated_cost': cantidad_sugerida * producto.get('costo', 0),
                'created_at': hoy.isoformat()
            })

        return sugerencias

    except Exception as e:
        print(f"Error obteniendo sugerencias de reordenamiento: {e}")
        return []

def actualizar_precios_por_porcentaje(percentage, department=None):
    """Actualiza precios de productos por porcentaje."""
    try:
        productos_afectados = 0

        if department and department != 'all':
            # Actualizar solo productos de un departamento específico
            productos = productos_collection.find({"departamento": department})
        else:
            # Actualizar todos los productos
            productos = productos_collection.find({})

        for producto in productos:
            precio_actual = producto.get('precio', 0)
            if precio_actual > 0:
                nuevo_precio = precio_actual * (1 + percentage / 100)

                productos_collection.update_one(
                    {"_id": producto["_id"]},
                    {"$set": {"precio": round(nuevo_precio, 2)}}
                )
                productos_afectados += 1

        return productos_afectados

    except Exception as e:
        print(f"Error actualizando precios por porcentaje: {e}")
        raise e

def obtener_prediccion_ventas(days):
    """Predice ventas futuras basado en datos históricos."""
    try:
        hoy = datetime.now()
        fecha_inicio = hoy - timedelta(days=days*2)  # Datos del doble del período

        # Obtener ventas del período histórico
        ventas_historicas = list(ventas_collection.find({
            "fecha": {"$gte": fecha_inicio, "$lte": hoy}
        }))

        if not ventas_historicas:
            return {"predicted_sales": 0, "confidence": 0, "message": "Sin datos históricos suficientes"}

        # Calcular promedio diario
        total_ventas_historico = sum(v.get('total', 0) for v in ventas_historicas)
        dias_datos = (hoy - fecha_inicio).days
        promedio_diario = total_ventas_historico / max(dias_datos, 1)

        # Predicción simple: multiplicar por el período solicitado
        prediccion_total = promedio_diario * days

        # Calcular confianza basada en varianza de datos históricos
        import statistics
        montos = [v.get('total', 0) for v in ventas_historicas]
        if len(montos) > 1:
            varianza = statistics.variance(montos)
            desviacion_std = statistics.sqrt(variance)
            confianza = max(0, min(100, 100 - (desviacion_std / promedio_diario * 100)))
        else:
            confianza = 50  # Confianza moderada con pocos datos

        return {
            "predicted_sales": round(prediccion_total, 2),
            "confidence": round(confianza, 1),
            "avg_daily_sales": round(promedio_diario, 2),
            "period_days": days,
            "data_points": len(ventas_historicas),
            "prediction_message": f"Se predicen RD${prediccion_total:.2f} en ventas para los próximos {days} días"
        }

    except Exception as e:
        print(f"Error obteniendo predicción de ventas: {e}")
        return {
            "predicted_sales": 0,
            "confidence": 0,
            "error": str(e)
        }

def registrar_devolucion(items_devueltos, usuario_id, razon, venta_original_id=None):
    """
    Registra una devolución, actualizando el stock de los productos.
    """
    try:
        if not db:
            raise ConnectionFailure("No hay conexión a la base de datos.")

        total_devuelto = sum(item['cantidad'] * item['precio'] for item in items_devueltos)

        devolucion = {
            "fecha": datetime.now(),
            "usuario_id": ObjectId(usuario_id),
            "venta_original_id": ObjectId(venta_original_id) if venta_original_id else None,
            "razon": razon,
            "total_devuelto": total_devuelto
        }
        result = devoluciones_collection.insert_one(devolucion)
        devolucion_id = result.inserted_id

        for item in items_devueltos:
            producto_id = item['producto_id']
            cantidad = item['cantidad']

            # Insertar detalle de la devolución
            devoluciones_detalle_collection.insert_one({
                "devolucion_id": devolucion_id,
                "producto_id": ObjectId(producto_id),
                "cantidad": cantidad,
                "precio_unitario": item['precio']
            })

            # Devolver el producto al stock
            sumar_stock_producto(producto_id, cantidad)

        return str(devolucion_id)
    except Exception as e:
        raise e

def obtener_resumen_ventas_por_metodo(fecha_inicio, fecha_fin):
    """
    Calcula el total de ventas agrupado por método de pago para un rango de fechas.
    """
    try:
        if db is None:
            raise ConnectionFailure("No hay conexión a la base de datos.")

        pipeline = [
            {
                "$match": {
                    "fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}
                }
            },
            {
                "$group": {
                    "_id": "$tipo_pago",
                    "total": {"$sum": "$total"}
                }
            }
        ]
        resultados = list(ventas_collection.aggregate(pipeline))
        
        resumen = {item['_id']: item['total'] for item in resultados}
        return resumen

    except Exception as e:
        print(f"Error al obtener resumen de ventas por método: {e}")
        return {}

def registrar_cierre_caja(datos_cierre):
    """Guarda un nuevo registro de cierre de caja en la base de datos."""
    try:
        cierres_caja_collection.insert_one(datos_cierre)
    except Exception as e:
        raise e

def sincronizar_cambios_pendientes():
    """
    Sube los cambios locales de productos/clientes a MongoDB.
    """
    print("Iniciando proceso de sincronización de cambios pendientes...")
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, modelo, id_modelo, operacion, datos FROM cambios_pendientes ORDER BY id ASC")
        cambios = cursor.fetchall()
        conn.close()

        if not cambios:
            print("No hay cambios pendientes para sincronizar.")
            return

        if not db:
            print("No hay conexión a la base de datos central para sincronizar cambios. Se reintentará más tarde.")
            return

        exitosas = 0
        for local_id, modelo, id_modelo, operacion, datos_json in cambios:
            try:
                datos = json.loads(datos_json) if datos_json else {}
                if modelo == 'producto':
                    if operacion == 'actualizar':
                        # Extraer los argumentos correctos para la función
                        args = {k: datos[k] for k in ['id_producto', 'codigo', 'nombre', 'costo', 'precio', 'stock', 'stock_minimo', 'departamento', 'unidad_medida']}
                        actualizar_producto(**args)
                    elif operacion == 'crear':
                        # El 'id' en 'datos' es temporal, lo quitamos para que Mongo genere uno nuevo
                        temp_id = datos.pop('id', None)
                        datos.pop('_id', None) # Asegurarse de que no haya _id
                        # Llamamos a la función original de agregar, que ahora solo interactúa con Mongo
                        result = productos_collection.insert_one(datos)
                        nuevo_id_mongo = str(result.inserted_id)
                        # Actualizamos el ID en la base de datos local para mantener la consistencia
                        actualizar_id_producto_local(temp_id, nuevo_id_mongo)
                        print(f"Producto local con ID temporal {temp_id} actualizado a ID de MongoDB {nuevo_id_mongo}.")
                    elif operacion == 'eliminar':
                        eliminar_producto(id_modelo)
                
                # Si no hay error, eliminar el cambio de la cola local
                conn_del = sqlite3.connect(LOCAL_DB_FILE)
                cursor_del = conn_del.cursor()
                cursor_del.execute("DELETE FROM cambios_pendientes WHERE id = ?", (local_id,))
                conn_del.commit()
                conn_del.close()
                exitosas += 1
                print(f"Cambio local ID {local_id} ({modelo} {operacion}) sincronizado exitosamente.")
            except Exception as e:
                print(f"Error al sincronizar cambio local ID {local_id}: {e}. Se reintentará más tarde.")
                continue
        print(f"Sincronización de cambios completada. {exitosas} operaciones subidas al servidor.")
    except sqlite3.Error as e:
        print(f"Error accediendo a la base de datos local para sincronización de cambios: {e}")

def sincronizar_ventas_pendientes():
    """
    Busca ventas guardadas localmente y las sube a MongoDB.
    """
    print("Iniciando proceso de sincronización de ventas pendientes...")
    try:
        conn = sqlite3.connect(LOCAL_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, datos_venta FROM ventas_pendientes ORDER BY id ASC")
        ventas_pendientes = cursor.fetchall()
        conn.close()

        if not ventas_pendientes:
            print("No hay ventas pendientes para sincronizar.")
            return

        if not db:
            print("No hay conexión a la base de datos central. Se reintentará más tarde.")
            return

        exitosas = 0
        for local_id, datos_json in ventas_pendientes:
            try:
                datos_venta = json.loads(datos_json)
                # Llamamos a la función original de registro en MongoDB
                registrar_venta(**datos_venta)
                
                # Si no hay error, la eliminamos de la cola local
                conn_del = sqlite3.connect(LOCAL_DB_FILE)
                cursor_del = conn_del.cursor()
                cursor_del.execute("DELETE FROM ventas_pendientes WHERE id = ?", (local_id,))
                conn_del.commit()
                conn_del.close()
                exitosas += 1
                print(f"Venta local ID {local_id} sincronizada exitosamente.")
            except Exception as e:
                print(f"Error al sincronizar venta local ID {local_id}: {e}. Se reintentará más tarde.")
                continue # Pasa a la siguiente venta
        print(f"Sincronización completada. {exitosas} ventas subidas al servidor.")
    except sqlite3.Error as e:
        print(f"Error accediendo a la base de datos local para sincronización: {e}")
