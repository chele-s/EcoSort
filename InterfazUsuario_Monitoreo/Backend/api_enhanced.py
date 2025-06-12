# -*- coding: utf-8 -*-
"""
api_enhanced.py - API REST Enhanced para EcoSort v2.1

Características Enhanced:
- Autenticación JWT con roles y permisos
- Rate limiting inteligente por usuario/IP
- Validación robusta con esquemas
- WebSocket avanzado para streaming en tiempo real
- Endpoints específicos para animaciones React
- Middleware para CORS, logging, compresión
- Cache inteligente para respuestas
- Sistema de notificaciones push
- Analytics avanzados para dashboard
- Configuración dinámica sin reinicio
"""

from flask import Flask, jsonify, request, send_from_directory, g, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
import jwt
from functools import wraps
import logging
import time
import json
import os
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib
import gzip
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.middleware.proxy_fix import ProxyFix

from InterfazUsuario_Monitoreo.Backend.database_enhanced import DatabaseManagerEnhanced, get_enhanced_database

logger = logging.getLogger(__name__)

# Esquemas de validación con Marshmallow
class ClassificationSchema(Schema):
    category = fields.Str(required=True, validate=validate.OneOf(['metal', 'plastic', 'glass', 'carton', 'other']))
    subcategory = fields.Str(missing=None)
    confidence = fields.Float(required=True, validate=validate.Range(0.0, 1.0))
    processing_time_ms = fields.Float(missing=None, validate=validate.Range(0, 10000))
    object_uuid = fields.Str(missing=None)
    session_id = fields.Str(missing=None)
    bounding_box = fields.Dict(missing=None)
    features_vector = fields.List(fields.Float(), missing=None)
    weight_grams = fields.Float(missing=None, validate=validate.Range(0, 10000))
    size_dimensions = fields.Dict(missing=None)
    material_composition = fields.Dict(missing=None)
    recycling_score = fields.Float(missing=None, validate=validate.Range(0, 100))

class AnimationSchema(Schema):
    animation_type = fields.Str(required=True, validate=validate.OneOf([
        'object_flow', 'diverter_action', 'bin_fill', 'alert_pulse', 'system_status'
    ]))
    object_id = fields.Str(required=True)
    start_position = fields.Dict(required=True)
    end_position = fields.Dict(required=True)
    duration_ms = fields.Integer(missing=1000, validate=validate.Range(100, 10000))
    easing_function = fields.Str(missing='easeInOutQuad')
    properties = fields.Dict(missing=dict)

class NotificationSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf([
        'info', 'warning', 'error', 'success', 'system'
    ]))
    severity = fields.Str(required=True, validate=validate.OneOf([
        'low', 'medium', 'high', 'critical'
    ]))
    title = fields.Str(required=True, validate=validate.Length(1, 100))
    message = fields.Str(required=True, validate=validate.Length(1, 500))
    category = fields.Str(missing=None)
    action_required = fields.Bool(missing=False)
    action_url = fields.Str(missing=None)
    expires_at = fields.Float(missing=None)

@dataclass
class UserSession:
    """Sesión de usuario autenticado"""
    user_id: str
    username: str
    role: str
    permissions: List[str]
    login_time: float
    last_activity: float
    ip_address: str

class AuthenticationManager:
    """Gestor de autenticación JWT"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.active_sessions: Dict[str, UserSession] = {}
        self.refresh_tokens: Dict[str, str] = {}
        self.token_blacklist: set = set()
        
        # Roles y permisos
        self.role_permissions = {
            'admin': ['read', 'write', 'delete', 'config', 'control'],
            'operator': ['read', 'write', 'control'],
            'viewer': ['read'],
            'maintenance': ['read', 'config', 'maintenance']
        }
    
    def generate_token(self, user_id: str, username: str, role: str) -> Dict[str, str]:
        """Genera tokens JWT"""
        now = datetime.utcnow()
        
        # Access token (15 minutos)
        access_payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'permissions': self.role_permissions.get(role, []),
            'exp': now + timedelta(minutes=15),
            'iat': now,
            'type': 'access'
        }
        
        # Refresh token (7 días)
        refresh_payload = {
            'user_id': user_id,
            'exp': now + timedelta(days=7),
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')
        
        # Guardar refresh token
        self.refresh_tokens[refresh_token] = user_id
        
        # Crear sesión
        session_data = UserSession(
            user_id=user_id,
            username=username,
            role=role,
            permissions=self.role_permissions.get(role, []),
            login_time=time.time(),
            last_activity=time.time(),
            ip_address=request.remote_addr if request else 'unknown'
        )
        self.active_sessions[access_token] = session_data
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 900,  # 15 minutos
            'token_type': 'Bearer'
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica y decodifica token"""
        if token in self.token_blacklist:
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Actualizar última actividad
            if token in self.active_sessions:
                self.active_sessions[token].last_activity = time.time()
            
            return payload
        except jwt.ExpiredSignatureError:
            # Limpiar sesión expirada
            if token in self.active_sessions:
                del self.active_sessions[token]
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Renueva access token usando refresh token"""
        if refresh_token not in self.refresh_tokens:
            return None
        
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])
            user_id = payload['user_id']
            
            # Buscar información de usuario (simplificado)
            # En producción, consultar base de datos
            user_info = {'username': f'user_{user_id}', 'role': 'operator'}
            
            return self.generate_token(user_id, user_info['username'], user_info['role'])
            
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str):
        """Revoca token"""
        self.token_blacklist.add(token)
        if token in self.active_sessions:
            del self.active_sessions[token]

class RateLimitManager:
    """Gestor de rate limiting avanzado"""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.limits = {
            'default': {'requests': 100, 'window': 60},  # 100 req/min
            'auth': {'requests': 5, 'window': 60},        # 5 req/min para auth
            'control': {'requests': 10, 'window': 60},    # 10 req/min para control
            'realtime': {'requests': 200, 'window': 60}   # 200 req/min para datos en tiempo real
        }
    
    def is_allowed(self, key: str, limit_type: str = 'default') -> bool:
        """Verifica si la request está permitida"""
        now = time.time()
        limits = self.limits.get(limit_type, self.limits['default'])
        
        # Limpiar requests antiguas
        while self.requests[key] and self.requests[key][0] < now - limits['window']:
            self.requests[key].popleft()
        
        # Verificar límite
        if len(self.requests[key]) >= limits['requests']:
            return False
        
        # Agregar request actual
        self.requests[key].append(now)
        return True

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
        
        # Rate limiting
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )
        
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
        
        # Configurar rutas y eventos
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
            g.request_id = hashlib.md5(f"{time.time()}{request.remote_addr}".encode()).hexdigest()[:8]
            
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
    
    def _get_available_endpoints(self) -> List[str]:
        """Obtiene lista de endpoints disponibles"""
        endpoints = []
        for rule in self.app.url_map.iter_rules():
            if rule.endpoint != 'static':
                endpoints.append(f"{rule.methods} {rule.rule}")
        return endpoints
    
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
        
        # === AUTENTICACIÓN ===
        
        @self.app.route('/api/v2/auth/login', methods=['POST'])
        def login():
            """Login con JWT"""
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                
                # Validación simplificada (en producción usar hash + salt)
                if not username or not password:
                    return jsonify({
                        'success': False,
                        'error': 'Username and password required'
                    }), 400
                
                # Verificar credenciales (simplificado)
                valid_users = {
                    'admin': {'password': 'admin123', 'role': 'admin'},
                    'operator': {'password': 'operator123', 'role': 'operator'},
                    'viewer': {'password': 'viewer123', 'role': 'viewer'}
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
        
        @self.app.route('/api/v2/analytics/trends', methods=['GET'])
        @self.require_auth('read')
        def analytics_trends():
            """Tendencias para gráficos animados"""
            try:
                hours = request.args.get('hours', 24, type=int)
                metric = request.args.get('metric', 'all')
                
                # Implementar lógica de tendencias
                # Placeholder por ahora
                trends_data = {
                    'objects_per_hour': [],
                    'confidence_trend': [],
                    'error_rate_trend': [],
                    'efficiency_trend': []
                }
                
                return jsonify({
                    'success': True,
                    'data': trends_data,
                    'period_hours': hours,
                    'metric_filter': metric
                })
                
            except Exception as e:
                logger.error(f"Error en trends: {e}")
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
                
                # Implementar query con filtros
                # Por ahora usar método básico
                recent = self.db.get_recent_classifications(limit)
                
                # Filtrar por categoría si se especifica
                if category:
                    recent = [c for c in recent if c.get('category') == category]
                
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
        
        # === NOTIFICACIONES ===
        
        @self.app.route('/api/v2/notifications', methods=['GET'])
        @self.require_auth('read')
        def get_notifications():
            """Obtener notificaciones"""
            try:
                unread_only = request.args.get('unread_only', 'false').lower() == 'true'
                limit = request.args.get('limit', 50, type=int)
                
                # Implementar query de notificaciones
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
    
    def _setup_socketio_events(self):
        """Configura eventos WebSocket avanzados"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Maneja conexión WebSocket con autenticación"""
            try:
                # Verificar token en auth
                token = auth.get('token') if auth else None
                
                if token:
                    payload = self.auth_manager.verify_token(token)
                    if payload:
                        session['user'] = payload
                        logger.info(f"Usuario autenticado conectado: {payload['username']}")
                    else:
                        logger.warning("Token inválido en conexión WebSocket")
                        return False
                else:
                    logger.info("Conexión WebSocket sin autenticación")
                
                emit('connected', {
                    'message': 'Conectado a EcoSort Enhanced',
                    'server_time': datetime.now().isoformat(),
                    'features': ['realtime_data', 'animations', 'notifications']
                })
                
                self.system_state['active_users'] += 1
                
            except Exception as e:
                logger.error(f"Error en conexión WebSocket: {e}")
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Maneja desconexión"""
            logger.info("Cliente WebSocket desconectado")
            self.system_state['active_users'] = max(0, self.system_state['active_users'] - 1)
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Une usuario a room específico"""
            room = data.get('room')
            if room in self.socket_rooms:
                join_room(room)
                self.socket_rooms[room].add(request.sid)
                emit('joined_room', {'room': room})
                logger.info(f"Usuario unido a room: {room}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """Saca usuario de room"""
            room = data.get('room')
            if room in self.socket_rooms:
                leave_room(room)
                self.socket_rooms[room].discard(request.sid)
                emit('left_room', {'room': room})
        
        @self.socketio.on('request_realtime_data')
        def handle_realtime_request():
            """Solicita datos en tiempo real"""
            try:
                data = self.db.get_realtime_analytics(minutes=5)
                emit('realtime_data', {
                    'data': data,
                    'timestamp': time.time()
                })
            except Exception as e:
                emit('error', {'message': str(e)})
        
        @self.socketio.on('ping')
        def handle_ping():
            """Responde a ping para mantener conexión"""
            emit('pong', {'timestamp': time.time()})
    
    def _start_background_tasks(self):
        """Inicia tareas en segundo plano"""
        # Tarea para emitir métricas en tiempo real
        def realtime_metrics_broadcaster():
            while True:
                try:
                    time.sleep(5)  # Cada 5 segundos
                    if self.socket_rooms['dashboard']:
                        data = self.db.get_realtime_analytics(minutes=1)
                        self.socketio.emit('metrics_update', {
                            'data': data,
                            'timestamp': time.time()
                        }, room='dashboard')
                except Exception as e:
                    logger.error(f"Error en metrics broadcaster: {e}")
        
        # Tarea para limpiar sesiones expiradas
        def session_cleaner():
            while True:
                try:
                    time.sleep(300)  # Cada 5 minutos
                    now = time.time()
                    expired_tokens = []
                    
                    for token, session in self.auth_manager.active_sessions.items():
                        if now - session.last_activity > 3600:  # 1 hora sin actividad
                            expired_tokens.append(token)
                    
                    for token in expired_tokens:
                        self.auth_manager.revoke_token(token)
                    
                    if expired_tokens:
                        logger.info(f"Limpiadas {len(expired_tokens)} sesiones expiradas")
                        
                except Exception as e:
                    logger.error(f"Error en session cleaner: {e}")
        
        # Iniciar threads
        threading.Thread(target=realtime_metrics_broadcaster, daemon=True).start()
        threading.Thread(target=session_cleaner, daemon=True).start()
    
    def run(self, debug=False):
        """Inicia el servidor Enhanced"""
        logger.info(f"Iniciando EcoSort API Enhanced en {self.host}:{self.port}")
        logger.info("Características habilitadas:")
        logger.info("- Autenticación JWT con roles")
        logger.info("- Rate limiting inteligente")
        logger.info("- WebSocket para tiempo real")
        logger.info("- Cache optimizado")
        logger.info("- Validación robusta")
        logger.info("- Soporte para animaciones React")
        
        self.socketio.run(
            self.app, 
            host=self.host, 
            port=self.port, 
            debug=debug,
            use_reloader=False  # Evitar problemas con threads
        )

def create_enhanced_api(database_manager: DatabaseManagerEnhanced = None, 
                       host='0.0.0.0', port=5000, secret_key=None):
    """Crea instancia de API Enhanced"""
    if database_manager is None:
        database_manager = get_enhanced_database()
    
    return EcoSortAPIEnhanced(database_manager, host, port, secret_key)

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear e iniciar API Enhanced
    api = create_enhanced_api()
    api.run(debug=True) 