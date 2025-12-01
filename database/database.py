import pymongo
from pymongo import MongoClient
from pathlib import Path
from utils.security import hash_password, check_password

# Define la ruta del proyecto
ROOT_PATH = Path(__file__).parent.parent
MONGODB_URI = "mongodb+srv://JJR5:Guacamole97@cluster0.e1gxa7c.mongodb.net/?retryWrites=true&w=majority"

### MongoDB ###
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
facturas_compra_collection = db["facturas_compra"]
devoluciones_collection = db["devoluciones"]
ventas_detalle_collection = db["ventas_detalle"]
devoluciones_detalle_collection = db["devoluciones_detalle"]

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
            del producto["_id"]
        return productos
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return []

def agregar_producto(codigo, nombre, costo, precio, stock, stock_minimo, departamento):
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
        }
        productos_collection.insert_one(producto)
    except Exception as e:
        raise e

def actualizar_producto(id_producto, codigo, nombre, costo, precio, stock, stock_minimo, departamento):
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
            del producto["_id"]
        return productos
    except Exception as e:
        print(f"Error al buscar productos por nombre: {e}")
        return []

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

def registrar_venta(items_venta, total, itbis, usuario_id):
    """
    Registra una venta completa en la base de datos, incluyendo el detalle
    y la actualización del stock de los productos.
    """
    try:
        venta = {
            "total": total,
            "itbis": itbis,
            "usuario_id": usuario_id,
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

from bson.objectid import ObjectId
from datetime import datetime, timedelta

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

def registrar_devolucion(venta_id, items_a_devolver, total_devuelto, usuario_id):
    """
    Registra una devolución, incluyendo el detalle y la actualización del stock.
    """
    try:
        devolucion = {
            "venta_id": venta_id,
            "total_devuelto": total_devuelto,
            "usuario_id": usuario_id,
            "fecha": datetime.now()
        }
        result = devoluciones_collection.insert_one(devolucion)
        devolucion_id = str(result.inserted_id)

        for item in items_a_devolver:
            producto_id = item['producto_id']
            cantidad = item['cantidad_a_devolver']

            # Insertar detalle de devolución
            devoluciones_detalle_collection.insert_one({
                "devolucion_id": devolucion_id,
                "producto_id": producto_id,
                "cantidad": cantidad
            })

            # Reingresar el producto al stock
            productos_collection.update_one(
                {"_id": ObjectId(producto_id)},
                {"$inc": {"stock": cantidad}}
            )

    except Exception as e:
        print(f"Error al registrar la devolución: {e}")
        raise e
