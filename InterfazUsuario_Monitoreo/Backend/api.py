# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# api.py - API REST para el sistema de monitoreo
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   API REST que expone endpoints para:
#   - Estadísticas en tiempo real
#   - Control del sistema
#   - Visualización de datos históricos
#   - Configuración del sistema
# -----------------------------------------------------------------------------

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import time
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import threading

# Importar módulos del proyecto
from InterfazUsuario_Monitoreo.Backend.database import DatabaseManager

# Configuración de logging
logger = logging.getLogger(__name__)

class SystemAPI:
    """API REST para el sistema de clasificación de residuos."""
    
    def __init__(self, database_manager: DatabaseManager, 
                 host='0.0.0.0', port=5000):
        """
        Inicializa la API del sistema.
        
        Args:
            database_manager: Instancia del gestor de base de datos
            host: Host donde se ejecutará la API
            port: Puerto de la API
        """
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'ecosort-industrial-2025'
        
        # Habilitar CORS para permitir acceso desde frontend
        CORS(self.app, resources={r"/*": {"origins": "*"}})
        
        # Configurar SocketIO para tiempo real
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.db = database_manager
        self.host = host
        self.port = port
        
        # Estado del sistema
        self.system_state = {
            'running': False,
            'emergency_stop': False,
            'plc_connected': False,
            'camera_active': False,
            'last_classification': None,
            'current_stats': {},
            'alerts': []
        }
        
        # Configurar rutas
        self._setup_routes()
        self._setup_socketio_events()
        
    def _setup_routes(self):
        """Configura todas las rutas de la API."""
        
        # Ruta principal - Dashboard
        @self.app.route('/')
        def index():
            return jsonify({
                'name': 'EcoSort Industrial API',
                'version': '1.0.0',
                'status': 'online',
                'endpoints': {
                    'statistics': '/api/stats',
                    'system_status': '/api/status',
                    'classifications': '/api/classifications',
                    'events': '/api/events',
                    'bins': '/api/bins',
                    'control': '/api/control/*',
                    'config': '/api/config/*'
                }
            })
        
        # --- Endpoints de Estadísticas ---
        
        @self.app.route('/api/stats', methods=['GET'])
        def get_statistics():
            """Obtiene estadísticas del sistema."""
            try:
                # Parámetros opcionales
                hours = request.args.get('hours', 24, type=int)
                start_time = time.time() - (hours * 3600)
                
                stats = self.db.get_statistics(start_time=start_time)
                return jsonify({
                    'success': True,
                    'data': stats
                })
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/stats/realtime', methods=['GET'])
        def get_realtime_stats():
            """Obtiene estadísticas en tiempo real."""
            return jsonify({
                'success': True,
                'data': self.system_state['current_stats']
            })
        
        # --- Endpoints de Estado del Sistema ---
        
        @self.app.route('/api/status', methods=['GET'])
        def get_system_status():
            """Obtiene el estado actual del sistema."""
            return jsonify({
                'success': True,
                'data': {
                    'system_running': self.system_state['running'],
                    'emergency_stop': self.system_state['emergency_stop'],
                    'plc_connected': self.system_state['plc_connected'],
                    'camera_active': self.system_state['camera_active'],
                    'last_classification': self.system_state['last_classification'],
                    'active_alerts': len(self.system_state['alerts']),
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        # --- Endpoints de Clasificaciones ---
        
        @self.app.route('/api/classifications', methods=['GET'])
        def get_classifications():
            """Obtiene las clasificaciones recientes."""
            try:
                limit = request.args.get('limit', 100, type=int)
                classifications = self.db.get_recent_classifications(limit=limit)
                
                return jsonify({
                    'success': True,
                    'data': classifications,
                    'count': len(classifications)
                })
            except Exception as e:
                logger.error(f"Error obteniendo clasificaciones: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/classifications/summary', methods=['GET'])
        def get_classifications_summary():
            """Obtiene resumen de clasificaciones por categoría."""
            try:
                hours = request.args.get('hours', 24, type=int)
                start_time = time.time() - (hours * 3600)
                
                stats = self.db.get_statistics(start_time=start_time)
                
                return jsonify({
                    'success': True,
                    'data': stats.get('by_category', {}),
                    'period_hours': hours
                })
            except Exception as e:
                logger.error(f"Error obteniendo resumen: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # --- Endpoints de Eventos ---
        
        @self.app.route('/api/events', methods=['GET'])
        def get_events():
            """Obtiene eventos del sistema."""
            try:
                severity = request.args.get('severity')
                limit = request.args.get('limit', 100, type=int)
                
                events = self.db.get_system_events(severity=severity, limit=limit)
                
                return jsonify({
                    'success': True,
                    'data': events,
                    'count': len(events)
                })
            except Exception as e:
                logger.error(f"Error obteniendo eventos: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # --- Endpoints de Tolvas ---
        
        @self.app.route('/api/bins', methods=['GET'])
        def get_bins_status():
            """Obtiene el estado actual de todas las tolvas."""
            try:
                stats = self.db.get_statistics()
                bin_status = stats.get('current_bin_status', {})
                
                # Agregar información adicional
                for category, status in bin_status.items():
                    # Determinar si hay alerta
                    if status['fill_level_percent'] > 80:
                        status['alert_level'] = 'high'
                    elif status['fill_level_percent'] > 60:
                        status['alert_level'] = 'medium'
                    else:
                        status['alert_level'] = 'normal'
                
                return jsonify({
                    'success': True,
                    'data': bin_status
                })
            except Exception as e:
                logger.error(f"Error obteniendo estado de tolvas: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/bins/<category>/history', methods=['GET'])
        def get_bin_history(category):
            """Obtiene el historial de una tolva específica."""
            # TODO: Implementar consulta específica para historial de tolva
            return jsonify({
                'success': True,
                'data': {
                    'category': category,
                    'history': []  # Placeholder
                }
            })
        
        # --- Endpoints de Control ---
        
        @self.app.route('/api/control/start', methods=['POST'])
        @self._require_auth
        def start_system():
            """Inicia el sistema de clasificación."""
            try:
                # Aquí se comunicaría con el sistema principal
                self.system_state['running'] = True
                self.db.log_system_event('control', 'info', 'Sistema iniciado vía API')
                
                # Emitir evento por WebSocket
                self.socketio.emit('system_started', {
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Sistema iniciado correctamente'
                })
            except Exception as e:
                logger.error(f"Error iniciando sistema: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/control/stop', methods=['POST'])
        @self._require_auth
        def stop_system():
            """Detiene el sistema de clasificación."""
            try:
                self.system_state['running'] = False
                self.db.log_system_event('control', 'info', 'Sistema detenido vía API')
                
                self.socketio.emit('system_stopped', {
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Sistema detenido correctamente'
                })
            except Exception as e:
                logger.error(f"Error deteniendo sistema: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/control/emergency', methods=['POST'])
        def emergency_stop():
            """Activa la parada de emergencia."""
            try:
                self.system_state['emergency_stop'] = True
                self.system_state['running'] = False
                
                self.db.log_system_event('emergency', 'critical', 
                                       'PARADA DE EMERGENCIA ACTIVADA VÍA API')
                
                self.socketio.emit('emergency_stop', {
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Parada de emergencia activada'
                })
            except Exception as e:
                logger.error(f"Error en parada de emergencia: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # --- Endpoints de Configuración ---
        
        @self.app.route('/api/config', methods=['GET'])
        @self._require_auth
        def get_config():
            """Obtiene la configuración actual del sistema."""
            try:
                # Obtener configuración de la base de datos
                config_keys = ['belt_speed', 'confidence_threshold', 
                             'bin_alert_threshold', 'maintenance_schedule']
                
                config = {}
                for key in config_keys:
                    value = self.db.get_config(key)
                    if value is not None:
                        config[key] = value
                
                return jsonify({
                    'success': True,
                    'data': config
                })
            except Exception as e:
                logger.error(f"Error obteniendo configuración: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config', methods=['POST'])
        @self._require_auth
        def update_config():
            """Actualiza la configuración del sistema."""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'No se proporcionaron datos'
                    }), 400
                
                # Guardar cada configuración
                for key, value in data.items():
                    self.db.save_config(key, value)
                
                self.db.log_system_event('config', 'info', 
                                       'Configuración actualizada vía API',
                                       {'changes': list(data.keys())})
                
                return jsonify({
                    'success': True,
                    'message': 'Configuración actualizada correctamente'
                })
            except Exception as e:
                logger.error(f"Error actualizando configuración: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # --- Endpoints de Reportes ---
        
        @self.app.route('/api/reports/export', methods=['GET'])
        @self._require_auth
        def export_report():
            """Exporta datos para análisis externo."""
            try:
                hours = request.args.get('hours', 24, type=int)
                start_time = time.time() - (hours * 3600)
                
                # Generar nombre de archivo único
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'ecosort_report_{timestamp}.json'
                filepath = os.path.join('exports', filename)
                
                # Crear directorio si no existe
                os.makedirs('exports', exist_ok=True)
                
                # Exportar datos
                self.db.export_data(filepath, start_time=start_time)
                
                return send_from_directory('exports', filename, 
                                         as_attachment=True)
            except Exception as e:
                logger.error(f"Error exportando reporte: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _setup_socketio_events(self):
        """Configura eventos de WebSocket para comunicación en tiempo real."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Maneja nueva conexión WebSocket."""
            logger.info(f"Cliente conectado: {request.sid}")
            emit('connected', {
                'message': 'Conectado al servidor EcoSort',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Maneja desconexión de cliente."""
            logger.info(f"Cliente desconectado: {request.sid}")
        
        @self.socketio.on('request_update')
        def handle_update_request():
            """Maneja solicitud de actualización de estado."""
            emit('status_update', {
                'system_state': self.system_state,
                'timestamp': datetime.now().isoformat()
            })
    
    def _require_auth(self, f):
        """Decorador para endpoints que requieren autenticación."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Por ahora, autenticación simple con token
            # En producción, usar JWT o similar
            auth_token = request.headers.get('Authorization')
            
            if not auth_token or auth_token != 'Bearer ecosort-admin-token':
                return jsonify({
                    'success': False,
                    'error': 'No autorizado'
                }), 401
            
            return f(*args, **kwargs)
        return decorated_function
    
    def update_system_state(self, state_updates: dict):
        """Actualiza el estado del sistema y notifica a clientes."""
        self.system_state.update(state_updates)
        
        # Emitir actualización por WebSocket
        self.socketio.emit('state_update', {
            'updates': state_updates,
            'timestamp': datetime.now().isoformat()
        })
    
    def broadcast_classification(self, classification_data: dict):
        """Transmite una nueva clasificación a todos los clientes."""
        self.system_state['last_classification'] = classification_data
        
        self.socketio.emit('new_classification', {
            'data': classification_data,
            'timestamp': datetime.now().isoformat()
        })
    
    def run(self, debug=False):
        """Inicia el servidor de la API."""
        logger.info(f"Iniciando API en {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)

# Función auxiliar para crear e iniciar la API
def create_api(database_manager: DatabaseManager, host='0.0.0.0', port=5000):
    """Crea una instancia de la API del sistema."""
    return SystemAPI(database_manager, host, port)

# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear gestor de base de datos
    db = DatabaseManager()
    
    # Crear y ejecutar API
    api = create_api(db)
    api.run(debug=True)
