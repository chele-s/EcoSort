# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Trash_detect.py - Detector Avanzado de Residuos con YOLO12
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio 2025
# Versión: 2.1 Enhanced Edition con YOLOv12
# Descripción: 
#   Sistema avanzado de detección de residuos con soporte para YOLOv12,
#   arquitectura OOP, recuperación automática de errores, monitoreo en tiempo
#   real y configuración dinámica. Soporta múltiples modelos YOLO.
# -----------------------------------------------------------------------------

import os
import sys
import cv2
import math
import argparse
import yaml
import logging
import time
import asyncio
import threading
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
import psutil
import numpy as np

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    YOLO = None

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TrashDetect')

# --- Enums y Dataclasses ---

class ModelType(Enum):
    """Tipos de modelos YOLO soportados."""
    YOLOV8 = "yolov8"
    YOLOV11 = "yolov11"
    YOLOV12 = "yolov12"  # Nuevo soporte para YOLOv12

class DetectorState(Enum):
    """Estados del detector."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    DETECTING = "detecting"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class ModelConfiguration:
    """Configuración del modelo de detección."""
    model_path: str = 'models/best.pt'
    model_type: str = "yolov12"  # Default a YOLOv12
    min_confidence: float = 0.5
    class_names: List[str] = field(default_factory=lambda: ['Metal', 'Glass', 'Plastic', 'Carton'])
    input_size: Tuple[int, int] = (640, 640)
    use_flash_attention: bool = False  # Nueva opción para YOLOv12
    device: str = "auto"  # auto, cpu, cuda, mps
    half_precision: bool = False
    max_detections: int = 50
    nms_threshold: float = 0.45
    agnostic_nms: bool = False

@dataclass
class DetectionResult:
    """Resultado de una detección."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    area: float
    center: Tuple[float, float]
    timestamp: float = field(default_factory=time.time)

@dataclass
class DetectorMetrics:
    """Métricas del detector."""
    total_detections: int = 0
    successful_detections: int = 0
    failed_detections: int = 0
    avg_inference_time_ms: float = 0.0
    avg_confidence: float = 0.0
    detections_by_class: Dict[str, int] = field(default_factory=dict)
    uptime_s: float = 0.0
    model_load_time_s: float = 0.0

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del sistema."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_mb: float = 0.0
    inference_times: List[float] = field(default_factory=list)
    throughput_fps: float = 0.0

# --- Clase Principal del Detector ---

class AdvancedTrashDetector:
    """Detector avanzado de residuos con soporte para YOLOv12."""
    
    def __init__(self, config: ModelConfiguration):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Estado del detector
        self.state = DetectorState.IDLE
        self.model = None
        self.model_class_names = []
        
        # Métricas y rendimiento
        self.metrics = DetectorMetrics()
        self.performance = PerformanceMetrics()
        self._start_time = time.time()
        
        # Control de threads y recovery
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="TrashDetector")
        self._error_history = []
        self._recovery_in_progress = False
        
        # Cache de inferencia para optimización
        self._inference_cache = {}
        self._cache_size_limit = 100
    
    async def initialize(self) -> bool:
        """Inicializar el detector."""
        try:
            self.logger.info(f"Inicializando Detector Avanzado de Residuos v2.1 con {self.config.model_type.upper()}")
            self.state = DetectorState.INITIALIZING
            
            # Verificar disponibilidad de Ultralytics
            if not ULTRALYTICS_AVAILABLE:
                raise ImportError("Ultralytics no está instalado. Ejecute: pip install ultralytics")
            
            # Verificar archivo del modelo
            if not await self._verify_model_file():
                return False
            
            # Cargar modelo
            if not await self._load_model():
                return False
            
            # Configurar dispositivo
            await self._configure_device()
            
            # Configurar YOLOv12 específico
            if self.config.model_type.lower() == "yolov12":
                await self._configure_yolov12()
            
            self.state = DetectorState.READY
            self.metrics.model_load_time_s = time.time() - self._start_time
            self.logger.info(f"Detector inicializado correctamente en {self.metrics.model_load_time_s:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando detector: {e}")
            self.state = DetectorState.ERROR
            self._error_history.append(time.time())
            return False
    
    async def _verify_model_file(self) -> bool:
        """Verificar que el archivo del modelo existe."""
        try:
            model_path = Path(self.config.model_path)
            
            if not model_path.exists():
                self.logger.error(f"Archivo del modelo no encontrado: {self.config.model_path}")
                
                # Intentar descargar modelo por defecto basado en el tipo
                return await self._download_default_model()
            
            # Verificar tamaño del archivo
            size_mb = model_path.stat().st_size / (1024 * 1024)
            if size_mb < 1:  # Modelo muy pequeño, probablemente corrupto
                self.logger.warning(f"Archivo del modelo sospechosamente pequeño: {size_mb:.2f}MB")
                return await self._download_default_model()
            
            self.logger.info(f"Modelo verificado: {self.config.model_path} ({size_mb:.2f}MB)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verificando modelo: {e}")
            return False
    
    async def _download_default_model(self) -> bool:
        """Descargar modelo por defecto basado en el tipo especificado."""
        try:
            model_type = self.config.model_type.lower()
            
            # Mapeo de modelos por defecto
            default_models = {
                "yolov8": "yolov8n.pt",
                "yolov11": "yolo11n.pt", 
                "yolov12": "yolo12n.pt"  # Nuevo modelo YOLOv12
            }
            
            default_model = default_models.get(model_type, "yolov8n.pt")
            self.logger.info(f"Descargando modelo por defecto: {default_model}")
            
            # Crear directorio si no existe
            model_dir = Path(self.config.model_path).parent
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Descargar usando Ultralytics (se descarga automáticamente al cargar)
            temp_model = YOLO(default_model)
            
            # Guardar en la ruta especificada
            temp_model.save(self.config.model_path)
            self.logger.info(f"Modelo descargado y guardado en: {self.config.model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error descargando modelo por defecto: {e}")
            return False
    
    async def _load_model(self) -> bool:
        """Cargar el modelo YOLO."""
        try:
            load_start = time.time()
            
            # Cargar modelo con configuración específica
            self.model = YOLO(self.config.model_path)
            
            # Obtener nombres de clases del modelo
            if hasattr(self.model, 'names') and self.model.names:
                self.model_class_names = list(self.model.names.values())
            else:
                self.model_class_names = self.config.class_names
                self.logger.warning("Usando nombres de clases de configuración")
            
            load_time = time.time() - load_start
            self.logger.info(f"Modelo cargado en {load_time:.2f}s. Clases: {self.model_class_names}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cargando modelo: {e}")
            return False
    
    async def _configure_device(self) -> None:
        """Configurar dispositivo de inferencia."""
        try:
            if self.config.device == "auto":
                # Detección automática del mejor dispositivo
                import torch
                if torch.cuda.is_available():
                    self.config.device = "cuda"
                    self.logger.info("GPU CUDA detectada, usando GPU")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.config.device = "mps"
                    self.logger.info("Apple MPS detectado, usando GPU")
                else:
                    self.config.device = "cpu"
                    self.logger.info("Usando CPU para inferencia")
            
            # Configurar modelo para usar el dispositivo seleccionado
            if self.model:
                self.model.to(self.config.device)
                
        except Exception as e:
            self.logger.warning(f"Error configurando dispositivo: {e}")
            self.config.device = "cpu"
    
    async def _configure_yolov12(self) -> None:
        """Configuraciones específicas para YOLOv12."""
        try:
            self.logger.info("Aplicando configuraciones específicas de YOLOv12")
            
            # Verificar soporte para FlashAttention
            if self.config.use_flash_attention:
                if await self._check_flash_attention_support():
                    self.logger.info("FlashAttention habilitado para YOLOv12")
                    # Aquí se configurarían los parámetros específicos de FlashAttention
                    # La implementación específica dependería de la API de Ultralytics
                else:
                    self.logger.warning("FlashAttention no soportado en este hardware")
                    self.config.use_flash_attention = False
            
            # Configurar parámetros optimizados para YOLOv12
            if hasattr(self.model, 'model') and hasattr(self.model.model, 'args'):
                # Configuraciones específicas de YOLOv12
                model_args = self.model.model.args
                
                # Optimizaciones de attention mechanism
                if hasattr(model_args, 'attention_type'):
                    model_args.attention_type = 'area_attention'  # Usar Area Attention
                
                # Configurar R-ELAN si está disponible
                if hasattr(model_args, 'use_rela'):
                    model_args.use_rela = True
                    
                self.logger.info("Configuraciones específicas de YOLOv12 aplicadas")
            
        except Exception as e:
            self.logger.warning(f"Error configurando YOLOv12: {e}")
    
    async def _check_flash_attention_support(self) -> bool:
        """Verificar soporte para FlashAttention."""
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            
            # Verificar versiones de GPU compatibles
            gpu_name = torch.cuda.get_device_name(0).lower()
            
            # GPUs compatibles con FlashAttention según documentación YOLOv12
            compatible_gpus = [
                'tesla t4', 'quadro rtx', 'geforce rtx 20', 'geforce rtx 30', 
                'geforce rtx 40', 'tesla a10', 'tesla a30', 'tesla a40', 
                'tesla a100', 'tesla h100', 'tesla h200'
            ]
            
            for compatible in compatible_gpus:
                if compatible in gpu_name:
                    return True
            
            self.logger.info(f"GPU {gpu_name} puede no ser compatible con FlashAttention")
            return False
            
        except Exception as e:
            self.logger.warning(f"Error verificando soporte FlashAttention: {e}")
            return False
    
    async def detect_objects(self, frame: np.ndarray) -> List[DetectionResult]:
        """Detectar objetos en un frame."""
        if self.state != DetectorState.READY:
            self.logger.warning(f"Detector no está listo. Estado actual: {self.state}")
            return []
        
        async with asyncio.Lock():
            try:
                self.state = DetectorState.DETECTING
                start_time = time.time()
                
                # Validar entrada
                if frame is None or frame.size == 0:
                    raise ValueError("Frame de entrada inválido")
                
                # Verificar cache primero
                frame_hash = hash(frame.tobytes())
                if frame_hash in self._inference_cache:
                    self.logger.debug("Usando resultado de cache")
                    return self._inference_cache[frame_hash]
                
                # Realizar inferencia
                detections = await self._run_inference(frame)
                
                # Actualizar métricas
                inference_time = (time.time() - start_time) * 1000  # ms
                await self._update_metrics(detections, inference_time)
                
                # Guardar en cache
                await self._cache_result(frame_hash, detections)
                
                self.state = DetectorState.READY
                return detections
                
            except Exception as e:
                self.logger.error(f"Error en detección: {e}")
                self.state = DetectorState.ERROR
                self._error_history.append(time.time())
                
                # Intentar recuperación automática
                if not self._recovery_in_progress:
                    await self._attempt_recovery("detection_error")
                
                return []
    
    async def _run_inference(self, frame: np.ndarray) -> List[DetectionResult]:
        """Ejecutar inferencia del modelo."""
        try:
            # Configurar parámetros de inferencia
            inference_params = {
                'conf': self.config.min_confidence,
                'iou': self.config.nms_threshold,
                'max_det': self.config.max_detections,
                'agnostic_nms': self.config.agnostic_nms,
                'half': self.config.half_precision,
                'device': self.config.device,
                'verbose': False
            }
            
            # Añadir parámetros específicos de YOLOv12
            if self.config.model_type.lower() == "yolov12":
                if self.config.use_flash_attention:
                    inference_params['use_flash_attention'] = True
                # Otros parámetros específicos pueden añadirse aquí
            
            # Ejecutar inferencia
            results = self.model(frame, **inference_params)
            
            # Procesar resultados
            detections = []
            for result in results:
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    
                    for i in range(len(boxes)):
                        try:
                            # Extraer datos de la detección
                            conf = float(boxes.conf[i])
                            cls_idx = int(boxes.cls[i])
                            
                            # Validar índice de clase
                            if 0 <= cls_idx < len(self.model_class_names):
                                class_name = self.model_class_names[cls_idx]
                            else:
                                self.logger.warning(f"Índice de clase inválido: {cls_idx}")
                                continue
                            
                            # Extraer coordenadas
                            x1, y1, x2, y2 = map(int, boxes.xyxy[i])
                            
                            # Validar coordenadas
                            h, w = frame.shape[:2]
                            x1 = max(0, min(x1, w - 1))
                            y1 = max(0, min(y1, h - 1))
                            x2 = max(0, min(x2, w - 1))
                            y2 = max(0, min(y2, h - 1))
                            
                            if x1 >= x2 or y1 >= y2:
                                continue
                            
                            # Calcular área y centro
                            area = (x2 - x1) * (y2 - y1)
                            center = ((x1 + x2) / 2, (y1 + y2) / 2)
                            
                            # Crear resultado de detección
                            detection = DetectionResult(
                                class_name=class_name,
                                confidence=conf,
                                bbox=(x1, y1, x2, y2),
                                area=area,
                                center=center
                            )
                            
                            detections.append(detection)
                            
                        except Exception as e:
                            self.logger.warning(f"Error procesando detección {i}: {e}")
                            continue
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Error en inferencia: {e}")
            raise
    
    async def _update_metrics(self, detections: List[DetectionResult], inference_time_ms: float) -> None:
        """Actualizar métricas del detector."""
        try:
            self.metrics.total_detections += 1
            
            if detections:
                self.metrics.successful_detections += 1
                
                # Actualizar estadísticas de confianza
                confidences = [d.confidence for d in detections]
                if confidences:
                    self.metrics.avg_confidence = (
                        self.metrics.avg_confidence * (self.metrics.successful_detections - 1) + 
                        sum(confidences) / len(confidences)
                    ) / self.metrics.successful_detections
                
                # Actualizar contadores por clase
                for detection in detections:
                    class_name = detection.class_name
                    self.metrics.detections_by_class[class_name] = (
                        self.metrics.detections_by_class.get(class_name, 0) + 1
                    )
            else:
                self.metrics.failed_detections += 1
            
            # Actualizar tiempo de inferencia promedio
            self.metrics.avg_inference_time_ms = (
                self.metrics.avg_inference_time_ms * (self.metrics.total_detections - 1) + 
                inference_time_ms
            ) / self.metrics.total_detections
            
            # Actualizar métricas de rendimiento
            self.performance.inference_times.append(inference_time_ms)
            if len(self.performance.inference_times) > 100:  # Mantener solo últimas 100
                self.performance.inference_times.pop(0)
            
            # Calcular throughput
            if len(self.performance.inference_times) >= 10:
                avg_time = sum(self.performance.inference_times[-10:]) / 10
                self.performance.throughput_fps = 1000.0 / avg_time if avg_time > 0 else 0
            
            # Actualizar uptime
            self.metrics.uptime_s = time.time() - self._start_time
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {e}")
    
    async def _cache_result(self, frame_hash: int, detections: List[DetectionResult]) -> None:
        """Guardar resultado en cache."""
        try:
            if len(self._inference_cache) >= self._cache_size_limit:
                # Remover entrada más antigua
                oldest_key = next(iter(self._inference_cache))
                del self._inference_cache[oldest_key]
            
            self._inference_cache[frame_hash] = detections
            
        except Exception as e:
            self.logger.warning(f"Error guardando en cache: {e}")
    
    async def _attempt_recovery(self, error_type: str) -> bool:
        """Intentar recuperación automática."""
        if self._recovery_in_progress:
            return False
        
        self._recovery_in_progress = True
        self.logger.warning(f"Iniciando recuperación automática: {error_type}")
        
        try:
            # Limpiar cache
            self._inference_cache.clear()
            
            # Recargar modelo
            if await self._load_model():
                await self._configure_device()
                if self.config.model_type.lower() == "yolov12":
                    await self._configure_yolov12()
                
                self.state = DetectorState.READY
                self.logger.info("Recuperación automática exitosa")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error en recuperación automática: {e}")
            return False
        finally:
            self._recovery_in_progress = False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado completo del detector."""
        return {
            "detector": {
                "state": self.state.value,
                "model_type": self.config.model_type,
                "model_path": self.config.model_path,
                "device": self.config.device,
                "use_flash_attention": self.config.use_flash_attention,
                "class_names": self.model_class_names,
                "ready": self.state == DetectorState.READY
            },
            "metrics": {
                "total_detections": self.metrics.total_detections,
                "successful_detections": self.metrics.successful_detections,
                "success_rate": (
                    self.metrics.successful_detections / max(self.metrics.total_detections, 1)
                ) * 100,
                "avg_inference_time_ms": self.metrics.avg_inference_time_ms,
                "avg_confidence": self.metrics.avg_confidence,
                "detections_by_class": self.metrics.detections_by_class,
                "uptime_s": self.metrics.uptime_s,
                "model_load_time_s": self.metrics.model_load_time_s
            },
            "performance": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "throughput_fps": self.performance.throughput_fps,
                "cache_size": len(self._inference_cache),
                "error_count": len(self._error_history)
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas detalladas."""
        return {
            "inference": {
                "total_detections": self.metrics.total_detections,
                "successful_detections": self.metrics.successful_detections,
                "failed_detections": self.metrics.failed_detections,
                "success_rate": (
                    self.metrics.successful_detections / max(self.metrics.total_detections, 1)
                ) * 100,
                "avg_inference_time_ms": self.metrics.avg_inference_time_ms,
                "throughput_fps": self.performance.throughput_fps
            },
            "quality": {
                "avg_confidence": self.metrics.avg_confidence,
                "detections_by_class": self.metrics.detections_by_class,
                "min_confidence_threshold": self.config.min_confidence
            },
            "system": {
                "uptime_s": self.metrics.uptime_s,
                "model_load_time_s": self.metrics.model_load_time_s,
                "cache_hit_rate": len(self._inference_cache) / max(self.metrics.total_detections, 1),
                "error_rate": len(self._error_history) / max(self.metrics.uptime_s / 3600, 1)  # errores por hora
            }
        }
    
    async def reload_model(self, new_model_path: Optional[str] = None) -> bool:
        """Recargar modelo dinámicamente."""
        try:
            self.logger.info("Recargando modelo...")
            
            if new_model_path:
                self.config.model_path = new_model_path
            
            # Limpiar cache
            self._inference_cache.clear()
            
            # Recargar modelo
            success = await self._load_model()
            if success:
                await self._configure_device()
                if self.config.model_type.lower() == "yolov12":
                    await self._configure_yolov12()
                
                self.state = DetectorState.READY
                self.logger.info("Modelo recargado exitosamente")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error recargando modelo: {e}")
            self.state = DetectorState.ERROR
            return False
    
    async def cleanup(self) -> None:
        """Limpiar recursos."""
        try:
            self.logger.info("Limpiando recursos del detector...")
            
            self.state = DetectorState.IDLE
            self._inference_cache.clear()
            
            if self.model:
                del self.model
                self.model = None
            
            self._executor.shutdown(wait=True)
            
            self.logger.info("Limpieza del detector completada")
            
        except Exception as e:
            self.logger.error(f"Error durante limpieza del detector: {e}")

# --- Clase Legacy para Compatibilidad ---

class TrashDetector:
    """Clase legacy para mantener compatibilidad con código existente."""
    
    def __init__(self, model_path: str, min_confidence: float = 0.5):
        """Inicializar detector legacy."""
        config = ModelConfiguration(
            model_path=model_path,
            min_confidence=min_confidence,
            model_type="yolov12"  # Default a YOLOv12
        )
        
        self._advanced_detector = AdvancedTrashDetector(config)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Asegurar que el detector está inicializado."""
        if not self._initialized:
            self._initialized = await self._advanced_detector.initialize()
            if not self._initialized:
                raise RuntimeError("Error inicializando detector")
    
    def detect_objects(self, frame) -> list:
        """Detectar objetos (interfaz legacy)."""
        try:
            # Ejecutar de forma sincrónica para compatibilidad
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._ensure_initialized())
                detections = loop.run_until_complete(
                    self._advanced_detector.detect_objects(frame)
                )
                
                # Convertir a formato legacy
                legacy_results = []
                for detection in detections:
                    legacy_results.append((
                        detection.class_name,
                        detection.confidence,
                        detection.bbox
                    ))
                
                return legacy_results
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error en detect_objects legacy: {e}")
            return []

# --- Funciones de Utilidad ---

def parse_arguments():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Detección avanzada de residuos con YOLOv12')
    
    parser.add_argument('--model', type=str, default='models/best.pt',
                        help='Ruta al modelo YOLO')
    parser.add_argument('--model-type', type=str, default='yolov12',
                        choices=['yolov8', 'yolov11', 'yolov12'],
                        help='Tipo de modelo YOLO')
    parser.add_argument('--camera', type=int, default=0,
                        help='Índice de la cámara')
    parser.add_argument('--width', type=int, default=640,
                        help='Ancho de captura')
    parser.add_argument('--height', type=int, default=640,
                        help='Alto de captura')
    parser.add_argument('--conf', type=float, default=0.45,
                        help='Umbral de confianza')
    parser.add_argument('--device', type=str, default='auto',
                        choices=['auto', 'cpu', 'cuda', 'mps'],
                        help='Dispositivo de inferencia')
    parser.add_argument('--flash-attention', action='store_true',
                        help='Usar FlashAttention (solo YOLOv12)')
    parser.add_argument('--half', action='store_true',
                        help='Usar precisión FP16')
    parser.add_argument('--no-display', action='store_true',
                        help='No mostrar ventana de video')
    
    return parser.parse_args()

async def main():
    """Función principal para prueba del detector."""
    args = parse_arguments()
    
    # Configurar detector
    config = ModelConfiguration(
        model_path=args.model,
        model_type=args.model_type,
        min_confidence=args.conf,
        device=args.device,
        use_flash_attention=args.flash_attention,
        half_precision=args.half
    )
    
    detector = AdvancedTrashDetector(config)
    
    try:
        # Inicializar detector
        if not await detector.initialize():
            logger.error("Error inicializando detector")
            return 1
        
        # Configurar cámara
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            logger.error(f"No se pudo abrir la cámara {args.camera}")
            return 1
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        
        logger.info("Iniciando detección en tiempo real. Presiona 'ESC' o 'q' para salir.")
        
        # Variables de rendimiento
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Error capturando frame")
                break
            
            # Detectar objetos
            detections = await detector.detect_objects(frame)
            
            # Mostrar resultados
            if not args.no_display:
                annotated_frame = frame.copy()
                
                for detection in detections:
                    x1, y1, x2, y2 = detection.bbox
                    class_name = detection.class_name
                    confidence = detection.confidence
                    
                    # Dibujar bbox
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Dibujar etiqueta
                    label = f'{class_name} {confidence:.2f}'
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
                    )
                    cv2.rectangle(
                        annotated_frame, 
                        (x1, y1 - text_height - baseline), 
                        (x1 + text_width, y1), 
                        (0, 255, 0), -1
                    )
                    cv2.putText(
                        annotated_frame, label, (x1, y1 - baseline), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
                    )
                
                # Mostrar métricas
                metrics = detector.get_metrics()
                fps_text = f"FPS: {metrics['inference']['throughput_fps']:.1f}"
                cv2.putText(
                    annotated_frame, fps_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
                )
                
                cv2.imshow('EcoSort - Detección Avanzada con YOLOv12', annotated_frame)
            
            # Mostrar estadísticas cada 100 frames
            frame_count += 1
            if frame_count % 100 == 0:
                status = detector.get_status()
                logger.info(f"Detecciones: {status['metrics']['total_detections']}, "
                           f"Éxito: {status['metrics']['success_rate']:.1f}%, "
                           f"FPS: {status['performance']['throughput_fps']:.1f}")
            
            # Verificar salida
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):  # ESC o 'q'
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupción por usuario")
    except Exception as e:
        logger.error(f"Error en bucle principal: {e}")
    finally:
        # Limpiar recursos
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        await detector.cleanup()
        
        # Mostrar estadísticas finales
        status = detector.get_status()
        logger.info("\n=== Estadísticas Finales ===")
        logger.info(f"Detecciones totales: {status['metrics']['total_detections']}")
        logger.info(f"Tasa de éxito: {status['metrics']['success_rate']:.1f}%")
        logger.info(f"Tiempo promedio: {status['metrics']['avg_inference_time_ms']:.1f}ms")
        logger.info(f"Detecciones por clase: {status['metrics']['detections_by_class']}")
    
    return 0

if __name__ == "__main__":
    # Ejecutar programa principal
    sys.exit(asyncio.run(main()))