# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# conveyor_belt_controller.py - Módulo para controlar la banda transportadora.
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este módulo maneja la inicialización y operación del motor de la
#   banda transportadora. Puede operar en modo simple ON/OFF o,
#   opcionalmente, con control de velocidad PWM si el hardware lo permite.
#   La configuración se carga desde 'config_industrial.json'.
# -----------------------------------------------------------------------------

import RPi.GPIO as GPIO
import time
import logging
import json
import os

# Obtener logger (configurado en el script principal)
logger = logging.getLogger(__name__)

# --- Variables Globales del Módulo ---
belt_config = {}
# Ejemplo de config:
# "conveyor_belt_settings": {
#     "control_type": "gpio_on_off", // "gpio_on_off" o "pwm_dc_motor"
#     "motor_pin_bcm": 26,          // Pin para ON/OFF o pin PWM para velocidad
#     "enable_pin_bcm": null,       // Opcional: Pin de habilitación separado para el driver
#     "direction_pin_bcm": null,    // Opcional: Pin de dirección si el motor lo requiere
#     "active_state_on": "HIGH",    // Para gpio_on_off: HIGH o LOW para encender
#     "pwm_frequency_hz": 100,      // Para pwm_dc_motor
#     "min_duty_cycle": 20,         // Para pwm_dc_motor (0-100)
#     "max_duty_cycle": 100,        // Para pwm_dc_motor (0-100)
#     "default_speed_percent": 75   // Velocidad por defecto si es PWM (0-100)
# }
pwm_instance = None
is_running = False
current_speed_percent = 0 # 0-100

def load_belt_config(config_file='Control_Banda/config_industrial.json'):
    """
    Carga la configuración de la banda transportadora desde el archivo JSON.
    """
    global belt_config
    try:
        if not os.path.exists(config_file):
            logger.error(f"Archivo de configuración {config_file} no encontrado.")
            return False
        
        with open(config_file, 'r') as f:
            full_config = json.load(f)
        
        if 'conveyor_belt_settings' not in full_config:
            logger.error("'conveyor_belt_settings' no encontrado en el archivo de configuración.")
            return False
            
        belt_config = full_config['conveyor_belt_settings']
        logger.info(f"Configuración de la banda transportadora cargada: {belt_config}")
        return True

    except Exception as e:
        logger.error(f"Error cargando la configuración de la banda: {e}", exc_info=True)
        return False

def setup_belt_gpio():
    """
    Configura los pines GPIO para el control de la banda.
    Debe llamarse después de load_belt_config().
    """
    global pwm_instance, current_speed_percent
    if not belt_config:
        logger.error("Configuración de la banda no cargada. Ejecute load_belt_config() primero.")
        return False
    
    try:
        # Asumiendo que GPIO.setmode(GPIO.BCM) se llama en el script principal
        # GPIO.setwarnings(False)

        control_type = belt_config.get("control_type", "gpio_on_off")
        motor_pin = belt_config.get("motor_pin_bcm")
        enable_pin = belt_config.get("enable_pin_bcm")
        direction_pin = belt_config.get("direction_pin_bcm")

        if motor_pin is None and control_type != "external_plc": # external_plc no necesitaría pines directos
            logger.error("No se especificó 'motor_pin_bcm' en la configuración de la banda.")
            return False

        if enable_pin is not None:
            GPIO.setup(enable_pin, GPIO.OUT)
            GPIO.output(enable_pin, GPIO.LOW) # Asumir que LOW deshabilita o es estado seguro inicial
            logger.info(f"Pin ENABLE de la banda configurado en GPIO {enable_pin} y puesto en BAJO.")

        if direction_pin is not None:
            GPIO.setup(direction_pin, GPIO.OUT)
            # Establecer una dirección por defecto si es necesario, ej: GPIO.LOW
            # GPIO.output(direction_pin, GPIO.LOW) 
            logger.info(f"Pin DIRECTION de la banda configurado en GPIO {direction_pin}.")

        if control_type == "gpio_on_off":
            if motor_pin is not None:
                GPIO.setup(motor_pin, GPIO.OUT)
                initial_state = GPIO.LOW if belt_config.get('active_state_on', 'HIGH') == 'HIGH' else GPIO.HIGH
                GPIO.output(motor_pin, initial_state) # Asegurar que esté apagado inicialmente
                logger.info(f"Banda (ON/OFF) configurada en GPIO {motor_pin}. Estado inicial: APAGADO.")
        
        elif control_type == "pwm_dc_motor":
            if motor_pin is not None:
                freq = belt_config.get("pwm_frequency_hz", 100)
                GPIO.setup(motor_pin, GPIO.OUT)
                pwm_instance = GPIO.PWM(motor_pin, freq)
                pwm_instance.start(0) # Iniciar con duty cycle 0 (apagado)
                current_speed_percent = 0
                logger.info(f"Banda (PWM) configurada en GPIO {motor_pin} con frecuencia {freq}Hz.")
            else:
                logger.error("Tipo de control PWM seleccionado pero 'motor_pin_bcm' no especificado.")
                return False
        elif control_type == "external_plc":
            logger.info("Control de banda configurado para 'external_plc'. No se configuran GPIOs directos para el motor.")
        else:
            logger.error(f"Tipo de control de banda desconocido: {control_type}")
            return False
            
        logger.info("GPIOs para la banda transportadora configurados.")
        return True
        
    except Exception as e:
        logger.error(f"Error configurando GPIOs para la banda: {e}", exc_info=True)
        return False

def start_belt(speed_percent=None):
    """
    Enciende el motor de la banda transportadora.
    Si el control es PWM, se puede especificar una velocidad.
    """
    global is_running, current_speed_percent
    if not belt_config:
        logger.error("Configuración de la banda no cargada.")
        return False

    control_type = belt_config.get("control_type", "gpio_on_off")
    motor_pin = belt_config.get("motor_pin_bcm")
    enable_pin = belt_config.get("enable_pin_bcm")
    
    logger.info("Intentando encender la banda transportadora...")

    # Habilitar driver si existe un pin de enable
    if enable_pin is not None:
        GPIO.output(enable_pin, GPIO.HIGH) # Asumir que HIGH habilita
        logger.debug(f"Pin ENABLE (GPIO {enable_pin}) puesto en ALTO.")
        time.sleep(0.01) # Pequeña pausa para el driver

    if control_type == "gpio_on_off":
        if motor_pin is not None:
            active_level = GPIO.HIGH if belt_config.get('active_state_on', 'HIGH') == 'HIGH' else GPIO.LOW
            GPIO.output(motor_pin, active_level)
            is_running = True
            current_speed_percent = 100 # Asumir máxima velocidad para on/off
            logger.info(f"Banda (ON/OFF) encendida. GPIO {motor_pin} a {belt_config.get('active_state_on')}.")
            return True
    
    elif control_type == "pwm_dc_motor":
        if pwm_instance:
            target_speed = speed_percent if speed_percent is not None else belt_config.get("default_speed_percent", 75)
            min_dc = belt_config.get("min_duty_cycle", 0) # Permitir 0 para detener completamente
            max_dc = belt_config.get("max_duty_cycle", 100)
            
            # Mapear porcentaje de velocidad (0-100) a duty cycle (min_dc - max_dc)
            if target_speed == 0:
                actual_duty_cycle = 0
            else:
                actual_duty_cycle = min_dc + (target_speed / 100.0) * (max_dc - min_dc)
            
            actual_duty_cycle = max(0, min(100, actual_duty_cycle)) # Asegurar que esté entre 0 y 100

            pwm_instance.ChangeDutyCycle(actual_duty_cycle)
            is_running = actual_duty_cycle > 0
            current_speed_percent = target_speed if is_running else 0
            logger.info(f"Banda (PWM) encendida a {target_speed}% velocidad ({actual_duty_cycle:.1f}% duty cycle).")
            return True
    
    logger.warning("No se pudo encender la banda, configuración o tipo de control no válidos (asegúrate que no sea 'external_plc').")
    return False

def stop_belt():
    """Detiene el motor de la banda transportadora."""
    global is_running, current_speed_percent
    if not belt_config:
        logger.error("Configuración de la banda no cargada.")
        return False

    control_type = belt_config.get("control_type", "gpio_on_off")
    motor_pin = belt_config.get("motor_pin_bcm")
    enable_pin = belt_config.get("enable_pin_bcm")

    logger.info("Intentando detener la banda transportadora...")

    if control_type == "gpio_on_off":
        if motor_pin is not None:
            inactive_level = GPIO.LOW if belt_config.get('active_state_on', 'HIGH') == 'HIGH' else GPIO.HIGH
            GPIO.output(motor_pin, inactive_level)
    
    elif control_type == "pwm_dc_motor":
        if pwm_instance:
            pwm_instance.ChangeDutyCycle(0)
            
    # Deshabilitar driver si existe un pin de enable
    if enable_pin is not None:
        GPIO.output(enable_pin, GPIO.LOW) # Asumir que LOW deshabilita
        logger.debug(f"Pin ENABLE (GPIO {enable_pin}) puesto en BAJO.")

    is_running = False
    current_speed_percent = 0
    logger.info("Banda detenida.")
    return True

def set_belt_speed(speed_percent):
    """
    Establece la velocidad de la banda si el control es PWM.
    speed_percent: 0-100
    """
    global current_speed_percent, is_running
    if belt_config.get("control_type") != "pwm_dc_motor":
        logger.warning("Control de velocidad solo disponible para 'pwm_dc_motor'.")
        return False
    
    if not pwm_instance:
        logger.error("Instancia PWM no inicializada.")
        return False

    min_dc = belt_config.get("min_duty_cycle", 0)
    max_dc = belt_config.get("max_duty_cycle", 100)
    
    if speed_percent == 0:
        actual_duty_cycle = 0
    else:
        actual_duty_cycle = min_dc + (speed_percent / 100.0) * (max_dc - min_dc)
    
    actual_duty_cycle = max(0, min(100, actual_duty_cycle))

    pwm_instance.ChangeDutyCycle(actual_duty_cycle)
    current_speed_percent = speed_percent
    is_running = actual_duty_cycle > 0
    logger.info(f"Velocidad de la banda (PWM) ajustada a {speed_percent}% ({actual_duty_cycle:.1f}% duty cycle).")
    return True

def get_belt_status():
    """Devuelve el estado actual de la banda."""
    return {"is_running": is_running, "speed_percent": current_speed_percent}

def cleanup_belt_gpio():
    """Libera los recursos GPIO utilizados por el control de la banda."""
    logger.info("Limpiando GPIOs de la banda transportadora...")
    if is_running:
        stop_belt() # Intentar detener la banda antes de limpiar
        time.sleep(0.1) # Pequeña pausa

    if pwm_instance:
        pwm_instance.stop()
        logger.debug("Instancia PWM detenida.")
    
    # La limpieza general de GPIO.cleanup() en main_sistema_banda.py
    # se encargará de los pines individuales si este script no es el único
    # que usa GPIO. Si es el único, se podría llamar GPIO.cleanup() aquí.
    # Por ahora, solo nos aseguramos de que el motor esté apagado.
    logger.info("Limpieza de GPIOs de la banda completada (principalmente parada del motor/PWM).")

# --- Código de Prueba ---
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    TEST_CONFIG_FILE_BELT = 'config_industrial_belt_test.json'
    if not os.path.exists(TEST_CONFIG_FILE_BELT):
        logger.info(f"Creando archivo de config de prueba para banda: {TEST_CONFIG_FILE_BELT}")
        test_belt_cfg_content = {
            "conveyor_belt_settings": {
                "control_type": "pwm_dc_motor", # Cambia a "gpio_on_off" para probar el otro modo
                "motor_pin_bcm": 19,      # Pin para PWM o ON/OFF
                "enable_pin_bcm": 26,     # Pin de habilitación del driver L298N, por ejemplo
                "direction_pin_bcm": 13,  # Pin de dirección del driver L298N
                "active_state_on": "HIGH",# Para gpio_on_off
                "pwm_frequency_hz": 100,
                "min_duty_cycle": 30,     # Velocidad mínima para que el motor arranque
                "max_duty_cycle": 100,
                "default_speed_percent": 50
            }
            # ... (podrías añadir otras secciones de config si tu main_test necesita más)
        }
        with open(TEST_CONFIG_FILE_BELT, 'w') as f:
            json.dump(test_belt_cfg_content, f, indent=4)
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        if load_belt_config(config_file=TEST_CONFIG_FILE_BELT):
            if setup_belt_gpio():
                logger.info("=== Prueba de Control de Banda Transportadora ===")
                
                # Configurar dirección (si aplica y está definida)
                # Ejemplo: GPIO.output(belt_config["direction_pin_bcm"], GPIO.HIGH) # Hacia adelante

                logger.info("\n--- Encendiendo banda al 50% (si es PWM) o ON ---")
                start_belt(speed_percent=50)
                print(f"Estado de la banda: {get_belt_status()}")
                time.sleep(3)

                if belt_config.get("control_type") == "pwm_dc_motor":
                    logger.info("\n--- Cambiando velocidad al 100% ---")
                    set_belt_speed(100)
                    print(f"Estado de la banda: {get_belt_status()}")
                    time.sleep(3)

                    logger.info("\n--- Cambiando velocidad al 20% (podría ser min_duty_cycle) ---")
                    set_belt_speed(20) # Esto se mapeará a min_duty_cycle si 20% es menor
                    print(f"Estado de la banda: {get_belt_status()}")
                    time.sleep(3)
                
                logger.info("\n--- Deteniendo banda ---")
                stop_belt()
                print(f"Estado de la banda: {get_belt_status()}")
                time.sleep(1)

                logger.info("\n--- Encendiendo banda con velocidad por defecto (si es PWM) o ON ---")
                start_belt() # Usa default_speed_percent de config si es PWM
                print(f"Estado de la banda: {get_belt_status()}")
                time.sleep(3)


            else:
                logger.error("Fallo al configurar GPIOs para la banda.")
        else:
            logger.error("Fallo al cargar la configuración de la banda.")

    except KeyboardInterrupt:
        logger.info("Prueba interrumpida por el usuario.")
    except Exception as e:
        logger.error(f"Error durante la prueba de la banda: {e}", exc_info=True)
    finally:
        logger.info("Limpiando GPIO al final de la prueba de banda...")
        cleanup_belt_gpio()
        GPIO.cleanup() # Limpieza final de todos los canales
        logger.info("=== Prueba de Banda Finalizada ===")

