#!/usr/bin/env python3
"""
Script de inicialización de la base de datos Ferretería.
Ejecuta este script una vez para crear la base de datos inicial y usuario admin.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_PATH = Path(__file__).parent
sys.path.append(str(ROOT_PATH))

from database.database import inicializar_db, crear_admin_por_defecto

def main():
    print("Inicializando base de datos del Sistema Ferreteria...")

    try:
        # Inicializar la base de datos (MongoDB no requiere creación de tablas)
        inicializar_db()
        print("Base de datos inicializada.")

        # Crear usuario administrador por defecto
        crear_admin_por_defecto()
        print("Usuario administrador creado/connectado (si no existia).")

        print("\nRESUMEN DE INICIALIZACION:")
        print("   - Base de datos: Ferreteria (MongoDB Atlas)")
        print("   - Usuario por defecto: ferreteria")
        print("   - Contraseña por defecto: ferreteria123")
        print("   - IMPORTANTE: Cambia la contraseña despues del primer login!")
        print("\nInicializacion completada exitosamente!")

    except Exception as e:
        print(f"Error durante la inicializacion: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
