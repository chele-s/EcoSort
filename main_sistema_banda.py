# -*- coding: utf-8 -*-
"""
Sistema de Clasificación de Residuos en Banda Transportadora Industrial
EcoSort v2.1 - Enhanced Edition

Autores: Gabriel Calderón, Elias Bautista, Cristian Hernandez
Fecha: Junio de 2025

Este módulo implementa un sistema completo de clasificación automática de residuos
utilizando IA, sensores, y actuadores en una Raspberry Pi con capacidades avanzadas
de recuperación de errores, monitoreo y seguridad.
"""

import asyncio
import cv2
import time
import json
import logging
import threading
import os
import signal
import sys
import psutil
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
from collections import deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import RPi.GPIO as GPIO

# Configuración de logging estructurado con rotación
from logging.handlers import RotatingFileHandler

# Crear directorio de logs si no existe
os.makedirs('logs', exist_ok=True)

# Configuración de logging avanzada
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler para archivo con rotación
file_handler = RotatingFileHandler(
    'logs/ecosort.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Configurar logger raíz
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """Estados del sistema de clasificación"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


class ErrorSeverity(Enum):
    """Niveles de severidad de errores"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SystemError(Exception):
    """Excepción base para errores del sistema"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, component: str = None):
        super().__init__(message)
        self.severity = severity
        self.component = component
        self.timestamp = datetime.now()


class ConfigurationError(SystemError):
    """Error de configuración del sistema"""
    pass


class HardwareError(SystemError):
    """Error de hardware del sistema"""
    pass


class AIError(SystemError):
    """Error del modelo de IA"""
    pass


class SecurityError(SystemError):
    """Error de seguridad del sistema"""
    pass


@dataclass
class ClassificationResult:
    """Resultado de clasificación de un objeto"""
    object_id: int
    classification_db_id: Optional[int]
    category_name: str
    category_index: int
    confidence: float
    processing_time_ms: float
    detection_time: float
    error_message: Optional[str] = None
    is_error: bool = False


@dataclass
class SystemMetrics:
    """Métricas avanzadas del sistema"""
    objects_processed: int = 0
    successful_classifications: int = 0
    failed_classifications: int = 0
    diversions_attempted: int = 0
    diversions_successful: int = 0
    system_uptime: float = 0.0
    average_processing_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    temperature_celsius: float = 0.0
    error_count_by_severity: Dict[str, int] = field(default_factory=dict)
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None


@dataclass
class SystemAlert:
    """Alerta del sistema"""
    alert_id: str
    severity: ErrorSeverity
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class ErrorRecoveryManager:
    """Gestor de recuperación automática de errores"""
    
    def __init__(self, config: 'ConfigManager'):
        self.config = config
        self.recovery_strategies: Dict[str, Callable] = {}
        self.active_alerts: Dict[str, SystemAlert] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        self.max_recovery_attempts = 3
        self.cooldown_period = 30  # segundos
        self.last_recovery_attempt = {}
        
        self._register_recovery_strategies()
    
    def _register_recovery_strategies(self):
        """Registra estrategias de recuperación para diferentes tipos de errores"""
        self.recovery_strategies.update({
            'camera_failure': self._recover_camera,
            'ai_model_failure': self._recover_ai_model,
            'hardware_failure': self._recover_hardware,
            'network_failure': self._recover_network,
            'memory_leak': self._recover_memory,
            'high_temperature': self._handle_overheating
        })
    
    async def handle_error(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Maneja un error y trata de recuperarse automáticamente"""
        try:
            error_type = self._classify_error(error)
            alert_id = f"{error_type}_{int(time.time())}"
            
            # Crear alerta
            alert = SystemAlert(
                alert_id=alert_id,
                severity=error.severity,
                component=error.component or 'unknown',
                message=str(error),
                timestamp=datetime.now()
            )
            
            self.active_alerts[alert_id] = alert
            
            # Verificar si podemos intentar recuperación
            if not self._can_attempt_recovery(error_type):
                logger.error(f"No se puede intentar recuperación para {error_type} - en cooldown o excedido max intentos")
                return False
            
            # Intentar recuperación
            if error_type in self.recovery_strategies:
                logger.info(f"Intentando recuperación automática para {error_type}")
                recovery_success = await self.recovery_strategies[error_type](error, system)
                
                self._record_recovery_attempt(error_type, recovery_success)
                
                if recovery_success:
                    alert.resolved = True
                    alert.resolution_time = datetime.now()
                    logger.info(f"Recuperación exitosa para {error_type}")
                    return True
                else:
                    logger.error(f"Fallo en recuperación automática para {error_type}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error en el gestor de recuperación: {e}")
            return False
    
    def _classify_error(self, error: SystemError) -> str:
        """Clasifica el tipo de error para seleccionar estrategia de recuperación"""
        error_msg = str(error).lower()
        
        if 'camera' in error_msg or 'captur' in error_msg:
            return 'camera_failure'
        elif 'model' in error_msg or 'ia' in error_msg or 'ai' in error_msg:
            return 'ai_model_failure'
        elif 'gpio' in error_msg or 'hardware' in error_msg or 'actuator' in error_msg:
            return 'hardware_failure'
        elif 'network' in error_msg or 'api' in error_msg or 'connection' in error_msg:
            return 'network_failure'
        elif 'memory' in error_msg or 'ram' in error_msg:
            return 'memory_leak'
        elif 'temperature' in error_msg or 'overheat' in error_msg:
            return 'high_temperature'
        else:
            return 'unknown_error'
    
    def _can_attempt_recovery(self, error_type: str) -> bool:
        """Verifica si se puede intentar recuperación"""
        now = time.time()
        
        if error_type not in self.last_recovery_attempt:
            return True
        
        last_attempt = self.last_recovery_attempt[error_type]
        
        # Verificar cooldown
        if now - last_attempt['timestamp'] < self.cooldown_period:
            return False
        
        # Verificar número de intentos
        if last_attempt['attempts'] >= self.max_recovery_attempts:
            # Reset después de 1 hora
            if now - last_attempt['timestamp'] > 3600:
                self.last_recovery_attempt[error_type] = {'attempts': 0, 'timestamp': now}
                return True
            return False
        
        return True
    
    def _record_recovery_attempt(self, error_type: str, success: bool):
        """Registra intento de recuperación"""
        now = time.time()
        
        if error_type not in self.last_recovery_attempt:
            self.last_recovery_attempt[error_type] = {'attempts': 0, 'timestamp': now}
        
        self.last_recovery_attempt[error_type]['attempts'] += 1
        self.last_recovery_attempt[error_type]['timestamp'] = now
        
        self.recovery_history.append({
            'error_type': error_type,
            'timestamp': datetime.now(),
            'success': success
        })
        
        # Mantener solo los últimos 100 registros
        if len(self.recovery_history) > 100:
            self.recovery_history = self.recovery_history[-100:]
    
    async def _recover_camera(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia de recuperación para fallos de cámara"""
        try:
            # Liberar cámara actual
            if system.components.camera and system.components.camera.isOpened():
                system.components.camera.release()
            
            await asyncio.sleep(1)
            
            # Reinicializar cámara
            await system.components._initialize_camera()
            
            # Probar captura
            ret, frame = system.components.camera.read()
            return ret and frame is not None
            
        except Exception as e:
            logger.error(f"Error en recuperación de cámara: {e}")
            return False
    
    async def _recover_ai_model(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia de recuperación para fallos del modelo IA"""
        try:
            # Reinicializar modelo IA
            await system.components._initialize_ai_model()
            
            # Probar clasificación dummy
            if system.components.ai_detector:
                dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
                detections = system.components.ai_detector.detect_objects(dummy_image)
                return True  # Si no hay excepción, el modelo está funcionando
            
            return False
            
        except Exception as e:
            logger.error(f"Error en recuperación de modelo IA: {e}")
            return False
    
    async def _recover_hardware(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia de recuperación para fallos de hardware"""
        try:
            # Limpiar y reinicializar GPIO
            GPIO.cleanup()
            await asyncio.sleep(0.5)
            
            # Reinicializar hardware
            await system.components._initialize_hardware()
            
            return True
            
        except Exception as e:
            logger.error(f"Error en recuperación de hardware: {e}")
            return False
    
    async def _recover_network(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia de recuperación para fallos de red"""
        try:
            # Reinicializar API si está disponible
            if hasattr(system.components, 'api_server'):
                await system.components._initialize_database_and_api()
            
            return True
            
        except Exception as e:
            logger.error(f"Error en recuperación de red: {e}")
            return False
    
    async def _recover_memory(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia de recuperación para problemas de memoria"""
        try:
            import gc
            
            # Forzar garbage collection
            gc.collect()
            
            # Limpiar caches si existen
            if hasattr(system, 'object_queue'):
                system.object_queue.clear()
            
            await asyncio.sleep(1)
            
            # Verificar mejora en memoria
            memory_percent = psutil.virtual_memory().percent
            return memory_percent < 90
            
        except Exception as e:
            logger.error(f"Error en recuperación de memoria: {e}")
            return False
    
    async def _handle_overheating(self, error: SystemError, system: 'EcoSortSystem') -> bool:
        """Estrategia para manejar sobrecalentamiento"""
        try:
            logger.warning("Sistema sobrecalentado - pausando operación")
            
            # Pausar sistema
            if system.state == SystemState.RUNNING:
                system.pause()
            
            # Esperar enfriamiento
            for i in range(30):  # Esperar hasta 30 segundos
                await asyncio.sleep(1)
                temp = self._get_cpu_temperature()
                if temp < 65:  # Temperatura aceptable
                    # Reanudar operación
                    if system.state == SystemState.PAUSED:
                        system.resume()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error manejando sobrecalentamiento: {e}")
            return False
    
    def _get_cpu_temperature(self) -> float:
        """Obtiene temperatura del CPU"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return temp
        except:
            return 0.0


class SecurityManager:
    """Gestor de seguridad del sistema"""
    
    def __init__(self, config: 'ConfigManager'):
        self.config = config
        self.failed_attempts = {}
        self.blocked_ips = set()
        self.api_keys = set()
        self.emergency_stop_active = False
        
        # Cargar configuración de seguridad
        self._load_security_config()
    
    def _load_security_config(self):
        """Carga configuración de seguridad"""
        safety_config = self.config.get('safety_settings', {})
        self.emergency_stop_enabled = safety_config.get('emergency_stop_enabled', True)
        self.max_failed_attempts = safety_config.get('max_failed_attempts', 5)
        self.lockout_duration = safety_config.get('lockout_duration_minutes', 30)
    
    def check_emergency_stop(self) -> bool:
        """Verifica estado del botón de parada de emergencia"""
        if not self.emergency_stop_enabled:
            return False
        
        try:
            from Control_Banda.RPi_control_bajo_nivel import sensor_interface
            return sensor_interface.check_emergency_stop()
        except:
            return False
    
    def validate_api_access(self, request_ip: str, api_key: str = None) -> bool:
        """Valida acceso a la API"""
        # Verificar IP bloqueada
        if request_ip in self.blocked_ips:
            return False
        
        # Verificar API key si está habilitada
        api_config = self.config.get('api_settings', {})
        if api_config.get('api_key_required', False):
            if not api_key or api_key not in self.api_keys:
                self._record_failed_attempt(request_ip)
                return False
        
        return True
    
    def _record_failed_attempt(self, ip: str):
        """Registra intento de acceso fallido"""
        now = datetime.now()
        
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = []
        
        self.failed_attempts[ip].append(now)
        
        # Limpiar intentos antiguos
        cutoff = now - timedelta(minutes=self.lockout_duration)
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip] 
            if attempt > cutoff
        ]
        
        # Bloquear IP si excede intentos máximos
        if len(self.failed_attempts[ip]) >= self.max_failed_attempts:
            self.blocked_ips.add(ip)
            logger.warning(f"IP {ip} bloqueada por exceder intentos de acceso")


class PerformanceMonitor:
    """Monitor de rendimiento del sistema"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.performance_alerts = []
        self.monitoring_active = True
        
        # Umbrales de alerta
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.temp_threshold = 70.0
        self.processing_time_threshold = 5000.0  # ms
    
    async def collect_system_metrics(self) -> Dict[str, float]:
        """Recolecta métricas del sistema"""
        try:
            metrics = {
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'temperature': self._get_cpu_temperature(),
                'network_bytes_sent': psutil.net_io_counters().bytes_sent,
                'network_bytes_recv': psutil.net_io_counters().bytes_recv
            }
            
            # Agregar a historial
            self.metrics_history.append(metrics)
            
            # Verificar umbrales
            await self._check_performance_thresholds(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recolectando métricas: {e}")
            return {}
    
    async def _check_performance_thresholds(self, metrics: Dict[str, float]):
        """Verifica umbrales de rendimiento"""
        alerts = []
        
        if metrics['cpu_percent'] > self.cpu_threshold:
            alerts.append(f"CPU al {metrics['cpu_percent']:.1f}%")
        
        if metrics['memory_percent'] > self.memory_threshold:
            alerts.append(f"Memoria al {metrics['memory_percent']:.1f}%")
        
        if metrics['temperature'] > self.temp_threshold:
            alerts.append(f"Temperatura {metrics['temperature']:.1f}°C")
        
        for alert in alerts:
            if alert not in [a['message'] for a in self.performance_alerts[-10:]]:
                self.performance_alerts.append({
                    'timestamp': datetime.now(),
                    'message': alert,
                    'severity': 'warning'
                })
                logger.warning(f"Alerta de rendimiento: {alert}")
    
    def _get_cpu_temperature(self) -> float:
        """Obtiene temperatura del CPU"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return temp
        except:
            return 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de rendimiento"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-10:]
        
        return {
            'avg_cpu': sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics),
            'avg_memory': sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics),
            'current_temp': recent_metrics[-1]['temperature'],
            'recent_alerts': self.performance_alerts[-5:],
            'metrics_count': len(self.metrics_history)
        }


class ConfigManager:
    """Gestor centralizado de configuración con validación avanzada"""
    
    def __init__(self, config_file: str = 'Control_Banda/config_industrial.json'):
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._config_timestamp = 0
        self._validation_schema = self._create_validation_schema()
        self._load_and_validate()
    
    def _load_and_validate(self) -> None:
        """Carga y valida la configuración"""
        try:
            if not os.path.exists(self.config_file):
                raise ConfigurationError(f"Archivo de configuración no encontrado: {self.config_file}")
            
            # Verificar si el archivo ha cambiado
            file_timestamp = os.path.getmtime(self.config_file)
            if file_timestamp <= self._config_timestamp:
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            # Validar configuración
            self._validate_config(new_config)
            
            # Verificar compatibilidad de versión
            self._validate_version_compatibility(new_config)
            
            # Si llegamos aquí, la configuración es válida
            self._config = new_config
            self._config_timestamp = file_timestamp
            
            logger.info(f"Configuración cargada y validada desde {self.config_file}")
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Error de formato JSON en {self.config_file}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error cargando configuración: {e}")
    
    def _create_validation_schema(self) -> Dict[str, Any]:
        """Crea esquema de validación para la configuración"""
        return {
            'required_sections': [
                'camera_settings',
                'ai_model_settings', 
                'conveyor_belt_settings',
                'sensors_settings',
                'diverter_control_settings'
            ],
            'optional_sections': [
                'database_settings',
                'api_settings',
                'monitoring_settings',
                'safety_settings',
                'calibration_settings'
            ],
            'version_requirements': {
                'min_version': '2.0',
                'max_version': '3.0'
            }
        }
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Valida la estructura de configuración con esquema avanzado"""
        schema = self._validation_schema
        
        # Verificar secciones requeridas
        for section in schema['required_sections']:
            if section not in config:
                raise ConfigurationError(f"Sección requerida '{section}' no encontrada en configuración")
        
        # Validar configuración de IA
        ai_config = config['ai_model_settings']
        if not ai_config.get('model_path'):
            raise ConfigurationError("'model_path' requerido en ai_model_settings")
        
        if not ai_config.get('class_names'):
            raise ConfigurationError("'class_names' requerido en ai_model_settings")
        
        # Validar que el archivo del modelo existe
        model_path = ai_config['model_path']
        if not os.path.exists(model_path):
            raise ConfigurationError(f"Archivo del modelo no encontrado: {model_path}")
        
        # Validar configuración de cámara
        cam_config = config['camera_settings']
        if cam_config.get('frame_width', 0) <= 0 or cam_config.get('frame_height', 0) <= 0:
            raise ConfigurationError("Dimensiones de cámara inválidas")
        
        # Validar configuración de banda
        belt_config = config['conveyor_belt_settings']
        if belt_config.get('belt_speed_mps', 0) <= 0:
            raise ConfigurationError("Velocidad de banda debe ser positiva")
        
        # Validar configuración de desviadores
        diverter_config = config['diverter_control_settings']
        if not diverter_config.get('diverters'):
            raise ConfigurationError("No hay desviadores configurados")
        
        # Validar que cada desviador tiene configuración válida
        for name, diverter in diverter_config['diverters'].items():
            if 'type' not in diverter:
                raise ConfigurationError(f"Tipo no especificado para desviador {name}")
            
            if diverter['type'] == 'stepper_A4988':
                required_keys = ['dir_pin_bcm', 'step_pin_bcm']
                for key in required_keys:
                    if key not in diverter:
                        raise ConfigurationError(f"Clave '{key}' requerida para desviador stepper {name}")
            
            elif diverter['type'] == 'gpio_on_off':
                required_keys = ['pin_bcm', 'active_state']
                for key in required_keys:
                    if key not in diverter:
                        raise ConfigurationError(f"Clave '{key}' requerida para desviador ON/OFF {name}")
    
    def _validate_version_compatibility(self, config: Dict[str, Any]) -> None:
        """Valida compatibilidad de versión"""
        config_version = config.get('version', '1.0')
        min_version = self._validation_schema['version_requirements']['min_version']
        max_version = self._validation_schema['version_requirements']['max_version']
        
        if config_version < min_version:
            raise ConfigurationError(f"Versión de configuración {config_version} obsoleta. Mínima: {min_version}")
        
        if config_version >= max_version:
            logger.warning(f"Versión de configuración {config_version} es muy nueva. Máxima probada: {max_version}")
    
    def reload_if_changed(self) -> bool:
        """Recarga configuración si el archivo ha cambiado"""
        try:
            old_timestamp = self._config_timestamp
            self._load_and_validate()
            
            if self._config_timestamp > old_timestamp:
                logger.info("Configuración recargada automáticamente")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recargando configuración: {e}")
            return False
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Obtiene un valor de configuración con validación"""
        # Verificar si necesita recargar
        self.reload_if_changed()
        
        if key is None:
            return self._config.get(section, default)
        return self._config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any, persist: bool = False) -> bool:
        """Establece un valor de configuración dinámicamente"""
        try:
            if section not in self._config:
                self._config[section] = {}
            
            old_value = self._config[section].get(key)
            self._config[section][key] = value
            
            # Validar nueva configuración
            self._validate_config(self._config)
            
            if persist:
                self._save_config()
            
            logger.info(f"Configuración actualizada: {section}.{key} = {value} (era {old_value})")
            return True
            
        except Exception as e:
            # Revertir cambio si falla validación
            if old_value is not None:
                self._config[section][key] = old_value
            else:
                self._config[section].pop(key, None)
            
            logger.error(f"Error actualizando configuración: {e}")
            return False
    
    def _save_config(self) -> None:
        """Guarda configuración actual al archivo"""
        try:
            # Crear backup
            backup_file = f"{self.config_file}.backup"
            if os.path.exists(self.config_file):
                os.rename(self.config_file, backup_file)
            
            # Guardar nueva configuración
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            # Actualizar timestamp
            self._config_timestamp = os.path.getmtime(self.config_file)
            
            logger.info(f"Configuración guardada en {self.config_file}")
            
        except Exception as e:
            # Restaurar backup si algo sale mal
            if os.path.exists(backup_file):
                os.rename(backup_file, self.config_file)
            raise ConfigurationError(f"Error guardando configuración: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Obtiene toda la configuración"""
        self.reload_if_changed()
        return self._config.copy()
    
    def get_validation_errors(self) -> List[str]:
        """Obtiene lista de errores de validación sin lanzar excepción"""
        errors = []
        try:
            self._validate_config(self._config)
        except ConfigurationError as e:
            errors.append(str(e))
        return errors


class ComponentManager:
    """Gestor avanzado de componentes del sistema"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.camera: Optional[cv2.VideoCapture] = None
        self.ai_detector = None
        self.database = None
        self.api_server = None
        self.error_recovery: Optional[ErrorRecoveryManager] = None
        self.security_manager: Optional[SecurityManager] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        
        self._components_initialized = False
        self._initialization_order = [
            'error_recovery',
            'security_manager', 
            'performance_monitor',
            'hardware',
            'camera',
            'ai_model',
            'database_and_api'
        ]
        self._component_status = {}
    
    async def initialize_all(self) -> None:
        """Inicializa todos los componentes del sistema en orden"""
        try:
            logger.info("Inicializando componentes del sistema...")
            
            for component in self._initialization_order:
                try:
                    await self._initialize_component(component)
                    self._component_status[component] = 'initialized'
                    logger.info(f"Componente {component} inicializado correctamente")
                    
                except Exception as e:
                    self._component_status[component] = f'error: {str(e)}'
                    logger.error(f"Error inicializando {component}: {e}")
                    
                    # Algunos componentes son críticos
                    if component in ['hardware', 'camera', 'ai_model']:
                        raise SystemError(f"Componente crítico {component} falló: {e}", 
                                        ErrorSeverity.CRITICAL, component)
            
            self._components_initialized = True
            logger.info("Todos los componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
            await self._cleanup_partial_initialization()
            raise SystemError(f"Fallo en inicialización: {e}")
    
    async def _initialize_component(self, component: str) -> None:
        """Inicializa un componente específico"""
        if component == 'error_recovery':
            self.error_recovery = ErrorRecoveryManager(self.config)
        
        elif component == 'security_manager':
            self.security_manager = SecurityManager(self.config)
        
        elif component == 'performance_monitor':
            self.performance_monitor = PerformanceMonitor()
        
        elif component == 'hardware':
            await self._initialize_hardware()
        
        elif component == 'camera':
            await self._initialize_camera()
        
        elif component == 'ai_model':
            await self._initialize_ai_model()
        
        elif component == 'database_and_api':
            await self._initialize_database_and_api()
        
        else:
            raise ValueError(f"Componente desconocido: {component}")
    
    async def _cleanup_partial_initialization(self) -> None:
        """Limpia componentes parcialmente inicializados"""
        logger.info("Limpiando inicialización parcial...")
        
        # Limpiar en orden inverso
        for component in reversed(self._initialization_order):
            if self._component_status.get(component) == 'initialized':
                try:
                    if component == 'camera' and self.camera:
                        self.camera.release()
                        self.camera = None
                    elif component == 'hardware':
                        GPIO.cleanup()
                    
                    self._component_status[component] = 'cleaned'
                    
                except Exception as e:
                    logger.error(f"Error limpiando {component}: {e}")
    
    async def _initialize_hardware(self) -> None:
        """Inicializa las interfaces de hardware con validación avanzada"""
        try:
            # Importar módulos de hardware
            from Control_Banda.RPi_control_bajo_nivel import sensor_interface as band_sensors
            from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
            from Control_Banda.RPi_control_bajo_nivel import motor_driver_interface
            
            # Configurar GPIO con validación
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
            except Exception as e:
                raise HardwareError(f"Error configurando GPIO: {e}", ErrorSeverity.CRITICAL, 'gpio')
            
            # Inicializar sensores con reintentos
            for attempt in range(3):
                try:
                    if not band_sensors.load_sensor_config(self.config.config_file):
                        raise HardwareError("Error cargando configuración de sensores")
                    
                    if not band_sensors.setup_sensor_gpio():
                        raise HardwareError("Error configurando GPIOs de sensores")
                    
                    break
                    
                except Exception as e:
                    if attempt == 2:  # Último intento
                        raise HardwareError(f"Error en sensores después de 3 intentos: {e}", 
                                          ErrorSeverity.HIGH, 'sensors')
                    await asyncio.sleep(1)
            
            # Inicializar control de banda
            if not belt_controller.load_belt_config(self.config.config_file):
                raise HardwareError("Error cargando configuración de banda", 
                                  ErrorSeverity.HIGH, 'conveyor_belt')
            
            if not belt_controller.setup_belt_gpio():
                raise HardwareError("Error configurando GPIOs de banda", 
                                  ErrorSeverity.HIGH, 'conveyor_belt')
            
            # Inicializar actuadores de desviación
            if not motor_driver_interface.load_diverter_configuration(self.config.config_file):
                raise HardwareError("Error cargando configuración de desviadores", 
                                  ErrorSeverity.HIGH, 'diverters')
            
            if not motor_driver_interface.setup_diverter_gpio():
                raise HardwareError("Error configurando GPIOs de desviadores", 
                                  ErrorSeverity.HIGH, 'diverters')
            
            logger.info("Hardware inicializado correctamente")
            
        except ImportError as e:
            raise HardwareError(f"Error importando módulos de hardware: {e}", 
                              ErrorSeverity.CRITICAL, 'imports')
    
    async def _initialize_camera(self) -> None:
        """Inicializa la cámara con configuración avanzada"""
        try:
            cam_settings = self.config.get('camera_settings')
            cam_index = cam_settings.get('index', 0)
            width = cam_settings.get('frame_width', 640)
            height = cam_settings.get('frame_height', 480)
            
            # Intentar varios índices de cámara si falla
            camera_indices = [cam_index, 0, 1, 2] if cam_index != 0 else [0, 1, 2]
            
            for idx in camera_indices:
                try:
                    self.camera = cv2.VideoCapture(idx)
                    if self.camera.isOpened():
                        cam_index = idx
                        break
                    self.camera.release()
                except:
                    continue
            else:
                raise HardwareError("No se encontró ninguna cámara disponible", 
                                  ErrorSeverity.CRITICAL, 'camera')
            
            # Configurar propiedades de cámara
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Configuraciones opcionales
            if 'fps' in cam_settings:
                self.camera.set(cv2.CAP_PROP_FPS, cam_settings['fps'])
            
            if not cam_settings.get('autofocus', True):
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            if 'exposure' in cam_settings:
                self.camera.set(cv2.CAP_PROP_EXPOSURE, cam_settings['exposure'])
            
            if 'brightness' in cam_settings:
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, cam_settings['brightness'])
            
            if 'contrast' in cam_settings:
                self.camera.set(cv2.CAP_PROP_CONTRAST, cam_settings['contrast'])
            
            # Probar captura
            for _ in range(cam_settings.get('warmup_frames', 5)):
                ret, frame = self.camera.read()
                if not ret:
                    raise HardwareError("Error en captura de prueba de cámara", 
                                      ErrorSeverity.HIGH, 'camera')
            
            # Verificar dimensiones reales
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width != width or actual_height != height:
                logger.warning(f"Resolución de cámara diferente a la solicitada: "
                             f"{actual_width}x{actual_height} vs {width}x{height}")
            
            logger.info(f"Cámara inicializada: Índice {cam_index}, Resolución {actual_width}x{actual_height}")
            
        except Exception as e:
            if isinstance(e, HardwareError):
                raise
            raise HardwareError(f"Error inicializando cámara: {e}", ErrorSeverity.HIGH, 'camera')
    
    async def _initialize_ai_model(self) -> None:
        """Inicializa el modelo de IA con validación"""
        try:
            from IA_Clasificacion.Trash_detect import TrashDetector
            
            ai_settings = self.config.get('ai_model_settings')
            model_path = ai_settings['model_path']
            min_confidence = ai_settings.get('min_confidence', 0.5)
            
            # Verificar archivo del modelo
            if not os.path.exists(model_path):
                raise AIError(f"Archivo del modelo no encontrado: {model_path}", 
                            ErrorSeverity.CRITICAL, 'ai_model')
            
            # Verificar tamaño del archivo
            model_size = os.path.getsize(model_path)
            if model_size < 1024:  # Menos de 1KB probablemente sea inválido
                raise AIError(f"Archivo del modelo parece inválido (tamaño: {model_size} bytes)", 
                            ErrorSeverity.CRITICAL, 'ai_model')
            
            # Inicializar detector
            self.ai_detector = TrashDetector(model_path, min_confidence)
            
            # Validar clases del modelo
            if not hasattr(self.ai_detector, 'model_class_names') or not self.ai_detector.model_class_names:
                raise AIError("Modelo no tiene clases definidas", 
                            ErrorSeverity.CRITICAL, 'ai_model')
            
            logger.info(f"Modelo de IA cargado desde {model_path}")
            logger.info(f"Clases detectables: {self.ai_detector.model_class_names}")
            
            # Validar compatibilidad entre clases del modelo y configuración
            model_classes = set(self.ai_detector.model_class_names)
            config_classes = set(ai_settings['class_names'])
            
            missing_classes = config_classes - model_classes - {'other', 'Desconocido', 'ErrorClase', 'ErrorIA'}
            if missing_classes:
                logger.warning(f"Clases en config no disponibles en modelo: {missing_classes}")
            
            # Prueba de inferencia
            try:
                dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
                detections = self.ai_detector.detect_objects(dummy_image)
                logger.info("Prueba de inferencia exitosa")
            except Exception as e:
                raise AIError(f"Fallo en prueba de inferencia: {e}", 
                            ErrorSeverity.HIGH, 'ai_model')
            
        except ImportError as e:
            raise AIError(f"Error importando detector de IA: {e}", 
                        ErrorSeverity.CRITICAL, 'ai_imports')
        except Exception as e:
            if isinstance(e, AIError):
                raise
            raise AIError(f"Error inicializando modelo de IA: {e}", 
                        ErrorSeverity.HIGH, 'ai_model')
    
    async def _initialize_database_and_api(self) -> None:
        """Inicializa la base de datos y API con manejo de errores mejorado"""
        try:
            from InterfazUsuario_Monitoreo.Backend.database_enhanced import DatabaseManagerEnhanced
            from InterfazUsuario_Monitoreo.Backend.api_enhanced import create_api
            
            # Inicializar base de datos
            try:
                self.database = DatabaseManager()
                
                # Verificar conexión
                self.database.log_system_event('startup', 'info', 'Sistema EcoSort v2.1 iniciado')
                
                logger.info("Base de datos inicializada correctamente")
                
            except Exception as e:
                logger.warning(f"Error inicializando base de datos: {e}")
                self.database = None
            
            # Inicializar API si está habilitada
            api_config = self.config.get('api_settings', {})
            if api_config.get('enabled', True):
                try:
                    host = api_config.get('host', '0.0.0.0')
                    port = api_config.get('port', 5000)
                    
                    self.api_server = create_api(self.database, host=host, port=port)
                    
                    # Iniciar en hilo separado
                    api_thread = threading.Thread(
                        target=self.api_server.run,
                        kwargs={
                            'debug': api_config.get('debug', False),
                            'threaded': True
                        },
                        daemon=True,
                        name='EcoSortAPI'
                    )
                    api_thread.start()
                    
                    # Esperar a que inicie
                    await asyncio.sleep(1)
                    
                    logger.info(f"API inicializada en http://{host}:{port}")
                    
                except Exception as e:
                    logger.warning(f"Error inicializando API: {e}")
                    self.api_server = None
            else:
                logger.info("API deshabilitada en configuración")
            
        except ImportError as e:
            logger.warning(f"Módulos de BD/API no disponibles: {e}")
            # No es crítico, el sistema puede funcionar sin BD/API
    
    def is_initialized(self) -> bool:
        """Verifica si todos los componentes están inicializados"""
        return self._components_initialized
    
    def get_component_status(self) -> Dict[str, str]:
        """Obtiene estado de todos los componentes"""
        return self._component_status.copy()
    
    async def restart_component(self, component: str) -> bool:
        """Reinicia un componente específico"""
        try:
            logger.info(f"Reiniciando componente {component}")
            
            # Limpiar componente actual
            if component == 'camera' and self.camera:
                self.camera.release()
                self.camera = None
            
            # Reinicializar
            await self._initialize_component(component)
            self._component_status[component] = 'restarted'
            
            logger.info(f"Componente {component} reiniciado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error reiniciando componente {component}: {e}")
            self._component_status[component] = f'restart_failed: {str(e)}'
            return False


class EcoSortSystem:
    """Sistema principal de clasificación de residuos con capacidades avanzadas"""
    
    def __init__(self, config_file: str = 'Control_Banda/config_industrial.json'):
        self.config = ConfigManager(config_file)
        self.components = ComponentManager(self.config)
        self.state = SystemState.INITIALIZING
        self.metrics = SystemMetrics()
        
        # Control de ejecución
        self._running = False
        self._shutdown_event = threading.Event()
        self._maintenance_mode = False
        
        # Queue para objetos detectados con límite
        self.object_queue: deque = deque(maxlen=100)
        self.active_diversions: Dict[int, Dict[str, Any]] = {}
        self.last_object_id = 0
        
        # Monitoreo de rendimiento
        self._performance_task = None
        self._recovery_task = None
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.start_time = time.time()
        
        # Configuración de logging específica para esta instancia
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Maneja señales del sistema para shutdown graceful"""
        self.logger.info(f"Señal {signum} recibida, iniciando shutdown...")
        self.request_shutdown()
    
    async def initialize(self) -> None:
        """Inicializa el sistema completo con validaciones"""
        try:
            self.logger.info("=== INICIANDO ECOSORT SYSTEM v2.1 ===")
            
            # Verificar requisitos del sistema
            await self._check_system_requirements()
            
            # Inicializar componentes
            await self.components.initialize_all()
            
            # Verificar configuración post-inicialización
            await self._post_initialization_checks()
            
            # Iniciar tareas de monitoreo
            await self._start_monitoring_tasks()
            
            self.state = SystemState.IDLE
            self.logger.info("Sistema inicializado correctamente")
            
        except Exception as e:
            self.state = SystemState.ERROR
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.now()
            
            # Intentar recuperación automática si es posible
            if self.components.error_recovery:
                self.logger.info("Intentando recuperación automática...")
                self.state = SystemState.RECOVERING
                
                recovery_success = await self.components.error_recovery.handle_error(e, self)
                
                if recovery_success:
                    self.logger.info("Recuperación exitosa - reiniciando operación")
                    self.metrics.successful_recoveries += 1
                    # Reintentar operación
                    await self.start()
                    return
                else:
                    self.metrics.recovery_attempts += 1
            
            self.logger.error(f"Error inicializando sistema: {e}")
            raise
    
    async def _check_system_requirements(self) -> None:
        """Verifica requisitos del sistema antes de inicializar"""
        # Verificar espacio en disco
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 1:  # Menos de 1GB libre
            raise SystemError("Espacio en disco insuficiente", ErrorSeverity.HIGH, 'storage')
        
        # Verificar memoria disponible
        memory = psutil.virtual_memory()
        if memory.available < 512 * 1024 * 1024:  # Menos de 512MB
            raise SystemError("Memoria RAM insuficiente", ErrorSeverity.HIGH, 'memory')
        
        # Verificar temperatura
        try:
            temp = self._get_cpu_temperature()
            if temp > 80:
                raise SystemError(f"Temperatura CPU muy alta: {temp}°C", 
                                ErrorSeverity.HIGH, 'temperature')
        except:
            pass  # Sensor de temperatura no disponible
        
        self.logger.info(f"Requisitos del sistema verificados - Disco: {free_gb:.1f}GB, RAM: {memory.available/(1024**2):.0f}MB")
    
    def _get_cpu_temperature(self) -> float:
        """Obtiene temperatura del CPU"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return temp
        except:
            return 0.0
    
    async def _post_initialization_checks(self) -> None:
        """Verificaciones post-inicialización"""
        # Verificar que los componentes críticos están funcionando
        if not self.components.camera or not self.components.camera.isOpened():
            raise HardwareError("Cámara no disponible", ErrorSeverity.CRITICAL, 'camera')
        
        if not self.components.ai_detector:
            raise AIError("Modelo de IA no disponible", ErrorSeverity.CRITICAL, 'ai_model')
        
        # Probar captura y clasificación
        try:
            ret, frame = self.components.camera.read()
            if ret and frame is not None:
                detections = self.components.ai_detector.detect_objects(frame)
                self.logger.info("Prueba de captura y clasificación exitosa")
            else:
                raise HardwareError("Error en prueba de captura", ErrorSeverity.HIGH, 'camera')
        except Exception as e:
            raise SystemError(f"Error en prueba post-inicialización: {e}", 
                            ErrorSeverity.HIGH, 'integration_test')
    
    async def _start_monitoring_tasks(self) -> None:
        """Inicia tareas de monitoreo en segundo plano"""
        if self.components.performance_monitor:
            self._performance_task = asyncio.create_task(
                self._performance_monitoring_loop()
            )
            self.logger.info("Monitoreo de rendimiento iniciado")
        
        # Tarea de verificación de configuración
        self._config_check_task = asyncio.create_task(
            self._config_check_loop()
        )
        
        # Tarea de verificación de seguridad
        if self.components.security_manager:
            self._security_task = asyncio.create_task(
                self._security_check_loop()
            )
    
    async def _performance_monitoring_loop(self) -> None:
        """Bucle de monitoreo de rendimiento"""
        while self._running and not self._shutdown_event.is_set():
            try:
                if self.components.performance_monitor:
                    metrics = await self.components.performance_monitor.collect_system_metrics()
                    
                    # Actualizar métricas del sistema
                    self.metrics.cpu_usage_percent = metrics.get('cpu_percent', 0)
                    self.metrics.memory_usage_percent = metrics.get('memory_percent', 0)
                    self.metrics.temperature_celsius = metrics.get('temperature', 0)
                
                await asyncio.sleep(10)  # Cada 10 segundos
                
            except Exception as e:
                self.logger.error(f"Error en monitoreo de rendimiento: {e}")
                await asyncio.sleep(30)
    
    async def _config_check_loop(self) -> None:
        """Bucle de verificación de configuración"""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Verificar si la configuración ha cambiado
                config_changed = self.config.reload_if_changed()
                
                if config_changed:
                    self.logger.info("Configuración actualizada - aplicando cambios")
                    await self._apply_config_changes()
                
                await asyncio.sleep(30)  # Cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"Error verificando configuración: {e}")
                await asyncio.sleep(60)
    
    async def _security_check_loop(self) -> None:
        """Bucle de verificación de seguridad"""
        while self._running and not self._shutdown_event.is_set():
            try:
                if self.components.security_manager:
                    # Verificar parada de emergencia
                    emergency_stop = self.components.security_manager.check_emergency_stop()
                    
                    if emergency_stop and not self.components.security_manager.emergency_stop_active:
                        self.logger.critical("PARADA DE EMERGENCIA ACTIVADA")
                        self.components.security_manager.emergency_stop_active = True
                        await self._emergency_stop()
                    
                    elif not emergency_stop and self.components.security_manager.emergency_stop_active:
                        self.logger.info("Parada de emergencia desactivada")
                        self.components.security_manager.emergency_stop_active = False
                        # Requerir reinicio manual después de emergencia
                        self.state = SystemState.MAINTENANCE
                
                await asyncio.sleep(1)  # Cada segundo para verificaciones de seguridad
                
            except Exception as e:
                self.logger.error(f"Error en verificación de seguridad: {e}")
                await asyncio.sleep(5)
    
    async def _apply_config_changes(self) -> None:
        """Aplica cambios de configuración dinámicamente"""
        try:
            # Reiniciar componentes afectados por cambios de configuración
            # Por ahora, solo logging level
            new_level = self.config.get('logging_level', 'INFO')
            logging.getLogger().setLevel(getattr(logging, new_level))
            
            self.logger.info(f"Nivel de logging actualizado a {new_level}")
            
        except Exception as e:
            self.logger.error(f"Error aplicando cambios de configuración: {e}")
    
    async def _emergency_stop(self) -> None:
        """Ejecuta secuencia de parada de emergencia"""
        self.logger.critical("Ejecutando secuencia de parada de emergencia")
        
        try:
            # Detener banda inmediatamente
            from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
            belt_controller.stop_belt()
            
            # Parar todos los actuadores
            from Control_Banda.RPi_control_bajo_nivel import motor_driver_interface
            manager = motor_driver_interface.get_diverter_manager()
            manager.stop_all()
            
            # Cambiar estado
            self.state = SystemState.ERROR
            self._running = False
            
            self.logger.critical("Parada de emergencia completada")
            
        except Exception as e:
            self.logger.critical(f"Error en parada de emergencia: {e}")
    
    async def start(self) -> None:
        """Inicia el sistema de clasificación con manejo avanzado de errores"""
        if not self.components.is_initialized():
            raise SystemError("Sistema no inicializado")
        
        if self.state not in [SystemState.IDLE, SystemState.PAUSED]:
            raise SystemError(f"No se puede iniciar desde estado {self.state}")
        
        try:
            self.logger.info("Iniciando sistema de clasificación...")
            self.state = SystemState.RUNNING
            self._running = True
            
            # Verificar parada de emergencia antes de iniciar
            if (self.components.security_manager and 
                self.components.security_manager.check_emergency_stop()):
                raise SecurityError("Parada de emergencia activa", 
                                  ErrorSeverity.CRITICAL, 'emergency_stop')
            
            # Iniciar banda transportadora
            await self._start_conveyor_belt()
            
            # Iniciar bucle principal
            await self._main_loop()
            
        except Exception as e:
            self.state = SystemState.ERROR
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.now()
            
            # Intentar recuperación automática
            if self.components.error_recovery:
                self.logger.info("Intentando recuperación automática...")
                self.state = SystemState.RECOVERING
                
                recovery_success = await self.components.error_recovery.handle_error(e, self)
                
                if recovery_success:
                    self.logger.info("Recuperación exitosa - reiniciando operación")
                    self.metrics.successful_recoveries += 1
                    # Reintentar operación
                    await self.start()
                    return
                else:
                    self.metrics.recovery_attempts += 1
            
            self.logger.error(f"Error en ejecución del sistema: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _start_conveyor_belt(self) -> None:
        """Inicia la banda transportadora con verificaciones"""
        try:
            from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
            
            # Verificar estado antes de iniciar
            belt_status = belt_controller.get_belt_status()
            if belt_status.get('is_running', False):
                self.logger.warning("Banda ya estaba en funcionamiento")
                return
            
            default_speed = self.config.get('conveyor_belt_settings', 'default_speed_percent', 75)
            
            if belt_controller.start_belt(speed_percent=default_speed):
                self.logger.info(f"Banda transportadora iniciada ({default_speed}%)")
                
                # Verificar que realmente está funcionando
                await asyncio.sleep(0.5)
                belt_status = belt_controller.get_belt_status()
                if not belt_status.get('is_running', False):
                    raise HardwareError("Banda no confirmó inicio", 
                                      ErrorSeverity.HIGH, 'conveyor_belt')
            else:
                raise HardwareError("Fallo al iniciar banda transportadora", 
                                  ErrorSeverity.HIGH, 'conveyor_belt')
                
        except Exception as e:
            if isinstance(e, HardwareError):
                raise
            raise HardwareError(f"Error iniciando banda: {e}", 
                              ErrorSeverity.HIGH, 'conveyor_belt')
    
    async def _main_loop(self) -> None:
        """Bucle principal de operación con manejo avanzado de errores"""
        self.logger.info("Iniciando bucle principal...")
        
        last_bin_check = time.time()
        last_metrics_update = time.time()
        bin_check_interval = self.config.get('system_settings', 'bin_check_interval_s', 30)
        metrics_interval = 5  # Actualizar métricas cada 5 segundos
        
        consecutive_errors = 0
        max_consecutive_errors = self.config.get('system_settings', 'max_processing_errors', 10)
        
        try:
            while self._running and not self._shutdown_event.is_set():
                loop_start_time = time.time()
                
                try:
                    # Verificar parada de emergencia
                    if (self.components.security_manager and 
                        self.components.security_manager.emergency_stop_active):
                        self.logger.warning("Operación pausada por parada de emergencia")
                        await asyncio.sleep(1)
                        continue
                    
                    # Verificar modo mantenimiento
                    if self._maintenance_mode:
                        await asyncio.sleep(1)
                        continue
                    
                    # Verificar trigger de objeto
                    if await self._wait_for_object_trigger():
                        await self._process_detected_object()
                        consecutive_errors = 0  # Reset contador de errores
                    
                    # Procesar queue de objetos
                    await self._process_object_queue()
                    
                    # Verificar niveles de tolva periódicamente
                    if time.time() - last_bin_check > bin_check_interval:
                        await self._check_bin_levels()
                        last_bin_check = time.time()
                    
                    # Actualizar métricas periódicamente
                    if time.time() - last_metrics_update > metrics_interval:
                        self._update_metrics()
                        last_metrics_update = time.time()
                    
                    # Control de velocidad del bucle
                    loop_time = time.time() - loop_start_time
                    if loop_time < 0.01:  # Mínimo 10ms entre iteraciones
                        await asyncio.sleep(0.01 - loop_time)
                
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"Error en bucle principal (#{consecutive_errors}): {e}")
                    
                    # Si hay muchos errores consecutivos, intentar recuperación
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error(f"Demasiados errores consecutivos ({consecutive_errors})")
                        
                        if self.components.error_recovery:
                            recovery_success = await self.components.error_recovery.handle_error(
                                SystemError(f"Errores consecutivos: {e}", ErrorSeverity.HIGH), self
                            )
                            
                            if recovery_success:
                                consecutive_errors = 0
                                self.logger.info("Recuperación exitosa después de errores múltiples")
                            else:
                                self.logger.error("Recuperación falló - deteniendo sistema")
                                break
                        else:
                            break
                    
                    # Pausa antes del siguiente intento
                    await asyncio.sleep(min(consecutive_errors * 0.1, 2.0))
        
        except Exception as e:
            self.logger.error(f"Error crítico en bucle principal: {e}")
            raise
        
        finally:
            self.logger.info("Bucle principal terminado")
    
    async def _wait_for_object_trigger(self) -> bool:
        """Espera trigger de objeto con timeout"""
        try:
            from Control_Banda.RPi_control_bajo_nivel import sensor_interface as band_sensors
            
            # Verificar trigger sin bloqueo
            return band_sensors.check_camera_trigger()
            
        except Exception as e:
            self.logger.error(f"Error verificando trigger: {e}")
            return False
    
    async def _process_detected_object(self) -> None:
        """Procesa un objeto detectado con manejo completo de errores"""
        process_start_time = time.time()
        object_id = None
        
        try:
            capture_time = time.time()
            
            # Capturar imagen
            image = await self._capture_image()
            if image is None:
                self.metrics.failed_classifications += 1
                return
            
            self.last_object_id += 1
            object_id = self.last_object_id
            
            # Clasificar objeto
            result = await self._classify_object(object_id, image, process_start_time)
            
            # Registrar en base de datos
            if self.components.database and not result.is_error:
                try:
                    result.classification_db_id = self.components.database.record_classification(
                        category=result.category_name,
                        confidence=result.confidence,
                        processing_time_ms=result.processing_time_ms,
                        diverter_activated=False,  # Se actualizará después
                        error_occurred=result.is_error,
                        error_message=result.error_message
                    )
                except Exception as e:
                    self.logger.warning(f"Error registrando en BD: {e}")
            
            # Añadir a queue para procesamiento de desviación
            if not result.is_error and result.category_index >= 0:
                try:
                    self.object_queue.append((
                        object_id,
                        result.classification_db_id,
                        result.category_index,
                        capture_time,
                        result.confidence
                    ))
                except Exception as e:
                    self.logger.error(f"Error añadiendo a queue: {e}")
            
            # Guardar imagen si está configurado
            await self._save_image_if_configured(image, object_id, result)
            
            # Actualizar métricas
            self.metrics.objects_processed += 1
            if result.is_error:
                self.metrics.failed_classifications += 1
                self.metrics.error_count_by_severity[result.error_message or 'unknown'] = \
                    self.metrics.error_count_by_severity.get(result.error_message or 'unknown', 0) + 1
            else:
                self.metrics.successful_classifications += 1
            
            # Actualizar tiempo promedio de procesamiento
            total_time = (time.time() - process_start_time) * 1000
            if self.metrics.objects_processed > 0:
                self.metrics.average_processing_time_ms = (
                    (self.metrics.average_processing_time_ms * (self.metrics.objects_processed - 1) + total_time) 
                    / self.metrics.objects_processed
                )
            
            self.logger.info(f"Objeto {object_id} procesado: {result.category_name} "
                           f"({result.confidence:.2f}) en {total_time:.1f}ms")
            
        except Exception as e:
            self.logger.error(f"Error procesando objeto detectado (ID: {object_id}): {e}")
            self.metrics.failed_classifications += 1
            
            # Intentar recuperación si es un error recurrente
            if "camera" in str(e).lower() or "captur" in str(e).lower():
                if self.components.error_recovery:
                    await self.components.error_recovery.handle_error(
                        HardwareError(str(e), ErrorSeverity.MEDIUM, 'camera'), self
                    )
    
    async def _capture_image(self) -> Optional[np.ndarray]:
        """Captura una imagen con reintentos y validación"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if not self.components.camera or not self.components.camera.isOpened():
                    raise HardwareError("Cámara no disponible", ErrorSeverity.HIGH, 'camera')
                
                ret, frame = self.components.camera.read()
                if not ret or frame is None:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1)
                        continue
                    raise HardwareError("Error capturando frame", ErrorSeverity.MEDIUM, 'camera')
                
                # Validar imagen
                if frame.size == 0:
                    raise HardwareError("Frame vacío", ErrorSeverity.MEDIUM, 'camera')
                
                return frame
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Error capturando imagen después de {max_retries} intentos: {e}")
                    return None
                await asyncio.sleep(0.1)
        
        return None
    
    def enter_maintenance_mode(self) -> None:
        """Entra en modo mantenimiento"""
        self._maintenance_mode = True
        self.state = SystemState.MAINTENANCE
        self.metrics.last_maintenance = datetime.now()
        self.logger.info("Sistema en modo mantenimiento")
    
    def exit_maintenance_mode(self) -> None:
        """Sale del modo mantenimiento"""
        self._maintenance_mode = False
        if self._running:
            self.state = SystemState.RUNNING
        else:
            self.state = SystemState.IDLE
        self.logger.info("Sistema salió del modo mantenimiento")
    
    def pause(self) -> None:
        """Pausa el sistema de manera segura"""
        if self.state == SystemState.RUNNING:
            self.state = SystemState.PAUSED
            self.logger.info("Sistema pausado")
    
    def resume(self) -> None:
        """Reanuda el sistema"""
        if self.state == SystemState.PAUSED:
            self.state = SystemState.RUNNING
            self.logger.info("Sistema reanudado")
    
    def request_shutdown(self) -> None:
        """Solicita shutdown del sistema"""
        self.logger.info("Shutdown solicitado...")
        self._running = False
        self._shutdown_event.set()
    
    async def shutdown(self) -> None:
        """Shutdown completo del sistema con limpieza avanzada"""
        if self.state == SystemState.SHUTDOWN:
            return
        
        self.logger.info("Iniciando shutdown del sistema...")
        self.state = SystemState.SHUTTING_DOWN
        
        try:
            # Cancelar tareas de monitoreo
            tasks_to_cancel = []
            if self._performance_task:
                tasks_to_cancel.append(self._performance_task)
            if hasattr(self, '_config_check_task'):
                tasks_to_cancel.append(self._config_check_task)
            if hasattr(self, '_security_task'):
                tasks_to_cancel.append(self._security_task)
            
            for task in tasks_to_cancel:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        self.logger.error(f"Error cancelando tarea: {e}")
            
            # Detener banda transportadora
            try:
                from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
                belt_controller.stop_belt()
                self.logger.info("Banda transportadora detenida")
            except Exception as e:
                self.logger.error(f"Error deteniendo banda: {e}")
            
            # Esperar a que terminen las diversiones activas
            if self.active_diversions:
                self.logger.info(f"Esperando {len(self.active_diversions)} diversiones activas...")
                max_wait_time = 10  # segundos
                wait_start = time.time()
                
                while self.active_diversions and (time.time() - wait_start) < max_wait_time:
                    await asyncio.sleep(0.1)
                
                # Forzar limpieza si algunas no terminaron
                if self.active_diversions:
                    self.logger.warning(f"Forzando limpieza de {len(self.active_diversions)} diversiones pendientes")
                    self.active_diversions.clear()
            
            # Limpiar componentes
            await self._cleanup_components()
            
            # Registrar evento final
            if self.components.database:
                try:
                    self.components.database.log_system_event(
                        'shutdown', 'info', 
                        f'Sistema detenido correctamente. Objetos procesados: {self.metrics.objects_processed}'
                    )
                except Exception as e:
                    self.logger.error(f"Error registrando evento final: {e}")
            
            self.state = SystemState.SHUTDOWN
            self.logger.info("=== SISTEMA DETENIDO CORRECTAMENTE ===")
            
        except Exception as e:
            self.logger.error(f"Error durante shutdown: {e}")
            self.state = SystemState.ERROR
    
    async def _cleanup_components(self) -> None:
        """Limpia todos los componentes del sistema"""
        self.logger.info("Limpiando componentes del sistema...")
        
        # Limpiar cámara
        if self.components.camera and self.components.camera.isOpened():
            self.components.camera.release()
            self.logger.info("Cámara liberada")
        
        # Limpiar hardware
        try:
            from Control_Banda.RPi_control_bajo_nivel import sensor_interface as band_sensors
            from Control_Banda.RPi_control_bajo_nivel import conveyor_belt_controller as belt_controller
            from Control_Banda.RPi_control_bajo_nivel import motor_driver_interface
            
            band_sensors.cleanup_sensor_gpio()
            belt_controller.cleanup_belt_gpio()
            motor_driver_interface.cleanup_gpio_diverters()
            GPIO.cleanup()
            
            self.logger.info("Hardware limpiado")
            
        except Exception as e:
            self.logger.error(f"Error limpiando hardware: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado completo del sistema"""
        return {
            'state': self.state.value,
            'uptime_seconds': time.time() - self.start_time,
            'metrics': {
                'objects_processed': self.metrics.objects_processed,
                'successful_classifications': self.metrics.successful_classifications,
                'failed_classifications': self.metrics.failed_classifications,
                'diversions_attempted': self.metrics.diversions_attempted,
                'diversions_successful': self.metrics.diversions_successful,
                'average_processing_time_ms': self.metrics.average_processing_time_ms,
                'cpu_usage_percent': self.metrics.cpu_usage_percent,
                'memory_usage_percent': self.metrics.memory_usage_percent,
                'temperature_celsius': self.metrics.temperature_celsius,
                'error_count_by_severity': self.metrics.error_count_by_severity,
                'recovery_attempts': self.metrics.recovery_attempts,
                'successful_recoveries': self.metrics.successful_recoveries,
                'last_error': self.metrics.last_error,
                'last_maintenance': self.metrics.last_maintenance.isoformat() if self.metrics.last_maintenance else None
            },
            'active_diversions': len(self.active_diversions),
            'queue_size': len(self.object_queue),
            'components_initialized': self.components.is_initialized(),
            'component_status': self.components.get_component_status(),
            'maintenance_mode': self._maintenance_mode,
            'config_version': self.config.get('version', 'unknown'),
            'performance_summary': (
                self.components.performance_monitor.get_performance_summary() 
                if self.components.performance_monitor else {}
            ),
            'alerts': (
                list(self.components.error_recovery.active_alerts.values())[-10:] 
                if self.components.error_recovery else []
            )
        }
    
    def get_detailed_diagnostics(self) -> Dict[str, Any]:
        """Obtiene diagnósticos detallados del sistema"""
        diagnostics = {
            'system_info': {
                'platform': sys.platform,
                'python_version': sys.version,
                'pid': os.getpid(),
                'working_directory': os.getcwd()
            },
            'hardware_status': {},
            'configuration_status': {
                'config_file': self.config.config_file,
                'config_timestamp': self.config._config_timestamp,
                'validation_errors': self.config.get_validation_errors()
            },
            'recent_errors': [],
            'performance_history': []
        }
        
        # Hardware status
        try:
            diagnostics['hardware_status'] = {
                'gpio_mode': GPIO.getmode(),
                'camera_available': self.components.camera and self.components.camera.isOpened(),
                'ai_model_loaded': self.components.ai_detector is not None,
            }
        except:
            pass
        
        # Recent errors from recovery manager
        if self.components.error_recovery:
            diagnostics['recent_errors'] = self.components.error_recovery.recovery_history[-10:]
        
        # Performance history
        if self.components.performance_monitor:
            diagnostics['performance_history'] = list(self.components.performance_monitor.metrics_history)[-20:]
        
        return diagnostics

    async def _classify_object(self, object_id: int, image, process_start: float) -> ClassificationResult:
        """Clasifica un objeto usando IA con manejo avanzado de errores"""
        try:
            if not self.components.ai_detector:
                raise AIError("Detector de IA no disponible", ErrorSeverity.HIGH, 'ai_model')
            
            # Realizar detección
            detections = self.components.ai_detector.detect_objects(image)
            processing_time_ms = (time.time() - process_start) * 1000
            
            system_class_names = self.config.get('ai_model_settings', 'class_names')

            if not detections:
                # No se detectó nada
                category_name = self._get_fallback_category(system_class_names)
                category_index = self._get_category_index(category_name, system_class_names)
                
                return ClassificationResult(
                    object_id=object_id,
                    classification_db_id=None,
                    category_name=category_name,
                    category_index=category_index,
                    confidence=0.0,
                    processing_time_ms=processing_time_ms,
                    detection_time=time.time()
                )
            
            # Tomar la mejor detección
            best_detection = max(detections, key=lambda d: d[1])
            detected_class, confidence, _ = best_detection
            
            # Mapear a clases del sistema
            if detected_class in system_class_names:
                category_name = detected_class
                category_index = system_class_names.index(detected_class)
            else:
                category_name = self._get_fallback_category(system_class_names)
                category_index = self._get_category_index(category_name, system_class_names)
            
            return ClassificationResult(
                object_id=object_id,
                classification_db_id=None,
                category_name=category_name,
                category_index=category_index,
                confidence=float(confidence),
                processing_time_ms=processing_time_ms,
                detection_time=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Error clasificando objeto {object_id}: {e}")
            
            # Retornar resultado de error
            error_category = "ErrorIA"
            system_class_names = self.config.get('ai_model_settings', 'class_names')
            error_index = self._get_category_index(error_category, system_class_names, default=-2)
            
            return ClassificationResult(
                object_id=object_id,
                classification_db_id=None,
                category_name=error_category,
                category_index=error_index,
                confidence=0.0,
                processing_time_ms=(time.time() - process_start) * 1000,
                detection_time=time.time(),
                error_message=str(e),
                is_error=True
            )
    
    def _get_fallback_category(self, system_class_names: List[str]) -> str:
        """Obtiene categoría de fallback para objetos no reconocidos"""
        if 'other' in system_class_names:
            return 'other'
        elif 'Desconocido' in system_class_names:
            return 'Desconocido'
        else:
            return 'other'  # Fallback por defecto
    
    def _get_category_index(self, category_name: str, system_class_names: List[str], default: int = -1) -> int:
        """Obtiene el índice de una categoría"""
        try:
            return system_class_names.index(category_name)
        except ValueError:
            return default
    
    async def _save_image_if_configured(self, image, object_id: int, result: ClassificationResult) -> None:
        """Guarda imagen si está configurado con mejoras de seguridad"""
        try:
            if not self.config.get('system_settings', 'save_images', False):
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            images_dir = 'captures'
            os.makedirs(images_dir, exist_ok=True)
            
            # Verificar espacio disponible
            disk_usage = psutil.disk_usage(images_dir)
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 0.5:  # Menos de 500MB
                self.logger.warning("Poco espacio en disco, omitiendo captura de imagen")
                return
            
            filename = f"obj_{object_id}_{result.category_name}_{timestamp}.jpg"
            image_path = os.path.join(images_dir, filename)
            
            # Guardar con calidad configurada
            image_quality = self.config.get('system_settings', 'image_quality', 85)
            cv2.imwrite(image_path, image, [cv2.IMWRITE_JPEG_QUALITY, image_quality])
            
            self.logger.debug(f"Imagen guardada: {image_path}")
            
        except Exception as e:
            self.logger.error(f"Error guardando imagen: {e}")
    
    async def _process_object_queue(self) -> None:
        """Procesa la queue de objetos para desviación con límites de procesamiento"""
        max_objects_per_iteration = 5  # Limitar procesamiento por iteración
        processed_count = 0
        
        while self.object_queue and processed_count < max_objects_per_iteration:
            try:
                object_data = self.object_queue.popleft()
                await self._schedule_diversion(*object_data)
                processed_count += 1
                
            except Exception as e:
                self.logger.error(f"Error procesando queue de objetos: {e}")
                break
    
    async def _schedule_diversion(self, object_id: int, classification_id: int, 
                                 category_index: int, detection_time: float, confidence: float) -> None:
        """Agenda la activación de un desviador con validaciones mejoradas"""
        try:
            system_class_names = self.config.get('ai_model_settings', 'class_names')
            if category_index < 0 or category_index >= len(system_class_names):
                self.logger.warning(f"Índice de categoría inválido: {category_index}")
                return

            category_name = system_class_names[category_index]
            
            # Verificar si requiere desviación
            distances = self.config.get('conveyor_belt_settings', 'distance_camera_to_diverters_m', {})
            
            if category_name.lower() == 'other' or category_name not in distances:
                self.logger.info(f"Objeto {object_id} ({category_name}) no requiere desviación")
                if self.components.database:
                    try:
                        self.components.database.update_classification_diversion_status(
                            classification_id, diverter_activated=False
                        )
                    except Exception as e:
                        self.logger.warning(f"Error actualizando BD: {e}")
                return

            # Calcular delay
            distance = distances[category_name]
            belt_speed = self.config.get('conveyor_belt_settings', 'belt_speed_mps', 0.1)
            
            if belt_speed <= 0:
                raise ValueError(f"Velocidad de banda inválida: {belt_speed}")
            
            delay_s = distance / belt_speed
            
            # Validar delay razonable
            if delay_s > 30:  # Más de 30 segundos es sospechoso
                self.logger.warning(f"Delay muy largo para objeto {object_id}: {delay_s:.1f}s")
                return
            
            # Verificar que el desviador esté disponible
            if hasattr(self.components, 'diverter_manager'):
                diverter_status = self.components.diverter_manager.get_diverter_status(category_name)
                if diverter_status and diverter_status.state not in [ActuatorState.IDLE, ActuatorState.DISABLED]:
                    self.logger.warning(f"Desviador {category_name} ocupado, omitiendo objeto {object_id}")
                    return
            
            # Crear y ejecutar tarea de desviación
            task = threading.Thread(
                target=self._diversion_task,
                args=(object_id, classification_id, category_name, category_index, delay_s),
                daemon=True,
                name=f'Diversion-{object_id}'
            )
            
            self.active_diversions[object_id] = {
                'thread': task,
                'classification_id': classification_id,
                'activation_time': time.time() + delay_s,
                'category': category_name,
                'confidence': confidence,
                'created_time': time.time()
            }
            
            task.start()
            self.metrics.diversions_attempted += 1
            
            self.logger.info(f"Desviación agendada para objeto {object_id} ({category_name}) en {delay_s:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error agendando desviación para objeto {object_id}: {e}")
    
    def _diversion_task(self, object_id: int, classification_id: int, category_name: str, 
                       category_index: int, delay_s: float) -> None:
        """Tarea de desviación ejecutada en hilo separado con mejoras de seguridad"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Esperando {delay_s:.2f}s para desviar objeto {object_id} ({category_name})")
            
            # Esperar con verificaciones periódicas
            sleep_interval = 0.1
            elapsed = 0
            
            while elapsed < delay_s:
                # Verificar si el sistema sigue funcionando
                if not self._running or self._shutdown_event.is_set():
                    self.logger.info(f"Cancelando desviación para objeto {object_id} - sistema detenido")
                    return
                
                # Verificar parada de emergencia
                if (self.components.security_manager and 
                    self.components.security_manager.emergency_stop_active):
                    self.logger.warning(f"Cancelando desviación para objeto {object_id} - parada de emergencia")
                    return
                
                time.sleep(min(sleep_interval, delay_s - elapsed))
                elapsed = time.time() - start_time
            
            # Activar desviador
            actuation_start = time.time()
            success = self._activate_diverter(category_name)
            actuation_time_ms = (time.time() - actuation_start) * 1000
            
            if success:
                self.metrics.diversions_successful += 1
                self.logger.info(f"Desviación exitosa para objeto {object_id} ({category_name}) "
                               f"en {actuation_time_ms:.1f}ms")
            else:
                self.logger.error(f"Fallo en desviación para objeto {object_id} ({category_name})")
            
            # Actualizar base de datos
            if self.components.database:
                try:
                    self.components.database.update_classification_diversion_status(
                        classification_id=classification_id,
                        diverter_activated=success,
                        actuation_time_ms=actuation_time_ms,
                        error_message=None if success else f"Fallo activando desviador {category_name}"
                    )
                except Exception as e:
                    self.logger.warning(f"Error actualizando BD para objeto {object_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error en tarea de desviación para objeto {object_id}: {e}")
            
            if self.components.database:
                try:
                    self.components.database.update_classification_diversion_status(
                        classification_id=classification_id,
                        diverter_activated=False,
                        error_message=str(e)
                    )
                except Exception as e:
                    self.logger.warning(f"Error actualizando BD con error: {e}")
                    
        finally:
            # Limpiar de diversiones activas
            if object_id in self.active_diversions:
                del self.active_diversions[object_id]
    
    def _activate_diverter(self, category_name: str) -> bool:
        """Activa un desviador específico con validaciones"""
        try:
            from Control_Banda.RPi_control_bajo_nivel import motor_driver_interface
            
            duration = self.config.get('conveyor_belt_settings', 'diverter_activation_duration_s', 0.75)
            
            # Validar duración
            if duration <= 0 or duration > 10:
                self.logger.warning(f"Duración de activación inválida: {duration}s")
                duration = 0.75
            
            return motor_driver_interface.activate_diverter(category_name, duration)
            
        except Exception as e:
            self.logger.error(f"Error activando desviador {category_name}: {e}")
            return False
    
    async def _check_bin_levels(self) -> None:
        """Verifica niveles de tolvas con alertas mejoradas"""
        try:
            from Control_Banda.RPi_control_bajo_nivel import sensor_interface as band_sensors
            
            levels = band_sensors.get_all_bin_fill_levels()
            
            for bin_name, level in levels.items():
                if level is not None:
                    self.logger.debug(f"Nivel tolva {bin_name}: {level:.1f}%")
                    
                    # Actualizar en base de datos
                    if self.components.database:
                        try:
                            threshold = self.config.get('sensors_settings', 'bin_level_sensors', 
                                                      'settings_common', 'full_threshold_percent', 80.0)
                            critical_threshold = self.config.get('sensors_settings', 'bin_level_sensors',
                                                               'settings_common', 'critical_threshold_percent', 95.0)
                            
                            alert_triggered = level > threshold
                            critical_alert = level > critical_threshold
                            
                            self.components.database.update_bin_status(bin_name, level, alert_triggered)
                            
                            # Generar alertas
                            if critical_alert:
                                self.logger.critical(f"ALERTA CRÍTICA: Tolva {bin_name} al {level:.1f}%")
                                self.components.database.log_system_event(
                                    'alert', 'critical',
                                    f'Tolva {bin_name} al {level:.1f}% - ACCIÓN REQUERIDA',
                                    {'bin': bin_name, 'level': level, 'threshold': critical_threshold}
                                )
                                
                                # Considerar pausar sistema si está muy lleno
                                if level > 98:
                                    self.logger.critical(f"Tolva {bin_name} al {level:.1f}% - PAUSANDO SISTEMA")
                                    self.pause()
                                    
                            elif alert_triggered:
                                self.logger.warning(f"ALERTA: Tolva {bin_name} al {level:.1f}%")
                                self.components.database.log_system_event(
                                    'alert', 'warning',
                                    f'Tolva {bin_name} al {level:.1f}%',
                                    {'bin': bin_name, 'level': level, 'threshold': threshold}
                                )
                        except Exception as e:
                            self.logger.warning(f"Error actualizando estado de tolva {bin_name}: {e}")
                            
        except Exception as e:
            self.logger.error(f"Error verificando niveles de tolva: {e}")
    
    def _update_metrics(self) -> None:
        """Actualiza métricas del sistema con cálculos avanzados"""
        self.metrics.system_uptime = time.time() - self.start_time
        
        # Calcular tasa de éxito
        if self.metrics.objects_processed > 0:
            success_rate = (self.metrics.successful_classifications / self.metrics.objects_processed) * 100
            diversion_rate = (self.metrics.diversions_successful / max(self.metrics.diversions_attempted, 1)) * 100
            
            # Log métricas periódicamente
            if self.metrics.objects_processed % 100 == 0:  # Cada 100 objetos
                self.logger.info(f"Métricas del sistema - Objetos: {self.metrics.objects_processed}, "
                               f"Éxito clasificación: {success_rate:.1f}%, "
                               f"Éxito desviación: {diversion_rate:.1f}%")


async def main():
    """Función principal del sistema mejorada"""
    system = None
    try:
        # Verificar argumentos de línea de comandos
        import argparse
        parser = argparse.ArgumentParser(description='EcoSort Industrial v2.1 - Sistema de Clasificación de Residuos')
        parser.add_argument('--config', '-c', default='Control_Banda/config_industrial.json',
                          help='Archivo de configuración')
        parser.add_argument('--debug', '-d', action='store_true',
                          help='Activar modo debug')
        parser.add_argument('--simulation', '-s', action='store_true',
                          help='Modo simulación (sin hardware)')
        parser.add_argument('--maintenance', '-m', action='store_true',
                          help='Iniciar en modo mantenimiento')
        
        args = parser.parse_args()
        
        # Configurar nivel de logging
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Modo debug activado")
        
        # Crear e inicializar sistema
        system = EcoSortSystem(args.config)
        
        # Modo simulación
        if args.simulation:
            logger.info("=== MODO SIMULACIÓN ACTIVADO ===")
            # Aquí se podrían desactivar los módulos de hardware real
        
        await system.initialize()
        
        # Modo mantenimiento
        if args.maintenance:
            system.enter_maintenance_mode()
            logger.info("Sistema iniciado en modo mantenimiento")
        
        # Mostrar información del sistema
        logger.info("=== CONFIGURACIÓN DEL SISTEMA ===")
        ai_classes = system.config.get('ai_model_settings', 'class_names')
        belt_speed = system.config.get('conveyor_belt_settings', 'belt_speed_mps')
        confidence = system.config.get('ai_model_settings', 'min_confidence')
        api_config = system.config.get('api_settings', {})
        
        logger.info(f"Clases detectables: {ai_classes}")
        logger.info(f"Velocidad de banda: {belt_speed} m/s")
        logger.info(f"Umbral de confianza: {confidence}")
        
        if api_config.get('enabled', True):
            host = api_config.get('host', 'localhost')
            port = api_config.get('port', 5000)
            logger.info(f"API de monitoreo: http://{host}:{port}")
        
        logger.info("=" * 50)
        
        # Verificar niveles iniciales
        await system._check_bin_levels()
        
        # Mostrar estado de componentes
        component_status = system.components.get_component_status()
        logger.info("Estado de componentes:")
        for component, status in component_status.items():
            logger.info(f"  {component}: {status}")
        
        # Verificar si hay alertas de configuración
        config_errors = system.config.get_validation_errors()
        if config_errors:
            logger.warning("Errores de configuración detectados:")
            for error in config_errors:
                logger.warning(f"  - {error}")
        
        # Iniciar sistema
        if not args.maintenance:
            logger.info("Iniciando operación automática...")
            await system.start()
        else:
            logger.info("Sistema en espera en modo mantenimiento")
            logger.info("Use 'exit_maintenance_mode()' para iniciar operación normal")
            
            # Mantener sistema vivo en modo mantenimiento
            try:
                while system.state == SystemState.MAINTENANCE:
                    await asyncio.sleep(1)
                    
                # Si sale de mantenimiento, iniciar operación
                if system.state == SystemState.IDLE:
                    await system.start()
                    
            except KeyboardInterrupt:
                logger.info("Saliendo del modo mantenimiento...")

    except KeyboardInterrupt:
        logger.info("Interrupción por teclado recibida")
    except SystemError as e:
        logger.error(f"Error del sistema: {e}")
        if hasattr(e, 'severity') and e.severity == ErrorSeverity.CRITICAL:
            logger.critical("Error crítico detectado - verificar hardware y configuración")
    except Exception as e:
        logger.error(f"Error fatal en main: {e}", exc_info=True)
    finally:
        if system:
            try:
                # Generar reporte final si está configurado
                if system.config.get('system_settings', 'generate_final_report', False):
                    await generate_final_report(system)
                
                await system.shutdown()
                
                # Mostrar resumen final
                status = system.get_status()
                logger.info("=== RESUMEN FINAL ===")
                logger.info(f"Tiempo de operación: {status['uptime_seconds']:.1f} segundos")
                logger.info(f"Objetos procesados: {status['metrics']['objects_processed']}")
                logger.info(f"Clasificaciones exitosas: {status['metrics']['successful_classifications']}")
                logger.info(f"Diversiones exitosas: {status['metrics']['diversions_successful']}")
                logger.info("====================")
                
            except Exception as e:
                logger.error(f"Error en limpieza final: {e}")


async def generate_final_report(system: EcoSortSystem) -> None:
    """Genera reporte final del sistema"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'reports/ecosort_report_{timestamp}.json'
        
        os.makedirs('reports', exist_ok=True)
        
        report_data = {
            'timestamp': timestamp,
            'system_status': system.get_status(),
            'diagnostics': system.get_detailed_diagnostics(),
            'configuration': system.config.get_all()
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Reporte final generado: {report_file}")
        
    except Exception as e:
        logger.error(f"Error generando reporte final: {e}")


if __name__ == "__main__":
    try:
        # Ejecutar con asyncio para soporte asíncrono
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        sys.exit(1)