import pymongo
from pymongo import MongoClient
from pathlib import Path
from bson import ObjectId
from datetime import datetime, timedelta
from gui.security import hash_password, check_password

# Define la ruta del proyectoo 
ROOT_PATH = Path(__file__).parent.parent
MONGODB_URI = "mongodb+srv://JJR5:Guacamole97@cluster0.e1gxa7c.mongodb.net/?retryWrites=true&w=majority"

### MongoDB ###c
# Reemplaza con tu cadena de conexión de MongoDB Atlas
DB_NAME = "ferreteria"  # Nombre de tu base de datos

# Inicializar el cliente de MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Definir las colecciones (equivalente a tablas en SQL)
productos_collection = db["productos"]
ventas_collection = db["ventas"]
usuarios_collection = db["usuarios"]
proveedores_collection = db["proveedores"]
clientes_collection = db["clientes"] # Nueva colección para clientes
facturas_compra_collection = db["facturas_compra"]
devoluciones_collection = db["devoluciones"]
ventas_detalle_collection = db["ventas_detalle"]
devoluciones_detalle_collection = db["devoluciones_detalle"]
cotizaciones_collection = db["cotizaciones"]
cotizaciones_detalle_collection = db["cotizaciones_detalle"]

def inicializar_db():
    """
    No es necesario crear tablas explícitamente en MongoDB.
    Las colecciones se crean automáticamente al insertar el primer documento.
    """
    print("Inicialización de la base de datos (MongoDB) completada.")

def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    try:
        productos = list(productos_collection.find({}))
        # Convertir ObjectId a string para que sea serializable en JSON
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]  # Eliminar el ObjectId original para evitar errores de serialización JSON
        return productos
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return []

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
    except Exception as e:
        raise e

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
    except Exception as e:
        raise e

def eliminar_producto(id_producto):
    """Elimina un producto de la base de datos por su ID."""
    try:
        productos_collection.delete_one({"_id": ObjectId(id_producto)})  # Buscar por ObjectId
    except Exception as e:
        raise e

def buscar_producto_por_codigo(codigo):
    """Busca un producto por su código de barras."""
    try:
        producto = productos_collection.find_one({"codigo_barras": codigo})
        if producto:
            producto["id"] = str(producto["_id"])
            del producto["_id"]
        return producto
    except Exception as e:
        print(f"Error al buscar producto: {e}")
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
        productos = list(productos_collection.find(
            {"nombre": {"$regex": search_term, "$options": "i"}}  # Búsqueda insensible a mayúsculas
        ).limit(10))
        for producto in productos:
            producto["id"] = str(producto["_id"])
            del producto["_id"]  # Eliminar ObjectId para evitar errores de serialización JSON
        return productos
    except Exception as e:
        print(f"Error al buscar productos por nombre: {e}")
        return []
    
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
    except Exception as e:
        print(f"Error al obtener productos con stock bajo: {e}")
        return []

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
        clientes_collection.insert_one(cliente)
    except Exception as e:
        raise e

def obtener_clientes():
    """Obtiene todos los clientes de la base de datos."""
    try:
        clientes = list(clientes_collection.find({}))
        for cliente in clientes:
            cliente["_id"] = str(cliente["_id"])
        return clientes
    except Exception as e:
        print(f"Error al obtener clientes: {e}")
        return []

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
    except Exception as e:
        print(f"Error al buscar clientes: {e}")
        return []

def eliminar_cliente(cliente_id):
    """Elimina un cliente por su ID."""
    try:
        clientes_collection.delete_one({"_id": ObjectId(cliente_id)})
    except Exception as e:
        raise e


def buscar_venta_por_id(venta_id):
    """Busca una venta y sus detalles por su ID."""
    try:
        venta = ventas_collection.find_one({"id": venta_id})
        detalles = list(ventas_detalle_collection.find({"venta_id": venta_id}))
        return venta, detalles
    except Exception as e:
        print(f"Error al buscar venta: {e}")
        return None, None

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

def obtener_proveedores():
    """Obtiene todos los proveedores."""
    try:
        proveedores = list(proveedores_collection.find({}))
        return proveedores
    except Exception as e:
        print(f"Error al obtener proveedores: {e}")
        return []

def agregar_factura_compra(proveedor_id, num_factura, fecha_emision, fecha_vencimiento, monto, moneda):
    """Agrega una nueva factura de compra (cuenta por pagar)."""
    try:
        factura = {
            "proveedor_id": proveedor_id,
            "numero_factura": num_factura,
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "monto": monto,
            "moneda": moneda,
            "estado": "Pendiente",
        }
        facturas_compra_collection.insert_one(factura)
    except Exception as e:
        raise e

def obtener_cuentas_por_pagar():
    """Obtiene todas las facturas pendientes, uniendo con el nombre del proveedor."""
    try:
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
                "$unwind": "$proveedor"
            },
            {
                "$match": {"estado": "Pendiente"}
            },
            {
                "$project": {
                    "_id": 1,
                    "proveedor": "$proveedor.nombre",
                    "numero_factura": 1,
                    "fecha_emision": 1,
                    "fecha_vencimiento": 1,
                    "monto": 1,
                    "moneda": 1
                }
            }
        ]))
        return cuentas
    except Exception as e:
        print(f"Error al obtener cuentas por pagar: {e}")
        return []

def marcar_factura_como_pagada(factura_id):
    """Cambia el estado de una factura de compra a 'Pagada'."""
    try:
        facturas_compra_collection.update_one(
            {"_id": ObjectId(factura_id)},
            {"$set": {"estado": "Pagada"}}
        )
    except Exception as e:
        raise e

def obtener_facturas_pagadas(fecha_inicio, fecha_fin):
    """Obtiene todas las facturas pagadas en un rango de fechas, uniendo con el nombre del proveedor."""
    try:
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
                "$unwind": "$proveedor"
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
                    "fecha_vencimiento": 1,
                    "fecha_pago": 1,
                    "monto": 1,
                    "moneda": 1
                }
            }
        ]))
        return facturas
    except Exception as e:
        print(f"Error al obtener facturas pagadas: {e}")
        return []

def crear_admin_por_defecto():
    """Crea un usuario administrador por defecto si no existe ninguno."""
    try:
        if usuarios_collection.count_documents({}) == 0:
            print("No se encontraron usuarios. Creando usuario 'admin' por defecto...")
            admin_pass_hash = hash_password("admin")
            usuarios_collection.insert_one({
                "nombre_usuario": "admin",
                "hash_contrasena": admin_pass_hash,
                "rol": "Administrador"
            })
            print("Usuario 'admin' con contraseña 'admin' creado. Por favor, cámbiela.")
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

def registrar_venta(items_venta, total, itbis, descuento, usuario_id, tipo_pago, cliente_id=None):
    """
    Registra una venta completa en la base de datos, incluyendo el detalle
    y la actualización del stock de los productos.
    """
    try:
        venta = {
            "fecha": datetime.now(),
            "total": total,
            "itbis": itbis,
            "descuento": descuento,
            "usuario_id": usuario_id,
            "tipo_pago": tipo_pago,
            "cliente_id": ObjectId(cliente_id) if cliente_id else None,
            # Si es a crédito, queda pendiente. Si no, se marca como pagada.
            "estado": "Pendiente" if tipo_pago == "Crédito" else "Pagada",
            "saldo_pendiente": total if tipo_pago == "Crédito" else 0
        }
        result = ventas_collection.insert_one(venta)
        venta_id = str(result.inserted_id)

        for item in items_venta:
            producto_id = item['id']
            cantidad = item['cantidad']
            precio_unitario = item['precio']
            costo_unitario = item['costo']

            # Insertar detalle de venta
            ventas_detalle_collection.insert_one({
                "venta_id": venta_id,
                "producto_id": producto_id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "costo_unitario": costo_unitario
            })

            # Actualizar stock (¡Cuidado con condiciones de carrera!)
            productos_collection.update_one(
                {"_id": ObjectId(producto_id)},
                {"$inc": {"stock": -cantidad}}
            )

        return venta_id

    except Exception as e:
        print(f"Error al registrar la venta: {e}")
        raise e

# --- Funciones para Cuentas por Cobrar ---

def obtener_cuentas_por_cobrar():
    """Obtiene todas las ventas pendientes de pago, uniendo con el nombre del cliente."""
    try:
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
            {"$unwind": "$cliente_info"},
            {
                "$project": {
                    "venta_id": {"$toString": "$_id"},
                    "fecha": "$fecha",
                    "cliente_nombre": "$cliente_info.nombre",
                    "total": "$total",
                    "saldo_pendiente": "$saldo_pendiente"
                }
            },
            {"$sort": {"fecha": 1}} # Ordenar por las más antiguas primero
        ]
        cuentas = list(ventas_collection.aggregate(pipeline))
        return cuentas
    except Exception as e:
        print(f"Error al obtener cuentas por cobrar: {e}")
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
        # Total de productos distintos
        total_productos = productos_collection.count_documents({})

        # Valor total del inventario
        pipeline = [
            {"$group": {"_id": None, "valor": {"$sum": {"$multiply": ["$costo", "$stock"]}}}}
        ]
        result = list(productos_collection.aggregate(pipeline))
        valor_inventario = result[0]["valor"] if result else 0

        # Total de ventas realizadas
        total_ventas = ventas_collection.count_documents({})

        return {"total_productos": total_productos, "valor_inventario": valor_inventario, "total_ventas": total_ventas}
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        return {"total_productos": 0, "valor_inventario": 0, "total_ventas": 0}

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
