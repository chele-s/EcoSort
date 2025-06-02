# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# app.py - Punto de entrada para la Interfaz de Usuario y Monitoreo
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este script inicia el backend de la interfaz de usuario, que incluye
#   la API REST y el servidor SocketIO para comunicación en tiempo real.
# -----------------------------------------------------------------------------

import logging
import os
import sys

# Añadir el directorio raíz del proyecto al PYTHONPATH
# Esto permite importar módulos de otros directorios (Comunicacion, Control_Banda, IA_Clasificacion)
# de forma relativa sin necesidad de instalar el paquete completo.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) # Sube dos niveles
sys.path.append(project_root)

from InterfazUsuario_Monitoreo.Backend.api import create_api
from InterfazUsuario_Monitoreo.Backend.database import DatabaseManager

# Configurar logging básico para este módulo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ecosort_app")

if __name__ == '__main__':
    logger.info("=== Iniciando Backend de Interfaz de Usuario EcoSort Industrial ===")
    
    # Determinar la ruta de la base de datos
    # Es importante que la ruta sea consistente, especialmente si main_sistema_banda.py
    # y este app.py se ejecutan desde diferentes directorios de trabajo.
    # Usamos una ruta relativa al directorio raíz del proyecto.
    db_file_path = os.path.join(project_root, "InterfazUsuario_Monitoreo", "data", "ecosort_industrial.db")
    logger.info(f"Usando archivo de base de datos en: {db_file_path}")

    try:
        # 1. Inicializar el gestor de la base de datos
        # Asegurarse de que el directorio de la base de datos existe
        os.makedirs(os.path.dirname(db_file_path), exist_ok=True)
        database_manager = DatabaseManager(db_path=db_file_path)
        logger.info("Gestor de base de datos inicializado.")

        # 2. Crear e iniciar la API de Flask y SocketIO
        # La API necesitará la instancia del gestor de base de datos
        api_host = os.getenv('FLASK_HOST', '0.0.0.0') # Permite configurar via variable de entorno
        api_port = int(os.getenv('FLASK_PORT', 5000))
        flask_debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

        logger.info(f"Configuración de API: Host={api_host}, Puerto={api_port}, Debug={flask_debug_mode}")
        
        system_api = create_api(database_manager, host=api_host, port=api_port)
        logger.info("Instancia de API creada.")
        
        # Iniciar el servidor Flask/SocketIO
        # El método run de SystemAPI ya maneja socketio.run
        logger.info(f"Iniciando servidor API en http://{api_host}:{api_port}")
        system_api.run(debug=flask_debug_mode)
        
    except Exception as e:
        logger.critical(f"Error fatal al iniciar el backend de la interfaz: {e}", exc_info=True)
        sys.exit(1)

    logger.info("=== Backend de Interfaz de Usuario Detenido ===")
