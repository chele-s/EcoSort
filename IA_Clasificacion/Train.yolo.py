# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# train_yolo.py - Sistema Avanzado de Entrenamiento YOLOv12
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio 2025
# Versión: 2.1 Enhanced Edition con YOLOv12
# Descripción: 
#   Sistema avanzado de entrenamiento con soporte para YOLOv12, sus nuevas
#   características de atención, FlashAttention, R-ELAN, monitoreo en tiempo
#   real, configuración dinámica y recuperación automática.
# -----------------------------------------------------------------------------

import os
import sys
import torch
import datetime
import argparse
import logging
import yaml
import platform
import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
import psutil
import time

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
logger = logging.getLogger('TrainYOLO')

# --- Enums y Dataclasses ---

class ModelType(Enum):
    """Tipos de modelos YOLO soportados."""
    YOLOV8 = "yolov8"
    YOLOV11 = "yolov11"
    YOLOV12 = "yolov12"

class ModelSize(Enum):
    """Tamaños de modelo disponibles."""
    NANO = "n"
    SMALL = "s"
    MEDIUM = "m"
    LARGE = "l"
    XLARGE = "x"

class TrainingState(Enum):
    """Estados del entrenamiento."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    TRAINING = "training"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"

@dataclass
class TrainingConfiguration:
    """Configuración avanzada de entrenamiento."""
    # Modelo
    model_type: str = "yolov12"
    model_size: str = "n"
    model_path: Optional[str] = None
    
    # Dataset
    data_config: str = './DATASET_basura/data.yaml'
    
    # Entrenamiento básico
    epochs: int = 100
    batch_size: int = 16
    image_size: int = 640
    workers: int = 4
    device: str = "auto"
    
    # Proyecto
    project_name: str = 'EcoSort_Training_v2'
    experiment_name: Optional[str] = None
    
    # Optimización
    optimizer: str = "auto"  # auto, SGD, Adam, AdamW
    learning_rate: float = 0.01
    momentum: float = 0.937
    weight_decay: float = 0.0005
    
    # Scheduler
    lr_scheduler: str = "cosine"  # linear, cosine, polynomial
    warmup_epochs: int = 3
    warmup_momentum: float = 0.8
    warmup_bias_lr: float = 0.1
    
    # Early stopping y paciencia
    patience: int = 25
    save_period: int = -1
    
    # Augmentation (mejorado para YOLOv12)
    degrees: float = 15.0
    translate: float = 0.1
    scale: float = 0.5
    shear: float = 5.0
    perspective: float = 0.0
    flipud: float = 0.3
    fliplr: float = 0.5
    mosaic: float = 0.8
    mixup: float = 0.15
    copy_paste: float = 0.1
    
    # YOLOv12 específico
    use_flash_attention: bool = False
    use_r_elan: bool = True
    attention_type: str = "area_attention"  # area_attention, standard
    area_attention_regions: int = 4
    mlp_ratio: float = 1.2  # Optimizado para YOLOv12
    
    # Validación y métricas
    validation: bool = True
    plots: bool = True
    save_json: bool = True
    save_hybrid: bool = True
    
    # Recursos y rendimiento
    half_precision: bool = False
    dnn: bool = False
    multi_scale: bool = False
    
    # Recuperación
    resume: bool = False
    resume_path: Optional[str] = None
    auto_backup: bool = True
    
    # Callbacks y monitoreo
    tensorboard: bool = True
    wandb: bool = False
    mlflow: bool = False

@dataclass
class TrainingMetrics:
    """Métricas de entrenamiento."""
    current_epoch: int = 0
    total_epochs: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    map50: float = 0.0
    map95: float = 0.0
    learning_rate: float = 0.0
    epochs_without_improvement: int = 0
    best_map50: float = 0.0
    training_time_s: float = 0.0
    estimated_time_remaining_s: float = 0.0

@dataclass
class SystemMetrics:
    """Métricas del sistema durante entrenamiento."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_mb: float = 0.0
    gpu_utilization: float = 0.0
    disk_usage_percent: float = 0.0
    temperature_c: float = 0.0

# --- Clase Principal de Entrenamiento ---

class AdvancedYOLOTrainer:
    """Entrenador avanzado YOLO con soporte para YOLOv12."""
    
    def __init__(self, config: TrainingConfiguration):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Estado del entrenamiento
        self.state = TrainingState.IDLE
        self.model = None
        self.training_metrics = TrainingMetrics()
        self.system_metrics = SystemMetrics()
        
        # Control de entrenamiento
        self._training_active = False
        self._paused = False
        self._stop_requested = False
        
        # Histórico y callbacks
        self._metrics_history = []
        self._callbacks = []
        self._start_time = None
        
        # Paths y directorios
        self.output_dir = None
        self.checkpoint_dir = None
        
    async def initialize(self) -> bool:
        """Inicializar el entrenador."""
        try:
            self.logger.info("Inicializando Entrenador Avanzado YOLOv12 v2.1")
            self.state = TrainingState.INITIALIZING
            
            # Verificar dependencias
            if not await self._check_dependencies():
                return False
            
            # Configurar directorios
            await self._setup_directories()
            
            # Validar configuración
            if not await self._validate_configuration():
                return False
            
            # Configurar dispositivo
            await self._configure_device()
            
            # Preparar modelo
            if not await self._prepare_model():
                return False
            
            # Configurar callbacks
            await self._setup_callbacks()
            
            self.state = TrainingState.IDLE
            self.logger.info("Entrenador inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando entrenador: {e}")
            self.state = TrainingState.ERROR
            return False
    
    async def _check_dependencies(self) -> bool:
        """Verificar dependencias del sistema."""
        try:
            if not ULTRALYTICS_AVAILABLE:
                self.logger.error("Ultralytics no disponible. Instale con: pip install ultralytics")
                return False
            
            # Verificar versión de PyTorch
            if not torch.cuda.is_available() and self.config.device != "cpu":
                self.logger.warning("CUDA no disponible, usando CPU")
                self.config.device = "cpu"
            
            # Verificar espacio en disco
            free_space_gb = psutil.disk_usage('.').free / (1024**3)
            if free_space_gb < 5:  # Mínimo 5GB
                self.logger.warning(f"Poco espacio en disco: {free_space_gb:.1f}GB")
            
            self.logger.info("Dependencias verificadas")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verificando dependencias: {e}")
            return False
    
    async def _setup_directories(self) -> None:
        """Configurar directorios de salida."""
        try:
            # Crear nombre único si no se especifica
            if not self.config.experiment_name:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                model_name = f"{self.config.model_type}{self.config.model_size}"
                self.config.experiment_name = f'{model_name}_epochs{self.config.epochs}_{timestamp}'
            
            # Crear directorios
            self.output_dir = Path('runs') / 'detect' / self.config.project_name / self.config.experiment_name
            self.checkpoint_dir = self.output_dir / 'checkpoints'
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar configuración
            config_path = self.output_dir / 'training_config.json'
            with open(config_path, 'w') as f:
                # Convertir dataclass a dict para JSON
                config_dict = {
                    'model_type': self.config.model_type,
                    'model_size': self.config.model_size,
                    'epochs': self.config.epochs,
                    'batch_size': self.config.batch_size,
                    'image_size': self.config.image_size,
                    'use_flash_attention': self.config.use_flash_attention,
                    'use_r_elan': self.config.use_r_elan,
                    'attention_type': self.config.attention_type,
                    'learning_rate': self.config.learning_rate,
                    'data_config': self.config.data_config,
                }
                json.dump(config_dict, f, indent=2)
            
            self.logger.info(f"Directorios configurados: {self.output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error configurando directorios: {e}")
            raise
    
    async def _validate_configuration(self) -> bool:
        """Validar configuración de entrenamiento."""
        try:
            self.state = TrainingState.VALIDATING
            
            # Validar dataset
            if not await self._validate_dataset():
                return False
            
            # Validar parámetros de modelo
            if self.config.model_type not in [t.value for t in ModelType]:
                self.logger.error(f"Tipo de modelo no soportado: {self.config.model_type}")
                return False
            
            if self.config.model_size not in [s.value for s in ModelSize]:
                self.logger.error(f"Tamaño de modelo no válido: {self.config.model_size}")
                return False
            
            # Validar parámetros de YOLOv12
            if self.config.model_type == "yolov12":
                if not await self._validate_yolov12_config():
                    return False
            
            # Validar recursos
            if self.config.batch_size < 1:
                self.logger.error("Batch size debe ser >= 1")
                return False
            
            if self.config.epochs < 1:
                self.logger.error("Épocas debe ser >= 1")
                return False
            
            self.logger.info("Configuración validada correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando configuración: {e}")
            return False
    
    async def _validate_dataset(self) -> bool:
        """Validar dataset y configuración."""
        try:
            data_path = Path(self.config.data_config)
            if not data_path.exists():
                self.logger.error(f"Archivo de dataset no encontrado: {data_path}")
                return False
            
            # Cargar y validar YAML
            with open(data_path, 'r') as f:
                data_config = yaml.safe_load(f)
            
            required_keys = ['train', 'val', 'nc', 'names']
            for key in required_keys:
                if key not in data_config:
                    self.logger.error(f"Clave requerida '{key}' no encontrada en dataset config")
                    return False
            
            # Validar coherencia
            if len(data_config['names']) != data_config['nc']:
                self.logger.error("Número de clases no coincide con lista de nombres")
                return False
            
            # Verificar rutas de datos
            base_dir = data_path.parent
            train_path = base_dir / data_config['train']
            val_path = base_dir / data_config['val']
            
            if not train_path.exists():
                self.logger.warning(f"Ruta de entrenamiento no encontrada: {train_path}")
            
            if not val_path.exists():
                self.logger.warning(f"Ruta de validación no encontrada: {val_path}")
            
            self.logger.info(f"Dataset validado: {data_config['nc']} clases - {data_config['names']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando dataset: {e}")
            return False
    
    async def _validate_yolov12_config(self) -> bool:
        """Validar configuración específica de YOLOv12."""
        try:
            # Verificar FlashAttention
            if self.config.use_flash_attention:
                if not await self._check_flash_attention_support():
                    self.logger.warning("FlashAttention no soportado, deshabilitando")
                    self.config.use_flash_attention = False
            
            # Validar parámetros de Area Attention
            if self.config.area_attention_regions not in [2, 4, 8]:
                self.logger.warning(f"Regiones de atención inválidas: {self.config.area_attention_regions}, usando 4")
                self.config.area_attention_regions = 4
            
            # Validar MLP ratio optimizado
            if not 1.0 <= self.config.mlp_ratio <= 4.0:
                self.logger.warning(f"MLP ratio fuera de rango: {self.config.mlp_ratio}, usando 1.2")
                self.config.mlp_ratio = 1.2
            
            self.logger.info("Configuración YOLOv12 validada")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando configuración YOLOv12: {e}")
            return False
    
    async def _check_flash_attention_support(self) -> bool:
        """Verificar soporte para FlashAttention."""
        try:
            if not torch.cuda.is_available():
                return False
            
            gpu_name = torch.cuda.get_device_name(0).lower()
            
            # GPUs compatibles con FlashAttention
            compatible_patterns = [
                'tesla t4', 'quadro rtx', 'geforce rtx 20', 'geforce rtx 30', 
                'geforce rtx 40', 'tesla a10', 'tesla a30', 'tesla a40', 
                'tesla a100', 'tesla h100', 'tesla h200'
            ]
            
            for pattern in compatible_patterns:
                if pattern in gpu_name:
                    self.logger.info(f"FlashAttention soportado en {gpu_name}")
                    return True
            
            self.logger.info(f"GPU {gpu_name} puede no soportar FlashAttention óptimamente")
            return False
            
        except Exception:
            return False
    
    async def _configure_device(self) -> None:
        """Configurar dispositivo de entrenamiento."""
        try:
            if self.config.device == "auto":
                if torch.cuda.is_available():
                    self.config.device = "cuda"
                    gpu_count = torch.cuda.device_count()
                    self.logger.info(f"Usando GPU CUDA: {gpu_count} dispositivo(s)")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.config.device = "mps"
                    self.logger.info("Usando Apple MPS")
                else:
                    self.config.device = "cpu"
                    self.logger.info("Usando CPU")
            
            # Ajustar batch size según dispositivo
            if self.config.device == "cpu" and self.config.batch_size > 8:
                self.logger.warning("Reduciendo batch size para CPU")
                self.config.batch_size = 4
            
        except Exception as e:
            self.logger.warning(f"Error configurando dispositivo: {e}")
            self.config.device = "cpu"
    
    async def _prepare_model(self) -> bool:
        """Preparar modelo para entrenamiento."""
        try:
            # Determinar modelo base
            if self.config.model_path:
                model_name = self.config.model_path
            else:
                model_name = f"{self.config.model_type}{self.config.model_size}.pt"
            
            self.logger.info(f"Cargando modelo: {model_name}")
            
            # Cargar modelo
            self.model = YOLO(model_name)
            
            # Configuraciones específicas de YOLOv12
            if self.config.model_type == "yolov12":
                await self._configure_yolov12_model()
            
            self.logger.info("Modelo preparado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error preparando modelo: {e}")
            return False
    
    async def _configure_yolov12_model(self) -> None:
        """Configurar parámetros específicos de YOLOv12."""
        try:
            if hasattr(self.model, 'model') and hasattr(self.model.model, 'args'):
                model_args = self.model.model.args
                
                # Configurar Area Attention
                if hasattr(model_args, 'attention_type'):
                    model_args.attention_type = self.config.attention_type
                
                if hasattr(model_args, 'area_attention_regions'):
                    model_args.area_attention_regions = self.config.area_attention_regions
                
                # Configurar R-ELAN
                if hasattr(model_args, 'use_r_elan'):
                    model_args.use_r_elan = self.config.use_r_elan
                
                # Configurar MLP ratio
                if hasattr(model_args, 'mlp_ratio'):
                    model_args.mlp_ratio = self.config.mlp_ratio
                
                # FlashAttention
                if hasattr(model_args, 'use_flash_attention'):
                    model_args.use_flash_attention = self.config.use_flash_attention
                
                self.logger.info("Configuraciones YOLOv12 aplicadas al modelo")
            
        except Exception as e:
            self.logger.warning(f"Error configurando YOLOv12: {e}")
    
    async def _setup_callbacks(self) -> None:
        """Configurar callbacks de entrenamiento."""
        try:
            # Callback para métricas en tiempo real
            def on_train_epoch_end(trainer):
                """Callback al final de cada época."""
                try:
                    self.training_metrics.current_epoch = trainer.epoch + 1
                    
                    # Actualizar métricas desde trainer
                    if hasattr(trainer, 'loss_items'):
                        self.training_metrics.train_loss = float(trainer.loss_items.mean())
                    
                    if hasattr(trainer, 'validator') and trainer.validator:
                        val = trainer.validator
                        if hasattr(val, 'metrics'):
                            metrics = val.metrics
                            self.training_metrics.precision = getattr(metrics, 'precision', 0.0)
                            self.training_metrics.recall = getattr(metrics, 'recall', 0.0)
                            self.training_metrics.map50 = getattr(metrics, 'map50', 0.0)
                            self.training_metrics.map95 = getattr(metrics, 'map', 0.0)
                    
                    # Actualizar tiempo estimado
                    elapsed = time.time() - self._start_time
                    if self.training_metrics.current_epoch > 0:
                        time_per_epoch = elapsed / self.training_metrics.current_epoch
                        remaining_epochs = self.config.epochs - self.training_metrics.current_epoch
                        self.training_metrics.estimated_time_remaining_s = time_per_epoch * remaining_epochs
                    
                    # Guardar en histórico
                    self._metrics_history.append({
                        'epoch': self.training_metrics.current_epoch,
                        'train_loss': self.training_metrics.train_loss,
                        'val_loss': self.training_metrics.val_loss,
                        'map50': self.training_metrics.map50,
                        'map95': self.training_metrics.map95,
                        'timestamp': time.time()
                    })
                    
                    # Log progreso
                    if self.training_metrics.current_epoch % 10 == 0:
                        self.logger.info(
                            f"Época {self.training_metrics.current_epoch}/{self.config.epochs} - "
                            f"mAP50: {self.training_metrics.map50:.3f} - "
                            f"Loss: {self.training_metrics.train_loss:.3f}"
                        )
                    
                except Exception as e:
                    self.logger.warning(f"Error en callback de época: {e}")
            
            # Registrar callbacks
            self._callbacks.append(on_train_epoch_end)
            
        except Exception as e:
            self.logger.warning(f"Error configurando callbacks: {e}")
    
    async def train(self) -> bool:
        """Ejecutar entrenamiento."""
        try:
            if self.state != TrainingState.IDLE:
                self.logger.error(f"No se puede entrenar en estado: {self.state}")
                return False
            
            self.logger.info("=== Iniciando Entrenamiento Avanzado ===")
            self.state = TrainingState.TRAINING
            self._training_active = True
            self._start_time = time.time()
            
            # Configurar parámetros de entrenamiento
            train_args = await self._prepare_training_args()
            
            # Iniciar entrenamiento
            self.logger.info(f"Entrenando {self.config.model_type.upper()}{self.config.model_size} por {self.config.epochs} épocas")
            self.logger.info(f"Dataset: {self.config.data_config}")
            self.logger.info(f"Batch size: {self.config.batch_size}, Image size: {self.config.image_size}")
            self.logger.info(f"Dispositivo: {self.config.device}")
            
            if self.config.model_type == "yolov12":
                features = []
                if self.config.use_flash_attention:
                    features.append("FlashAttention")
                if self.config.use_r_elan:
                    features.append("R-ELAN")
                features.append(f"Area Attention ({self.config.area_attention_regions} regiones)")
                self.logger.info(f"Características YOLOv12: {', '.join(features)}")
            
            # Ejecutar entrenamiento
            results = self.model.train(**train_args)
            
            # Procesar resultados
            self.training_metrics.training_time_s = time.time() - self._start_time
            self.state = TrainingState.COMPLETED
            self._training_active = False
            
            self.logger.info("=== Entrenamiento Completado ===")
            await self._save_final_results(results)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error durante entrenamiento: {e}")
            self.state = TrainingState.ERROR
            self._training_active = False
            return False
    
    async def _prepare_training_args(self) -> Dict[str, Any]:
        """Preparar argumentos de entrenamiento."""
        try:
            args = {
                # Básicos
                'data': self.config.data_config,
                'epochs': self.config.epochs,
                'batch': self.config.batch_size,
                'imgsz': self.config.image_size,
                'device': self.config.device,
                'workers': self.config.workers,
                
                # Proyecto
                'project': str(Path('runs') / 'detect' / self.config.project_name),
                'name': self.config.experiment_name,
                
                # Optimización
                'optimizer': self.config.optimizer,
                'lr0': self.config.learning_rate,
                'momentum': self.config.momentum,
                'weight_decay': self.config.weight_decay,
                'lrf': 0.01,  # Final learning rate factor
                
                # Scheduler
                'cos_lr': self.config.lr_scheduler == "cosine",
                'warmup_epochs': self.config.warmup_epochs,
                'warmup_momentum': self.config.warmup_momentum,
                'warmup_bias_lr': self.config.warmup_bias_lr,
                
                # Early stopping
                'patience': self.config.patience,
                'save_period': self.config.save_period,
                
                # Augmentation
                'degrees': self.config.degrees,
                'translate': self.config.translate,
                'scale': self.config.scale,
                'shear': self.config.shear,
                'perspective': self.config.perspective,
                'flipud': self.config.flipud,
                'fliplr': self.config.fliplr,
                'mosaic': self.config.mosaic,
                'mixup': self.config.mixup,
                'copy_paste': self.config.copy_paste,
                
                # Validación
                'val': self.config.validation,
                'plots': self.config.plots,
                'save_json': self.config.save_json,
                'save_hybrid': self.config.save_hybrid,
                
                # Performance
                'half': self.config.half_precision,
                'dnn': self.config.dnn,
                'multi_scale': self.config.multi_scale,
                
                # Resume
                'resume': self.config.resume,
                'exist_ok': True,
                'verbose': True
            }
            
            # Parámetros específicos de YOLOv12
            if self.config.model_type == "yolov12":
                if self.config.use_flash_attention:
                    args['flash_attention'] = True
                
                args['mlp_ratio'] = self.config.mlp_ratio
                args['attention_regions'] = self.config.area_attention_regions
            
            return args
            
        except Exception as e:
            self.logger.error(f"Error preparando argumentos: {e}")
            raise
    
    async def _save_final_results(self, results) -> None:
        """Guardar resultados finales."""
        try:
            results_path = self.output_dir / 'training_results.json'
            
            final_results = {
                'training_completed': True,
                'total_epochs': self.training_metrics.current_epoch,
                'training_time_hours': self.training_metrics.training_time_s / 3600,
                'best_map50': self.training_metrics.best_map50,
                'final_metrics': {
                    'precision': self.training_metrics.precision,
                    'recall': self.training_metrics.recall,
                    'map50': self.training_metrics.map50,
                    'map95': self.training_metrics.map95
                },
                'config': {
                    'model_type': self.config.model_type,
                    'model_size': self.config.model_size,
                    'epochs': self.config.epochs,
                    'batch_size': self.config.batch_size,
                    'learning_rate': self.config.learning_rate,
                    'use_flash_attention': self.config.use_flash_attention,
                    'use_r_elan': self.config.use_r_elan
                },
                'metrics_history': self._metrics_history
            }
            
            with open(results_path, 'w') as f:
                json.dump(final_results, f, indent=2)
            
            self.logger.info(f"Resultados guardados en: {results_path}")
            self.logger.info(f"Modelo entrenado disponible en: {self.output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado actual del entrenamiento."""
        return {
            'training': {
                'state': self.state.value,
                'active': self._training_active,
                'paused': self._paused,
                'current_epoch': self.training_metrics.current_epoch,
                'total_epochs': self.config.epochs,
                'progress_percent': (self.training_metrics.current_epoch / max(self.config.epochs, 1)) * 100,
                'estimated_time_remaining_s': self.training_metrics.estimated_time_remaining_s
            },
            'metrics': {
                'train_loss': self.training_metrics.train_loss,
                'val_loss': self.training_metrics.val_loss,
                'precision': self.training_metrics.precision,
                'recall': self.training_metrics.recall,
                'map50': self.training_metrics.map50,
                'map95': self.training_metrics.map95,
                'best_map50': self.training_metrics.best_map50,
                'learning_rate': self.training_metrics.learning_rate
            },
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('.').percent
            },
            'config': {
                'model_type': self.config.model_type,
                'model_size': self.config.model_size,
                'batch_size': self.config.batch_size,
                'image_size': self.config.image_size,
                'device': self.config.device,
                'use_flash_attention': self.config.use_flash_attention,
                'use_r_elan': self.config.use_r_elan
            }
        }
    
    async def cleanup(self) -> None:
        """Limpiar recursos."""
        try:
            self.logger.info("Limpiando recursos del entrenador...")
            
            self._training_active = False
            self._stop_requested = True
            
            if self.model:
                del self.model
                self.model = None
            
            # Limpiar cache de GPU si es necesario
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Limpieza del entrenador completada")
            
        except Exception as e:
            self.logger.error(f"Error durante limpieza: {e}")

# --- Función Principal Mejorada ---

def parse_arguments():
    """Parsear argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Entrenamiento Avanzado YOLOv12 para EcoSort')
    
    # Modelo
    parser.add_argument('--model-type', type=str, default='yolov12',
                        choices=['yolov8', 'yolov11', 'yolov12'],
                        help='Tipo de modelo YOLO')
    parser.add_argument('--model-size', type=str, default='n',
                        choices=['n', 's', 'm', 'l', 'x'],
                        help='Tamaño del modelo')
    parser.add_argument('--model', type=str, default=None,
                        help='Ruta a modelo preentrenado específico')
    
    # Dataset
    parser.add_argument('--data', type=str, default='./DATASET_basura/data.yaml',
                        help='Ruta al archivo data.yaml')
    
    # Entrenamiento
    parser.add_argument('--epochs', type=int, default=100,
                        help='Número de épocas')
    parser.add_argument('--batch', type=int, default=16,
                        help='Tamaño del batch')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='Tamaño de imagen')
    parser.add_argument('--device', type=str, default='auto',
                        help='Dispositivo (auto, cpu, cuda, mps)')
    
    # Proyecto
    parser.add_argument('--project', type=str, default='EcoSort_Training_v2',
                        help='Nombre del proyecto')
    parser.add_argument('--name', type=str, default=None,
                        help='Nombre del experimento')
    
    # YOLOv12 específico
    parser.add_argument('--flash-attention', action='store_true',
                        help='Usar FlashAttention (YOLOv12)')
    parser.add_argument('--no-r-elan', action='store_true',
                        help='Deshabilitar R-ELAN (YOLOv12)')
    parser.add_argument('--attention-regions', type=int, default=4,
                        choices=[2, 4, 8],
                        help='Regiones para Area Attention')
    parser.add_argument('--mlp-ratio', type=float, default=1.2,
                        help='Ratio MLP para YOLOv12')
    
    # Optimización
    parser.add_argument('--lr', type=float, default=0.01,
                        help='Learning rate inicial')
    parser.add_argument('--optimizer', type=str, default='auto',
                        choices=['auto', 'SGD', 'Adam', 'AdamW'],
                        help='Optimizador')
    parser.add_argument('--patience', type=int, default=25,
                        help='Paciencia para early stopping')
    
    # Performance
    parser.add_argument('--half', action='store_true',
                        help='Usar precisión FP16')
    parser.add_argument('--workers', type=int, default=4,
                        help='Número de workers')
    
    # Control
    parser.add_argument('--resume', action='store_true',
                        help='Reanudar entrenamiento')
    parser.add_argument('--resume-path', type=str, default=None,
                        help='Ruta específica para reanudar')
    
    return parser.parse_args()

async def main():
    """Función principal de entrenamiento."""
    args = parse_arguments()
    
    try:
        # Crear configuración
        config = TrainingConfiguration(
            model_type=args.model_type,
            model_size=args.model_size,
            model_path=args.model,
            data_config=args.data,
            epochs=args.epochs,
            batch_size=args.batch,
            image_size=args.imgsz,
            device=args.device,
            project_name=args.project,
            experiment_name=args.name,
            learning_rate=args.lr,
            optimizer=args.optimizer,
            patience=args.patience,
            use_flash_attention=args.flash_attention,
            use_r_elan=not args.no_r_elan,
            area_attention_regions=args.attention_regions,
            mlp_ratio=args.mlp_ratio,
            half_precision=args.half,
            workers=args.workers,
            resume=args.resume,
            resume_path=args.resume_path
        )
        
        # Crear y configurar entrenador
        trainer = AdvancedYOLOTrainer(config)
        
        # Inicializar
        if not await trainer.initialize():
            logger.error("Error inicializando entrenador")
            return 1
        
        # Mostrar información inicial
        status = trainer.get_status()
        logger.info("=== Configuración de Entrenamiento ===")
        logger.info(f"Modelo: {config.model_type.upper()}{config.model_size}")
        logger.info(f"Dataset: {config.data_config}")
        logger.info(f"Épocas: {config.epochs}")
        logger.info(f"Batch Size: {config.batch_size}")
        logger.info(f"Dispositivo: {config.device}")
        
        if config.model_type == "yolov12":
            logger.info("=== Características YOLOv12 ===")
            logger.info(f"FlashAttention: {config.use_flash_attention}")
            logger.info(f"R-ELAN: {config.use_r_elan}")
            logger.info(f"Area Attention Regiones: {config.area_attention_regions}")
            logger.info(f"MLP Ratio: {config.mlp_ratio}")
        
        # Ejecutar entrenamiento
        logger.info("Iniciando entrenamiento...")
        success = await trainer.train()
        
        if success:
            final_status = trainer.get_status()
            logger.info("=== Entrenamiento Completado Exitosamente ===")
            logger.info(f"Tiempo total: {final_status['metrics']['map50']:.1f} horas")
            logger.info(f"Mejor mAP50: {final_status['metrics']['map50']:.3f}")
            logger.info(f"Resultados en: {trainer.output_dir}")
            return 0
        else:
            logger.error("Entrenamiento falló")
            return 1
        
    except KeyboardInterrupt:
        logger.info("Entrenamiento interrumpido por usuario")
        return 1
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return 1
    finally:
        if 'trainer' in locals():
            await trainer.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))