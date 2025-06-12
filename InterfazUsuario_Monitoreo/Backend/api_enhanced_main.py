# -*- coding: utf-8 -*-
"""
api_enhanced_main.py - Clase principal de la API Enhanced

Contiene la implementación completa de la API con todos los endpoints
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import time
import threading
from datetime import datetime
from functools import wraps

from InterfazUsuario_Monitoreo.Backend.api_enhanced import *
from InterfazUsuario_Monitoreo.Backend.database_enhanced import DatabaseManagerEnhanced, get_enhanced_database

logger = logging.getLogger(__name__)

class EcoSortAPIEnhanced:
    """API REST Enhanced para EcoSort v2.1"""
    
    def __init__(self, database_manager: DatabaseManagerEnhanced, 
                 host='0.0.0.0', port=5000, secret_key=None):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secret_key or 'ecosort-enhanced-2025-jwt-secret'
        
        # Configurar middleware
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1)
        
        # CORS avanzado para React
        CORS(self.app, resources={
            r"/api/*": {
                "origins": ["http://localhost:3000", "http://localhost:3001", "*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "supports_credentials": True
            }
        })
        
        # Compresión para respuestas grandes
        Compress(self.app)
        
        # SocketIO avanzado
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='threading',
            ping_timeout=60,
            ping_interval=25
        )
        
        self.db = database_manager
        self.host = host
        self.port = port
        
        # Managers
        self.auth_manager = AuthenticationManager(self.app.config['SECRET_KEY'])
        self.rate_limit_manager = RateLimitManager()
        
        # Estado del sistema enhanced
        self.system_state = {
            'running': False,
            'mode': 'idle',  # idle, running, maintenance, error
            'emergency_stop': False,
            'components': {
                'camera': False,
                'ai_model': False,
                'plc': False,
                'sensors': False
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
        
        # Rooms para WebSocket
        self.socket_rooms = {
            'dashboard': set(),
            'analytics': set(),
            'control': set(),
            'maintenance': set()
        }
        
        # Configurar todo
        self._setup_middleware()
        self._setup_routes()
        self._setup_socketio_events()
        self._start_background_tasks()
        
        logger.info("EcoSortAPIEnhanced inicializada correctamente")
    
    def _setup_middleware(self):
        """Configura middleware personalizado"""
        
        @self.app.before_request
        def before_request():
            """Middleware ejecutado antes de cada request"""
            g.start_time = time.time()
            g.request_id = f"{time.time():.6f}_{request.remote_addr}"[-8:]
            
            # Rate limiting personalizado
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
            """Middleware ejecutado después de cada request"""
            # Logging de requests
            duration = time.time() - g.get('start_time', time.time())
            logger.info(f"[{g.get('request_id', 'unknown')}] {request.method} {request.path} - "
                       f"{response.status_code} - {duration:.3f}s")
            
            # Headers de seguridad
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
            
            return response
        
        @self.app.errorhandler(ValidationError)
        def handle_validation_error(e):
            """Maneja errores de validación"""
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'details': e.messages
            }), 400
        
        @self.app.errorhandler(404)
        def handle_not_found(e):
            """Maneja rutas no encontradas"""
            return jsonify({
                'success': False,
                'error': 'Endpoint not found',
                'available_endpoints': self._get_available_endpoints()
            }), 404
    
    def _get_limit_type(self, endpoint: str) -> str:
        """Determina tipo de límite según endpoint"""
        if 'auth' in endpoint or 'login' in endpoint:
            return 'auth'
        elif 'control' in endpoint:
            return 'control'
        elif 'realtime' in endpoint or 'stream' in endpoint:
            return 'realtime'
        return 'default'
    
    def _get_available_endpoints(self) -> list:
        """Obtiene lista de endpoints disponibles"""
        endpoints = []
        for rule in self.app.url_map.iter_rules():
            if rule.endpoint != 'static':
                endpoints.append(f"{list(rule.methods)} {rule.rule}")
        return endpoints[:20]  # Limitar a 20 para no sobrecargar respuesta
    
    def require_auth(self, required_permission: str = None):
        """Decorador para autenticación JWT"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                auth_header = request.headers.get('Authorization')
                
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({
                        'success': False,
                        'error': 'Missing or invalid authorization header'
                    }), 401
                
                token = auth_header.split(' ')[1]
                payload = self.auth_manager.verify_token(token)
                
                if not payload:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid or expired token'
                    }), 401
                
                # Verificar permisos
                if required_permission and required_permission not in payload.get('permissions', []):
                    return jsonify({
                        'success': False,
                        'error': 'Insufficient permissions'
                    }), 403
                
                g.current_user = payload
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def _setup_routes(self):
        """Configura todas las rutas de la API Enhanced"""
        
        # === INFO DE LA API ===
        
        @self.app.route('/api/v2')
        @self.app.route('/api/v2/')
        def api_info():
            """Información de la API v2"""
            return jsonify({
                'name': 'EcoSort Industrial API Enhanced',
                'version': '2.1.0',
                'status': 'online',
                'features': [
                    'JWT Authentication',
                    'Rate Limiting',
                    'Real-time WebSocket',
                    'Advanced Analytics',
                    'Animation Support',
                    'Intelligent Caching'
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
                    'rooms': list(self.socket_rooms.keys()),
                    'events': ['metrics_update', 'new_classification', 'new_notification', 'system_control']
                }
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
                
                # Validación simplificada (en producción usar hash + salt)
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
                
                # Log evento
                self.db._create_notification(
                    type='info',
                    severity='low',
                    title='Usuario Conectado',
                    message=f"Usuario {username} se ha conectado",
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
                logger.error(f"Error en login: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
        
        @self.app.route('/api/v2/auth/refresh', methods=['POST'])
        def refresh_token():
            """Renovar access token"""
            try:
                data = request.get_json()
                refresh_token = data.get('refresh_token')
                
                if not refresh_token:
                    return jsonify({
                        'success': False,
                        'error': 'Refresh token required'
                    }), 400
                
                new_tokens = self.auth_manager.refresh_access_token(refresh_token)
                
                if not new_tokens:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid refresh token'
                    }), 401
                
                return jsonify({
                    'success': True,
                    'data': new_tokens
                })
                
            except Exception as e:
                logger.error(f"Error en refresh: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
        
        @self.app.route('/api/v2/auth/logout', methods=['POST'])
        @self.require_auth()
        def logout():
            """Logout y revocación de token"""
            try:
                auth_header = request.headers.get('Authorization')
                token = auth_header.split(' ')[1]
                
                self.auth_manager.revoke_token(token)
                
                return jsonify({
                    'success': True,
                    'message': 'Logged out successfully'
                })
                
            except Exception as e:
                logger.error(f"Error en logout: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Internal server error'
                }), 500
        
        # === DASHBOARD Y ANALYTICS ===
        
        @self.app.route('/api/v2/dashboard/overview', methods=['GET'])
        @self.require_auth('read')
        def dashboard_overview():
            """Datos principales del dashboard"""
            try:
                # Obtener métricas en tiempo real
                realtime_data = self.db.get_realtime_analytics(minutes=60)
                
                # Estado del sistema
                system_status = {
                    'state': self.system_state['mode'],
                    'components': self.system_state['components'],
                    'performance': self.system_state['performance'],
                    'alerts_count': len(self.system_state['alerts']),
                    'active_users': self.system_state['active_users']
                }
                
                # Métricas de cache
                cache_stats = self.db.get_cache_stats()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'system_status': system_status,
                        'realtime_metrics': realtime_data,
                        'cache_performance': cache_stats,
                        'generated_at': time.time()
                    }
                })
                
            except Exception as e:
                logger.error(f"Error en dashboard overview: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/v2/analytics/realtime', methods=['GET'])
        @self.require_auth('read')
        def realtime_analytics():
            """Analytics en tiempo real para animaciones"""
            try:
                minutes = request.args.get('minutes', 10, type=int)
                data = self.db.get_realtime_analytics(minutes=minutes)
                
                return jsonify({
                    'success': True,
                    'data': data
                })
                
            except Exception as e:
                logger.error(f"Error en realtime analytics: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === ANIMACIONES ===
        
        @self.app.route('/api/v2/animations/data', methods=['GET'])
        @self.require_auth('read')
        def get_animation_data():
            """Datos para animaciones específicas"""
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
                logger.error(f"Error obteniendo animation data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/v2/animations/create', methods=['POST'])
        @self.require_auth('write')
        def create_animation():
            """Crear evento de animación"""
            try:
                # Validar datos
                schema = AnimationSchema()
                data = schema.load(request.get_json())
                
                # Crear animación
                animation_id = self.db.create_animation_event(**data)
                
                # Emitir por WebSocket
                self.socketio.emit('new_animation', {
                    'animation_id': animation_id,
                    'data': data,
                    'timestamp': time.time()
                }, room='dashboard')
                
                return jsonify({
                    'success': True,
                    'data': {
                        'animation_id': animation_id,
                        'message': 'Animation created successfully'
                    }
                })
                
            except ValidationError as e:
                return jsonify({
                    'success': False,
                    'error': 'Validation error',
                    'details': e.messages
                }), 400
            except Exception as e:
                logger.error(f"Error creando animación: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === CLASIFICACIONES ===
        
        @self.app.route('/api/v2/classifications', methods=['POST'])
        @self.require_auth('write')
        def create_classification():
            """Crear nueva clasificación"""
            try:
                # Validar datos
                schema = ClassificationSchema()
                data = schema.load(request.get_json())
                
                # Registrar clasificación
                classification_id = self.db.record_classification_enhanced(**data)
                
                # Emitir por WebSocket para animaciones en tiempo real
                self.socketio.emit('new_classification', {
                    'classification_id': classification_id,
                    'data': data,
                    'timestamp': time.time()
                }, room='dashboard')
                
                # Crear animación de flujo de objeto
                if data.get('object_uuid'):
                    animation_data = {
                        'animation_type': 'object_flow',
                        'object_id': data['object_uuid'],
                        'start_position': {'x': 0, 'y': 50},
                        'end_position': {'x': 100, 'y': 50},
                        'duration_ms': 2000,
                        'properties': {
                            'category': data['category'],
                            'confidence': data['confidence']
                        }
                    }
                    self.db.create_animation_event(**animation_data)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'classification_id': classification_id,
                        'message': 'Classification recorded successfully'
                    }
                })
                
            except ValidationError as e:
                return jsonify({
                    'success': False,
                    'error': 'Validation error',
                    'details': e.messages
                }), 400
            except Exception as e:
                logger.error(f"Error creando clasificación: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/v2/classifications/recent', methods=['GET'])
        @self.require_auth('read')
        def get_recent_classifications():
            """Obtener clasificaciones recientes"""
            try:
                limit = request.args.get('limit', 50, type=int)
                category = request.args.get('category')
                
                # Obtener clasificaciones (usar método básico por ahora)
                recent = []  # Placeholder - implementar query específica
                
                return jsonify({
                    'success': True,
                    'data': recent,
                    'count': len(recent)
                })
                
            except Exception as e:
                logger.error(f"Error obteniendo clasificaciones: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === CONTROL DEL SISTEMA ===
        
        @self.app.route('/api/v2/system/control/<action>', methods=['POST'])
        @self.require_auth('control')
        def system_control(action):
            """Control del sistema"""
            try:
                valid_actions = ['start', 'stop', 'pause', 'resume', 'emergency_stop']
                
                if action not in valid_actions:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid action. Valid actions: {valid_actions}'
                    }), 400
                
                # Ejecutar acción
                if action == 'start':
                    self.system_state['mode'] = 'running'
                    self.system_state['running'] = True
                elif action == 'stop':
                    self.system_state['mode'] = 'idle'
                    self.system_state['running'] = False
                elif action == 'pause':
                    self.system_state['mode'] = 'paused'
                elif action == 'resume':
                    self.system_state['mode'] = 'running'
                elif action == 'emergency_stop':
                    self.system_state['mode'] = 'emergency'
                    self.system_state['emergency_stop'] = True
                    self.system_state['running'] = False
                
                # Emitir evento
                self.socketio.emit('system_control', {
                    'action': action,
                    'state': self.system_state['mode'],
                    'timestamp': time.time(),
                    'user': g.current_user['username']
                })
                
                # Crear notificación
                self.db._create_notification(
                    type='system',
                    severity='medium' if action != 'emergency_stop' else 'critical',
                    title=f'Sistema {action.title()}',
                    message=f"Sistema {action} por usuario {g.current_user['username']}",
                    category='control'
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'action': action,
                        'new_state': self.system_state['mode'],
                        'message': f'System {action} executed successfully'
                    }
                })
                
            except Exception as e:
                logger.error(f"Error en control del sistema: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # === NOTIFICACIONES ===
        
        @self.app.route('/api/v2/notifications', methods=['GET'])
        @self.require_auth('read')
        def get_notifications():
            """Obtener notificaciones"""
            try:
                unread_only = request.args.get('unread_only', 'false').lower() == 'true'
                limit = request.args.get('limit', 50, type=int)
                
                # Obtener notificaciones desde la cola
                notifications = list(self.db._notifications_queue)
                
                if unread_only:
                    notifications = [n for n in notifications if not n.get('read_status', False)]
                
                return jsonify({
                    'success': True,
                    'data': notifications[-limit:],
                    'count': len(notifications)
                })
                
            except Exception as e:
                logger.error(f"Error obteniendo notificaciones: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/v2/notifications', methods=['POST'])
        @self.require_auth('write')
        def create_notification():
            """Crear notificación"""
            try:
                # Validar datos
                schema = NotificationSchema()
                data = schema.load(request.get_json())
                
                # Crear notificación
                self.db._create_notification(**data)
                
                # Emitir por WebSocket
                self.socketio.emit('new_notification', {
                    'data': data,
                    'timestamp': time.time()
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Notification created successfully'
                })
                
            except ValidationError as e:
                return jsonify({
                    'success': False,
                    'error': 'Validation error',
                    'details': e.messages
                }), 400
            except Exception as e:
                logger.error(f"Error creando notificación: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500 