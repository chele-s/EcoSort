# -*- coding: utf-8 -*-
"""
motor_driver_interface.py - Módulo mejorado para controlar actuadores de desviación

Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
Fecha: Junio de 2025
Versión: 2.0

Este módulo maneja la inicialización y operación de los actuadores responsables
de desviar los objetos clasificados. Soporta múltiples tipos de actuadores:
- Motores paso a paso con drivers A4988/DRV8825
- Actuadores ON/OFF (relés, solenoides)
- Control con retroalimentación de posición (opcional)
"""

import RPi.GPIO as GPIO
import time
import logging
import json
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Union, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class ActuatorType(Enum):
    """Tipos de actuadores soportados"""
    STEPPER_A4988 = "stepper_A4988"
    STEPPER_DRV8825 = "stepper_DRV8825"
    GPIO_ON_OFF = "gpio_on_off"
    SERVO = "servo"
    DC_MOTOR = "dc_motor"


class ActuatorState(Enum):
    """Estados del actuador"""
    UNKNOWN = "unknown"
    IDLE = "idle"
    MOVING = "moving"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ActuatorStatus:
    """Estado actual del actuador"""
    state: ActuatorState = ActuatorState.UNKNOWN
    position: int = 0
    target_position: int = 0
    is_enabled: bool = False
    last_operation_time: float = 0
    operation_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    temperature: Optional[float] = None


class DiverterError(Exception):
    """Excepción base para errores de desviadores"""
    pass


class ActuatorConfigurationError(DiverterError):
    """Error de configuración del actuador"""
    pass


class ActuatorOperationError(DiverterError):
    """Error de operación del actuador"""
    pass


class BaseActuator(ABC):
    """Clase base abstracta para todos los actuadores"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ActuatorStatus()
        self._lock = threading.Lock()
        self._initialized = False
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Valida la configuración del actuador"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Inicializa el actuador"""
        pass
    
    @abstractmethod
    def activate(self, duration_s: float = 1.0) -> bool:
        """Activa el actuador por la duración especificada"""
        pass
    
    @abstractmethod
    def move_to_position(self, position: int) -> bool:
        """Mueve el actuador a la posición especificada"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Detiene el actuador inmediatamente"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Limpia recursos del actuador"""
        pass
    
    def enable(self) -> bool:
        """Habilita el actuador"""
        with self._lock:
            if self._enable_hardware():
                self.status.is_enabled = True
                self.status.state = ActuatorState.IDLE
                logger.info(f"Actuador {self.name} habilitado")
                return True
            return False
        
    def disable(self) -> bool:
        """Deshabilita el actuador"""
        with self._lock:
            if self._disable_hardware():
                self.status.is_enabled = False
                self.status.state = ActuatorState.DISABLED
                logger.info(f"Actuador {self.name} deshabilitado")
                return True
            return False
    
    def _enable_hardware(self) -> bool:
        """Implementación específica para habilitar hardware"""
        return True
    
    def _disable_hardware(self) -> bool:
        """Implementación específica para deshabilitar hardware"""
        return True
    
    def get_status(self) -> ActuatorStatus:
        """Obtiene el estado actual del actuador"""
        return self.status
    
    def is_initialized(self) -> bool:
        """Verifica si el actuador está inicializado"""
        return self._initialized
    
    def _log_error(self, error_msg: str) -> None:
        """Registra un error del actuador"""
        self.status.error_count += 1
        self.status.last_error = error_msg
        self.status.state = ActuatorState.ERROR
        logger.error(f"Actuador {self.name}: {error_msg}")


class StepperActuator(BaseActuator):
    """Actuador de motor paso a paso"""
    
    def _validate_config(self) -> None:
        required_keys = ['dir_pin_bcm', 'step_pin_bcm']
        for key in required_keys:
            if key not in self.config:
                raise ActuatorConfigurationError(f"Clave requerida '{key}' no encontrada en configuración para {self.name}")
    
    def initialize(self) -> bool:
        """Inicializa el motor paso a paso"""
        try:
            dir_pin = self.config['dir_pin_bcm']
            step_pin = self.config['step_pin_bcm']
            enable_pin = self.config.get('enable_pin_bcm')
            
            # Configurar pines GPIO
            GPIO.setup(dir_pin, GPIO.OUT)
            GPIO.setup(step_pin, GPIO.OUT)
            GPIO.output(step_pin, GPIO.LOW)
            
            if enable_pin is not None and self.config.get('use_enable_pin', True):
                GPIO.setup(enable_pin, GPIO.OUT)
                GPIO.output(enable_pin, GPIO.HIGH)  # Deshabilitar inicialmente
            
            # Inicializar posición
            self.status.position = self.config.get('home_steps', 0)
            self.status.target_position = self.status.position
            self.status.state = ActuatorState.DISABLED
            
            self._initialized = True
            logger.info(f"Motor paso a paso {self.name} inicializado correctamente")
            return True
            
        except Exception as e:
            self._log_error(f"Error inicializando motor paso a paso: {e}")
            return False
    
    def activate(self, duration_s: float = 1.0) -> bool:
        """Activa el motor por la duración especificada"""
        if not self._initialized:
            self._log_error("Motor no inicializado")
            return False
        
        try:
            with self._lock:
                self.status.state = ActuatorState.MOVING
                
                # Mover a posición activa
                steps_to_activate = self.config.get('steps_to_activate', 200)
                if not self._move_relative_steps(steps_to_activate):
                    return False
                
                self.status.state = ActuatorState.ACTIVE
                
                # Esperar duración
                time.sleep(duration_s)
                
                # Mover de vuelta
                steps_to_deactivate = self.config.get('steps_to_deactivate', -steps_to_activate)
                if not self._move_relative_steps(steps_to_deactivate):
                    return False
                
                self.status.state = ActuatorState.IDLE
                self.status.operation_count += 1
                self.status.last_operation_time = time.time()
                
                logger.info(f"Motor {self.name} activado exitosamente")
                return True
                
        except Exception as e:
            self._log_error(f"Error activando motor: {e}")
            return False
    
    def move_to_position(self, position: int) -> bool:
        """Mueve el motor a la posición absoluta especificada"""
        if not self._initialized:
            self._log_error("Motor no inicializado")
            return False

        with self._lock:
            relative_steps = position - self.status.position
            return self._move_relative_steps(relative_steps)
    
    def _move_relative_steps(self, steps: int) -> bool:
        """Mueve el motor un número relativo de pasos"""
        if steps == 0:
            return True
        
        try:
            dir_pin = self.config['dir_pin_bcm']
            step_pin = self.config['step_pin_bcm']
            
            # Configurar dirección
            direction = GPIO.HIGH if steps > 0 else GPIO.LOW
            GPIO.output(dir_pin, direction)
            time.sleep(0.001)  # Pausa para establecer dirección
            
            abs_steps = abs(steps)
            
            # Aplicar ramping si está configurado
            if self.config.get('use_ramping', False):
                self._move_with_ramping(step_pin, abs_steps)
            else:
                step_delay = self.config.get('step_delay', 0.002)
                self._move_constant_speed(step_pin, abs_steps, step_delay)

            # Actualizar posición
            self.status.position += steps
            self.status.target_position = self.status.position
            
            return True

        except Exception as e:
            self._log_error(f"Error moviendo motor: {e}")
            return False
    
    def _move_with_ramping(self, step_pin: int, steps: int) -> None:
        """Mueve el motor con aceleración/desaceleración"""
        start_delay = self.config.get('ramping_start_delay', 0.005)
        min_delay = self.config.get('ramping_min_delay', 0.001)
        accel_steps = min(self.config.get('ramping_accel_steps', 50), steps // 2)
        
        for i in range(steps):
            if i < accel_steps:
                # Aceleración
                delay = start_delay - (i * (start_delay - min_delay) / accel_steps)
            elif i >= (steps - accel_steps):
                # Desaceleración
                steps_into_decel = i - (steps - accel_steps)
                delay = min_delay + (steps_into_decel * (start_delay - min_delay) / accel_steps)
            else:
                # Velocidad constante
                delay = min_delay
            
            delay = max(delay, min_delay)
            self._pulse_step(step_pin, delay)
    
    def _move_constant_speed(self, step_pin: int, steps: int, delay: float) -> None:
        """Mueve el motor a velocidad constante"""
        for _ in range(steps):
            self._pulse_step(step_pin, delay)
    
    def _pulse_step(self, step_pin: int, delay: float) -> None:
        """Genera un pulso en el pin STEP"""
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)

    def stop(self) -> bool:
        """Detiene el motor inmediatamente"""
        with self._lock:
            self.status.state = ActuatorState.IDLE
            return True
    
    def _enable_hardware(self) -> bool:
        """Habilita el driver del motor"""
        enable_pin = self.config.get('enable_pin_bcm')
        if enable_pin is not None and self.config.get('use_enable_pin', True):
            try:
                GPIO.output(enable_pin, GPIO.LOW)  # LOW habilita A4988
                time.sleep(0.01)
                return True
            except Exception as e:
                self._log_error(f"Error habilitando driver: {e}")
                return False
        return True

    def _disable_hardware(self) -> bool:
        """Deshabilita el driver del motor"""
        enable_pin = self.config.get('enable_pin_bcm')
        if enable_pin is not None and self.config.get('use_enable_pin', True):
            try:
                GPIO.output(enable_pin, GPIO.HIGH)  # HIGH deshabilita A4988
                return True
            except Exception as e:
                self._log_error(f"Error deshabilitando driver: {e}")
                return False
        return True
    
    def cleanup(self) -> None:
        """Limpia recursos del motor paso a paso"""
        try:
            # Mover a posición home si es necesario
            home_position = self.config.get('home_steps', 0)
            if self.status.position != home_position:
                self.move_to_position(home_position)
            
            # Deshabilitar motor
            self.disable()
            
            logger.info(f"Motor paso a paso {self.name} limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando motor {self.name}: {e}")


class OnOffActuator(BaseActuator):
    """Actuador ON/OFF (relé, solenoide, etc.)"""
    
    def _validate_config(self) -> None:
        required_keys = ['pin_bcm', 'active_state']
        for key in required_keys:
            if key not in self.config:
                raise ActuatorConfigurationError(f"Clave requerida '{key}' no encontrada en configuración para {self.name}")
    
    def initialize(self) -> bool:
        """Inicializa el actuador ON/OFF"""
        try:
            pin = self.config['pin_bcm']
            active_state = self.config['active_state']
            
            GPIO.setup(pin, GPIO.OUT)
            
            # Estado inicial inactivo
            initial_state = GPIO.LOW if active_state == 'HIGH' else GPIO.HIGH
            GPIO.output(pin, initial_state)
            
            self.status.state = ActuatorState.IDLE
            self.status.position = 0  # 0 = inactivo, 1 = activo
            
            self._initialized = True
            logger.info(f"Actuador ON/OFF {self.name} inicializado correctamente")
            return True
            
        except Exception as e:
            self._log_error(f"Error inicializando actuador ON/OFF: {e}")
            return False
    
    def activate(self, duration_s: float = 1.0) -> bool:
        """Activa el actuador por la duración especificada"""
        if not self._initialized:
            self._log_error("Actuador no inicializado")
            return False

        try:
            with self._lock:
                pin = self.config['pin_bcm']
                active_state = self.config['active_state']
                active_level = GPIO.HIGH if active_state == 'HIGH' else GPIO.LOW
                inactive_level = GPIO.LOW if active_level == GPIO.HIGH else GPIO.HIGH
                
                # Activar
                self.status.state = ActuatorState.ACTIVE
                self.status.position = 1
                GPIO.output(pin, active_level)
                
                # Esperar duración
                time.sleep(duration_s)
                
                # Desactivar
                GPIO.output(pin, inactive_level)
                self.status.state = ActuatorState.IDLE
                self.status.position = 0
                self.status.operation_count += 1
                self.status.last_operation_time = time.time()
                
                logger.info(f"Actuador ON/OFF {self.name} activado exitosamente")
            return True
                
        except Exception as e:
            self._log_error(f"Error activando actuador ON/OFF: {e}")
            return False

    def move_to_position(self, position: int) -> bool:
        """Mueve a posición (0=inactivo, 1=activo)"""
        if not self._initialized:
            return False
        
        try:
            with self._lock:
                pin = self.config['pin_bcm']
                active_state = self.config['active_state']
                
                if position == 1:
                    # Activar
                    active_level = GPIO.HIGH if active_state == 'HIGH' else GPIO.LOW
                    GPIO.output(pin, active_level)
                    self.status.state = ActuatorState.ACTIVE
                else:
                    # Desactivar
                    inactive_level = GPIO.LOW if active_state == 'HIGH' else GPIO.HIGH
                    GPIO.output(pin, inactive_level)
                    self.status.state = ActuatorState.IDLE
                
                self.status.position = position
            return True
                
        except Exception as e:
            self._log_error(f"Error moviendo actuador ON/OFF: {e}")
            return False
    
    def stop(self) -> bool:
        """Detiene el actuador (lo pone en estado inactivo)"""
        return self.move_to_position(0)
    
    def cleanup(self) -> None:
        """Limpia recursos del actuador ON/OFF"""
        try:
            self.move_to_position(0)  # Asegurar estado inactivo
            logger.info(f"Actuador ON/OFF {self.name} limpiado")
        except Exception as e:
            logger.error(f"Error limpiando actuador {self.name}: {e}")


class DiverterManager:
    """Gestor principal de todos los desviadores"""
    
    def __init__(self):
        self.actuators: Dict[str, BaseActuator] = {}
        self.common_config: Dict[str, Any] = {}
        self._initialized = False
        
    def load_configuration(self, config_file: str = 'Control_Banda/config_industrial.json') -> bool:
        """Carga la configuración de los desviadores"""
        try:
            if not os.path.exists(config_file):
                logger.error(f"Archivo de configuración no encontrado: {config_file}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'diverter_control_settings' not in config_data:
                logger.error("'diverter_control_settings' no encontrado en configuración")
                return False
            
            settings = config_data['diverter_control_settings']
            self.common_config = settings.get('common_motor_params', {})
            diverters_config = settings.get('diverters', {})
            
            # Crear actuadores
            for name, config in diverters_config.items():
                actuator = self._create_actuator(name, config)
                if actuator:
                    self.actuators[name] = actuator
                else:
                    logger.warning(f"No se pudo crear actuador para {name}")
            
            logger.info(f"Configuración cargada: {len(self.actuators)} actuadores")
            return len(self.actuators) > 0
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return False

    def _create_actuator(self, name: str, config: Dict[str, Any]) -> Optional[BaseActuator]:
        """Crea un actuador según su tipo"""
        try:
            actuator_type = config.get('type', 'stepper_A4988')
            
            # Combinar configuración común con específica
            merged_config = {**self.common_config, **config}
            
            if actuator_type in ['stepper_A4988', 'stepper_DRV8825']:
                return StepperActuator(name, merged_config)
            elif actuator_type == 'gpio_on_off':
                return OnOffActuator(name, merged_config)
            else:
                logger.error(f"Tipo de actuador no soportado: {actuator_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creando actuador {name}: {e}")
            return None
    
    def initialize_all(self) -> bool:
        """Inicializa todos los actuadores"""
        try:
            success_count = 0
            
            for name, actuator in self.actuators.items():
                if actuator.initialize():
                    success_count += 1
                    logger.info(f"Actuador {name} inicializado")
                else:
                    logger.error(f"Fallo inicializando actuador {name}")
            
            self._initialized = success_count > 0
            logger.info(f"Inicializados {success_count}/{len(self.actuators)} actuadores")
            return self._initialized
            
        except Exception as e:
            logger.error(f"Error inicializando actuadores: {e}")
            return False
    
    def activate_diverter(self, category_name: str, duration_s: float) -> bool:
        """Activa un desviador específico"""
        if not self._initialized:
            logger.error("Gestor de desviadores no inicializado")
            return False
        
        if category_name not in self.actuators:
            logger.error(f"Desviador '{category_name}' no encontrado")
            return False
        
        actuator = self.actuators[category_name]
        
        # Habilitar actuador si no está habilitado
        if not actuator.status.is_enabled:
            if not actuator.enable():
                logger.error(f"No se pudo habilitar actuador {category_name}")
                return False
        
        return actuator.activate(duration_s)
    
    def get_diverter_status(self, category_name: str) -> Optional[ActuatorStatus]:
        """Obtiene el estado de un desviador específico"""
        if category_name in self.actuators:
            return self.actuators[category_name].get_status()
        return None
    
    def get_all_status(self) -> Dict[str, ActuatorStatus]:
        """Obtiene el estado de todos los desviadores"""
        return {name: actuator.get_status() for name, actuator in self.actuators.items()}
    
    def stop_all(self) -> bool:
        """Detiene todos los desviadores"""
        success = True
        for actuator in self.actuators.values():
            if not actuator.stop():
                success = False
        return success
    
    def cleanup_all(self) -> None:
        """Limpia todos los desviadores"""
        logger.info("Limpiando todos los desviadores...")
        
        for name, actuator in self.actuators.items():
            try:
                actuator.cleanup()
            except Exception as e:
                logger.error(f"Error limpiando actuador {name}: {e}")
        
        logger.info("Limpieza de desviadores completada")


# Instancia global del gestor
_diverter_manager = DiverterManager()


# Funciones de compatibilidad con el API anterior
def load_diverter_configuration(config_file: str = 'Control_Banda/config_industrial.json') -> bool:
    """Función de compatibilidad: carga configuración de desviadores"""
    return _diverter_manager.load_configuration(config_file)


def setup_diverter_gpio() -> bool:
    """Función de compatibilidad: configura GPIOs de desviadores"""
    return _diverter_manager.initialize_all()


def activate_diverter(category_name: str, activation_duration_s: float) -> bool:
    """Función de compatibilidad: activa un desviador"""
    return _diverter_manager.activate_diverter(category_name, activation_duration_s)


def cleanup_gpio_diverters() -> None:
    """Función de compatibilidad: limpia recursos GPIO"""
    _diverter_manager.cleanup_all()


def get_diverter_manager() -> DiverterManager:
    """Obtiene la instancia del gestor de desviadores"""
    return _diverter_manager


# Código de prueba
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Usar archivo de configuración de prueba
        test_config = {
            "diverter_control_settings": {
                "common_motor_params": {
                    "step_delay": 0.002,
                    "use_ramping": True,
                    "ramping_start_delay": 0.005,
                    "ramping_min_delay": 0.0005,
                    "ramping_accel_steps": 50
                },
                "diverters": {
                    "test_stepper": {
                        "type": "stepper_A4988",
                        "dir_pin_bcm": 20,
                        "step_pin_bcm": 21,
                        "enable_pin_bcm": 16,
                        "use_enable_pin": True,
                        "steps_to_activate": 200,
                        "steps_to_deactivate": -200,
                        "home_steps": 0
                    },
                    "test_onoff": {
                        "type": "gpio_on_off",
                        "pin_bcm": 18,
                        "active_state": "HIGH"
                    }
                }
            }
        }
        
        # Guardar configuración de prueba
        test_config_file = 'test_diverters_config.json'
        with open(test_config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        # Probar el gestor
        manager = DiverterManager()
        
        if manager.load_configuration(test_config_file):
            if manager.initialize_all():
                logger.info("=== Prueba de Desviadores ===")
                
                # Mostrar estado inicial
                for name, status in manager.get_all_status().items():
                    logger.info(f"{name}: {status.state.value}")
                
                # Probar activación
                for name in manager.actuators.keys():
                    logger.info(f"Probando actuador {name}...")
                    success = manager.activate_diverter(name, 1.0)
                    logger.info(f"Resultado: {'Éxito' if success else 'Fallo'}")
                    time.sleep(0.5)

            else:
                logger.error("Fallo inicializando actuadores")
        else:
            logger.error("Fallo cargando configuración")
            
    except KeyboardInterrupt:
        logger.info("Prueba interrumpida")
    except Exception as e:
        logger.error(f"Error en prueba: {e}")
    finally:
        _diverter_manager.cleanup_all()
        GPIO.cleanup()
        
        # Limpiar archivo de prueba
        if os.path.exists('test_diverters_config.json'):
            os.remove('test_diverters_config.json')
        
        logger.info("Prueba completada")

