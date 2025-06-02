# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# main_sistema_banda.py - Orquestador Principal para el Sistema de
# Clasificación de Residuos en Banda Transportadora Industrial.
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
# Este script controla el flujo completo del sistema:
# 1. Detecta objetos en la banda transportadora.
# 2. Captura imágenes de los objetos.
# 3. Utiliza un modelo de IA (YOLOV12) para clasificar los objetos.
# 4. Activa los mecanismos de desviación apropiados (controlados por PLC).
# 5. Monitorea el nivel de llenado de las tolvas de destino.
# 6. Proporciona una API para monitoreo y control remoto.
# 7. Registra datos operativos en una base de datos.
# -----------------------------------------------------------------------------

import cv2
import time
import json
import logging
import threading
import os
import RPi.GPIO as GPIO
from collections import deque
from datetime import datetime

# --- Módulos del Proyecto ---
try:
    from IA_Clasificacion.TrashDetect import TrashDetector
    from Control_Banda.RPi_control_bajo_nivel import sensor_interface as band_sensors
    from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
    from Comunicacion.rpi_plc_interface import PLCInterface
    from InterfazUsuario_Monitoreo.Backend.database import DatabaseManager
    # La API se importa y se inicia en initialize_database_and_api()
except ImportError as e:
    logging.error(f"Error importando módulos del proyecto: {e}. Asegúrate de que PYTHONPATH esté configurado y los módulos existan.")
    exit(1)

# --- Configuración Global y Carga ---
CONFIG_FILE = 'Control_Banda/config_industrial.json'
config = {}
camera = None
ai_detector = None
plc_interface = None
database = None
api_server = None # Se asigna en initialize_database_and_api
last_object_id = 0
# active_diversions: {object_id: {'thread': thread, 'activation_time': float, 'category': str, 'confidence': float}}
active_diversions = {}
# object_queue: (object_id, category_index, detection_time, confidence)
object_queue = deque()

# --- Funciones de Inicialización ---

def setup_logging():
    """Configura el sistema de logging."""
    log_level_str = config.get('logging_level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Logging configurado.")

def load_configuration():
    """Carga la configuración desde el archivo JSON."""
    global config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logging.info(f"Configuración cargada desde {CONFIG_FILE}")
    except FileNotFoundError:
        logging.error(f"Archivo de configuración {CONFIG_FILE} no encontrado. Saliendo.")
        exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Error decodificando {CONFIG_FILE}: {e}. Saliendo.")
        exit(1)

def initialize_camera():
    """Inicializa la cámara."""
    global camera
    cam_settings = config.get('camera_settings', {})
    cam_index = cam_settings.get('index', 0)
    width = cam_settings.get('frame_width', 640)
    height = cam_settings.get('frame_height', 480)

    try:
        camera = cv2.VideoCapture(cam_index)
        if not camera.isOpened():
            raise IOError(f"No se puede abrir la cámara en el índice {cam_index}")
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # camera.set(cv2.CAP_PROP_AUTOFOCUS, 0) # Considerar desactivar autofocus si causa problemas
        # camera.set(cv2.CAP_PROP_EXPOSURE, -6) # Ajustar exposición si es necesario
        logging.info(f"Cámara inicializada: Índice {cam_index}, Resolución {width}x{height}")
    except Exception as e:
        logging.error(f"Error inicializando la cámara: {e}")
        camera = None # Asegurar que la cámara es None si falla

def initialize_ai_model():
    """Inicializa el detector de IA."""
    global ai_detector
    ai_settings = config.get('ai_model_settings', {})
    model_path = ai_settings.get('model_path')
    # class_names_from_config = ai_settings.get('class_names') # Still needed for system logic
    min_confidence = ai_settings.get('min_confidence', 0.5)

    if not model_path:
        logging.error("Falta 'model_path' en la configuración de IA. Saliendo.")
        exit(1)
    
    # class_names_from_config is essential for the main system's categorization and diverter logic,
    # even if TrashDetector now loads its own names from the model file.
    # We must ensure these are defined in the config.
    if not ai_settings.get('class_names'):
        logging.error("Falta 'class_names' en la configuración de IA (`ai_model_settings`). Esta lista es crucial para la lógica del sistema. Saliendo.")
        exit(1)

    try:
        # TrashDetector now only needs model_path and min_confidence.
        # It will load its own class names from the model file.
        ai_detector = TrashDetector(model_path, min_confidence)
        logging.info(f"Modelo de IA cargado desde {model_path}.")
        logging.info(f"Clases detectables por el modelo: {ai_detector.model_class_names}")
        logging.info(f"Clases esperadas por el sistema (config): {ai_settings.get('class_names')}")

        # Sanity check: Compare model's classes with config's classes
        # This is important because the main system logic uses config['ai_model_settings']['class_names']
        # to map to diverters, database categories, etc.
        model_classes_set = set(ai_detector.model_class_names)
        config_classes_set = set(ai_settings.get('class_names'))
        
        if not model_classes_set.issuperset(config_classes_set - {'other', 'Desconocido', 'ErrorClase', 'ErrorIA'}):
            logging.warning("Algunas clases definidas en `config_industrial.json` bajo `ai_model_settings.class_names` NO están presentes en las clases que el modelo IA cargado puede detectar. Esto podría llevar a que esas categorías nunca se activen.")
            logging.warning(f"Clases en config no en modelo: {config_classes_set - model_classes_set}")

        if 'other' not in ai_settings.get('class_names'):
             logging.warning("La clase 'other' no está en `config.ai_model_settings.class_names`. Se recomienda añadirla para manejar detecciones inesperadas.")

    except FileNotFoundError:
        logging.error(f"No se encontró el archivo del modelo de IA en: {model_path}. Saliendo.")
        ai_detector = None # Ensure it's None
        exit(1)
    except Exception as e:
        logging.error(f"Error inicializando el modelo de IA: {e}")
        ai_detector = None

def initialize_plc_interface():
    """Inicializa la interfaz de comunicación con el PLC."""
    global plc_interface
    plc_settings = config.get('plc_settings', {})
    plc_ip = plc_settings.get('ip_address', '192.168.1.100')
    plc_port = plc_settings.get('port', 502)
    
    try:
        plc_interface = PLCInterface(plc_ip, plc_port)
        if plc_interface.connect():
            logging.info("Conexión con PLC establecida exitosamente")
            
            # Configurar parámetros del PLC
            # Mapear nombres de config.json a los esperados por PLCInterface.configure_plc_parameters
            plc_params_to_set = {}
            cfg_belt_settings = config.get('conveyor_belt_settings', {})

            # Para diverter_activation_time_ms_hr
            diverter_duration_ms_cfg = cfg_belt_settings.get('diverter_activation_duration_ms')
            if diverter_duration_ms_cfg is not None:
                plc_params_to_set['diverter_activation_time_ms_hr'] = int(diverter_duration_ms_cfg)
            else:
                # Fallback o valor por defecto si no está en config
                plc_params_to_set['diverter_activation_time_ms_hr'] = 500 
                logging.warning("'diverter_activation_duration_ms' no encontrada en config, usando 500ms para PLC HR.")

            # Para plc_delay_time_ms_hr (ejemplo, puede ser otro parámetro que necesites)
            # Supongamos que trigger_to_diverter_delay_ms es lo que queremos configurar como un delay general en el PLC
            trigger_delay_cfg = cfg_belt_settings.get('trigger_to_diverter_delay_ms')
            if trigger_delay_cfg is not None:
                plc_params_to_set['plc_delay_time_ms_hr'] = int(trigger_delay_cfg) 
            # else: No hay un default obvio para un "delay general" si no está definido

            # Para banda_speed_setpoint_hr (el setpoint de velocidad)
            default_speed_percent_cfg = cfg_belt_settings.get('default_speed_percent')
            if default_speed_percent_cfg is not None:
                plc_params_to_set['banda_speed_setpoint_hr'] = int(default_speed_percent_cfg)
            else:
                plc_params_to_set['banda_speed_setpoint_hr'] = 75 # Default
                logging.warning("'default_speed_percent' no encontrada en config, usando 75% para PLC HR.")

            if plc_params_to_set: # Solo configurar si hay parámetros definidos
                plc_interface.configure_plc_parameters(plc_params_to_set)
            
            # Actualizar estado en API si está disponible
            if api_server:
                api_server.update_system_state({'plc_connected': True})
                
        else:
            logging.error("No se pudo conectar al PLC")
            plc_interface = None
    except Exception as e:
        logging.error(f"Error inicializando interfaz PLC: {e}")
        plc_interface = None

def initialize_database_and_api():
    """Inicializa la base de datos y el servidor API."""
    global database, api_server
    
    try:
        # Inicializar base de datos
        database = DatabaseManager()
        logging.info("Base de datos inicializada correctamente")
        
        # Registrar evento de inicio
        database.log_system_event('startup', 'info', 'Sistema EcoSort Industrial iniciado')
        
        # Inicializar servidor API en un thread separado
        from InterfazUsuario_Monitoreo.Backend.api import create_api
        api_server = create_api(database, host='0.0.0.0', port=5000)
        
        # Ejecutar API en thread separado
        api_thread = threading.Thread(target=api_server.run, kwargs={'debug': False})
        api_thread.daemon = True
        api_thread.start()
        
        logging.info("Servidor API iniciado en puerto 5000")
        
    except Exception as e:
        logging.error(f"Error inicializando base de datos/API: {e}")
        database = None
        api_server = None

def initialize_hardware_interface():
    """Inicializa las interfaces de hardware (sensores de disparo, actuadores, etc.)."""
    logging.info("Inicializando interfaces de hardware...")
    try:
        # Configurar modo GPIO (BCM es preferido)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False) # Suprimir advertencias de canal ya en uso si se reinicia mucho

        # 1. Configurar sensores usando el módulo sensor_interface
        if not band_sensors.load_sensor_config(CONFIG_FILE):
            logging.error("Error cargando configuración de sensores")
            return False
            
        if not band_sensors.setup_sensor_gpio():
            logging.error("Error configurando GPIOs de sensores")
            return False
            
        logging.info("Sensores configurados correctamente")

        # 2. Configurar control de banda transportadora
        if config.get('conveyor_belt_settings', {}).get('control_mode') == 'plc':
            logging.info("Control de banda configurado para PLC, no se configuran GPIOs locales")
        else:
            if not belt_controller.load_belt_config(CONFIG_FILE):
                logging.error("Error cargando configuración de banda")
                return False
                
            if not belt_controller.setup_belt_gpio():
                logging.error("Error configurando GPIOs de banda")
                return False
                
            logging.info("Control de banda local configurado")

        # 3. Los actuadores de división son controlados por PLC, no necesitamos configurar GPIOs locales
        logging.info("Actuadores de división serán controlados por PLC")

        logging.info("Interfaces de hardware configuradas.")
        return True
    except Exception as e:
        logging.error(f"Error inicializando hardware: {e}")
        return False

# --- Lógica Principal del Sistema ---

def wait_for_object_trigger():
    """Espera a que el sensor de disparo detecte un objeto."""
    # Usar el módulo sensor_interface
    return band_sensors.wait_for_camera_trigger(timeout_s=None)

def capture_image():
    """Captura un frame de la cámara."""
    if camera is None or not camera.isOpened():
        logging.error("Intento de captura pero la cámara no está disponible.")
        return None
    
    ret, frame = camera.read()
    if not ret or frame is None:
        logging.error("No se pudo capturar el frame de la cámara.")
        return None
    logging.debug("Frame capturado exitosamente.")
    return frame

def classify_object(image):
    """Clasifica el objeto en la imagen usando el modelo de IA.
    Devuelve: (nombre_clase_sistema, indice_clase_sistema, confianza_deteccion)
    Donde 'nombre_clase_sistema' e 'indice_clase_sistema' se basan en config['ai_model_settings']['class_names'].
    """
    if ai_detector is None:
        logging.error("Intento de clasificación pero el modelo de IA no está disponible.")
        # Tratar de obtener el índice de ErrorIA/ErrorClase desde la config si es posible
        system_class_names = config.get('ai_model_settings', {}).get('class_names', [])
        error_label = "ErrorIA"
        error_idx = -2 # Default error index
        if error_label in system_class_names:
            error_idx = system_class_names.index(error_label)
        elif "ErrorClase" in system_class_names:
            error_label = "ErrorClase"
            error_idx = system_class_names.index(error_label)
        return error_label, error_idx, 0.0

    # detections is a list of (detected_model_class_name, confidence, box_coords)
    detections = ai_detector.detect_objects(image)
    system_class_names = config.get('ai_model_settings', {}).get('class_names', [])
    other_idx = -1 # Default for unknown/other
    other_label = "Desconocido"

    if 'other' in system_class_names:
        other_idx = system_class_names.index('other')
        other_label = 'other'
    elif 'Desconocido' in system_class_names:
        other_idx = system_class_names.index('Desconocido')
    # If neither 'other' nor 'Desconocido' are in system_class_names, other_idx remains -1 (or some other defined error index)

    if not detections:
        logging.info("No se detectaron objetos o ninguno superó el umbral de confianza.")
        return other_label, other_idx, 0.0
    
    # Tomamos la detección con la mayor confianza.
    # TrashDetector ya aplica el filtro de min_confidence general.
    best_detection = max(detections, key=lambda det: det[1])
    
    model_detected_class_name = best_detection[0]
    confidence = float(best_detection[1])
    
    # Ahora, mapeamos model_detected_class_name al class_name y class_index del *sistema*
    # (definidos en config['ai_model_settings']['class_names'])
    try:
        if model_detected_class_name in system_class_names:
            system_class_index = system_class_names.index(model_detected_class_name)
            logging.info(f"Objeto clasificado como: {model_detected_class_name} (Índice sistema: {system_class_index}, Confianza: {confidence:.2f})")
            return model_detected_class_name, system_class_index, confidence
        else:
            # La clase detectada por el modelo no está directamente en las clases principales del sistema.
            # Se mapea a 'other' o 'Desconocido' según esté definido en config.
            logging.warning(f"Clase '{model_detected_class_name}' detectada por IA (conf: {confidence:.2f}) pero no en `class_names` de config principal. Tratando como '{other_label}'.")
            return other_label, other_idx, confidence
            
    except ValueError:
        # Esto podría pasar si system_class_names está vacío o hay un error grave.
        logging.error(f"Error crítico al buscar índice para clase '{model_detected_class_name}' o '{other_label}'. Verifica `class_names` en config.")
        # Usar un índice de error genérico si está disponible en config
        error_label_cfg = "ErrorClase"
        error_idx_cfg = -2
        if error_label_cfg in system_class_names:
            error_idx_cfg = system_class_names.index(error_label_cfg)
        elif "ErrorIA" in system_class_names:
            error_label_cfg = "ErrorIA"
            error_idx_cfg = system_class_names.index(error_label_cfg)
        return error_label_cfg, error_idx_cfg, confidence
    except Exception as e:
        logging.error(f"Excepción en classify_object procesando '{model_detected_class_name}': {e}", exc_info=True)
        # Usar un índice de error genérico
        error_label_cfg = "ErrorInternoIA"
        error_idx_cfg = -2
        if error_label_cfg in system_class_names:
            error_idx_cfg = system_class_names.index(error_label_cfg)
        elif "ErrorIA" in system_class_names:
             error_label_cfg = "ErrorIA"
             error_idx_cfg = system_class_names.index(error_label_cfg)
        return error_label_cfg, error_idx_cfg, 0.0

def diversion_task(object_id, classification_id, category_name, category_index, delay_s):
    """Tarea ejecutada en un hilo para activar un desviador después de un delay."""
    global active_diversions
    
    logging.info(f"[Obj ID: {object_id}, DB ID: {classification_id}] Esperando {delay_s:.2f}s para desviar a {category_name}...")
    time.sleep(delay_s)
    
    logging.info(f"[Obj ID: {object_id}, DB ID: {classification_id}] ¡TIEMPO! Activando desviador para: {category_name} (Índice: {category_index})")
    
    plc_success = False
    plc_comm_time_start = time.time()
    error_msg = None

    if plc_interface and plc_interface.connected:
        activation_duration_ms = int(config.get('conveyor_belt_settings', {}).get('diverter_activation_duration_s', 0.5) * 1000)
        
        # Obtener el coil_address del config para la categoría específica
        diverter_settings = config.get('diverter_control_settings', {}).get('diverters', {})
        category_plc_config = diverter_settings.get(category_name.lower()) # Asegurar Búsqueda en minúsculas
        if not category_plc_config or 'plc_register_id' not in category_plc_config:
            error_msg = f"Configuración de PLC (plc_register_id) no encontrada para la categoría '{category_name}'."
            logging.error(f"[Obj ID: {object_id}, DB ID: {classification_id}] {error_msg}")
            plc_success = False
        else:
            coil_address = category_plc_config['plc_register_id']
            plc_success = plc_interface.activate_diverter(coil_address, activation_duration_ms)
        
        plc_comm_time_ms = (time.time() - plc_comm_time_start) * 1000
        
        if not plc_success:
            error_msg = f"Fallo comando PLC para {category_name}"
            logging.error(f"[Obj ID: {object_id}, DB ID: {classification_id}] {error_msg}")
    else:
        error_msg = f"PLC no conectado, no se pudo activar desviador para {category_name}"
        logging.error(f"[Obj ID: {object_id}, DB ID: {classification_id}] {error_msg}")
        plc_comm_time_ms = None

    # Actualizar registro en base de datos con el resultado de la desviación
    if database:
        database.update_classification_diversion_status(
            classification_id=classification_id,
            diverter_activated=plc_success,
            plc_response_time_ms=plc_comm_time_ms,
            error_message=error_msg
        )
        if error_msg and plc_success == False: #Solo loguear si realmente hubo error
             database.log_system_event('diversion_error', 'error', error_msg, {'object_id': object_id, 'category': category_name})

    logging.info(f"[Obj ID: {object_id}, DB ID: {classification_id}] Proceso de desviación para {category_name} completado (Éxito PLC: {plc_success}).")
    
    if object_id in active_diversions:
        del active_diversions[object_id]

def schedule_diversion(object_id, classification_id, category_index, detection_time, confidence):
    """Calcula el delay y agenda la activación del desviador en un nuevo hilo."""
    global active_diversions
    
    belt_settings = config.get('conveyor_belt_settings', {})
    belt_speed_mps = belt_settings.get('belt_speed_mps', 0.1)
    distances_m = belt_settings.get('distance_camera_to_diverters_m', {})
    
    category_name = config['ai_model_settings']['class_names'][category_index]

    # Si es "other" o no hay desviador configurado, el objeto cae al final.
    # El registro de clasificación ya se hizo, solo necesitamos actualizarlo si no hay desviación.
    if category_name.lower() == 'other' or category_name not in distances_m:
        logging.info(f"[Obj ID: {object_id}, DB ID: {classification_id}] Categoría '{category_name}' no requiere desviación.")
        if database:
            # Actualizamos la entrada existente indicando que no hubo activación de desviador
            database.update_classification_diversion_status(classification_id, diverter_activated=False)
        return

    distance_to_diverter_m = distances_m[category_name]
    
    if belt_speed_mps <= 0:
        err_msg = f"Velocidad de la banda ({belt_speed_mps} m/s) no es válida. No se puede calcular delay para Obj ID {object_id}."
        logging.error(err_msg)
        if database:
            database.update_classification_diversion_status(classification_id, diverter_activated=False, error_message=err_msg)
            database.log_system_event('system_error', 'error', err_msg)
        return

    diversion_delay_s = distance_to_diverter_m / belt_speed_mps
    
    thread = threading.Thread(target=diversion_task, 
                              args=(object_id, classification_id, category_name, category_index, diversion_delay_s))
    
    active_diversions[object_id] = {
        'thread': thread,
        'classification_id': classification_id,
        'activation_time': time.time() + diversion_delay_s,
        'category': category_name,
        'confidence': confidence
    }
    thread.start()
    logging.info(f"[Obj ID: {object_id}, DB ID: {classification_id}] Agendada desviación para '{category_name}' en {diversion_delay_s:.2f}s.")

def process_object_queue():
    """Procesa la cola de objetos detectados para agendar su desviación."""
    if object_queue:
        object_id, classification_db_id, category_index, detection_time, confidence = object_queue.popleft()
        if category_index >= 0: # Solo procesar si es una clase válida
             schedule_diversion(object_id, classification_db_id, category_index, detection_time, confidence)
        else:
            # Esto cubre casos como "Desconocido" o si el error de IA se coló (aunque no debería)
            logging.info(f"[Obj ID: {object_id}, DB ID: {classification_db_id}] Objeto no clasificado o con error, no se agenda desviación.")
            # La base de datos ya tiene la información inicial del error o "Desconocido".
            # Si es "Desconocido", se marcará diverter_activated=False en schedule_diversion.
            # Si es un error de IA, ya está marcado como error.
            # No es necesario actualizar la base de datos aquí A MENOS que queramos marcar
            # específicamente que "no se intentó desviación". Pero ya lo hace schedule_diversion para 'other'.

            # Si queremos ser explícitos para "Desconocido" que no pasa por schedule_diversion:
            if category_index == -1 and database: # -1 es "Desconocido"
                 database.update_classification_diversion_status(classification_db_id, diverter_activated=False, error_message="Objeto desconocido, sin desviación")

def check_bin_levels():
    """Verifica y reporta los niveles de llenado de las tolvas."""
    try:
        levels = band_sensors.get_all_bin_fill_levels()
        
        for bin_name, level in levels.items():
            if level is not None:
                logging.info(f"Nivel tolva {bin_name}: {level:.1f}%")
                
                # Actualizar en base de datos
                if database:
                    alert_triggered = level > config.get('bin_level_sensor_settings', {}).get('full_threshold_percent', 80.0)
                    database.update_bin_status(bin_name, level, alert_triggered=alert_triggered)
                
                # Verificar alertas
                if level > 90.0:
                    logging.warning(f"¡ALERTA CRÍTICA! Tolva {bin_name} está casi llena ({level:.1f}%)")
                    if database:
                        database.log_system_event('alert', 'critical', 
                                                f'Tolva {bin_name} al {level:.1f}% de capacidad',
                                                {'bin': bin_name, 'level': level})
                    # Notificar por API
                    if api_server:
                        api_server.update_system_state({
                            'alerts': [{'type': 'bin_full', 'bin': bin_name, 'level': level}]
                        })
                elif level > 80.0:
                    logging.warning(f"¡ALERTA! Tolva {bin_name} está llegando a su límite ({level:.1f}%)")
    except Exception as e:
        logging.error(f"Error verificando niveles de tolva: {e}")

def update_ui_stats(classification_result=None):
    """Actualiza la interfaz de usuario con estadísticas."""
    try:
        if api_server and classification_result:
            # Transmitir clasificación por WebSocket
            api_server.broadcast_classification(classification_result)
            
            # Actualizar estadísticas en tiempo real
            stats = database.get_statistics(start_time=time.time() - 3600)  # Última hora
            api_server.update_system_state({'current_stats': stats})
    except Exception as e:
        logging.error(f"Error actualizando UI: {e}")

# --- Bucle Principal y Limpieza ---
def main_loop():
    """Bucle principal de operación del sistema."""
    global last_object_id
    
    logging.info("Iniciando bucle principal del sistema de clasificación...")
    
    # Iniciar banda transportadora
    if config.get('conveyor_belt_settings', {}).get('control_mode') == 'plc':
        if plc_interface:
            default_speed = config.get('conveyor_belt_settings', {}).get('default_speed_percent', 75)
            plc_interface.start_banda(speed_percent=default_speed)
            logging.info(f"Comando de inicio de banda enviado al PLC (velocidad: {default_speed}%)")
    else:
        belt_controller.start_belt()
        logging.info("Banda transportadora iniciada localmente")
    
    # Actualizar estado del sistema
    if api_server:
        api_server.update_system_state({
            'running': True,
            'camera_active': camera is not None,
            'plc_connected': plc_interface is not None and plc_interface.connected
        })
    
    running = True
    last_bin_check_time = time.time()
    bin_check_interval = config.get('system_settings', {}).get('bin_check_interval_s', 30)
    
    try:
        while running:
            if wait_for_object_trigger(): # Espera a que un objeto active el sensor
                capture_time = time.time()
                process_start_time = time.time()
                image = capture_image()
                
                if image is not None:
                    last_object_id += 1
                    
                    # Clasificar objeto
                    classified_name, classified_index, confidence = classify_object(image)
                    process_end_time = time.time()
                    processing_time_ms = (process_end_time - process_start_time) * 1000
                    
                    if classified_index >= -2: # -1 es "Desconocido", -2 es "ErrorClase" o "ErrorIA"
                        # Registrar en base de datos primero para obtener el ID
                        classification_db_id = None
                        if database:
                            is_error = classified_index == -2
                            error_msg = classified_name if is_error else None
                            category_to_log = classified_name if classified_index != -1 else "Desconocido"
                            
                            # No marcamos diverter_activated todavía, se actualizará después.
                            classification_db_id = database.record_classification(
                                category=category_to_log,
                                confidence=confidence,
                                processing_time_ms=processing_time_ms,
                                diverter_activated=False, # Se actualizará en diversion_task
                                error_occurred=is_error,
                                error_message=error_msg
                            )
                            logging.info(f"Objeto ID {last_object_id} registrado en BD con ID: {classification_db_id}")

                        # Añadir a la cola para procesamiento de desviación
                        # Solo agendar si no es error de IA (-2) y tenemos un ID de BD
                        if classified_index != -2 and classification_db_id is not None:
                            object_queue.append((last_object_id, classification_db_id, classified_index, capture_time, confidence))
                            logging.info(f"Objeto ID {last_object_id} (Clase: {classified_name}, Confianza: {confidence:.2f}) añadido a la cola de procesamiento.")
                        elif classification_db_id is None:
                            logging.error(f"Objeto ID {last_object_id} no pudo ser registrado en la BD. No se agendará desviación.")
                        else: # Error de IA
                            logging.error(f"Objeto ID {last_object_id} tuvo un error de clasificación IA ({classified_name}). No se agendará desviación.")
                            # La BD ya lo registró como error.
                    else: # Nunca debería llegar aquí si classify_object siempre devuelve >= -2
                        logging.error(f"Objeto ID {last_object_id} recibió un índice de clase inesperado: {classified_index}")

                    # Guardar imagen si está configurado
                    if config.get('system_settings', {}).get('save_images', False):
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        image_path = f"captures/obj_{last_object_id}_{classified_name}_{timestamp}.jpg"
                        os.makedirs('captures', exist_ok=True)
                        cv2.imwrite(image_path, image)
                        logging.debug(f"Imagen guardada: {image_path}")

                    update_ui_stats(classification_result={
                        "id": last_object_id,
                        "name": classified_name, 
                        "index": classified_index,
                        "confidence": confidence,
                        "processing_time_ms": processing_time_ms
                    })

            # Procesar la cola de objetos para agendar desviaciones
            process_object_queue()
            
            # Verificar niveles de tolva periódicamente
            current_time = time.time()
            if current_time - last_bin_check_time > bin_check_interval:
                check_bin_levels()
                last_bin_check_time = current_time
            
            # Verificar estado del PLC
            if plc_interface and plc_interface.connected:
                plc_status = plc_interface.read_plc_status()
                if plc_status and plc_status.get('error_code', 0) != 0:
                    logging.error(f"Error reportado por PLC: código {plc_status['error_code']}")
                    if database:
                        database.log_system_event('plc_error', 'error', 
                                                f"Error PLC: {plc_status['error_code']}")

            # Pequeña pausa para evitar uso excesivo de CPU
            time.sleep(0.001)

    except KeyboardInterrupt:
        logging.info("Interrupción por teclado recibida. Deteniendo el sistema...")
        running = False
    except Exception as e:
        logging.error(f"Error inesperado en el bucle principal: {e}", exc_info=True)
        running = False
        if database:
            database.log_system_event('system_error', 'critical', 
                                    f'Error crítico en bucle principal: {str(e)}')
    finally:
        cleanup()

def cleanup():
    """Libera recursos al finalizar."""
    logging.info("Iniciando proceso de limpieza...")
    
    # Detener banda transportadora
    try:
        if config.get('conveyor_belt_settings', {}).get('control_mode') == 'plc':
            if plc_interface:
                plc_interface.stop_banda()
                logging.info("Comando de parada de banda enviado al PLC")
        else:
            belt_controller.stop_belt()
            logging.info("Banda transportadora detenida")
    except Exception as e:
        logging.error(f"Error deteniendo banda: {e}")
    
    # Detener hilos de desviación activos
    logging.info(f"Esperando a que terminen {len(active_diversions)} tareas de desviación activas...")
    for object_id, diversion_info in list(active_diversions.items()):
        thread = diversion_info.get('thread')
        if thread and thread.is_alive():
            logging.debug(f"Esperando al hilo del objeto ID {object_id}...")
            thread.join(timeout=2.0)
    
    # Cerrar cámara
    if camera and camera.isOpened():
        camera.release()
        logging.info("Cámara liberada.")
    
    # Desconectar PLC
    if plc_interface:
        plc_interface.disconnect()
        logging.info("Desconectado del PLC")
    
    # Registrar evento de cierre en base de datos
    if database:
        database.log_system_event('shutdown', 'info', 'Sistema EcoSort Industrial detenido correctamente')
        # Limpiar datos antiguos si está configurado
        if config.get('system_settings', {}).get('auto_cleanup', True):
            days_to_keep = config.get('system_settings', {}).get('data_retention_days', 30)
            database.cleanup_old_data(days_to_keep)
    
    # Actualizar estado del sistema en API
    if api_server:
        api_server.update_system_state({
            'running': False,
            'camera_active': False,
            'plc_connected': False
        })
    
    # Limpiar GPIOs
    band_sensors.cleanup_sensor_gpio()
    belt_controller.cleanup_belt_gpio()
    GPIO.cleanup()
    logging.info("Recursos GPIO liberados.")
    
    logging.info("Limpieza completada. Adiós.")

# --- Punto de Entrada Principal ---
if __name__ == "__main__":
    load_configuration()
    setup_logging()
    
    logging.info("=== INICIANDO SISTEMA DE CLASIFICACIÓN EN BANDA TRANSPORTADORA ===")
    logging.info("EcoSort Industrial - Sistema de Clasificación de Residuos v1.0")
    logging.info("Autores: Gabriel Calderón, Elias Bautista, Cristian Hernandez")
    logging.info("========================================================")
    
    # Inicializar base de datos y API primero
    initialize_database_and_api()
    
    # Inicializar cámara
    initialize_camera()
    
    # Inicializar modelo de IA
    initialize_ai_model()
    
    if camera is None or ai_detector is None:
        logging.critical("No se pudo inicializar la cámara o el modelo de IA. Saliendo.")
        cleanup()
        exit(1)
    
    # Inicializar interfaz de hardware
    if not initialize_hardware_interface():
        logging.critical("No se pudo inicializar la interfaz de hardware. Saliendo.")
        cleanup()
        exit(1)
    
    # Inicializar comunicación con PLC
    initialize_plc_interface()
    
    if plc_interface is None:
        logging.warning("No se pudo conectar al PLC.")
        prompt_on_fail = config.get('system_settings', {}).get('prompt_on_plc_failure', True)
        if prompt_on_fail:
            response = input("¿Desea continuar sin conexión al PLC? (s/n): ").lower()
            if response != 's':
                logging.info("Sistema detenido por el usuario.")
                cleanup()
                exit(0)
            else:
                logging.info("Continuando en modo local limitado por elección del usuario.")
        else:
            logging.warning("Continuando en modo local limitado (prompt_on_plc_failure es false).")
            # Aquí podrías añadir lógica para determinar si el modo local es viable
            # Por ejemplo, si el control de banda también es PLC y no hay fallback, sería crítico.
            if config.get('conveyor_belt_settings', {}).get('control_mode') == 'plc':
                logging.critical("El control de la banda está configurado en modo PLC y no hay conexión. No se puede continuar.")
                cleanup()
                exit(1)
    
    # Mostrar configuración del sistema
    logging.info("\n--- Configuración del Sistema ---")
    logging.info(f"Clases detectables: {config['ai_model_settings']['class_names']}")
    logging.info(f"Velocidad de banda: {config['conveyor_belt_settings']['belt_speed_mps']} m/s")
    logging.info(f"Umbral de confianza IA: {config['ai_model_settings']['min_confidence']}")
    logging.info(f"API de monitoreo en: http://localhost:5000")
    logging.info("-------------------------------\n")
    
    # Verificar niveles iniciales de tolvas
    logging.info("Verificando niveles iniciales de tolvas...")
    check_bin_levels()
    
    # Iniciar bucle principal
    main_loop()
    
    logging.info("=== SISTEMA DE CLASIFICACIÓN DETENIDO ===")
    
    # Generar reporte final si está configurado
    if config.get('system_settings', {}).get('generate_final_report', True) and database:
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = f"reports/final_report_{timestamp}.json"
            os.makedirs('reports', exist_ok=True)
            database.export_data(report_path)
            logging.info(f"Reporte final generado: {report_path}")
        except Exception as e:
            logging.error(f"Error generando reporte final: {e}")
    
    logging.info("Programa finalizado correctamente.")