#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite para EcoSort Industrial v2.1 - Enhanced Edition
Pruebas comprehensivas del sistema de clasificación de residuos

Autores: Gabriel Calderón, Elias Bautista, Cristian Hernandez
Fecha: Junio de 2025
"""

import pytest
import asyncio
import tempfile
import os
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import asdict
import numpy as np
import cv2

# Importar módulos del sistema
import sys
sys.path.append('..')

from main_sistema_banda import (
    EcoSortSystem, ConfigManager, ComponentManager, 
    ErrorRecoveryManager, SecurityManager, PerformanceMonitor,
    SystemState, ErrorSeverity, SystemError, HardwareError, AIError,
    ClassificationResult, SystemMetrics, SystemAlert
)


class TestConfigManager:
    """Tests para ConfigManager con validación avanzada"""
    
    @pytest.fixture
    def temp_config_file(self):
        """Crea un archivo de configuración temporal para pruebas"""
        config_data = {
            "version": "2.1",
            "camera_settings": {
                "index": 0,
                "frame_width": 640,
                "frame_height": 480
            },
            "ai_model_settings": {
                "model_path": "test_model.pt",
                "class_names": ["metal", "plastic", "glass"],
                "min_confidence": 0.5
            },
            "conveyor_belt_settings": {
                "belt_speed_mps": 0.1,
                "distance_camera_to_diverters_m": {
                    "metal": 0.5,
                    "plastic": 0.7
                }
            },
            "sensors_settings": {
                "camera_trigger_sensor": {"pin_bcm": 18}
            },
            "diverter_control_settings": {
                "diverters": {
                    "metal": {
                        "type": "stepper_A4988",
                        "dir_pin_bcm": 2,
                        "step_pin_bcm": 3
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            return f.name
    
    def test_config_loading_valid(self, temp_config_file):
        """Test carga de configuración válida"""
        config = ConfigManager(temp_config_file)
        assert config.get('version') == "2.1"
        assert config.get('camera_settings', 'frame_width') == 640
        
        # Cleanup
        os.unlink(temp_config_file)
    
    def test_config_validation_missing_sections(self):
        """Test validación con secciones faltantes"""
        invalid_config = {"version": "2.1"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_file = f.name
        
        with pytest.raises(Exception):  # Should raise ConfigurationError
            ConfigManager(temp_file)
        
        os.unlink(temp_file)
    
    def test_config_hot_reload(self, temp_config_file):
        """Test recarga en caliente de configuración"""
        config = ConfigManager(temp_config_file)
        original_value = config.get('camera_settings', 'frame_width')
        
        # Modificar archivo
        with open(temp_config_file, 'r') as f:
            data = json.load(f)
        data['camera_settings']['frame_width'] = 1280
        
        with open(temp_config_file, 'w') as f:
            json.dump(data, f)
        
        # Simular paso de tiempo para cambio de timestamp
        time.sleep(0.1)
        
        # Verificar recarga
        reloaded = config.reload_if_changed()
        assert reloaded is True
        assert config.get('camera_settings', 'frame_width') == 1280
        
        os.unlink(temp_config_file)
    
    def test_config_set_and_validate(self, temp_config_file):
        """Test establecer valores dinámicamente con validación"""
        config = ConfigManager(temp_config_file)
        
        # Cambio válido
        success = config.set('camera_settings', 'fps', 60)
        assert success is True
        assert config.get('camera_settings', 'fps') == 60
        
        os.unlink(temp_config_file)


class TestErrorRecoveryManager:
    """Tests para el gestor de recuperación de errores"""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get.return_value = {}
        return config
    
    @pytest.fixture
    def recovery_manager(self, mock_config):
        return ErrorRecoveryManager(mock_config)
    
    @pytest.mark.asyncio
    async def test_error_classification(self, recovery_manager):
        """Test clasificación de tipos de error"""
        camera_error = SystemError("Camera capture failed", ErrorSeverity.HIGH, 'camera')
        ai_error = SystemError("AI model inference error", ErrorSeverity.MEDIUM, 'ai_model')
        
        assert recovery_manager._classify_error(camera_error) == 'camera_failure'
        assert recovery_manager._classify_error(ai_error) == 'ai_model_failure'
    
    @pytest.mark.asyncio
    async def test_recovery_cooldown(self, recovery_manager):
        """Test sistema de cooldown para recuperación"""
        error_type = 'test_error'
        
        # Primer intento debería ser permitido
        assert recovery_manager._can_attempt_recovery(error_type) is True
        
        # Registrar intento
        recovery_manager._record_recovery_attempt(error_type, False)
        
        # Inmediatamente después debería estar en cooldown
        assert recovery_manager._can_attempt_recovery(error_type) is False
    
    @pytest.mark.asyncio
    async def test_recovery_strategies(self, recovery_manager):
        """Test estrategias de recuperación registradas"""
        expected_strategies = [
            'camera_failure',
            'ai_model_failure', 
            'hardware_failure',
            'network_failure',
            'memory_leak',
            'high_temperature'
        ]
        
        for strategy in expected_strategies:
            assert strategy in recovery_manager.recovery_strategies


class TestSecurityManager:
    """Tests para el gestor de seguridad"""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get.return_value = {
            'emergency_stop_enabled': True,
            'max_failed_attempts': 3,
            'lockout_duration_minutes': 5
        }
        return config
    
    @pytest.fixture
    def security_manager(self, mock_config):
        return SecurityManager(mock_config)
    
    def test_api_access_validation(self, security_manager):
        """Test validación de acceso a la API"""
        # IP no bloqueada debería tener acceso
        assert security_manager.validate_api_access('192.168.1.100') is True
        
        # Simular intentos fallidos
        for _ in range(3):
            security_manager._record_failed_attempt('192.168.1.100')
        
        # IP debería estar bloqueada
        assert '192.168.1.100' in security_manager.blocked_ips
        assert security_manager.validate_api_access('192.168.1.100') is False
    
    @patch('Control_Banda.RPi_control_bajo_nivel.sensor_interface.check_emergency_stop')
    def test_emergency_stop_check(self, mock_emergency_check, security_manager):
        """Test verificación de parada de emergencia"""
        mock_emergency_check.return_value = True
        
        assert security_manager.check_emergency_stop() is True
        
        mock_emergency_check.return_value = False
        assert security_manager.check_emergency_stop() is False


class TestPerformanceMonitor:
    """Tests para el monitor de rendimiento"""
    
    @pytest.fixture
    def performance_monitor(self):
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, performance_monitor):
        """Test recolección de métricas del sistema"""
        metrics = await performance_monitor.collect_system_metrics()
        
        expected_keys = [
            'timestamp', 'cpu_percent', 'memory_percent', 
            'disk_percent', 'temperature'
        ]
        
        for key in expected_keys:
            assert key in metrics
        
        # Verificar que los valores están en rangos razonables
        assert 0 <= metrics['cpu_percent'] <= 100
        assert 0 <= metrics['memory_percent'] <= 100
        assert 0 <= metrics['disk_percent'] <= 100
    
    def test_performance_history(self, performance_monitor):
        """Test historial de métricas"""
        # Añadir métricas de prueba
        test_metrics = {
            'timestamp': time.time(),
            'cpu_percent': 50.0,
            'memory_percent': 60.0
        }
        
        performance_monitor.metrics_history.append(test_metrics)
        
        summary = performance_monitor.get_performance_summary()
        assert 'avg_cpu' in summary
        assert 'avg_memory' in summary
        assert summary['metrics_count'] == 1


class TestComponentManager:
    """Tests para el gestor de componentes"""
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get.side_effect = lambda section, key=None, default=None: {
            'camera_settings': {
                'index': 0,
                'frame_width': 640,
                'frame_height': 480,
                'warmup_frames': 5
            },
            'ai_model_settings': {
                'model_path': 'test_model.pt',
                'min_confidence': 0.5,
                'class_names': ['metal', 'plastic']
            }
        }.get(section, {}).get(key, default) if key else {
            'camera_settings': {
                'index': 0,
                'frame_width': 640,
                'frame_height': 480,
                'warmup_frames': 5
            },
            'ai_model_settings': {
                'model_path': 'test_model.pt',
                'min_confidence': 0.5,
                'class_names': ['metal', 'plastic']
            }
        }.get(section, default)
        
        config.config_file = 'test_config.json'
        return config
    
    @pytest.fixture
    def component_manager(self, mock_config):
        return ComponentManager(mock_config)
    
    def test_component_initialization_order(self, component_manager):
        """Test orden de inicialización de componentes"""
        expected_order = [
            'error_recovery',
            'security_manager', 
            'performance_monitor',
            'hardware',
            'camera',
            'ai_model',
            'database_and_api'
        ]
        
        assert component_manager._initialization_order == expected_order
    
    @patch('cv2.VideoCapture')
    @pytest.mark.asyncio
    async def test_camera_initialization_with_fallback(self, mock_video_capture, component_manager):
        """Test inicialización de cámara con fallback a otros índices"""
        # Simular que el índice 0 falla pero el 1 funciona
        mock_camera_0 = Mock()
        mock_camera_0.isOpened.return_value = False
        
        mock_camera_1 = Mock()
        mock_camera_1.isOpened.return_value = True
        mock_camera_1.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_camera_1.get.return_value = 640  # frame width
        
        mock_video_capture.side_effect = [mock_camera_0, mock_camera_1]
        
        await component_manager._initialize_camera()
        
        assert component_manager.camera == mock_camera_1
        assert mock_video_capture.call_count == 2
    
    @pytest.mark.asyncio
    async def test_component_restart(self, component_manager):
        """Test reinicio de componente específico"""
        # Simular componente inicializado
        component_manager._component_status['camera'] = 'initialized'
        component_manager.camera = Mock()
        
        with patch.object(component_manager, '_initialize_component') as mock_init:
            mock_init.return_value = None
            
            success = await component_manager.restart_component('camera')
            
            assert success is True
            assert component_manager._component_status['camera'] == 'restarted'
            mock_init.assert_called_once_with('camera')


class TestEcoSortSystem:
    """Tests para el sistema principal EcoSort"""
    
    @pytest.fixture
    def mock_config_file(self):
        """Crea archivo de configuración mock para pruebas"""
        config_data = {
            "version": "2.1",
            "camera_settings": {"index": 0, "frame_width": 640, "frame_height": 480},
            "ai_model_settings": {
                "model_path": "test_model.pt",
                "class_names": ["metal", "plastic", "glass"],
                "min_confidence": 0.5
            },
            "conveyor_belt_settings": {
                "belt_speed_mps": 0.1,
                "distance_camera_to_diverters_m": {"metal": 0.5}
            },
            "sensors_settings": {"camera_trigger_sensor": {"pin_bcm": 18}},
            "diverter_control_settings": {
                "diverters": {
                    "metal": {"type": "stepper_A4988", "dir_pin_bcm": 2, "step_pin_bcm": 3}
                }
            },
            "system_settings": {"bin_check_interval_s": 10}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            return f.name
    
    @pytest.fixture 
    def ecosort_system(self, mock_config_file):
        system = EcoSortSystem(mock_config_file)
        yield system
        # Cleanup
        os.unlink(mock_config_file)
    
    def test_system_initialization(self, ecosort_system):
        """Test inicialización del sistema"""
        assert ecosort_system.state == SystemState.INITIALIZING
        assert ecosort_system.metrics.objects_processed == 0
        assert isinstance(ecosort_system.config, ConfigManager)
        assert isinstance(ecosort_system.components, ComponentManager)
    
    def test_signal_handler(self, ecosort_system):
        """Test manejo de señales del sistema"""
        with patch.object(ecosort_system, 'request_shutdown') as mock_shutdown:
            ecosort_system._signal_handler(2, None)  # SIGINT
            mock_shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_system_requirements_check(self, ecosort_system):
        """Test verificación de requisitos del sistema"""
        with patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.virtual_memory') as mock_memory:
            
            # Simular condiciones normales
            mock_disk.return_value = Mock(free=2*1024**3)  # 2GB libre
            mock_memory.return_value = Mock(available=1024*1024*1024)  # 1GB disponible
            
            # No debería lanzar excepción
            await ecosort_system._check_system_requirements()
            
            # Simular poco espacio en disco
            mock_disk.return_value = Mock(free=0.5*1024**3)  # 500MB libre
            
            with pytest.raises(SystemError):
                await ecosort_system._check_system_requirements()
    
    def test_classification_result_creation(self, ecosort_system):
        """Test creación de resultados de clasificación"""
        result = ClassificationResult(
            object_id=1,
            classification_db_id=None,
            category_name="metal",
            category_index=0,
            confidence=0.85,
            processing_time_ms=150.0,
            detection_time=time.time()
        )
        
        assert result.object_id == 1
        assert result.category_name == "metal"
        assert result.confidence == 0.85
        assert not result.is_error
    
    def test_fallback_category_selection(self, ecosort_system):
        """Test selección de categoría de fallback"""
        class_names = ["metal", "plastic", "other"]
        fallback = ecosort_system._get_fallback_category(class_names)
        assert fallback == "other"
        
        class_names = ["metal", "plastic", "Desconocido"]
        fallback = ecosort_system._get_fallback_category(class_names)
        assert fallback == "Desconocido"
    
    def test_metrics_update(self, ecosort_system):
        """Test actualización de métricas"""
        # Simular algunos datos
        ecosort_system.metrics.objects_processed = 10
        ecosort_system.metrics.successful_classifications = 8
        ecosort_system.metrics.diversions_attempted = 5
        ecosort_system.metrics.diversions_successful = 4
        
        ecosort_system._update_metrics()
        
        assert ecosort_system.metrics.system_uptime > 0
    
    def test_status_report(self, ecosort_system):
        """Test generación de reporte de estado"""
        status = ecosort_system.get_status()
        
        required_keys = [
            'state', 'uptime_seconds', 'metrics', 'active_diversions',
            'queue_size', 'components_initialized', 'component_status'
        ]
        
        for key in required_keys:
            assert key in status
        
        assert isinstance(status['metrics'], dict)
        assert isinstance(status['uptime_seconds'], (int, float))


class TestIntegration:
    """Tests de integración del sistema completo"""
    
    @pytest.fixture
    def full_system_config(self):
        """Configuración completa para pruebas de integración"""
        return {
            "version": "2.1",
            "camera_settings": {
                "index": 0,
                "frame_width": 640,
                "frame_height": 480,
                "warmup_frames": 2
            },
            "ai_model_settings": {
                "model_path": "test_model.pt",
                "class_names": ["metal", "plastic", "glass", "carton", "other"],
                "min_confidence": 0.5
            },
            "conveyor_belt_settings": {
                "belt_speed_mps": 0.1,
                "distance_camera_to_diverters_m": {
                    "metal": 0.5,
                    "plastic": 0.7,
                    "glass": 0.9
                },
                "diverter_activation_duration_s": 0.5
            },
            "sensors_settings": {
                "camera_trigger_sensor": {"pin_bcm": 18},
                "bin_level_sensors": {
                    "enabled": True,
                    "sensors": {
                        "metal_bin": {"trigger_pin_bcm": 24, "echo_pin_bcm": 25}
                    }
                }
            },
            "diverter_control_settings": {
                "diverters": {
                    "metal": {
                        "type": "stepper_A4988",
                        "dir_pin_bcm": 2,
                        "step_pin_bcm": 3,
                        "steps_per_activation": 200
                    },
                    "plastic": {
                        "type": "gpio_on_off",
                        "pin_bcm": 7,
                        "active_state": "HIGH"
                    }
                }
            },
            "system_settings": {
                "bin_check_interval_s": 5,
                "save_images": False,
                "max_processing_errors": 5
            },
            "database_settings": {"enabled": False},
            "api_settings": {"enabled": False}
        }
    
    @pytest.mark.asyncio
    async def test_full_object_processing_simulation(self, full_system_config):
        """Test simulación completa de procesamiento de objeto"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(full_system_config, f)
            config_file = f.name
        
        try:
            system = EcoSortSystem(config_file)
            
            # Mock de todos los componentes hardware
            with patch('cv2.VideoCapture') as mock_camera, \
                 patch('Control_Banda.RPi_control_bajo_nivel.sensor_interface') as mock_sensors, \
                 patch('Control_Banda.RPi_control_bajo_nivel.conveyor_belt_controller') as mock_belt, \
                 patch('Control_Banda.RPi_control_bajo_nivel.motor_driver_interface') as mock_motors, \
                 patch('IA_Clasificacion.Trash_detect.TrashDetector') as mock_ai, \
                 patch('RPi.GPIO') as mock_gpio:
                
                # Configurar mocks
                mock_camera_instance = Mock()
                mock_camera_instance.isOpened.return_value = True
                mock_camera_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
                mock_camera_instance.get.return_value = 640
                mock_camera.return_value = mock_camera_instance
                
                mock_ai_instance = Mock()
                mock_ai_instance.detect_objects.return_value = [('metal', 0.85, (100, 100, 200, 200))]
                mock_ai_instance.model_class_names = ['metal', 'plastic', 'glass']
                mock_ai.return_value = mock_ai_instance
                
                mock_sensors.load_sensor_config.return_value = True
                mock_sensors.setup_sensor_gpio.return_value = True
                mock_sensors.check_camera_trigger.return_value = False
                mock_sensors.get_all_bin_fill_levels.return_value = {'metal_bin': 50.0}
                
                mock_belt.load_belt_config.return_value = True
                mock_belt.setup_belt_gpio.return_value = True
                mock_belt.get_belt_status.return_value = {'is_running': False}
                mock_belt.start_belt.return_value = True
                
                mock_motors.load_diverter_configuration.return_value = True
                mock_motors.setup_diverter_gpio.return_value = True
                mock_motors.activate_diverter.return_value = True
                
                # Inicializar sistema
                await system.initialize()
                
                assert system.state == SystemState.IDLE
                assert system.components.is_initialized()
                
                # Simular procesamiento de objeto
                test_image = np.zeros((480, 640, 3), dtype=np.uint8)
                result = await system._classify_object(1, test_image, time.time())
                
                assert result.object_id == 1
                assert result.category_name == "metal"
                assert result.confidence == 0.85
                assert not result.is_error
                
                # Verificar métricas
                system.metrics.objects_processed += 1
                system.metrics.successful_classifications += 1
                
                status = system.get_status()
                assert status['metrics']['objects_processed'] == 1
                assert status['metrics']['successful_classifications'] == 1
        
        finally:
            os.unlink(config_file)
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, full_system_config):
        """Test integración del sistema de recuperación de errores"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(full_system_config, f)
            config_file = f.name
        
        try:
            system = EcoSortSystem(config_file)
            
            # Inicializar componentes de recuperación
            system.components.error_recovery = ErrorRecoveryManager(system.config)
            system.components.security_manager = SecurityManager(system.config)
            system.components.performance_monitor = PerformanceMonitor()
            
            # Simular error de hardware
            hardware_error = HardwareError("GPIO initialization failed", ErrorSeverity.HIGH, 'gpio')
            
            # Mock de métodos de recuperación
            with patch.object(system.components.error_recovery, '_recover_hardware', 
                            new_callable=AsyncMock) as mock_recover:
                mock_recover.return_value = True
                
                # Intentar recuperación
                recovery_success = await system.components.error_recovery.handle_error(
                    hardware_error, system
                )
                
                assert recovery_success is True
                mock_recover.assert_called_once()
        
        finally:
            os.unlink(config_file)


class TestPerformance:
    """Tests de rendimiento del sistema"""
    
    @pytest.mark.asyncio
    async def test_classification_performance(self):
        """Test rendimiento de clasificación"""
        # Simular múltiples clasificaciones
        num_objects = 100
        processing_times = []
        
        for i in range(num_objects):
            start_time = time.time()
            
            # Simular procesamiento (operaciones dummy)
            dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Simular tiempo de procesamiento de IA
            await asyncio.sleep(0.001)  # 1ms simulado
            
            processing_time = (time.time() - start_time) * 1000
            processing_times.append(processing_time)
        
        # Verificar métricas de rendimiento
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        
        assert avg_time < 100  # Menos de 100ms promedio
        assert max_time < 500  # Menos de 500ms máximo
        assert len(processing_times) == num_objects
    
    def test_memory_usage_monitoring(self):
        """Test monitoreo de uso de memoria"""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simular carga de memoria
        large_arrays = []
        for _ in range(10):
            large_arrays.append(np.zeros((1000, 1000), dtype=np.uint8))
        
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # Verificar que el aumento es razonable
        assert memory_increase > 0
        assert memory_increase < 100 * 1024 * 1024  # Menos de 100MB
        
        # Limpiar memoria
        del large_arrays


@pytest.mark.asyncio
async def test_system_lifecycle():
    """Test ciclo de vida completo del sistema"""
    config_data = {
        "version": "2.1",
        "camera_settings": {"index": 0, "frame_width": 640, "frame_height": 480},
        "ai_model_settings": {
            "model_path": "test_model.pt", 
            "class_names": ["metal", "plastic"],
            "min_confidence": 0.5
        },
        "conveyor_belt_settings": {"belt_speed_mps": 0.1},
        "sensors_settings": {"camera_trigger_sensor": {"pin_bcm": 18}},
        "diverter_control_settings": {"diverters": {}},
        "system_settings": {"bin_check_interval_s": 1}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_file = f.name
    
    try:
        system = EcoSortSystem(config_file)
        
        # Test estados del sistema
        assert system.state == SystemState.INITIALIZING
        
        # Simular inicialización exitosa (sin hardware real)
        system.state = SystemState.IDLE
        
        # Test transiciones de estado
        system.pause()
        assert system.state == SystemState.PAUSED
        
        system.resume()
        assert system.state == SystemState.RUNNING
        
        system.enter_maintenance_mode()
        assert system.state == SystemState.MAINTENANCE
        
        system.exit_maintenance_mode()
        assert system.state == SystemState.RUNNING
        
        # Test shutdown request
        system.request_shutdown()
        assert system._shutdown_event.is_set()
        
    finally:
        os.unlink(config_file)


if __name__ == "__main__":
    # Ejecutar tests con configuración específica
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--color=yes"
    ]) 