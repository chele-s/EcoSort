# -*- coding: utf-8 -*-
"""
database_enhanced.py - Gestor de Base de Datos Enhanced para EcoSort v2.1

Características Enhanced:
- Cache inteligente con Redis-like functionality
- Nuevas tablas para analytics avanzados
- Índices optimizados para queries complejas
- Soporte para streaming de datos en tiempo real
- Validación robusta de datos
- Sistema de notificaciones integrado
- Métricas avanzadas para frontend React
"""

import sqlite3
import logging
import time
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Union
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import hashlib
import gzip
import pickle
import os

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Entrada de cache con metadatos"""
    key: str
    data: Any
    timestamp: float
    ttl: float
    hit_count: int = 0
    size_bytes: int = 0

@dataclass
class RealtimeMetrics:
    """Métricas en tiempo real para animaciones"""
    timestamp: float
    objects_per_minute: float
    avg_confidence: float
    processing_time_ms: float
    error_rate: float
    throughput_efficiency: float
    system_load: float
    active_diversions: int

class IntelligentCache:
    """Sistema de cache inteligente en memoria"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 300):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_times: deque = deque()
        self._lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'current_size_bytes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del cache"""
        with self._lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Verificar TTL
            if time.time() > entry.timestamp + entry.ttl:
                del self.cache[key]
                self.stats['misses'] += 1
                return None
            
            # Actualizar estadísticas
            entry.hit_count += 1
            self.stats['hits'] += 1
            self.access_times.append((time.time(), key))
            
            return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Almacena valor en cache"""
        with self._lock:
            ttl = ttl or self.default_ttl
            
            # Calcular tamaño aproximado
            try:
                serialized = pickle.dumps(data)
                size_bytes = len(serialized)
            except:
                size_bytes = len(str(data).encode('utf-8'))
            
            # Verificar espacio disponible
            self._ensure_space(size_bytes)
            
            # Crear entrada
            entry = CacheEntry(
                key=key,
                data=data,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            # Actualizar cache existente
            if key in self.cache:
                old_size = self.cache[key].size_bytes
                self.stats['current_size_bytes'] -= old_size
            
            self.cache[key] = entry
            self.stats['current_size_bytes'] += size_bytes
            
            return True
    
    def _ensure_space(self, needed_bytes: int):
        """Asegura espacio disponible en cache"""
        while (self.stats['current_size_bytes'] + needed_bytes > self.max_size_bytes and 
               self.cache):
            # Estrategia LRU mejorada
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].timestamp + self.cache[k].hit_count * 60)
            
            removed_entry = self.cache.pop(oldest_key)
            self.stats['current_size_bytes'] -= removed_entry.size_bytes
            self.stats['evictions'] += 1
    
    def invalidate_pattern(self, pattern: str):
        """Invalida entradas que coincidan con el patrón"""
        with self._lock:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.stats['current_size_bytes'] -= self.cache[key].size_bytes
                del self.cache[key]

class DatabaseManagerEnhanced:
    """Gestor de base de datos enhanced con funcionalidades avanzadas"""
    
    def __init__(self, db_path: str = "InterfazUsuario_Monitoreo/data/ecosort_enhanced.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._connection_pool = {}
        self.cache = IntelligentCache(max_size_mb=150)
        
        # Métricas en tiempo real
        self._realtime_metrics = deque(maxlen=1000)
        self._notifications_queue = deque(maxlen=500)
        
        # Configuración de performance
        self.batch_size = 100
        self.write_buffer = []
        self._write_lock = threading.Lock()
        
        # Crear directorio si no existe
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos
        self._initialize_enhanced_database()
        
        # Iniciar workers en background
        self._start_background_workers()
        
        logger.info("DatabaseManagerEnhanced inicializado correctamente")
    
    def _initialize_enhanced_database(self):
        """Inicializa base de datos con tablas enhanced"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Habilitar optimizaciones de SQLite
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=memory")
            
            # Tabla de clasificaciones enhanced
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications_enhanced (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    session_id TEXT,
                    object_uuid TEXT UNIQUE,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    confidence REAL NOT NULL,
                    processing_time_ms REAL,
                    image_path TEXT,
                    thumbnail_path TEXT,
                    bounding_box JSON,
                    features_vector JSON,
                    diverter_activated BOOLEAN DEFAULT 0,
                    diverter_delay_ms REAL,
                    diverter_response_time_ms REAL,
                    belt_speed_mps REAL,
                    ambient_temperature REAL,
                    humidity_percent REAL,
                    error_occurred BOOLEAN DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    qr_code_data TEXT,
                    weight_grams REAL,
                    size_dimensions JSON,
                    material_composition JSON,
                    recycling_score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de analytics en tiempo real
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS realtime_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    minute_bucket INTEGER NOT NULL,
                    objects_processed INTEGER DEFAULT 0,
                    avg_confidence REAL,
                    avg_processing_time_ms REAL,
                    throughput_per_minute REAL,
                    error_rate REAL,
                    efficiency_score REAL,
                    system_load REAL,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    active_diversions INTEGER DEFAULT 0,
                    belt_utilization_percent REAL,
                    quality_index REAL,
                    UNIQUE(minute_bucket)
                )
            ''')
            
            # Tabla de notificaciones para frontend
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    category TEXT,
                    data JSON,
                    read_status BOOLEAN DEFAULT 0,
                    dismissed BOOLEAN DEFAULT 0,
                    expires_at REAL,
                    action_required BOOLEAN DEFAULT 0,
                    action_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de sesiones de operación
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_uuid TEXT UNIQUE NOT NULL,
                    start_timestamp REAL NOT NULL,
                    end_timestamp REAL,
                    operator_name TEXT,
                    shift_type TEXT,
                    configuration_snapshot JSON,
                    total_objects INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    efficiency_score REAL,
                    notes TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Tabla de configuración dinámica
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dynamic_config (
                    key TEXT PRIMARY KEY,
                    value JSON NOT NULL,
                    data_type TEXT NOT NULL,
                    category TEXT,
                    description TEXT,
                    validation_rules JSON,
                    requires_restart BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT
                )
            ''')
            
            # Tabla de métricas de performance para analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    tags JSON,
                    component TEXT,
                    session_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de datos para animaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS animation_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    animation_type TEXT NOT NULL,
                    object_id TEXT,
                    start_position JSON,
                    end_position JSON,
                    duration_ms REAL,
                    easing_function TEXT,
                    properties JSON,
                    status TEXT DEFAULT 'pending',
                    completed_at REAL
                )
            ''')
            
            # Tabla de alertas avanzadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS advanced_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity_level INTEGER NOT NULL,
                    component TEXT,
                    metric_name TEXT,
                    threshold_value REAL,
                    current_value REAL,
                    trend_direction TEXT,
                    prediction_confidence REAL,
                    auto_resolved BOOLEAN DEFAULT 0,
                    resolved_at REAL,
                    resolution_action TEXT,
                    escalation_level INTEGER DEFAULT 0,
                    data_snapshot JSON
                )
            ''')
            
            # Índices optimizados para queries complejas
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_classifications_timestamp_category ON classifications_enhanced(timestamp, category)",
                "CREATE INDEX IF NOT EXISTS idx_classifications_session ON classifications_enhanced(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_classifications_confidence ON classifications_enhanced(confidence)",
                "CREATE INDEX IF NOT EXISTS idx_classifications_processing_time ON classifications_enhanced(processing_time_ms)",
                "CREATE INDEX IF NOT EXISTS idx_realtime_analytics_minute ON realtime_analytics(minute_bucket)",
                "CREATE INDEX IF NOT EXISTS idx_notifications_type_severity ON notifications(type, severity)",
                "CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(read_status, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_performance_metrics_component ON performance_metrics(component, metric_type)",
                "CREATE INDEX IF NOT EXISTS idx_animation_data_type_status ON animation_data(animation_type, status)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_severity_resolved ON advanced_alerts(severity_level, auto_resolved)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            # Crear triggers para actualización automática
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_classification_timestamp 
                AFTER UPDATE ON classifications_enhanced
                FOR EACH ROW
                BEGIN
                    UPDATE classifications_enhanced 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_config_timestamp 
                AFTER UPDATE ON dynamic_config
                FOR EACH ROW
                BEGIN
                    UPDATE dynamic_config 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE key = NEW.key;
                END
            ''')
            
            conn.commit()
            logger.info("Base de datos enhanced inicializada con todas las tablas y optimizaciones")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones con pool"""
        thread_id = threading.get_ident()
        
        if thread_id not in self._connection_pool:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            self._connection_pool[thread_id] = conn
        
        try:
            yield self._connection_pool[thread_id]
        except Exception as e:
            self._connection_pool[thread_id].rollback()
            raise e
    
    def _start_background_workers(self):
        """Inicia workers en background para tareas asíncronas"""
        # Worker para batch writes
        self._batch_writer_thread = threading.Thread(
            target=self._batch_writer_worker, daemon=True)
        self._batch_writer_thread.start()
        
        # Worker para métricas en tiempo real
        self._metrics_worker_thread = threading.Thread(
            target=self._metrics_worker, daemon=True)
        self._metrics_worker_thread.start()
        
        # Worker para limpieza de cache
        self._cache_cleaner_thread = threading.Thread(
            target=self._cache_cleaner_worker, daemon=True)
        self._cache_cleaner_thread.start()
    
    def _batch_writer_worker(self):
        """Worker para escrituras por lotes"""
        while True:
            try:
                time.sleep(1)  # Escribir cada segundo
                if self.write_buffer:
                    with self._write_lock:
                        if self.write_buffer:
                            self._flush_write_buffer()
            except Exception as e:
                logger.error(f"Error en batch writer: {e}")
    
    def _metrics_worker(self):
        """Worker para generar métricas en tiempo real"""
        while True:
            try:
                time.sleep(5)  # Cada 5 segundos
                self._generate_realtime_metrics()
            except Exception as e:
                logger.error(f"Error en metrics worker: {e}")
    
    def _cache_cleaner_worker(self):
        """Worker para limpieza de cache"""
        while True:
            try:
                time.sleep(60)  # Cada minuto
                self._cleanup_expired_cache()
            except Exception as e:
                logger.error(f"Error en cache cleaner: {e}")
    
    def record_classification_enhanced(self, **kwargs) -> int:
        """Registra clasificación con datos enhanced"""
        classification_data = {
            'timestamp': time.time(),
            'object_uuid': kwargs.get('object_uuid', self._generate_uuid()),
            'session_id': kwargs.get('session_id'),
            'category': kwargs['category'],
            'subcategory': kwargs.get('subcategory'),
            'confidence': kwargs['confidence'],
            'processing_time_ms': kwargs.get('processing_time_ms'),
            'image_path': kwargs.get('image_path'),
            'thumbnail_path': kwargs.get('thumbnail_path'),
            'bounding_box': json.dumps(kwargs.get('bounding_box')) if kwargs.get('bounding_box') else None,
            'features_vector': json.dumps(kwargs.get('features_vector')) if kwargs.get('features_vector') else None,
            'diverter_activated': kwargs.get('diverter_activated', False),
            'diverter_delay_ms': kwargs.get('diverter_delay_ms'),
            'diverter_response_time_ms': kwargs.get('diverter_response_time_ms'),
            'belt_speed_mps': kwargs.get('belt_speed_mps'),
            'ambient_temperature': kwargs.get('ambient_temperature'),
            'humidity_percent': kwargs.get('humidity_percent'),
            'error_occurred': kwargs.get('error_occurred', False),
            'error_code': kwargs.get('error_code'),
            'error_message': kwargs.get('error_message'),
            'qr_code_data': kwargs.get('qr_code_data'),
            'weight_grams': kwargs.get('weight_grams'),
            'size_dimensions': json.dumps(kwargs.get('size_dimensions')) if kwargs.get('size_dimensions') else None,
            'material_composition': json.dumps(kwargs.get('material_composition')) if kwargs.get('material_composition') else None,
            'recycling_score': kwargs.get('recycling_score')
        }
        
        # Agregar a buffer para batch write
        with self._write_lock:
            self.write_buffer.append(('classifications_enhanced', classification_data))
        
        # Invalidar cache relacionado
        self.cache.invalidate_pattern('stats_')
        self.cache.invalidate_pattern('recent_')
        
        # Crear notificación si es necesario
        if classification_data['error_occurred']:
            self._create_notification(
                type='error',
                severity='warning',
                title='Error en Clasificación',
                message=f"Error procesando objeto {classification_data['category']}: {classification_data['error_message']}",
                category='classification'
            )
        
        # Retornar ID temporal (se actualizará en flush)
        return len(self.write_buffer)
    
    def get_realtime_analytics(self, minutes: int = 10) -> Dict[str, Any]:
        """Obtiene analytics en tiempo real para animaciones"""
        cache_key = f"realtime_analytics_{minutes}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        current_time = time.time()
        start_time = current_time - (minutes * 60)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Datos agregados por minuto
            cursor.execute('''
                SELECT 
                    minute_bucket,
                    objects_processed,
                    avg_confidence,
                    avg_processing_time_ms,
                    throughput_per_minute,
                    error_rate,
                    efficiency_score,
                    system_load,
                    active_diversions
                FROM realtime_analytics
                WHERE minute_bucket >= ?
                ORDER BY minute_bucket DESC
                LIMIT ?
            ''', (int(start_time // 60), minutes))
            
            analytics_data = [dict(row) for row in cursor.fetchall()]
            
            # Métricas actuales
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_objects,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate
                FROM classifications_enhanced
                WHERE timestamp >= ?
            ''', (start_time,))
            
            current_metrics = dict(cursor.fetchone() or {})
            
        result = {
            'timeline': analytics_data,
            'current': current_metrics,
            'generated_at': current_time,
            'period_minutes': minutes
        }
        
        self.cache.set(cache_key, result, ttl=30)  # Cache por 30 segundos
        return result
    
    def get_animation_data(self, animation_type: str = None, limit: int = 100) -> List[Dict]:
        """Obtiene datos para animaciones específicas"""
        cache_key = f"animation_data_{animation_type}_{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if animation_type:
                cursor.execute('''
                    SELECT * FROM animation_data
                    WHERE animation_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (animation_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM animation_data
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            data = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Deserializar JSON
                for json_field in ['start_position', 'end_position', 'properties']:
                    if row_dict.get(json_field):
                        row_dict[json_field] = json.loads(row_dict[json_field])
                data.append(row_dict)
        
        self.cache.set(cache_key, data, ttl=60)
        return data
    
    def create_animation_event(self, animation_type: str, object_id: str, **kwargs) -> int:
        """Crea evento de animación para frontend"""
        animation_data = {
            'timestamp': time.time(),
            'animation_type': animation_type,
            'object_id': object_id,
            'start_position': json.dumps(kwargs.get('start_position', {})),
            'end_position': json.dumps(kwargs.get('end_position', {})),
            'duration_ms': kwargs.get('duration_ms', 1000),
            'easing_function': kwargs.get('easing_function', 'easeInOutQuad'),
            'properties': json.dumps(kwargs.get('properties', {})),
            'status': 'pending'
        }
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO animation_data ({}) VALUES ({})
            '''.format(
                ', '.join(animation_data.keys()),
                ', '.join(['?' for _ in animation_data])
            ), list(animation_data.values()))
            
            conn.commit()
            
            # Invalidar cache de animaciones
            self.cache.invalidate_pattern('animation_data_')
            
            return cursor.lastrowid
    
    def _generate_uuid(self) -> str:
        """Genera UUID único para objetos"""
        import uuid
        return str(uuid.uuid4())
    
    def _create_notification(self, type: str, severity: str, title: str, 
                           message: str, **kwargs):
        """Crea notificación para frontend"""
        notification_data = {
            'uuid': self._generate_uuid(),
            'timestamp': time.time(),
            'type': type,
            'severity': severity,
            'title': title,
            'message': message,
            'category': kwargs.get('category'),
            'data': json.dumps(kwargs.get('data', {})),
            'expires_at': kwargs.get('expires_at'),
            'action_required': kwargs.get('action_required', False),
            'action_url': kwargs.get('action_url')
        }
        
        # Agregar a cola de notificaciones
        self._notifications_queue.append(notification_data)
        
        # Agregar a buffer para escritura
        with self._write_lock:
            self.write_buffer.append(('notifications', notification_data))
    
    def _flush_write_buffer(self):
        """Ejecuta escrituras por lotes"""
        if not self.write_buffer:
            return
        
        buffer_copy = self.write_buffer.copy()
        self.write_buffer.clear()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Agrupar por tabla
            by_table = defaultdict(list)
            for table, data in buffer_copy:
                by_table[table].append(data)
            
            # Ejecutar inserts por tabla
            for table, records in by_table.items():
                if records:
                    try:
                        # Construir query de insert múltiple
                        first_record = records[0]
                        columns = list(first_record.keys())
                        placeholders = ', '.join(['?' for _ in columns])
                        
                        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                        
                        # Preparar datos
                        data_tuples = [tuple(record[col] for col in columns) for record in records]
                        
                        cursor.executemany(query, data_tuples)
                        logger.debug(f"Inserted {len(records)} records into {table}")
                        
                    except Exception as e:
                        logger.error(f"Error inserting into {table}: {e}")
            
            conn.commit()
    
    def _generate_realtime_metrics(self):
        """Genera métricas en tiempo real"""
        current_minute = int(time.time() // 60)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Calcular métricas del último minuto
            minute_start = current_minute * 60
            minute_end = minute_start + 60
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as objects_processed,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time,
                    COUNT(*) * 1.0 / 1.0 as throughput_per_minute,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) * 100.0 / MAX(COUNT(*), 1) as error_rate
                FROM classifications_enhanced
                WHERE timestamp BETWEEN ? AND ?
            ''', (minute_start, minute_end))
            
            metrics = dict(cursor.fetchone() or {})
            
            # Calcular métricas adicionales
            metrics.update({
                'minute_bucket': current_minute,
                'timestamp': time.time(),
                'efficiency_score': max(0, 100 - (metrics.get('error_rate', 0) * 2)),
                'system_load': 50,  # Placeholder - obtener de sistema real
                'memory_usage_mb': 100,  # Placeholder
                'cpu_usage_percent': 25,  # Placeholder
                'active_diversions': 0,  # Placeholder
                'belt_utilization_percent': 75,  # Placeholder
                'quality_index': metrics.get('avg_confidence', 0) * 100 if metrics.get('avg_confidence') else 0
            })
            
            # Insertar o actualizar
            cursor.execute('''
                INSERT OR REPLACE INTO realtime_analytics 
                (minute_bucket, timestamp, objects_processed, avg_confidence, 
                 avg_processing_time_ms, throughput_per_minute, error_rate, 
                 efficiency_score, system_load, memory_usage_mb, cpu_usage_percent,
                 active_diversions, belt_utilization_percent, quality_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics['minute_bucket'], metrics['timestamp'],
                metrics['objects_processed'], metrics.get('avg_confidence'),
                metrics.get('avg_processing_time'), metrics['throughput_per_minute'],
                metrics['error_rate'], metrics['efficiency_score'], 
                metrics['system_load'], metrics['memory_usage_mb'],
                metrics['cpu_usage_percent'], metrics['active_diversions'],
                metrics['belt_utilization_percent'], metrics['quality_index']
            ))
            
            conn.commit()
            
            # Agregar a cola de métricas en tiempo real
            realtime_metric = RealtimeMetrics(
                timestamp=metrics['timestamp'],
                objects_per_minute=metrics['objects_processed'],
                avg_confidence=metrics.get('avg_confidence', 0),
                processing_time_ms=metrics.get('avg_processing_time', 0),
                error_rate=metrics['error_rate'],
                throughput_efficiency=metrics['efficiency_score'],
                system_load=metrics['system_load'],
                active_diversions=metrics['active_diversions']
            )
            
            self._realtime_metrics.append(realtime_metric)
    
    def _cleanup_expired_cache(self):
        """Limpia entradas expiradas del cache"""
        current_time = time.time()
        expired_keys = []
        
        with self.cache._lock:
            for key, entry in self.cache.cache.items():
                if current_time > entry.timestamp + entry.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self.cache.cache:
                    self.cache.stats['current_size_bytes'] -= self.cache.cache[key].size_bytes
                    del self.cache.cache[key]
        
        if expired_keys:
            logger.debug(f"Limpiadas {len(expired_keys)} entradas expiradas del cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        total_requests = self.cache.stats['hits'] + self.cache.stats['misses']
        hit_rate = (self.cache.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_entries': len(self.cache.cache),
            'size_mb': round(self.cache.stats['current_size_bytes'] / (1024*1024), 2),
            'max_size_mb': round(self.cache.max_size_bytes / (1024*1024), 2),
            'evictions': self.cache.stats['evictions'],
            'hits': self.cache.stats['hits'],
            'misses': self.cache.stats['misses']
        }

# Instancia global para compatibilidad
_enhanced_db_instance = None

def get_enhanced_database(db_path: str = None) -> DatabaseManagerEnhanced:
    """Obtiene instancia singleton de la base de datos enhanced"""
    global _enhanced_db_instance
    if _enhanced_db_instance is None:
        _enhanced_db_instance = DatabaseManagerEnhanced(db_path)
    return _enhanced_db_instance 