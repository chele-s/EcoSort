# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# conveyor_belt_controller.py - Controlador Avanzado de Banda Transportadora
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio 2025
# Versión: 2.0 Enhanced Edition
# Descripción:
#   Sistema avanzado de control de banda transportadora con arquitectura OOP,
#   recuperación automática de errores, monitoreo en tiempo real y configuración
#   dinámica. Soporta múltiples tipos de control: PWM, ON/OFF y PLC externo.
# -----------------------------------------------------------------------------

import RPi.GPIO as GPIO
import time
import logging
import json
import os
import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import psutil
from concurrent.futures import ThreadPoolExecutor

# --- Configuración de Logging ---
logger = logging.getLogger(__name__)

# --- Enums y Dataclasses ---

class BeltState(Enum):
    """Estados de la banda transportadora."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class ControlType(Enum):
    """Tipos de control de banda soportados."""
    GPIO_ON_OFF = "gpio_on_off"
    PWM_DC_MOTOR = "pwm_dc_motor"
    EXTERNAL_PLC = "external_plc"
    SERVO_CONTROL = "servo_control"

@dataclass
class BeltConfiguration:
    """Configuración de la banda transportadora."""
    control_type: str = "gpio_on_off"
    motor_pin_bcm: Optional[int] = None
    enable_pin_bcm: Optional[int] = None
    direction_pin_bcm: Optional[int] = None
    active_state_on: str = "HIGH"
    pwm_frequency_hz: int = 100
    min_duty_cycle: int = 20
    max_duty_cycle: int = 100
    default_speed_percent: int = 75
    safety_timeout_s: float = 10.0
    recovery_attempts: int = 3
    health_check_interval_s: float = 1.0

@dataclass
class BeltStatus:
    """Estado actual de la banda transportadora."""
    state: BeltState = BeltState.IDLE
    is_running: bool = False
    speed_percent: float = 0.0
    current_draw_ma: float = 0.0
    temperature_c: float = 0.0
    error_count: int = 0
    uptime_s: float = 0.0
    last_error: Optional[str] = None
    health_score: float = 100.0

@dataclass
class BeltMetrics:
    """Métricas de rendimiento de la banda."""
    total_runtime_hours: float = 0.0
    start_count: int = 0
    error_count: int = 0
    emergency_stops: int = 0
    avg_speed_percent: float = 0.0
    efficiency_score: float = 100.0
    last_maintenance: Optional[str] = None

# --- Clases Base ---

class BeltDriver(ABC):
    """Clase abstracta base para drivers de banda transportadora."""
    
    def __init__(self, config: BeltConfiguration):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Inicializar el driver."""
        pass
        
    @abstractmethod
    async def start_belt(self, speed_percent: float = None) -> bool:
        """Iniciar la banda."""
        pass
        
    @abstractmethod
    async def stop_belt(self) -> bool:
        """Detener la banda."""
        pass
        
    @abstractmethod
    async def set_speed(self, speed_percent: float) -> bool:
        """Establecer velocidad."""
        pass
        
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del driver."""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Limpiar recursos."""
        pass

class GPIOOnOffDriver(BeltDriver):
    """Driver para control ON/OFF via GPIO."""
    
    async def initialize(self) -> bool:
        """Inicializar control ON/OFF."""
        try:
            if self.config.motor_pin_bcm is None:
                raise ValueError("motor_pin_bcm no especificado para control ON/OFF")
                
            # Configurar pin principal
            GPIO.setup(self.config.motor_pin_bcm, GPIO.OUT)
            inactive_level = GPIO.LOW if self.config.active_state_on == "HIGH" else GPIO.HIGH
            GPIO.output(self.config.motor_pin_bcm, inactive_level)
            
            # Configurar pin de habilitación si existe
            if self.config.enable_pin_bcm is not None:
                GPIO.setup(self.config.enable_pin_bcm, GPIO.OUT)
                GPIO.output(self.config.enable_pin_bcm, GPIO.LOW)
                
            # Configurar pin de dirección si existe
            if self.config.direction_pin_bcm is not None:
                GPIO.setup(self.config.direction_pin_bcm, GPIO.OUT)
                GPIO.output(self.config.direction_pin_bcm, GPIO.LOW)
                
            self._initialized = True
            self.logger.info(f"Driver ON/OFF inicializado en GPIO {self.config.motor_pin_bcm}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando driver ON/OFF: {e}")
            return False
    
    async def start_belt(self, speed_percent: float = None) -> bool:
        """Iniciar banda en modo ON/OFF."""
        try:
            if not self._initialized:
                raise RuntimeError("Driver no inicializado")
                
            # Habilitar driver si hay pin enable
            if self.config.enable_pin_bcm is not None:
                GPIO.output(self.config.enable_pin_bcm, GPIO.HIGH)
                await asyncio.sleep(0.01)
                
            # Activar motor
            active_level = GPIO.HIGH if self.config.active_state_on == "HIGH" else GPIO.LOW
            GPIO.output(self.config.motor_pin_bcm, active_level)
            
            self.logger.info("Banda iniciada (modo ON/OFF)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando banda ON/OFF: {e}")
            return False
    
    async def stop_belt(self) -> bool:
        """Detener banda."""
        try:
            if not self._initialized:
                return True  # Ya está "detenida"
                
            # Desactivar motor
            inactive_level = GPIO.LOW if self.config.active_state_on == "HIGH" else GPIO.HIGH
            GPIO.output(self.config.motor_pin_bcm, inactive_level)
            
            # Deshabilitar driver
            if self.config.enable_pin_bcm is not None:
                GPIO.output(self.config.enable_pin_bcm, GPIO.LOW)
                
            self.logger.info("Banda detenida (modo ON/OFF)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deteniendo banda ON/OFF: {e}")
            return False
    
    async def set_speed(self, speed_percent: float) -> bool:
        """Cambiar velocidad (no aplicable para ON/OFF)."""
        self.logger.warning("Control de velocidad no disponible en modo ON/OFF")
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del driver ON/OFF."""
        try:
            if not self._initialized:
                return {"initialized": False, "running": False}
                
            # Verificar estado actual del pin
            current_state = GPIO.input(self.config.motor_pin_bcm)
            active_level = GPIO.HIGH if self.config.active_state_on == "HIGH" else GPIO.LOW
            is_running = current_state == active_level
            
            return {
                "initialized": True,
                "running": is_running,
                "speed_percent": 100.0 if is_running else 0.0,
                "control_type": "on_off"
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado ON/OFF: {e}")
            return {"error": str(e)}
    
    async def cleanup(self) -> None:
        """Limpiar recursos ON/OFF."""
        if self._initialized:
            await self.stop_belt()
            self._initialized = False

class PWMDriver(BeltDriver):
    """Driver para control PWM."""
    
    def __init__(self, config: BeltConfiguration):
        super().__init__(config)
        self.pwm_instance = None
        self.current_duty_cycle = 0.0
    
    async def initialize(self) -> bool:
        """Inicializar control PWM."""
        try:
            if self.config.motor_pin_bcm is None:
                raise ValueError("motor_pin_bcm no especificado para control PWM")
                
            # Configurar pin PWM
            GPIO.setup(self.config.motor_pin_bcm, GPIO.OUT)
            self.pwm_instance = GPIO.PWM(self.config.motor_pin_bcm, self.config.pwm_frequency_hz)
            self.pwm_instance.start(0)
            
            # Configurar pin de habilitación si existe
            if self.config.enable_pin_bcm is not None:
                GPIO.setup(self.config.enable_pin_bcm, GPIO.OUT)
                GPIO.output(self.config.enable_pin_bcm, GPIO.LOW)
                
            # Configurar pin de dirección si existe
            if self.config.direction_pin_bcm is not None:
                GPIO.setup(self.config.direction_pin_bcm, GPIO.OUT)
                GPIO.output(self.config.direction_pin_bcm, GPIO.LOW)
                
            self._initialized = True
            self.logger.info(f"Driver PWM inicializado en GPIO {self.config.motor_pin_bcm}, {self.config.pwm_frequency_hz}Hz")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando driver PWM: {e}")
            return False
    
    async def start_belt(self, speed_percent: float = None) -> bool:
        """Iniciar banda con velocidad PWM."""
        try:
            if not self._initialized or not self.pwm_instance:
                raise RuntimeError("Driver PWM no inicializado")
                
            target_speed = speed_percent if speed_percent is not None else self.config.default_speed_percent
            
            # Habilitar driver si hay pin enable
            if self.config.enable_pin_bcm is not None:
                GPIO.output(self.config.enable_pin_bcm, GPIO.HIGH)
                await asyncio.sleep(0.01)
                
            # Establecer velocidad
            await self.set_speed(target_speed)
            
            self.logger.info(f"Banda iniciada (modo PWM) a {target_speed}% velocidad")
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando banda PWM: {e}")
            return False
    
    async def stop_belt(self) -> bool:
        """Detener banda PWM."""
        try:
            if not self._initialized or not self.pwm_instance:
                return True
                
            # Establecer duty cycle a 0
            self.pwm_instance.ChangeDutyCycle(0)
            self.current_duty_cycle = 0.0
            
            # Deshabilitar driver
            if self.config.enable_pin_bcm is not None:
                GPIO.output(self.config.enable_pin_bcm, GPIO.LOW)
                
            self.logger.info("Banda detenida (modo PWM)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deteniendo banda PWM: {e}")
            return False
    
    async def set_speed(self, speed_percent: float) -> bool:
        """Establecer velocidad PWM."""
        try:
            if not self._initialized or not self.pwm_instance:
                raise RuntimeError("Driver PWM no inicializado")
                
            # Validar rango
            speed_percent = max(0.0, min(100.0, speed_percent))
            
            # Calcular duty cycle
            if speed_percent == 0:
                duty_cycle = 0.0
            else:
                duty_cycle = self.config.min_duty_cycle + (speed_percent / 100.0) * (
                    self.config.max_duty_cycle - self.config.min_duty_cycle)
            
            # Aplicar duty cycle
            self.pwm_instance.ChangeDutyCycle(duty_cycle)
            self.current_duty_cycle = duty_cycle
            
            self.logger.debug(f"Velocidad PWM establecida: {speed_percent}% ({duty_cycle:.1f}% duty cycle)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error estableciendo velocidad PWM: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del driver PWM."""
        try:
            if not self._initialized:
                return {"initialized": False, "running": False}
                
            is_running = self.current_duty_cycle > 0
            speed_percent = 0.0
            
            if is_running and self.current_duty_cycle > 0:
                # Calcular velocidad desde duty cycle
                speed_range = self.config.max_duty_cycle - self.config.min_duty_cycle
                if speed_range > 0:
                    speed_percent = ((self.current_duty_cycle - self.config.min_duty_cycle) / speed_range) * 100.0
                    speed_percent = max(0.0, min(100.0, speed_percent))
            
            return {
                "initialized": True,
                "running": is_running,
                "speed_percent": speed_percent,
                "duty_cycle": self.current_duty_cycle,
                "control_type": "pwm"
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado PWM: {e}")
            return {"error": str(e)}
    
    async def cleanup(self) -> None:
        """Limpiar recursos PWM."""
        if self.pwm_instance:
            self.pwm_instance.stop()
            self.pwm_instance = None
        self._initialized = False

# --- Clase Principal del Controlador ---

class ConveyorBeltController:
    """Controlador avanzado de banda transportadora con recuperación automática."""
    
    def __init__(self, config_file: str = 'Control_Banda/config_industrial.json'):
        self.config_file = config_file
        self.logger = logging.getLogger(f"{__name__}.Controller")
        
        # Estado interno
        self.config = BeltConfiguration()
        self.status = BeltStatus()
        self.metrics = BeltMetrics()
        self.driver: Optional[BeltDriver] = None
        
        # Control de threads
        self._shutdown_event = threading.Event()
        self._monitor_task = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="BeltController")
        
        # Métricas de rendimiento
        self._start_time = time.time()
        self._last_speed_update = time.time()
        self._speed_history = []
        
        # Recovery y health monitoring
        self._error_history = []
        self._recovery_in_progress = False
        
    async def initialize(self) -> bool:
        """Inicializar el controlador de banda."""
        try:
            self.logger.info("Inicializando Controlador de Banda Transportadora v2.1")
            
            # Cargar configuración
            if not await self._load_configuration():
                return False
                
            # Crear driver apropiado
            if not await self._initialize_driver():
                return False
                
            # Iniciar monitoreo
            await self._start_monitoring()
            
            self.status.state = BeltState.IDLE
            self.logger.info("Controlador de banda inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando controlador de banda: {e}")
            self.status.state = BeltState.ERROR
            return False
    
    async def _load_configuration(self) -> bool:
        """Cargar configuración desde archivo."""
        try:
            if not os.path.exists(self.config_file):
                self.logger.error(f"Archivo de configuración no encontrado: {self.config_file}")
                return False
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                
            belt_config = full_config.get('conveyor_belt_settings', {})
            if not belt_config:
                self.logger.error("Sección 'conveyor_belt_settings' no encontrada en configuración")
                return False
                
            # Cargar configuración en dataclass
            self.config = BeltConfiguration(
                control_type=belt_config.get('control_type', 'gpio_on_off'),
                motor_pin_bcm=belt_config.get('motor_pin_bcm'),
                enable_pin_bcm=belt_config.get('enable_pin_bcm'),
                direction_pin_bcm=belt_config.get('direction_pin_bcm'),
                active_state_on=belt_config.get('active_state_on', 'HIGH'),
                pwm_frequency_hz=belt_config.get('pwm_frequency_hz', 100),
                min_duty_cycle=belt_config.get('min_duty_cycle', 20),
                max_duty_cycle=belt_config.get('max_duty_cycle', 100),
                default_speed_percent=belt_config.get('default_speed_percent', 75),
                safety_timeout_s=belt_config.get('safety_timeout_s', 10.0),
                recovery_attempts=belt_config.get('recovery_attempts', 3),
                health_check_interval_s=belt_config.get('health_check_interval_s', 1.0)
            )
            
            self.logger.info(f"Configuración cargada: {self.config.control_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cargando configuración: {e}")
            return False
    
    async def _initialize_driver(self) -> bool:
        """Inicializar el driver apropiado."""
        try:
            control_type = ControlType(self.config.control_type)
            
            if control_type == ControlType.GPIO_ON_OFF:
                self.driver = GPIOOnOffDriver(self.config)
            elif control_type == ControlType.PWM_DC_MOTOR:
                self.driver = PWMDriver(self.config)
            elif control_type == ControlType.EXTERNAL_PLC:
                self.logger.warning("Control PLC externo configurado - funcionalidad limitada")
                return True
            else:
                raise ValueError(f"Tipo de control no soportado: {self.config.control_type}")
                
            if self.driver:
                return await self.driver.initialize()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando driver: {e}")
            return False
    
    async def _start_monitoring(self) -> None:
        """Iniciar monitoreo en segundo plano."""
        try:
            if not self._shutdown_event.is_set():
                self._monitor_task = asyncio.create_task(self._monitor_loop())
                
        except Exception as e:
            self.logger.error(f"Error iniciando monitoreo: {e}")
    
    async def _monitor_loop(self) -> None:
        """Loop de monitoreo en segundo plano."""
        while not self._shutdown_event.is_set():
            try:
                await self._update_status()
                await self._check_health()
                await self._update_metrics()
                await asyncio.sleep(self.config.health_check_interval_s)
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                await asyncio.sleep(1.0)
    
    async def _update_status(self) -> None:
        """Actualizar estado actual."""
        try:
            if self.driver:
                driver_status = await self.driver.get_status()
                self.status.is_running = driver_status.get('running', False)
                self.status.speed_percent = driver_status.get('speed_percent', 0.0)
                
            # Actualizar uptime
            self.status.uptime_s = time.time() - self._start_time
            
            # Simular métricas de hardware (en producción, leer sensores reales)
            if self.status.is_running:
                self.status.current_draw_ma = 250.0 + (self.status.speed_percent * 2.0)
                self.status.temperature_c = 25.0 + (self.status.speed_percent * 0.3)
            else:
                self.status.current_draw_ma = 10.0
                self.status.temperature_c = 25.0
                
        except Exception as e:
            self.logger.error(f"Error actualizando estado: {e}")
    
    async def _check_health(self) -> None:
        """Verificar salud del sistema."""
        try:
            health_score = 100.0
            
            # Verificar temperatura
            if self.status.temperature_c > 60.0:
                health_score -= 20.0
                
            # Verificar corriente
            if self.status.current_draw_ma > 500.0:
                health_score -= 15.0
                
            # Verificar errores recientes
            recent_errors = len([e for e in self._error_history if time.time() - e < 300])  # 5 min
            health_score -= min(recent_errors * 5, 30)
            
            self.status.health_score = max(0.0, health_score)
            
            # Trigger recovery si es necesario
            if self.status.health_score < 50.0 and not self._recovery_in_progress:
                await self._attempt_recovery("Low health score")
                
        except Exception as e:
            self.logger.error(f"Error verificando salud: {e}")
    
    async def _update_metrics(self) -> None:
        """Actualizar métricas de rendimiento."""
        try:
            # Actualizar runtime total
            self.metrics.total_runtime_hours = (time.time() - self._start_time) / 3600.0
            
            # Actualizar velocidad promedio
            if self.status.is_running:
                self._speed_history.append(self.status.speed_percent)
                # Mantener solo últimas 100 lecturas
                if len(self._speed_history) > 100:
                    self._speed_history.pop(0)
                    
                if self._speed_history:
                    self.metrics.avg_speed_percent = sum(self._speed_history) / len(self._speed_history)
                    
            # Calcular efficiency score
            if self.metrics.total_runtime_hours > 0:
                error_rate = self.metrics.error_count / max(self.metrics.total_runtime_hours, 1)
                self.metrics.efficiency_score = max(0.0, 100.0 - (error_rate * 10))
                
        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {e}")
    
    async def _attempt_recovery(self, reason: str) -> bool:
        """Intentar recuperación automática."""
        if self._recovery_in_progress:
            return False
            
        self._recovery_in_progress = True
        self.logger.warning(f"Iniciando recuperación automática: {reason}")
        
        try:
            # Detener banda
            await self.stop_belt()
            await asyncio.sleep(1.0)
            
            # Reinicializar driver
            if self.driver:
                await self.driver.cleanup()
                if await self.driver.initialize():
                    self.status.state = BeltState.IDLE
                    self.logger.info("Recuperación exitosa")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error en recuperación: {e}")
            return False
        finally:
            self._recovery_in_progress = False
    
    # --- API Pública ---
    
    async def start_belt(self, speed_percent: Optional[float] = None) -> bool:
        """Iniciar la banda transportadora."""
        async with asyncio.Lock():
            try:
                if self.status.state == BeltState.ERROR:
                    self.logger.warning("Intentando iniciar banda en estado de error")
                    return False
                    
                if self.status.is_running:
                    self.logger.info("Banda ya está ejecutándose")
                    if speed_percent is not None:
                        return await self.set_speed(speed_percent)
                    return True
                    
                self.status.state = BeltState.STARTING
                
                if not self.driver:
                    raise RuntimeError("Driver no inicializado")
                    
                success = await self.driver.start_belt(speed_percent)
                
                if success:
                    self.status.state = BeltState.RUNNING
                    self.metrics.start_count += 1
                    self.logger.info(f"Banda iniciada exitosamente a {speed_percent or self.config.default_speed_percent}% velocidad")
                else:
                    self.status.state = BeltState.ERROR
                    self.metrics.error_count += 1
                    self._error_history.append(time.time())
                    
                return success
                
            except Exception as e:
                self.logger.error(f"Error iniciando banda: {e}")
                self.status.state = BeltState.ERROR
                self.status.last_error = str(e)
                self.metrics.error_count += 1
                self._error_history.append(time.time())
                return False
    
    async def stop_belt(self) -> bool:
        """Detener la banda transportadora."""
        async with asyncio.Lock():
            try:
                if not self.status.is_running and self.status.state == BeltState.IDLE:
                    self.logger.info("Banda ya está detenida")
                    return True
                    
                self.status.state = BeltState.STOPPING
                
                if not self.driver:
                    self.status.state = BeltState.IDLE
                    return True
                    
                success = await self.driver.stop_belt()
                
                if success:
                    self.status.state = BeltState.IDLE
                    self.logger.info("Banda detenida exitosamente")
                else:
                    self.status.state = BeltState.ERROR
                    self.metrics.error_count += 1
                    self._error_history.append(time.time())
                    
                return success
                
            except Exception as e:
                self.logger.error(f"Error deteniendo banda: {e}")
                self.status.state = BeltState.ERROR
                self.status.last_error = str(e)
                self.metrics.error_count += 1
                self._error_history.append(time.time())
                return False
    
    async def set_speed(self, speed_percent: float) -> bool:
        """Establecer velocidad de la banda."""
        try:
            if not self.driver:
                raise RuntimeError("Driver no inicializado")
                
            # Validar rango
            speed_percent = max(0.0, min(100.0, speed_percent))
            
            success = await self.driver.set_speed(speed_percent)
            
            if success:
                self.logger.info(f"Velocidad establecida a {speed_percent}%")
            else:
                self.logger.error("Error estableciendo velocidad")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error estableciendo velocidad: {e}")
            return False
    
    async def emergency_stop(self) -> bool:
        """Parada de emergencia."""
        try:
            self.logger.warning("PARADA DE EMERGENCIA ACTIVADA")
            self.status.state = BeltState.ERROR
            self.metrics.emergency_stops += 1
            
            if self.driver:
                await self.driver.stop_belt()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error en parada de emergencia: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del sistema."""
        return {
            "status": {
                "state": self.status.state.value,
                "is_running": self.status.is_running,
                "speed_percent": self.status.speed_percent,
                "current_draw_ma": self.status.current_draw_ma,
                "temperature_c": self.status.temperature_c,
                "error_count": self.status.error_count,
                "uptime_s": self.status.uptime_s,
                "last_error": self.status.last_error,
                "health_score": self.status.health_score
            },
            "metrics": {
                "total_runtime_hours": self.metrics.total_runtime_hours,
                "start_count": self.metrics.start_count,
                "error_count": self.metrics.error_count,
                "emergency_stops": self.metrics.emergency_stops,
                "avg_speed_percent": self.metrics.avg_speed_percent,
                "efficiency_score": self.metrics.efficiency_score,
                "last_maintenance": self.metrics.last_maintenance
            },
            "config": {
                "control_type": self.config.control_type,
                "motor_pin_bcm": self.config.motor_pin_bcm,
                "default_speed_percent": self.config.default_speed_percent,
                "safety_timeout_s": self.config.safety_timeout_s
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de rendimiento."""
        return {
            "performance": {
                "total_runtime_hours": self.metrics.total_runtime_hours,
                "start_count": self.metrics.start_count,
                "error_rate": self.metrics.error_count / max(self.metrics.total_runtime_hours, 1),
                "avg_speed_percent": self.metrics.avg_speed_percent,
                "efficiency_score": self.metrics.efficiency_score,
                "health_score": self.status.health_score
            },
            "current": {
                "state": self.status.state.value,
                "is_running": self.status.is_running,
                "speed_percent": self.status.speed_percent,
                "current_draw_ma": self.status.current_draw_ma,
                "temperature_c": self.status.temperature_c,
                "uptime_s": self.status.uptime_s
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
    
    async def reload_config(self) -> bool:
        """Recargar configuración sin reiniciar."""
        try:
            self.logger.info("Recargando configuración...")
            
            # Detener banda si está ejecutándose
            was_running = self.status.is_running
            current_speed = self.status.speed_percent
            
            if was_running:
                await self.stop_belt()
                
            # Limpiar driver actual
            if self.driver:
                await self.driver.cleanup()
                self.driver = None
                
            # Recargar configuración
            if not await self._load_configuration():
                return False
                
            # Reinicializar driver
            if not await self._initialize_driver():
                return False
                
            # Restaurar estado si era necesario
            if was_running:
                await self.start_belt(current_speed)
                
            self.logger.info("Configuración recargada exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recargando configuración: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Limpiar recursos y finalizar."""
        try:
            self.logger.info("Limpiando recursos del controlador de banda...")
            
            # Señalar shutdown
            self._shutdown_event.set()
            
            # Detener banda
            await self.stop_belt()
            
            # Cancelar task de monitoreo
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                    
            # Limpiar driver
            if self.driver:
                await self.driver.cleanup()
                
            # Cerrar executor
            self._executor.shutdown(wait=True)
            
            self.logger.info("Limpieza completada")
            
        except Exception as e:
            self.logger.error(f"Error durante limpieza: {e}")

# --- Funciones de Compatibilidad (Legacy API) ---

# Variables globales para mantener compatibilidad
_controller_instance: Optional[ConveyorBeltController] = None
_loop = None

def _get_or_create_loop():
    """Obtener o crear event loop."""
    global _loop
    try:
        _loop = asyncio.get_event_loop()
    except RuntimeError:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

def _run_async(coro):
    """Ejecutar corrutina de forma sincrónica."""
    loop = _get_or_create_loop()
    if loop.is_running():
        # Si el loop está ejecutándose, crear task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return loop.run_until_complete(coro)

def load_belt_config(config_file='Control_Banda/config_industrial.json'):
    """Función legacy para cargar configuración."""
    global _controller_instance
    try:
        _controller_instance = ConveyorBeltController(config_file)
        success = _run_async(_controller_instance.initialize())
        if success:
            logger.info("Configuración de banda cargada (legacy API)")
        return success
    except Exception as e:
        logger.error(f"Error en load_belt_config legacy: {e}")
        return False

def setup_belt_gpio():
    """Función legacy para configurar GPIO."""
    # La nueva implementación hace esto automáticamente en initialize()
    if _controller_instance:
        logger.info("GPIO configurado automáticamente en nueva implementación")
        return True
    else:
        logger.error("Controlador no inicializado. Ejecute load_belt_config() primero")
        return False

def start_belt(speed_percent=None):
    """Función legacy para iniciar banda."""
    if not _controller_instance:
        logger.error("Controlador no inicializado")
        return False
    return _run_async(_controller_instance.start_belt(speed_percent))

def stop_belt():
    """Función legacy para detener banda."""
    if not _controller_instance:
        logger.error("Controlador no inicializado")
        return False
    return _run_async(_controller_instance.stop_belt())

def set_belt_speed(speed_percent):
    """Función legacy para establecer velocidad."""
    if not _controller_instance:
        logger.error("Controlador no inicializado")
        return False
    return _run_async(_controller_instance.set_speed(speed_percent))

def get_belt_status():
    """Función legacy para obtener estado."""
    if not _controller_instance:
        return {"is_running": False, "speed_percent": 0}
    status = _controller_instance.get_status()
    return {
        "is_running": status["status"]["is_running"],
        "speed_percent": status["status"]["speed_percent"]
    }

def cleanup_belt_gpio():
    """Función legacy para limpiar GPIO."""
    global _controller_instance
    if _controller_instance:
        _run_async(_controller_instance.cleanup())
        _controller_instance = None
    logger.info("Limpieza GPIO completada (legacy API)")

# --- Código de Prueba ---
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    async def test_advanced_controller():
        """Test del controlador avanzado."""
        logger.info("=== Prueba de Controlador Avanzado de Banda ===")
        
        controller = ConveyorBeltController('config_industrial_belt_test.json')
        
        try:
            # Crear config de prueba si no existe
            test_config_path = 'config_industrial_belt_test.json'
            if not os.path.exists(test_config_path):
                test_config = {
                    "conveyor_belt_settings": {
                        "control_type": "pwm_dc_motor",
                        "motor_pin_bcm": 19,
                        "enable_pin_bcm": 26,
                        "direction_pin_bcm": 13,
                        "active_state_on": "HIGH",
                        "pwm_frequency_hz": 100,
                        "min_duty_cycle": 30,
                        "max_duty_cycle": 100,
                        "default_speed_percent": 50,
                        "safety_timeout_s": 10.0,
                        "recovery_attempts": 3,
                        "health_check_interval_s": 1.0
                    }
                }
                with open(test_config_path, 'w') as f:
                    json.dump(test_config, f, indent=4)
                logger.info(f"Configuración de prueba creada: {test_config_path}")

            # Configurar GPIO para test
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
            except Exception as e:
                logger.warning(f"Error configurando GPIO (esperado en simulación): {e}")

            # Inicializar controlador
            if await controller.initialize():
                logger.info("✓ Controlador inicializado")
                
                # Mostrar estado inicial
                status = controller.get_status()
                logger.info(f"Estado inicial: {status['status']['state']}")
                
                # Test de inicio
                logger.info("\n--- Test de Inicio ---")
                if await controller.start_belt(75):
                    logger.info("✓ Banda iniciada al 75%")
                    await asyncio.sleep(2)
                    
                    # Mostrar métricas
                    metrics = controller.get_metrics()
                    logger.info(f"Métricas: {metrics['performance']}")
                    
                    # Test de cambio de velocidad
                    logger.info("\n--- Test de Cambio de Velocidad ---")
                    if await controller.set_speed(50):
                        logger.info("✓ Velocidad cambiada a 50%")
                        await asyncio.sleep(2)
                    
                    # Test de parada
                    logger.info("\n--- Test de Parada ---")
                    if await controller.stop_belt():
                        logger.info("✓ Banda detenida")
                        
                    # Test de recarga de configuración
                    logger.info("\n--- Test de Recarga de Configuración ---")
                    if await controller.reload_config():
                        logger.info("✓ Configuración recargada")
                        
                else:
                    logger.error("✗ Error iniciando banda")
                    
            else:
                logger.error("✗ Error inicializando controlador")
                
        except Exception as e:
            logger.error(f"Error en prueba: {e}")
            
        finally:
            await controller.cleanup()
            try:
                GPIO.cleanup()
            except:
                pass
            logger.info("=== Prueba Finalizada ===")

    # Ejecutar prueba
    asyncio.run(test_advanced_controller())

