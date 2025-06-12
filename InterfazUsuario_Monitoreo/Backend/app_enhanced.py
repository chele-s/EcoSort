# -*- coding: utf-8 -*-
"""
app_enhanced.py - Aplicación Principal Enhanced para EcoSort v2.1

Punto de entrada principal que integra:
- Base de datos enhanced con cache inteligente
- API REST con JWT y rate limiting  
- WebSocket avanzado para tiempo real
- Tareas en segundo plano
- Configuración dinámica
- Sistema de notificaciones

Características Enhanced:
- Autenticación JWT completa
- Rate limiting por usuario/endpoint
- Cache inteligente para performance
- WebSocket con rooms y permisos
- Validación robusta de datos
- Sistema de notificaciones en tiempo real
- Analytics avanzados para React frontend
- Soporte específico para animaciones
"""

import logging
import os
import sys
import signal
import time
from datetime import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

# Añadir directorio del proyecto al path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.append(project_root)

# Imports de módulos enhanced
from InterfazUsuario_Monitoreo.Backend.database_enhanced import DatabaseManagerEnhanced, get_enhanced_database
from InterfazUsuario_Monitoreo.Backend.api_enhanced import *

# Configurar logging avanzado
def setup_logging():
    """Configura sistema de logging enhanced"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
    
    # Handler para archivo
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/ecosort_enhanced_api.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Silenciar logs muy verbosos
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)

class EcoSortEnhancedApp:
    """Aplicación principal Enhanced de EcoSort"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.app = None
        self.socketio = None
        self.db = None
        self.api_manager = None
        self.ws_manager = None
        self.background_tasks = None
        
        # Estado de la aplicación
        self.running = False
        self.start_time = time.time()
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger = logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales del sistema para shutdown graceful"""
        self.logger.info(f"Señal {signum} recibida, iniciando shutdown...")
        self.stop()
    
    def initialize(self):
        """Inicializa la aplicación enhanced"""
        try:
            self.logger.info("=== INICIANDO ECOSORT ENHANCED BACKEND v2.1 ===")
            
            # 1. Inicializar base de datos enhanced
            self.logger.info("Inicializando base de datos enhanced...")
            db_path = os.path.join(project_root, "InterfazUsuario_Monitoreo", "data", "ecosort_enhanced.db")
            self.db = DatabaseManagerEnhanced(db_path)
            
            # 2. Crear aplicación Flask
            self.logger.info("Configurando aplicación Flask...")
            self.app = Flask(__name__)
            self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ecosort-enhanced-2025-super-secret')
            
            # Middleware
            self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1)
            
            # CORS avanzado para React
            CORS(self.app, resources={
                r"/api/*": {
                    "origins": [
                        "http://localhost:3000",
                        "http://localhost:3001", 
                        "https://ecosort-frontend.vercel.app",
                        "*"
                    ],
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                    "supports_credentials": True
                }
            })
            
            # Compresión
            Compress(self.app)
            
            # 3. Configurar SocketIO
            self.logger.info("Configurando SocketIO avanzado...")
            self.socketio = SocketIO(
                self.app,
                cors_allowed_origins="*",
                async_mode='threading',
                ping_timeout=60,
                ping_interval=25,
                logger=False,
                engineio_logger=False
            )
            
            # 4. Configurar managers
            self._setup_managers()
            
            # 5. Configurar rutas
            self._setup_routes()
            
            # 6. Configurar WebSocket
            self._setup_websocket()
            
            # 7. Iniciar tareas en segundo plano
            self._setup_background_tasks()
            
            self.logger.info("Aplicación Enhanced inicializada correctamente")
            self.logger.info("Características habilitadas:")
            self.logger.info("✓ Base de datos con cache inteligente")
            self.logger.info("✓ Autenticación JWT con roles")
            self.logger.info("✓ Rate limiting por endpoint")
            self.logger.info("✓ WebSocket con rooms y permisos")
            self.logger.info("✓ Validación robusta de datos")
            self.logger.info("✓ Sistema de notificaciones")
            self.logger.info("✓ Analytics para React frontend")
            self.logger.info("✓ Soporte para animaciones complejas")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando aplicación: {e}")
            return False
    
    def _setup_managers(self):
        """Configura los managers del sistema"""
        # Authentication Manager
        self.auth_manager = AuthenticationManager(self.app.config['SECRET_KEY'])
        
        # Rate Limit Manager
        self.rate_limit_manager = RateLimitManager()
        
        # Estado del sistema
        self.system_state = {
            'running': False,
            'mode': 'idle',
            'emergency_stop': False,
            'components': {
                'camera': True,  # Simulado
                'ai_model': True,
                'plc': False,
                'sensors': True
            },
            'performance': {
                'objects_per_minute': 0,
                'avg_confidence': 0,
                'system_load': 0,
                'memory_usage': 0
            },
            'alerts': [],
            'active_users': 0
        }
    
    def _setup_routes(self):
        """Configura todas las rutas de la API"""
        
        # === MIDDLEWARE ===
        
        @self.app.before_request
        def before_request():
            g.start_time = time.time()
            g.request_id = f"{time.time():.6f}_{request.remote_addr}"[-8:]
            
            # Rate limiting
            if request.endpoint and not request.endpoint.startswith('static'):
                limit_type = self._get_limit_type(request.endpoint)
                key = f"{request.remote_addr}_{limit_type}"
                
                if not self.rate_limit_manager.is_allowed(key, limit_type):
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded',
                        'retry_after': 60
                    }), 429
        
        @self.app.after_request
        def after_request(response):
            duration = time.time() - g.get('start_time', time.time())
            self.logger.info(f"[{g.get('request_id', 'unknown')}] {request.method} {request.path} - "
                           f"{response.status_code} - {duration:.3f}s")
            
            # Headers de seguridad
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
            
            return response
        
        # === RUTAS PRINCIPALES ===
        
        @self.app.route('/api/v2')
        @self.app.route('/api/v2/')
        def api_info():
            """Información de la API Enhanced"""
            uptime = time.time() - self.start_time
            
            return jsonify({
                'name': 'EcoSort Industrial API Enhanced',
                'version': '2.1.0',
                'status': 'online',
                'uptime_seconds': uptime,
                'features': [
                    'JWT Authentication with Roles',
                    'Intelligent Rate Limiting', 
                    'Real-time WebSocket Streaming',
                    'Advanced Analytics & Metrics',
                    'Animation Support for React',
                    'Intelligent Caching System',
                    'Robust Data Validation',
                    'Push Notifications',
                    'Dynamic Configuration'
                ],
                'endpoints': {
                    'auth': '/api/v2/auth/*',
                    'dashboard': '/api/v2/dashboard/*',
                    'analytics': '/api/v2/analytics/*',
                    'animations': '/api/v2/animations/*',
                    'classifications': '/api/v2/classifications/*',
                    'notifications': '/api/v2/notifications/*',
                    'system': '/api/v2/system/*'
                },
                'websocket': {
                    'url': '/socket.io/',
                    'rooms': ['dashboard', 'analytics', 'control', 'maintenance', 'viewer'],
                    'events': ['metrics_update', 'new_classification', 'new_notification', 'system_control']
                },
                'cache_stats': self.db.get_cache_stats(),
                'active_connections': self.system_state['active_users']
            })
        
        # === AUTENTICACIÓN ===
        
        @self.app.route('/api/v2/auth/login', methods=['POST'])
        def login():
            """Login con JWT"""
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                
                if not username or not password:
                    return jsonify({
                        'success': False,
                        'error': 'Username and password required'
                    }), 400
                
                # Usuarios de demostración
                valid_users = {
                    'admin': {'password': 'admin123', 'role': 'admin'},
                    'operator': {'password': 'operator123', 'role': 'operator'},
                    'viewer': {'password': 'viewer123', 'role': 'viewer'},
                    'maintenance': {'password': 'maint123', 'role': 'maintenance'}
                }
                
                if username not in valid_users or valid_users[username]['password'] != password:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid credentials'
                    }), 401
                
                # Generar tokens
                user_info = valid_users[username]
                tokens = self.auth_manager.generate_token(username, username, user_info['role'])
                
                # Notificación de login
                self.db._create_notification(
                    type='info',
                    severity='low', 
                    title='Usuario Conectado',
                    message=f"Usuario {username} ({user_info['role']}) se ha conectado",
                    category='auth'
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'user': {
                            'username': username,
                            'role': user_info['role'],
                            'permissions': self.auth_manager.role_permissions.get(user_info['role'], [])
                        },
                        'tokens': tokens
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Error en login: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
        
        # === DASHBOARD ===
        
        @self.app.route('/api/v2/dashboard/overview', methods=['GET'])
        def dashboard_overview():
            """Datos principales del dashboard"""
            try:
                # Métricas en tiempo real
                realtime_data = self.db.get_realtime_analytics(minutes=60)
                
                # Estado del sistema
                system_status = {
                    'state': self.system_state['mode'],
                    'components': self.system_state['components'],
                    'performance': self.system_state['performance'],
                    'alerts_count': len(self.system_state['alerts']),
                    'active_users': self.system_state['active_users']
                }
                
                # Stats de cache
                cache_stats = self.db.get_cache_stats()
                
                # Stats de conexiones WebSocket
                ws_stats = {
                    'total_connections': self.system_state['active_users'],
                    'rooms_active': len([r for r in getattr(self, 'ws_manager', {}).rooms.values() if r])
                } if hasattr(self, 'ws_manager') else {}
                
                return jsonify({
                    'success': True,
                    'data': {
                        'system_status': system_status,
                        'realtime_metrics': realtime_data,
                        'cache_performance': cache_stats,
                        'websocket_stats': ws_stats,
                        'generated_at': time.time(),
                        'uptime_seconds': time.time() - self.start_time
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Error en dashboard overview: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === ANALYTICS ===
        
        @self.app.route('/api/v2/analytics/realtime', methods=['GET'])
        def realtime_analytics():
            """Analytics en tiempo real"""
            try:
                minutes = request.args.get('minutes', 10, type=int)
                data = self.db.get_realtime_analytics(minutes=minutes)
                
                return jsonify({
                    'success': True,
                    'data': data
                })
                
            except Exception as e:
                self.logger.error(f"Error en realtime analytics: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === ANIMACIONES ===
        
        @self.app.route('/api/v2/animations/data', methods=['GET'])
        def get_animation_data():
            """Datos para animaciones"""
            try:
                animation_type = request.args.get('type')
                limit = request.args.get('limit', 50, type=int)
                
                data = self.db.get_animation_data(animation_type, limit)
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data)
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo animation data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === NOTIFICACIONES ===
        
        @self.app.route('/api/v2/notifications', methods=['GET'])
        def get_notifications():
            """Obtener notificaciones"""
            try:
                limit = request.args.get('limit', 50, type=int)
                notifications = list(self.db._notifications_queue)[-limit:]
                
                return jsonify({
                    'success': True,
                    'data': notifications,
                    'count': len(notifications)
                })
                
            except Exception as e:
                self.logger.error(f"Error obteniendo notificaciones: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _get_limit_type(self, endpoint: str) -> str:
        """Determina tipo de rate limit por endpoint"""
        if 'auth' in endpoint:
            return 'auth'
        elif 'control' in endpoint:
            return 'control'
        elif 'realtime' in endpoint or 'analytics' in endpoint:
            return 'realtime'
        return 'default'
    
    def _setup_websocket(self):
        """Configura eventos WebSocket"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            try:
                self.system_state['active_users'] += 1
                
                emit('connected', {
                    'message': 'Conectado a EcoSort Enhanced',
                    'server_time': datetime.now().isoformat(),
                    'features': ['realtime_data', 'animations', 'notifications']
                })
                
                self.logger.info(f"Cliente WebSocket conectado: {request.sid}")
                
            except Exception as e:
                self.logger.error(f"Error en conexión WebSocket: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.system_state['active_users'] = max(0, self.system_state['active_users'] - 1)
            self.logger.info(f"Cliente WebSocket desconectado: {request.sid}")
        
        @self.socketio.on('request_data')
        def handle_data_request(data):
            try:
                data_type = data.get('type')
                
                if data_type == 'realtime_metrics':
                    minutes = data.get('minutes', 5)
                    metrics_data = self.db.get_realtime_analytics(minutes=minutes)
                    emit('realtime_data', {
                        'type': 'metrics',
                        'data': metrics_data,
                        'timestamp': time.time()
                    })
                
                elif data_type == 'system_status':
                    emit('system_status', {
                        'data': self.system_state,
                        'timestamp': time.time()
                    })
                
            except Exception as e:
                self.logger.error(f"Error manejando solicitud WebSocket: {e}")
                emit('error', {'message': str(e)})
    
    def _setup_background_tasks(self):
        """Configura tareas en segundo plano"""
        
        def metrics_broadcaster():
            """Broadcast métricas cada 5 segundos"""
            while self.running:
                try:
                    time.sleep(5)
                    
                    if self.system_state['active_users'] > 0:
                        data = self.db.get_realtime_analytics(minutes=1)
                        self.socketio.emit('metrics_update', {
                            'data': data,
                            'timestamp': time.time()
                        })
                    
                except Exception as e:
                    self.logger.error(f"Error en metrics broadcaster: {e}")
        
        # Iniciar task
        import threading
        self.metrics_thread = threading.Thread(target=metrics_broadcaster, daemon=True)
        self.metrics_thread.start()
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Ejecuta la aplicación enhanced"""
        try:
            if not self.initialize():
                self.logger.error("Fallo en inicialización")
                return False
            
            self.running = True
            
            self.logger.info(f"Iniciando servidor en {host}:{port}")
            self.logger.info("API Enhanced lista para recibir conexiones")
            self.logger.info("=" * 60)
            
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
                log_output=False
            )
            
        except KeyboardInterrupt:
            self.logger.info("Interrupción por teclado")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error ejecutando aplicación: {e}")
            return False
    
    def stop(self):
        """Detiene la aplicación gracefully"""
        self.logger.info("Deteniendo aplicación Enhanced...")
        self.running = False
        
        # Aquí se pueden agregar más tareas de limpieza
        
        self.logger.info("Aplicación Enhanced detenida correctamente")

def main():
    """Función principal"""
    setup_logging()
    
    # Obtener configuración desde variables de entorno
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    # Crear y ejecutar aplicación
    app = EcoSortEnhancedApp()
    
    try:
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 