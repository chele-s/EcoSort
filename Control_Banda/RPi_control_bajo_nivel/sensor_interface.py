# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# sensor_interface.py - Módulo para controlar los sensores de la banda
#                       transportadora (disparo de cámara y niveles de tolva).
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este módulo maneja la inicialización y lectura de:
#   1. Un sensor de disparo para la cámara (ej: fotocelda).
#   2. Múltiples sensores ultrasónicos HC-SR04 para medir el nivel
#      de llenado de las tolvas de destino.
#   La configuración se carga desde 'config_industrial.json'.
# -----------------------------------------------------------------------------

import RPi.GPIO as GPIO
import time
import logging
import json
import os
import statistics

# Obtener logger (configurado en el script principal)
logger = logging.getLogger(__name__)

# --- Variables Globales del Módulo ---
config_data = {} # Contendrá toda la sección de sensores del config
camera_trigger_config = {}
bin_level_common_config = {}
bin_specific_configs = {} # { "CategoryName": {config_details}, ... }

# Para compensación de temperatura (si se usa)
current_temperature_c = 20.0
current_sound_speed_cm_s = 34300.0 # cm/s a 20°C

# Caché para niveles de llenado para evitar lecturas fallidas consecutivas
bin_fill_level_cache = {}

def load_sensor_config(config_file='Control_Banda/config_industrial.json'):
    """
    Carga la configuración de todos los sensores desde el archivo JSON.
    """
    global config_data, camera_trigger_config, bin_level_common_config, \
           bin_specific_configs, current_temperature_c, current_sound_speed_cm_s
    try:
        if not os.path.exists(config_file):
            logger.error(f"Archivo de configuración {config_file} no encontrado.")
            return False
        
        with open(config_file, 'r') as f:
            full_config = json.load(f)
        
        if 'sensors_settings' not in full_config:
            logger.error("'sensors_settings' no encontrado en el archivo de configuración.")
            return False
            
        config_data = full_config['sensors_settings']
        
        # Cargar configuración del sensor de disparo de cámara
        camera_trigger_config = config_data.get('camera_trigger_sensor', {})
        if not camera_trigger_config.get('pin_bcm'):
            logger.warning("No se especificó 'pin_bcm' para 'camera_trigger_sensor'. Funcionalidad limitada.")
        else:
            logger.info(f"Configuración de sensor de disparo de cámara cargada: {camera_trigger_config}")

        # Cargar configuración de sensores de nivel de tolva
        bin_sensors_config = config_data.get('bin_level_sensors', {})
        bin_level_common_config = bin_sensors_config.get('settings_common', {
            # Valores por defecto si no están en config
            "sound_speed_cm_s": 34300,
            "readings_per_measurement": 3,
            "measurement_timeout_s": 0.1, # Timeout más corto para HC-SR04
            "reading_interval_s": 0.05,
            "use_temperature_compensation": False,
            "default_temperature_c": 20.0
        })
        current_temperature_c = bin_level_common_config.get("default_temperature_c", 20.0)
        if bin_level_common_config.get("use_temperature_compensation", False):
            current_sound_speed_cm_s = _calculate_sound_speed_with_temp(current_temperature_c)
        else:
            current_sound_speed_cm_s = bin_level_common_config.get("sound_speed_cm_s", 34300)

        bin_specific_configs = bin_sensors_config.get('bins', {})
        if not bin_specific_configs:
            logger.warning("No se encontraron configuraciones específicas para 'bins' en 'bin_level_sensors'.")
        else:
            for bin_name, s_config in bin_specific_configs.items():
                # Heredar/validar parámetros comunes
                for key, val in bin_level_common_config.items():
                    if key not in s_config: # Si no está en la config específica, no lo añadimos aquí
                                            # se usará el común al leer.
                        pass
                logger.info(f"Configuración de sensor de nivel para tolva '{bin_name}' cargada.")
        
        logger.info("Configuración de sensores cargada exitosamente.")
        return True

    except Exception as e:
        logger.error(f"Error cargando la configuración de sensores: {e}", exc_info=True)
        return False

def setup_sensor_gpio():
    """
    Configura los pines GPIO para todos los sensores definidos.
    Debe llamarse después de load_sensor_config().
    """
    if not config_data: # Verifica si config_data tiene algo
        logger.error("Configuración de sensores no cargada. Ejecute load_sensor_config() primero.")
        return False
    
    try:
        # Asumiendo que GPIO.setmode(GPIO.BCM) se llama en el script principal
        # GPIO.setwarnings(False)

        # Configurar sensor de disparo de cámara
        if camera_trigger_config.get('pin_bcm') is not None:
            pin = camera_trigger_config['pin_bcm']
            pull_up_down_str = camera_trigger_config.get('pull_up_down', None)
            pud = GPIO.PUD_OFF
            if pull_up_down_str == "PUD_UP":
                pud = GPIO.PUD_UP
            elif pull_up_down_str == "PUD_DOWN":
                pud = GPIO.PUD_DOWN
            
            GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
            logger.info(f"GPIO {pin} (Sensor Disparo Cámara) configurado como ENTRADA (pull: {pull_up_down_str}).")

        # Configurar sensores de nivel de tolva (HC-SR04)
        for bin_name, s_config in bin_specific_configs.items():
            trig_pin = s_config.get('trig_pin_bcm')
            echo_pin = s_config.get('echo_pin_bcm')
            if trig_pin is not None and echo_pin is not None:
                GPIO.setup(trig_pin, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(echo_pin, GPIO.IN)
                logger.info(f"GPIOs para sensor de nivel tolva '{bin_name}' (TRIG={trig_pin}, ECHO={echo_pin}) configurados.")
            else:
                logger.warning(f"Pines TRIG/ECHO no definidos para sensor de tolva '{bin_name}'.")
        
        logger.info("Todos los GPIOs de sensores configurados.")
        # Pequeña pausa para estabilización de sensores ultrasónicos si es necesario
        time.sleep(bin_level_common_config.get("stabilization_time_s", 0.2))
        return True
    except Exception as e:
        logger.error(f"Error configurando GPIOs para sensores: {e}", exc_info=True)
        return False

# --- Funciones para Sensor de Disparo de Cámara ---

def check_camera_trigger():
    """
    Verifica el estado actual del sensor de disparo de la cámara.
    Devuelve True si está activado, False en caso contrario.
    """
    pin = camera_trigger_config.get('pin_bcm')
    if pin is None:
        # logger.debug("Sensor de disparo de cámara no configurado, devolviendo False.")
        return False # O lanzar excepción, o manejar de otra forma

    trigger_on = camera_trigger_config.get('trigger_on_state', 'LOW')
    current_state = GPIO.input(pin)

    if trigger_on == 'LOW':
        return current_state == GPIO.LOW
    else: # trigger_on == 'HIGH'
        return current_state == GPIO.HIGH

def wait_for_camera_trigger(timeout_s=None):
    """
    Espera (bloqueante) hasta que el sensor de disparo de la cámara se active
    o hasta que se alcance el timeout.
    Devuelve True si se activó, False si hubo timeout.
    """
    pin = camera_trigger_config.get('pin_bcm')
    if pin is None:
        logger.warning("Sensor de disparo de cámara no configurado. Simulará activación tras input.")
        input("Presiona Enter para simular disparo de cámara...")
        return True
    
    trigger_on_level = GPIO.LOW if camera_trigger_config.get('trigger_on_state', 'LOW') == 'LOW' else GPIO.HIGH
    debounce_s = camera_trigger_config.get('debounce_s', 0.05)
    
    logger.debug(f"Esperando disparo de cámara en GPIO {pin} (activación en {camera_trigger_config.get('trigger_on_state', 'LOW')})...")
    
    start_time = time.time()
    while True:
        if GPIO.input(pin) == trigger_on_level:
            time.sleep(debounce_s) # Anti-rebote
            if GPIO.input(pin) == trigger_on_level: # Confirmar después del debounce
                logger.info(f"Disparo de cámara detectado en GPIO {pin}.")
                return True
        
        if timeout_s is not None and (time.time() - start_time) > timeout_s:
            logger.debug(f"Timeout esperando disparo de cámara en GPIO {pin}.")
            return False
        
        time.sleep(0.005) # Pequeña pausa para no saturar CPU

# --- Funciones para Sensores de Nivel de Tolva (Ultrasónicos HC-SR04) ---

def _calculate_sound_speed_with_temp(temperature_c):
    """Calcula la velocidad del sonido ajustada por temperatura (cm/s)."""
    return (331.3 + 0.606 * temperature_c) * 100

def set_current_temperature(temperature_c):
    """Actualiza la temperatura ambiente y recalcula la velocidad del sonido si la compensación está activa."""
    global current_temperature_c, current_sound_speed_cm_s
    current_temperature_c = temperature_c
    if bin_level_common_config.get("use_temperature_compensation", False):
        current_sound_speed_cm_s = _calculate_sound_speed_with_temp(temperature_c)
        logger.info(f"Temperatura actualizada a {temperature_c}°C. Nueva velocidad del sonido: {current_sound_speed_cm_s:.2f} cm/s.")
    else:
        logger.debug("Compensación de temperatura desactivada, `set_current_temperature` no cambia la velocidad del sonido.")

def _get_distance_cm_ultrasonic(trig_pin, echo_pin, retries=1):
    """Mide la distancia para un sensor ultrasónico específico."""
    timeout = bin_level_common_config.get("measurement_timeout_s", 0.1)
    
    for attempt in range(retries + 1):
        try:
            GPIO.output(trig_pin, GPIO.LOW)
            time.sleep(0.000002) # 2µs de pausa antes del pulso

            GPIO.output(trig_pin, GPIO.HIGH)
            time.sleep(0.00001) # Pulso TRIG de 10µs
            GPIO.output(trig_pin, GPIO.LOW)

            pulse_start_time = time.time()
            loop_start_time = pulse_start_time

            while GPIO.input(echo_pin) == GPIO.LOW:
                pulse_start_time = time.time()
                if pulse_start_time - loop_start_time > timeout:
                    if attempt < retries: continue
                    # logger.debug(f"Timeout (TRIG={trig_pin},ECHO={echo_pin}): No se detectó inicio de pulso ECHO.")
                    return None
            
            pulse_end_time = time.time()
            loop_start_time = pulse_end_time
            while GPIO.input(echo_pin) == GPIO.HIGH:
                pulse_end_time = time.time()
                if pulse_end_time - loop_start_time > timeout: # El pulso ECHO no debería ser tan largo
                    if attempt < retries: continue
                    # logger.debug(f"Timeout (TRIG={trig_pin},ECHO={echo_pin}): Pulso ECHO demasiado largo.")
                    return None # O un valor muy pequeño si se asume objeto muy cerca

            if pulse_start_time and pulse_end_time > pulse_start_time:
                pulse_duration = pulse_end_time - pulse_start_time
                distance = (pulse_duration * current_sound_speed_cm_s) / 2
                return distance
            # else:
                # logger.debug(f"Error en tiempos de pulso para TRIG={trig_pin}, ECHO={echo_pin}")

        except RuntimeError as e: # Captura errores si GPIO no está configurado, etc.
            logger.error(f"RuntimeError midiendo distancia (TRIG={trig_pin},ECHO={echo_pin}): {e}")
            return None # Importante devolver None para que no falle el promedio
        except Exception as e:
            logger.error(f"Excepción midiendo distancia (TRIG={trig_pin},ECHO={echo_pin}): {e}", exc_info=False) # Poner True para debug
            # No reintentar en excepciones generales, podría ser un problema de configuración
            return None
        
        if attempt < retries:
            time.sleep(0.01) # Pequeña pausa entre reintentos

    return None # Todos los intentos fallaron

def _get_avg_distance_ultrasonic(trig_pin, echo_pin):
    """Obtiene un promedio (mediana) de múltiples lecturas de distancia."""
    num_readings = bin_level_common_config.get("readings_per_measurement", 3)
    reading_interval = bin_level_common_config.get("reading_interval_s", 0.05)
    readings = []
    
    for _ in range(num_readings):
        dist = _get_distance_cm_ultrasonic(trig_pin, echo_pin, retries=0) # Reintentos ya en _get_distance_cm_ultrasonic
        if dist is not None:
            readings.append(dist)
        if num_readings > 1 : time.sleep(reading_interval)
            
    if not readings:
        return None
    
    if len(readings) >= 3: # Usar mediana si hay suficientes datos para robustez
        return statistics.median(readings)
    else: # Promedio simple para menos de 3 lecturas válidas
        return sum(readings) / len(readings)

def _calculate_fill_percentage(distance_cm, bin_depth_cm_val):
    """Calcula el porcentaje de llenado a partir de la distancia medida."""
    if distance_cm is None or bin_depth_cm_val <= 0:
        return None
        
    # Distancia es desde el sensor hasta el contenido.
    # Espacio lleno = Profundidad total - distancia medida (espacio vacío)
    filled_space = bin_depth_cm_val - distance_cm
    
    # Asegurar que el espacio lleno no sea negativo (objeto más allá del fondo)
    # o mayor que la profundidad (sensor reporta algo muy cerca/error)
    filled_space = max(0, min(filled_space, bin_depth_cm_val))
    
    fill_percentage = (filled_space / bin_depth_cm_val) * 100
    return round(max(0, min(100, fill_percentage)), 1)


def get_bin_fill_level(category_name):
    """
    Obtiene el nivel de llenado (0-100%) para una tolva específica.
    Devuelve el valor de caché si la lectura actual falla.
    """
    global bin_fill_level_cache
    if category_name not in bin_specific_configs:
        logger.warning(f"No hay configuración de sensor de nivel para la tolva '{category_name}'.")
        return None

    s_config = bin_specific_configs[category_name]
    trig_pin = s_config.get('trig_pin_bcm')
    echo_pin = s_config.get('echo_pin_bcm')
    depth = s_config.get('bin_depth_cm', bin_level_common_config.get('bin_depth_cm', 50.0)) # Usa específico o común

    if trig_pin is None or echo_pin is None:
        logger.error(f"Pines TRIG/ECHO no configurados para tolva '{category_name}'.")
        return bin_fill_level_cache.get(category_name) # Devuelve caché si existe

    distance = _get_avg_distance_ultrasonic(trig_pin, echo_pin)
    fill_percentage = _calculate_fill_percentage(distance, depth)

    if fill_percentage is not None:
        bin_fill_level_cache[category_name] = fill_percentage # Actualizar caché
        logger.debug(f"Nivel tolva '{category_name}': {fill_percentage}% (Dist: {distance:.1f}cm)")
        return fill_percentage
    else:
        logger.warning(f"Fallo al leer sensor de nivel para tolva '{category_name}'. Usando valor de caché si existe.")
        return bin_fill_level_cache.get(category_name) # Devuelve el último valor bueno

def get_all_bin_fill_levels():
    """Obtiene el nivel de llenado para todas las tolvas configuradas."""
    levels = {}
    for bin_name in bin_specific_configs.keys():
        levels[bin_name] = get_bin_fill_level(bin_name)
    return levels

def cleanup_sensor_gpio():
    """Libera los recursos GPIO utilizados por los sensores."""
    logger.info("Limpiando GPIOs de los sensores...")
    # La limpieza general de GPIO.cleanup() en main_sistema_banda.py
    # se encargará de todos los pines. Este módulo no necesita llamar
    # a GPIO.cleanup() por sí mismo si es parte de un sistema más grande.
    logger.info("Limpieza de GPIOs de sensores completada (no se requiere acción específica aquí si se limpia en main).")

# --- Código de Prueba ---
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    TEST_CONFIG_FILE_SENSORS = 'config_industrial_sensors_test.json'
    if not os.path.exists(TEST_CONFIG_FILE_SENSORS):
        logger.info(f"Creando archivo de config de prueba para sensores: {TEST_CONFIG_FILE_SENSORS}")
        test_sensor_cfg_content = {
            "sensors_settings": {
                "camera_trigger_sensor": {
                    "pin_bcm": 17, # Ejemplo, ajusta a un pin libre
                    "trigger_on_state": "LOW",
                    "pull_up_down": "PUD_UP",
                    "debounce_s": 0.1
                },
                "bin_level_sensors": {
                    "settings_common": {
                        "sound_speed_cm_s": 34300,
                        "readings_per_measurement": 5,
                        "measurement_timeout_s": 0.1,
                        "reading_interval_s": 0.05,
                        "use_temperature_compensation": True,
                        "default_temperature_c": 22.5,
                        "stabilization_time_s": 0.2
                    },
                    "bins": {
                        "Metal": { # Asegúrate que estos pines estén libres y conectados a un HC-SR04
                            "trig_pin_bcm": 23,
                            "echo_pin_bcm": 24,
                            "bin_depth_cm": 50.0
                        },
                        "Plastic": {
                            "trig_pin_bcm": 25, # Ejemplo, ajusta
                            "echo_pin_bcm": 8,  # Ejemplo, ajusta
                            "bin_depth_cm": 40.0
                        }
                    }
                }
            }
        }
        with open(TEST_CONFIG_FILE_SENSORS, 'w') as f:
            json.dump(test_sensor_cfg_content, f, indent=4)
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        if load_sensor_config(config_file=TEST_CONFIG_FILE_SENSORS):
            if setup_sensor_gpio():
                logger.info("=== Prueba de Interfaz de Sensores ===")
                
                # Probar sensor de disparo de cámara
                logger.info("\n--- Probando Sensor de Disparo de Cámara ---")
                logger.info(f"Por favor, activa el sensor en GPIO {camera_trigger_config.get('pin_bcm')}...")
                if wait_for_camera_trigger(timeout_s=10.0):
                    logger.info("¡Sensor de disparo de cámara FUNCIONA!")
                else:
                    logger.warning("Sensor de disparo de cámara NO detectado o timeout.")
                logger.info(f"Estado actual del trigger: {check_camera_trigger()}")
                time.sleep(1)

                # Probar sensores de nivel de tolva
                logger.info("\n--- Probando Sensores de Nivel de Tolva ---")
                if bin_specific_configs:
                    set_current_temperature(25.0) # Probar cambio de temperatura
                    
                    for i in range(3): # Leer varias veces
                        levels = get_all_bin_fill_levels()
                        for bin_name, level in levels.items():
                            if level is not None:
                                logger.info(f"Lectura {i+1}: Nivel tolva '{bin_name}': {level:.1f}%")
                            else:
                                logger.warning(f"Lectura {i+1}: No se pudo leer el nivel para tolva '{bin_name}'.")
                        time.sleep(1)
                else:
                    logger.info("No hay sensores de nivel de tolva configurados para probar.")
            else:
                logger.error("Fallo al configurar GPIOs para sensores.")
        else:
            logger.error("Fallo al cargar la configuración de sensores.")

    except KeyboardInterrupt:
        logger.info("Prueba interrumpida por el usuario.")
    except Exception as e:
        logger.error(f"Error durante la prueba de sensores: {e}", exc_info=True)
    finally:
        logger.info("Limpiando GPIO al final de la prueba de sensores...")
        cleanup_sensor_gpio()
        GPIO.cleanup() # Limpieza final de todos los canales
        logger.info("=== Prueba de Sensores Finalizada ===")
