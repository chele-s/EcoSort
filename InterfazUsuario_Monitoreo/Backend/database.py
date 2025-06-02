# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# database.py - Módulo de gestión de base de datos para el sistema
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este módulo maneja la persistencia de datos del sistema:
#   - Registro de clasificaciones
#   - Estadísticas de operación
#   - Historial de eventos
#   - Métricas de rendimiento
# -----------------------------------------------------------------------------

import sqlite3
import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import threading
from contextlib import contextmanager
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gestor de base de datos para el sistema de clasificación de residuos.
    Utiliza SQLite para almacenamiento local eficiente.
    """
    
    def __init__(self, db_path: str = "InterfazUsuario_Monitoreo/data/ecosort_industrial.db"):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._connection = None
        
        # Crear directorio si no existe
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos
        self._initialize_database()
        
    def _initialize_database(self):
        """Crea las tablas necesarias si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de clasificaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    processing_time_ms REAL,
                    image_path TEXT,
                    diverter_activated BOOLEAN DEFAULT 0,
                    diverter_delay_ms REAL,
                    plc_response_time_ms REAL,
                    error_occurred BOOLEAN DEFAULT 0,
                    error_message TEXT
                )
            ''')
            
            # Tabla de estadísticas por hora
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_timestamp INTEGER NOT NULL UNIQUE,
                    total_items INTEGER DEFAULT 0,
                    metal_count INTEGER DEFAULT 0,
                    plastic_count INTEGER DEFAULT 0,
                    glass_count INTEGER DEFAULT 0,
                    carton_count INTEGER DEFAULT 0,
                    other_count INTEGER DEFAULT 0,
                    avg_confidence REAL,
                    avg_processing_time_ms REAL,
                    error_count INTEGER DEFAULT 0,
                    uptime_seconds INTEGER DEFAULT 0
                )
            ''')
            
            # Tabla de eventos del sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                )
            ''')
            
            # Tabla de estado de tolvas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bin_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    category TEXT NOT NULL,
                    fill_level_percent REAL NOT NULL,
                    temperature REAL,
                    alert_triggered BOOLEAN DEFAULT 0
                )
            ''')
            
            # Tabla de configuración del sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            ''')
            
            # Tabla de mantenimiento
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    component TEXT NOT NULL,
                    action TEXT NOT NULL,
                    technician TEXT,
                    notes TEXT,
                    next_maintenance_date TEXT
                )
            ''')
            
            # Índices para mejorar rendimiento
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_classifications_timestamp ON classifications(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_classifications_category ON classifications(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hourly_stats_timestamp ON hourly_stats(hour_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bin_status_timestamp ON bin_status(timestamp)')
            
            conn.commit()
            logger.info("Base de datos inicializada correctamente")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para manejar conexiones de forma segura."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
        try:
            yield conn
        finally:
            conn.close()
    
    def record_classification(self, category: str, confidence: float, 
                            processing_time_ms: float = None,
                            image_path: str = None,
                            diverter_activated: bool = False,
                            diverter_delay_ms: float = None,
                            plc_response_time_ms: float = None,
                            error_occurred: bool = False,
                            error_message: str = None) -> int:
        """
        Registra una clasificación en la base de datos.
        
        Returns:
            ID del registro insertado
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO classifications 
                    (timestamp, category, confidence, processing_time_ms, image_path,
                     diverter_activated, diverter_delay_ms, plc_response_time_ms,
                     error_occurred, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    time.time(), category, confidence, processing_time_ms, image_path,
                    diverter_activated, diverter_delay_ms, plc_response_time_ms,
                    error_occurred, error_message
                ))
                conn.commit()
                
                # Actualizar estadísticas horarias
                self._update_hourly_stats(category, confidence, processing_time_ms, error_occurred)
                
                return cursor.lastrowid
    
    def _update_hourly_stats(self, category: str, confidence: float, 
                             processing_time_ms: Optional[float], error_occurred: bool):
        """Actualiza las estadísticas horarias."""
        current_hour = int(time.time() // 3600) * 3600
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM hourly_stats WHERE hour_timestamp = ?', (current_hour,))
            row = cursor.fetchone()
            
            if row:
                # Actualizar registro existente
                new_total_items = row['total_items'] + 1
                new_avg_confidence = ((row['avg_confidence'] * row['total_items']) + confidence) / new_total_items if row['avg_confidence'] is not None else confidence
                
                new_avg_processing_time = None
                if processing_time_ms is not None:
                    if row['avg_processing_time_ms'] is not None and row['total_items'] > 0: # total_items should not be 0 if row exists
                        new_avg_processing_time = ((row['avg_processing_time_ms'] * row['total_items']) + processing_time_ms) / new_total_items
                    else:
                        new_avg_processing_time = processing_time_ms

                new_error_count = row['error_count'] + 1 if error_occurred else row['error_count']

                update_query = f"""
                    UPDATE hourly_stats 
                    SET total_items = ?,
                        {category.lower()}_count = {category.lower()}_count + 1,
                        avg_confidence = ?,
                        avg_processing_time_ms = ?,
                        error_count = ?
                    WHERE hour_timestamp = ?
                """
                cursor.execute(update_query, (
                    new_total_items, 
                    new_avg_confidence, 
                    new_avg_processing_time, 
                    new_error_count, 
                    current_hour
                ))
            else:
                # Crear nuevo registro
                avg_proc_time = processing_time_ms if processing_time_ms is not None else None
                err_count = 1 if error_occurred else 0
                cursor.execute(f"""
                    INSERT INTO hourly_stats 
                    (hour_timestamp, total_items, {category.lower()}_count, avg_confidence, avg_processing_time_ms, error_count)
                    VALUES (?, 1, 1, ?, ?, ?)
                """, (current_hour, confidence, avg_proc_time, err_count))
            
            conn.commit()
    
    def log_system_event(self, event_type: str, severity: str, 
                        message: str, details: Dict = None):
        """
        Registra un evento del sistema.
        
        Args:
            event_type: Tipo de evento (startup, shutdown, error, warning, info)
            severity: Severidad (critical, error, warning, info, debug)
            message: Mensaje del evento
            details: Detalles adicionales en formato diccionario
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_events (timestamp, event_type, severity, message, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    time.time(), event_type, severity, message,
                    json.dumps(details) if details else None
                ))
                conn.commit()
    
    def update_bin_status(self, category: str, fill_level_percent: float,
                         temperature: float = None, alert_triggered: bool = False):
        """Actualiza el estado de una tolva."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bin_status (timestamp, category, fill_level_percent, temperature, alert_triggered)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    time.time(), category, fill_level_percent, temperature, alert_triggered
                ))
                conn.commit()
    
    def get_statistics(self, start_time: float = None, end_time: float = None) -> Dict:
        """
        Obtiene estadísticas del sistema para un rango de tiempo.
        
        Args:
            start_time: Timestamp de inicio (por defecto: últimas 24 horas)
            end_time: Timestamp de fin (por defecto: ahora)
            
        Returns:
            Diccionario con estadísticas
        """
        if end_time is None:
            end_time = time.time()
        if start_time is None:
            start_time = end_time - 86400  # Últimas 24 horas
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de clasificaciones
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count
                FROM classifications
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))
            
            totals = dict(cursor.fetchone())
            
            # Clasificaciones por categoría
            cursor.execute('''
                SELECT 
                    category,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM classifications
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY category
            ''', (start_time, end_time))
            
            by_category = {row['category']: {
                'count': row['count'],
                'avg_confidence': row['avg_confidence']
            } for row in cursor.fetchall()}
            
            # Tendencia por hora
            cursor.execute('''
                SELECT 
                    hour_timestamp,
                    total_items,
                    metal_count,
                    plastic_count,
                    glass_count,
                    carton_count,
                    other_count,
                    error_count
                FROM hourly_stats
                WHERE hour_timestamp BETWEEN ? AND ?
                ORDER BY hour_timestamp
            ''', (int(start_time), int(end_time)))
            
            hourly_trend = [dict(row) for row in cursor.fetchall()]
            
            # Estado actual de tolvas
            cursor.execute('''
                SELECT DISTINCT category FROM bin_status
            ''')
            categories = [row['category'] for row in cursor.fetchall()]
            
            current_bin_status = {}
            for category in categories:
                cursor.execute('''
                    SELECT fill_level_percent, temperature, alert_triggered
                    FROM bin_status
                    WHERE category = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (category,))
                row = cursor.fetchone()
                if row:
                    current_bin_status[category] = dict(row)
            
            return {
                'period': {
                    'start': datetime.fromtimestamp(start_time).isoformat(),
                    'end': datetime.fromtimestamp(end_time).isoformat()
                },
                'totals': totals,
                'by_category': by_category,
                'hourly_trend': hourly_trend,
                'current_bin_status': current_bin_status,
                'generated_at': datetime.now().isoformat()
            }
    
    def get_recent_classifications(self, limit: int = 100) -> List[Dict]:
        """Obtiene las clasificaciones más recientes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM classifications
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_system_events(self, severity: str = None, limit: int = 100) -> List[Dict]:
        """Obtiene eventos del sistema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if severity:
                cursor.execute('''
                    SELECT * FROM system_events
                    WHERE severity = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (severity, limit))
            else:
                cursor.execute('''
                    SELECT * FROM system_events
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event['details']:
                    event['details'] = json.loads(event['details'])
                events.append(event)
            
            return events
    
    def save_config(self, key: str, value: any):
        """Guarda un valor de configuración."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, json.dumps(value), time.time()))
                conn.commit()
    
    def get_config(self, key: str) -> any:
        """Obtiene un valor de configuración."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM system_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['value'])
            return None
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Limpia datos antiguos de la base de datos."""
        cutoff_time = time.time() - (days_to_keep * 86400)
        
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Limpiar clasificaciones antiguas
                cursor.execute('DELETE FROM classifications WHERE timestamp < ?', (cutoff_time,))
                deleted_classifications = cursor.rowcount
                
                # Limpiar eventos antiguos (excepto críticos)
                cursor.execute('''
                    DELETE FROM system_events 
                    WHERE timestamp < ? AND severity != 'critical'
                ''', (cutoff_time,))
                deleted_events = cursor.rowcount
                
                # Limpiar estado de tolvas antiguo
                cursor.execute('DELETE FROM bin_status WHERE timestamp < ?', (cutoff_time,))
                deleted_bin_status = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Limpieza de datos: {deleted_classifications} clasificaciones, "
                          f"{deleted_events} eventos, {deleted_bin_status} estados de tolva eliminados")
    
    def export_data(self, output_path: str, start_time: float = None, end_time: float = None):
        """Exporta datos a un archivo JSON para análisis externo."""
        stats = self.get_statistics(start_time, end_time)
        classifications = self.get_recent_classifications(1000)
        
        export_data = {
            'statistics': stats,
            'recent_classifications': classifications,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Datos exportados a {output_path}")

    def update_classification_diversion_status(self, classification_id: int, 
                                               diverter_activated: bool, 
                                               plc_response_time_ms: Optional[float] = None,
                                               error_message: Optional[str] = None):
        """Actualiza el estado de desviación de una clasificación existente."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []

                updates.append("diverter_activated = ?")
                params.append(diverter_activated)

                if plc_response_time_ms is not None:
                    updates.append("plc_response_time_ms = ?")
                    params.append(plc_response_time_ms)
                
                if error_message is not None:
                    updates.append("error_occurred = ?")
                    params.append(True)
                    updates.append("error_message = ?")
                    params.append(error_message)
                
                params.append(classification_id)
                
                query = f"UPDATE classifications SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, tuple(params))
                conn.commit()
                logger.debug(f"Estado de desviación actualizado para clasificación ID: {classification_id}")

# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear instancia del gestor
    db = DatabaseManager()
    
    # Registrar algunas clasificaciones de prueba
    print("Registrando clasificaciones de prueba...")
    for i in range(10):
        category = ['metal', 'plastic', 'glass', 'carton', 'other'][i % 5]
        confidence = 0.85 + (i % 10) * 0.01
        db.record_classification(
            category=category,
            confidence=confidence,
            processing_time_ms=50 + i * 5,
            diverter_activated=category != 'other'
        )
        time.sleep(0.1)
    
    # Registrar eventos
    db.log_system_event('startup', 'info', 'Sistema iniciado correctamente')
    db.log_system_event('warning', 'warning', 'Nivel de tolva alto', 
                       {'category': 'plastic', 'level': 85})
    
    # Actualizar estado de tolvas
    db.update_bin_status('metal', 45.5, temperature=22.3)
    db.update_bin_status('plastic', 85.0, temperature=22.5, alert_triggered=True)
    db.update_bin_status('glass', 30.2, temperature=22.1)
    
    # Obtener estadísticas
    print("\n--- Estadísticas del Sistema ---")
    stats = db.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # Obtener clasificaciones recientes
    print("\n--- Clasificaciones Recientes ---")
    recent = db.get_recent_classifications(5)
    for classification in recent:
        print(f"- {classification['category']}: {classification['confidence']:.2f}")
    
    # Obtener eventos
    print("\n--- Eventos del Sistema ---")
    events = db.get_system_events(limit=5)
    for event in events:
        print(f"- [{event['severity']}] {event['message']}")
