import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
ROOT_PATH = Path(__file__).parent
sys.path.append(str(ROOT_PATH))

from gui.app import App
from database.database import inicializar_db, crear_admin_por_defecto

if __name__ == "__main__":
    # 1. Asegurarse de que la base de datos y sus tablas existan
    inicializar_db()

    # 2. Crear un usuario admin si la base de datos está vacía
    crear_admin_por_defecto()

    # 3. Iniciar la aplicación de interfaz gráfica
    app = App()
    app.mainloop()