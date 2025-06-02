# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# main_web_adapter_industrial.py - Adaptador para la Interfaz Web (Ejemplo)
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este archivo servía como un placeholder o un posible punto de entrada
#   alternativo o complementario para la interfaz de usuario y monitoreo.
#
#   En la estructura actual del proyecto, el backend principal de la interfaz
#   de usuario (API REST y WebSockets) se inicia a través de:
#       InterfazUsuario_Monitoreo/Backend/app.py
#
#   Dicho script `app.py` ya se encarga de:
#   1. Configurar el entorno (PYTHONPATH).
#   2. Inicializar el DatabaseManager.
#   3. Crear e iniciar la aplicación Flask con SocketIO (definida en api.py).
#
# ESTADO ACTUAL:
#   Este archivo (`main_web_adapter_industrial.py`) no está siendo utilizado
#   activamente en el flujo principal del sistema y se considera REDUNDANTE
#   dada la funcionalidad provista por `InterfazUsuario_Monitoreo/Backend/app.py`.
#
# POSIBLES USOS ANTERIORES O FUTUROS (Si se reestructura el proyecto):
#   - Podría haber sido un script para lanzar solo ciertos componentes de la UI.
#   - Un punto de entrada para un tipo diferente de interfaz (ej: un panel de control local sin web).
#   - Pruebas de componentes específicos de la UI o API de forma aislada.
#
# RECOMENDACIÓN:
#   - Para la funcionalidad actual, referirse y utilizar directamente:
#       `InterfazUsuario_Monitoreo/Backend/app.py`
#   - Considerar eliminar este archivo (`main_web_adapter_industrial.py`) para evitar
#     confusión, a menos que haya planes específicos para reutilizarlo con un
#     propósito claramente definido y diferente al de `app.py`.
#
# Si se decide mantenerlo para un propósito futuro, se debería documentar claramente
# ese propósito aquí.
# -----------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)

def main_web_adapter():
    """
    Función principal placeholder para el adaptador web.
    Actualmente, la funcionalidad principal está en InterfazUsuario_Monitoreo/Backend/app.py
    """
    logger.info("Iniciando main_web_adapter_industrial.py...")
    logger.warning("Este script es actualmente un placeholder y no inicia el servidor web principal.")
    logger.warning("Para iniciar la API y el backend de monitoreo, ejecute: InterfazUsuario_Monitoreo/Backend/app.py")
    
    print("---------------------------------------------------------------------")
    print("INFO: main_web_adapter_industrial.py")
    print("Este script es un PLACHOLDER y no inicia el servidor web principal.")
    print("Para la funcionalidad completa del backend de monitoreo, ejecute: ")
    print("  python InterfazUsuario_Monitoreo/Backend/app.py")
    print("---------------------------------------------------------------------")

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    main_web_adapter()
