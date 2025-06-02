# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# motor_driver_interface.py - Módulo para controlar los actuadores de desviación
#                             de la banda transportadora.
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este módulo maneja la inicialización y operación de los actuadores
#   (asumidos como motores a pasos con drivers A4988) responsables de
#   desviar los objetos clasificados a sus respectivas tolvas.
#   La configuración de cada motor/actuador se carga desde 'config_industrial.json'.
# -----------------------------------------------------------------------------

import RPi.GPIO as GPIO
import time
import logging
import json
import os

# Obtener logger (se asume que está configurado en el script principal, ej: main_sistema_banda.py)
logger = logging.getLogger(__name__)

# --- Variables Globales del Módulo ---
# Estas se llenarán desde config_industrial.json
diverter_configs = {} # { "CategoryName": {config_details}, ... }
# Ejemplo de config_details para un motor a pasos:
# {
#   "type": "stepper_A4988",
#   "dir_pin_bcm": 20,
#   "step_pin_bcm": 21,
#   "enable_pin_bcm": 16, (opcional)
#   "use_enable_pin": True,
#   "steps_to_activate": 200, # Pasos para mover a la posición de "desviar"
#   "steps_to_deactivate": -200, # Pasos para mover de vuelta a "home" o "no desviar"
#                                 # o podría ser una posición absoluta "home_steps": 0
#   "current_pos_steps": 0, # Estado interno para cada motor
#   # Parámetros de ramping y velocidad pueden ser comunes o por desviador
#   "step_delay": 0.005,
#   "use_ramping": True,
#   "ramping_start_delay": 0.01,
#   "ramping_min_delay": 0.001,
#   "ramping_accel_steps": 20
# }
# O para un solenoide/relé:
# {
#   "type": "gpio_on_off",
#   "pin_bcm": 17,
#   "active_state": "HIGH" # o "LOW"
# }

common_motor_params = {} # Para parámetros comunes a todos los steppers

def load_diverter_configuration(config_file='Control_Banda/config_industrial.json'):
    """
    Carga la configuración de los desviadores y parámetros comunes del motor
    desde el archivo JSON especificado.
    """
    global diverter_configs, common_motor_params
    try:
        if not os.path.exists(config_file):
            logger.error(f"Archivo de configuración {config_file} no encontrado.")
            return False
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        if 'diverter_control_settings' not in config_data:
            logger.error("'diverter_control_settings' no encontrado en el archivo de configuración.")
            return False
            
        settings = config_data['diverter_control_settings']
        common_motor_params = settings.get('common_motor_params', {
            # Valores por defecto si no están en config
            "step_delay": 0.005,
            "use_ramping": True,
            "ramping_start_delay": 0.01,
            "ramping_min_delay": 0.001,
            "ramping_accel_steps": 20,
            "use_common_enable_pin": False, # Si hay un pin ENABLE para todos los drivers
            "common_enable_pin_bcm": None
        })
        
        loaded_diverters = settings.get('diverters', {})
        if not loaded_diverters:
            logger.warning("No se encontraron configuraciones de 'diverters' en el archivo.")
            return False

        for category, d_config in loaded_diverters.items():
            # Heredar parámetros comunes si no están definidos específicamente para el desviador
            # y si el tipo es stepper
            if d_config.get("type", "stepper_A4988") == "stepper_A4988":
                for param, default_value in common_motor_params.items():
                    if param not in d_config:
                        d_config[param] = default_value
                d_config['current_pos_steps'] = d_config.get('home_steps', 0) # Iniciar en home

            diverter_configs[category] = d_config
            logger.info(f"Configuración cargada para desviador '{category}': {d_config}")
            
        return True

    except Exception as e:
        logger.error(f"Error cargando la configuración de desviadores: {e}", exc_info=True)
        return False

def setup_diverter_gpio():
    """
    Configura los pines GPIO para todos los desviadores definidos.
    Debe llamarse después de load_diverter_configuration().
    """
    if not diverter_configs:
        logger.error("No hay configuraciones de desviador cargadas. Ejecute load_diverter_configuration() primero.")
        return False
    
    try:
        # Asumiendo que GPIO.setmode(GPIO.BCM) se llama en el script principal (main_sistema_banda.py)
        # Si no, descomentar:
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setwarnings(False)

        if common_motor_params.get("use_common_enable_pin") and common_motor_params.get("common_enable_pin_bcm") is not None:
            pin = common_motor_params["common_enable_pin_bcm"]
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH) # Deshabilitar drivers A4988 (activo bajo)
            logger.info(f"Pin ENABLE común configurado en GPIO {pin} y puesto en ALTO (deshabilitado).")

        for category, config in diverter_configs.items():
            dev_type = config.get("type", "stepper_A4988")
            
            if dev_type == "stepper_A4988":
                GPIO.setup(config['dir_pin_bcm'], GPIO.OUT)
                GPIO.setup(config['step_pin_bcm'], GPIO.OUT)
                GPIO.output(config['step_pin_bcm'], GPIO.LOW)
                
                if config.get('use_enable_pin') and 'enable_pin_bcm' in config and config['enable_pin_bcm'] is not None:
                    GPIO.setup(config['enable_pin_bcm'], GPIO.OUT)
                    GPIO.output(config['enable_pin_bcm'], GPIO.HIGH) # Deshabilitar driver
                logger.info(f"GPIOs para desviador stepper '{category}' configurados.")

            elif dev_type == "gpio_on_off":
                GPIO.setup(config['pin_bcm'], GPIO.OUT)
                initial_state = GPIO.LOW if config.get('active_state', 'HIGH') == 'HIGH' else GPIO.HIGH
                GPIO.output(config['pin_bcm'], initial_state) # Estado inactivo
                logger.info(f"GPIO para desviador on/off '{category}' (pin {config['pin_bcm']}) configurado.")
            else:
                logger.warning(f"Tipo de desviador desconocido '{dev_type}' para '{category}'. No se configuró GPIO.")
        
        logger.info("Todos los GPIOs de desviadores configurados.")
        return True
    except Exception as e:
        logger.error(f"Error configurando GPIOs para desviadores: {e}", exc_info=True)
        return False

def _pulse_step_motor(step_pin, delay):
    """Genera un pulso en el pin STEP."""
    GPIO.output(step_pin, GPIO.HIGH)
    time.sleep(delay)
    GPIO.output(step_pin, GPIO.LOW)
    time.sleep(delay)

def _move_stepper(category_name, target_relative_steps):
    """
    Mueve un motor a pasos específico una cantidad relativa de pasos,
    aplicando ramping si está configurado.
    Actualiza la posición actual del motor.
    """
    if category_name not in diverter_configs or diverter_configs[category_name].get("type") != "stepper_A4988":
        logger.error(f"No es un desviador stepper válido: {category_name}")
        return False

    config = diverter_configs[category_name]
    current_pos = config['current_pos_steps']
    # El target_relative_steps es cuántos pasos moverse DESDE la posición actual
    # No es una posición absoluta.
    
    if target_relative_steps == 0:
        logger.debug(f"Desviador '{category_name}' no requiere movimiento (0 pasos relativos).")
        return True

    logger.info(f"Moviendo desviador '{category_name}' {target_relative_steps} pasos desde {current_pos}.")

    # Habilitar driver (si usa enable pin individual o común)
    enable_pin_to_use = None
    if config.get('use_enable_pin') and config.get('enable_pin_bcm') is not None:
        enable_pin_to_use = config['enable_pin_bcm']
    elif common_motor_params.get("use_common_enable_pin") and common_motor_params.get("common_enable_pin_bcm") is not None:
        enable_pin_to_use = common_motor_params["common_enable_pin_bcm"]
    
    if enable_pin_to_use is not None:
        GPIO.output(enable_pin_to_use, GPIO.LOW) # LOW habilita A4988
        time.sleep(0.01) # Pausa para que el driver esté listo

    # Establecer dirección
    direction_gpio_state = GPIO.HIGH if target_relative_steps > 0 else GPIO.LOW
    GPIO.output(config['dir_pin_bcm'], direction_gpio_state)
    time.sleep(0.01) # Pausa para que la dirección se establezca

    abs_steps = abs(target_relative_steps)

    if config.get('use_ramping', False):
        start_delay = config.get('ramping_start_delay', 0.01)
        min_delay = config.get('ramping_min_delay', 0.001)
        accel_steps_cfg = config.get('ramping_accel_steps', 20)
        
        # Asegurar que los pasos de aceleración no excedan la mitad del movimiento
        actual_accel_steps = min(accel_steps_cfg, abs_steps // 2)
        if actual_accel_steps == 0 and abs_steps > 0 : # Para movimientos muy cortos
             actual_accel_steps = 1 if abs_steps > 1 else 0


        for i in range(abs_steps):
            current_delay = min_delay # Por defecto para la fase de velocidad constante
            if actual_accel_steps > 0:
                if i < actual_accel_steps: # Fase de aceleración
                    current_delay = start_delay - (i * (start_delay - min_delay) / actual_accel_steps)
                elif i >= (abs_steps - actual_accel_steps): # Fase de desaceleración
                    steps_into_decel = i - (abs_steps - actual_accel_steps)
                    current_delay = min_delay + (steps_into_decel * (start_delay - min_delay) / actual_accel_steps)
            
            current_delay = max(current_delay, min_delay) # Asegurar que no sea menor al mínimo
            _pulse_step_motor(config['step_pin_bcm'], current_delay)
    else:
        step_delay_val = config.get('step_delay', 0.005)
        for _ in range(abs_steps):
            _pulse_step_motor(config['step_pin_bcm'], step_delay_val)

    new_pos = current_pos + target_relative_steps
    config['current_pos_steps'] = new_pos
    logger.info(f"Desviador '{category_name}' movido a nueva posición relativa {new_pos} (movió {target_relative_steps} pasos).")

    # Opcional: Deshabilitar driver después del movimiento
    # if enable_pin_to_use is not None and config.get("disable_after_move", False):
    #     GPIO.output(enable_pin_to_use, GPIO.HIGH)
    return True


def activate_diverter(category_name, activation_duration_s):
    """
    Activa el desviador para una categoría específica durante un tiempo determinado.
    Para steppers: mueve a 'steps_to_activate', espera, luego mueve 'steps_to_deactivate'.
    Para on_off: enciende, espera, apaga.
    """
    if category_name not in diverter_configs:
        logger.error(f"Desviador para la categoría '{category_name}' no encontrado en la configuración.")
        return False

    config = diverter_configs[category_name]
    dev_type = config.get("type", "stepper_A4988")
    logger.info(f"Activando desviador '{category_name}' (tipo: {dev_type}) por {activation_duration_s}s.")

    if dev_type == "stepper_A4988":
        steps_on = config.get('steps_to_activate', 0)
        # steps_off puede ser un valor negativo para revertir, o una posición absoluta "home_steps"
        # Para simplificar, asumimos que steps_to_deactivate es el movimiento relativo para volver.
        steps_off_relative = config.get('steps_to_deactivate', -steps_on if steps_on !=0 else 0)

        if _move_stepper(category_name, steps_on):
            time.sleep(activation_duration_s)
            _move_stepper(category_name, steps_off_relative) # Mover de vuelta
            logger.info(f"Desviador stepper '{category_name}' ciclo completado.")
            return True
        else:
            logger.error(f"Fallo al mover el desviador stepper '{category_name}'.")
            return False

    elif dev_type == "gpio_on_off":
        pin = config['pin_bcm']
        active_level = GPIO.HIGH if config.get('active_state', 'HIGH') == 'HIGH' else GPIO.LOW
        inactive_level = GPIO.LOW if active_level == GPIO.HIGH else GPIO.HIGH
        
        try:
            GPIO.output(pin, active_level)
            logger.debug(f"Desviador on/off '{category_name}' (pin {pin}) puesto en {config.get('active_state')}.")
            time.sleep(activation_duration_s)
            GPIO.output(pin, inactive_level)
            logger.debug(f"Desviador on/off '{category_name}' (pin {pin}) devuelto a estado inactivo.")
            logger.info(f"Desviador on/off '{category_name}' ciclo completado.")
            return True
        except Exception as e:
            logger.error(f"Error activando desviador on/off '{category_name}': {e}", exc_info=True)
            return False
    else:
        logger.warning(f"Tipo de actuador '{dev_type}' no soportado para '{category_name}'.")
        return False

def return_all_diverters_to_home():
    """Mueve todos los desviadores stepper a su posición 'home' (asumida como 0 pasos)."""
    logger.info("Intentando devolver todos los desviadores stepper a la posición home...")
    success_all = True
    for category, config in diverter_configs.items():
        if config.get("type", "stepper_A4988") == "stepper_A4988":
            current_pos = config['current_pos_steps']
            home_pos = config.get('home_steps', 0) # Podrías definir una posición home específica
            steps_to_home = home_pos - current_pos
            if steps_to_home != 0:
                logger.info(f"Desviador '{category}': Moviendo de {current_pos} a home ({home_pos}), {steps_to_home} pasos.")
                if not _move_stepper(category, steps_to_home):
                    success_all = False
            else:
                logger.info(f"Desviador '{category}' ya está en home ({current_pos}).")
    return success_all


def cleanup_gpio_diverters():
    """
    Libera los recursos GPIO utilizados por los desviadores.
    Idealmente, se llama al finalizar el programa principal.
    """
    logger.info("Limpiando GPIOs de los desviadores...")
    # Opcional: intentar devolver todos los motores a una posición home antes de limpiar
    return_all_diverters_to_home()
    time.sleep(0.5) # Dar tiempo a que los motores terminen

    # La limpieza general de GPIO.cleanup() en main_sistema_banda.py se encargará
    # de todos los pines. Si este módulo es el único que usa GPIO, se podría llamar aquí.
    # Por ahora, solo deshabilita los enable si están configurados.
    if common_motor_params.get("use_common_enable_pin") and common_motor_params.get("common_enable_pin_bcm") is not None:
        try:
            GPIO.output(common_motor_params["common_enable_pin_bcm"], GPIO.HIGH)
        except Exception:
            pass # Puede que ya esté limpiado

    for category, config in diverter_configs.items():
        if config.get("type", "stepper_A4988") == "stepper_A4988":
            if config.get('use_enable_pin') and 'enable_pin_bcm' in config and config['enable_pin_bcm'] is not None:
                try:
                    GPIO.output(config['enable_pin_bcm'], GPIO.HIGH)
                except Exception:
                    pass # Puede que ya esté limpiado
    logger.info("Pines ENABLE de desviadores (si existen) deshabilitados.")
    # GPIO.cleanup() # No llamar aquí si se llama en el main

# --- Código de Prueba (ejecutar solo si se llama directamente al script) ---
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG, # Nivel DEBUG para ver más detalles en la prueba
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Crear un config_industrial.json de prueba en el directorio actual si no existe
    TEST_CONFIG_FILE = 'config_industrial_test.json'
    if not os.path.exists(TEST_CONFIG_FILE):
        logger.info(f"Creando archivo de configuración de prueba: {TEST_CONFIG_FILE}")
        test_config_content = {
            "diverter_control_settings": {
                "common_motor_params": {
                    "step_delay": 0.002, # Más rápido para prueba
                    "use_ramping": True,
                    "ramping_start_delay": 0.005,
                    "ramping_min_delay": 0.0005, # Muy rápido
                    "ramping_accel_steps": 50,
                    "use_common_enable_pin": False 
                },
                "diverters": {
                    "Metal": {
                        "type": "stepper_A4988",
                        "dir_pin_bcm": 20,
                        "step_pin_bcm": 21,
                        "enable_pin_bcm": 16,
                        "use_enable_pin": True,
                        "steps_to_activate": 200, # 1 revolución para motor de 200 pasos/rev
                        "steps_to_deactivate": -200,
                        "home_steps": 0
                    },
                    "Plastic": {
                        "type": "gpio_on_off",
                        "pin_bcm": 17, # Usar un pin diferente para prueba
                        "active_state": "HIGH"
                    }
                }
            }
        }
        with open(TEST_CONFIG_FILE, 'w') as f:
            json.dump(test_config_content, f, indent=4)
    
    # Configurar GPIO
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        if load_diverter_configuration(config_file=TEST_CONFIG_FILE):
            if setup_diverter_gpio():
                logger.info("=== Prueba de Control de Desviadores ===")
                
                # Probar desviador stepper "Metal"
                if "Metal" in diverter_configs:
                    logger.info("\n--- Probando desviador 'Metal' (Stepper) ---")
                    activate_diverter("Metal", activation_duration_s=1.0)
                    time.sleep(1)
                    # Probar devolver a home explícitamente
                    logger.info("Devolviendo 'Metal' a home (si no lo está ya)...")
                    metal_conf = diverter_configs["Metal"]
                    steps_to_home = metal_conf.get('home_steps',0) - metal_conf['current_pos_steps']
                    if steps_to_home != 0:
                         _move_stepper("Metal", steps_to_home)
                    time.sleep(1)

                # Probar desviador on/off "Plastic"
                if "Plastic" in diverter_configs:
                    logger.info("\n--- Probando desviador 'Plastic' (GPIO On/Off) ---")
                    activate_diverter("Plastic", activation_duration_s=2.0)
                    time.sleep(1)

                logger.info("\n--- Prueba de devolver todos a home ---")
                return_all_diverters_to_home()

            else:
                logger.error("Fallo al configurar GPIOs para desviadores.")
        else:
            logger.error("Fallo al cargar la configuración de desviadores.")
            
    except KeyboardInterrupt:
        logger.info("Prueba interrumpida por el usuario.")
    except Exception as e:
        logger.error(f"Error durante la prueba: {e}", exc_info=True)
    finally:
        logger.info("Limpiando GPIO al final de la prueba...")
        cleanup_gpio_diverters() # Llama a return_all_diverters_to_home() dentro
        GPIO.cleanup() # Limpieza final de todos los canales
        logger.info("=== Prueba Finalizada ===")

