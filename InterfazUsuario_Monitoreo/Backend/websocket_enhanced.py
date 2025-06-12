# -*- coding: utf-8 -*-
"""
websocket_enhanced.py - Eventos WebSocket y tareas en segundo plano

Características:
- Eventos WebSocket para tiempo real
- Autenticación de sesiones WebSocket
- Rooms para diferentes tipos de usuarios
- Broadcasting inteligente de datos
- Tareas en segundo plano para métricas
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import session, request
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Set

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Gestor de eventos WebSocket enhanced"""
    
    def __init__(self, socketio, auth_manager, db_manager, system_state):
        self.socketio = socketio
        self.auth_manager = auth_manager
        self.db = db_manager
        self.system_state = system_state
        
        # Rooms para diferentes tipos de datos
        self.rooms = {
            'dashboard': set(),
            'analytics': set(), 
            'control': set(),
            'maintenance': set(),
            'viewer': set()
        }
        
        # Estado de conexiones
        self.active_connections = {}
        
        self._setup_events()
    
    def _setup_events(self):
        """Configura todos los eventos WebSocket"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Maneja nueva conexión WebSocket"""
            try:
                # Verificar autenticación si se proporciona
                user_data = None
                if auth and auth.get('token'):
                    payload = self.auth_manager.verify_token(auth['token'])
                    if payload:
                        user_data = payload
                        session['user'] = payload
                        logger.info(f"Usuario autenticado conectado: {payload['username']}")
                    else:
                        logger.warning("Token inválido en conexión WebSocket")
                        disconnect()
                        return False
                
                # Registrar conexión
                self.active_connections[request.sid] = {
                    'user': user_data,
                    'connected_at': time.time(),
                    'last_ping': time.time(),
                    'rooms': set()
                }
                
                # Respuesta de conexión exitosa
                emit('connected', {
                    'message': 'Conectado a EcoSort Enhanced',
                    'server_time': datetime.now().isoformat(),
                    'features': ['realtime_data', 'animations', 'notifications'],
                    'authenticated': user_data is not None,
                    'user_role': user_data.get('role') if user_data else None
                })
                
                # Actualizar contador de usuarios activos
                self.system_state['active_users'] = len(self.active_connections)
                
                logger.info(f"Cliente WebSocket conectado: {request.sid}")
                
            except Exception as e:
                logger.error(f"Error en conexión WebSocket: {e}")
                disconnect()
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Maneja desconexión"""
            try:
                # Limpiar de todos los rooms
                if request.sid in self.active_connections:
                    connection_data = self.active_connections[request.sid]
                    for room in connection_data.get('rooms', []):
                        if room in self.rooms:
                            self.rooms[room].discard(request.sid)
                    
                    del self.active_connections[request.sid]
                
                # Actualizar contador
                self.system_state['active_users'] = len(self.active_connections)
                
                logger.info(f"Cliente WebSocket desconectado: {request.sid}")
                
            except Exception as e:
                logger.error(f"Error en desconexión: {e}")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Une cliente a room específico"""
            try:
                room = data.get('room')
                
                if not room or room not in self.rooms:
                    emit('error', {'message': f'Room inválido: {room}'})
                    return
                
                # Verificar permisos según el room
                user_data = self.active_connections.get(request.sid, {}).get('user')
                if not self._check_room_permission(room, user_data):
                    emit('error', {'message': 'Sin permisos para acceder a este room'})
                    return
                
                # Unir al room
                join_room(room)
                self.rooms[room].add(request.sid)
                
                if request.sid in self.active_connections:
                    self.active_connections[request.sid]['rooms'].add(room)
                
                emit('joined_room', {
                    'room': room,
                    'message': f'Unido a {room}',
                    'room_size': len(self.rooms[room])
                })
                
                # Enviar datos iniciales según el room
                self._send_initial_room_data(room)
                
                logger.info(f"Cliente {request.sid} unido a room: {room}")
                
            except Exception as e:
                logger.error(f"Error uniendo a room: {e}")
                emit('error', {'message': 'Error uniendo a room'})
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """Saca cliente de room"""
            try:
                room = data.get('room')
                
                if room in self.rooms:
                    leave_room(room)
                    self.rooms[room].discard(request.sid)
                    
                    if request.sid in self.active_connections:
                        self.active_connections[request.sid]['rooms'].discard(room)
                
                emit('left_room', {
                    'room': room,
                    'message': f'Saliste de {room}'
                })
                
            except Exception as e:
                logger.error(f"Error saliendo de room: {e}")
        
        @self.socketio.on('ping')
        def handle_ping():
            """Maneja ping para keepalive"""
            if request.sid in self.active_connections:
                self.active_connections[request.sid]['last_ping'] = time.time()
            emit('pong', {'timestamp': time.time()})
        
        @self.socketio.on('request_data')
        def handle_data_request(data):
            """Maneja solicitudes específicas de datos"""
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
                        'data': {
                            'state': self.system_state['mode'],
                            'components': self.system_state['components'],
                            'performance': self.system_state['performance']
                        },
                        'timestamp': time.time()
                    })
                
                elif data_type == 'animations':
                    animation_type = data.get('animation_type')
                    limit = data.get('limit', 20)
                    animation_data = self.db.get_animation_data(animation_type, limit)
                    emit('animation_data', {
                        'data': animation_data,
                        'timestamp': time.time()
                    })
                
                else:
                    emit('error', {'message': f'Tipo de datos no soportado: {data_type}'})
                
            except Exception as e:
                logger.error(f"Error manejando solicitud de datos: {e}")
                emit('error', {'message': 'Error obteniendo datos'})
    
    def _check_room_permission(self, room: str, user_data: dict) -> bool:
        """Verifica permisos para acceder a un room"""
        if not user_data:
            # Solo rooms públicos para usuarios no autenticados
            return room in ['dashboard', 'viewer']
        
        role = user_data.get('role', 'viewer')
        permissions = user_data.get('permissions', [])
        
        # Control de acceso por room
        room_permissions = {
            'dashboard': ['read'],
            'analytics': ['read'],
            'control': ['control'],
            'maintenance': ['maintenance', 'config'],
            'viewer': []  # Público
        }
        
        required_permissions = room_permissions.get(room, [])
        
        # Admin tiene acceso a todo
        if role == 'admin':
            return True
        
        # Verificar permisos específicos
        return any(perm in permissions for perm in required_permissions) or not required_permissions
    
    def _send_initial_room_data(self, room: str):
        """Envía datos iniciales según el room"""
        try:
            if room == 'dashboard':
                # Datos del dashboard
                data = self.db.get_realtime_analytics(minutes=30)
                emit('initial_data', {
                    'type': 'dashboard',
                    'data': data,
                    'timestamp': time.time()
                })
            
            elif room == 'analytics':
                # Datos de analytics
                data = self.db.get_realtime_analytics(minutes=60)
                emit('initial_data', {
                    'type': 'analytics', 
                    'data': data,
                    'timestamp': time.time()
                })
            
            elif room == 'control':
                # Estado del sistema para control
                emit('initial_data', {
                    'type': 'control',
                    'data': {
                        'system_state': self.system_state,
                        'components': self.system_state['components']
                    },
                    'timestamp': time.time()
                })
            
        except Exception as e:
            logger.error(f"Error enviando datos iniciales para {room}: {e}")
    
    def broadcast_to_room(self, room: str, event: str, data: dict):
        """Broadcast datos a un room específico"""
        if room in self.rooms and self.rooms[room]:
            self.socketio.emit(event, data, room=room)
    
    def broadcast_to_all(self, event: str, data: dict):
        """Broadcast a todas las conexiones"""
        self.socketio.emit(event, data)
    
    def get_connection_stats(self) -> dict:
        """Obtiene estadísticas de conexiones"""
        room_counts = {room: len(clients) for room, clients in self.rooms.items()}
        
        # Estadísticas por rol
        role_counts = {}
        for conn_data in self.active_connections.values():
            user = conn_data.get('user')
            if user:
                role = user.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
            else:
                role_counts['anonymous'] = role_counts.get('anonymous', 0) + 1
        
        return {
            'total_connections': len(self.active_connections),
            'room_counts': room_counts,
            'role_distribution': role_counts,
            'authenticated_users': len([c for c in self.active_connections.values() if c.get('user')])
        }

class BackgroundTaskManager:
    """Gestor de tareas en segundo plano"""
    
    def __init__(self, socketio, db_manager, websocket_manager, system_state):
        self.socketio = socketio
        self.db = db_manager
        self.ws_manager = websocket_manager
        self.system_state = system_state
        self.running = True
        
        self._start_tasks()
    
    def _start_tasks(self):
        """Inicia todas las tareas en segundo plano"""
        
        # Tarea para métricas en tiempo real
        def realtime_metrics_task():
            while self.running:
                try:
                    time.sleep(5)  # Cada 5 segundos
                    
                    # Obtener métricas recientes
                    data = self.db.get_realtime_analytics(minutes=1)
                    
                    # Broadcast a dashboard
                    self.ws_manager.broadcast_to_room('dashboard', 'metrics_update', {
                        'data': data,
                        'timestamp': time.time()
                    })
                    
                    # Actualizar estado del sistema con métricas simuladas
                    if data and data.get('current'):
                        current = data['current']
                        self.system_state['performance'].update({
                            'objects_per_minute': current.get('total_objects', 0) * 60,
                            'avg_confidence': current.get('avg_confidence', 0),
                            'system_load': 45,  # Simulado
                            'memory_usage': 65   # Simulado
                        })
                    
                except Exception as e:
                    logger.error(f"Error en realtime metrics task: {e}")
        
        # Tarea para limpiar conexiones muertas
        def connection_cleanup_task():
            while self.running:
                try:
                    time.sleep(30)  # Cada 30 segundos
                    
                    current_time = time.time()
                    dead_connections = []
                    
                    for sid, conn_data in self.ws_manager.active_connections.items():
                        # Conexiones sin ping por más de 2 minutos
                        if current_time - conn_data['last_ping'] > 120:
                            dead_connections.append(sid)
                    
                    # Limpiar conexiones muertas
                    for sid in dead_connections:
                        if sid in self.ws_manager.active_connections:
                            conn_data = self.ws_manager.active_connections[sid]
                            for room in conn_data.get('rooms', []):
                                if room in self.ws_manager.rooms:
                                    self.ws_manager.rooms[room].discard(sid)
                            del self.ws_manager.active_connections[sid]
                    
                    if dead_connections:
                        logger.info(f"Limpiadas {len(dead_connections)} conexiones muertas")
                        self.system_state['active_users'] = len(self.ws_manager.active_connections)
                    
                except Exception as e:
                    logger.error(f"Error en connection cleanup: {e}")
        
        # Tarea para estadísticas del sistema
        def system_stats_task():
            while self.running:
                try:
                    time.sleep(60)  # Cada minuto
                    
                    # Obtener estadísticas de conexiones
                    conn_stats = self.ws_manager.get_connection_stats()
                    
                    # Obtener estadísticas de cache
                    cache_stats = self.db.get_cache_stats()
                    
                    # Broadcast estadísticas a analytics room
                    self.ws_manager.broadcast_to_room('analytics', 'system_stats', {
                        'connections': conn_stats,
                        'cache': cache_stats,
                        'timestamp': time.time()
                    })
                    
                except Exception as e:
                    logger.error(f"Error en system stats task: {e}")
        
        # Iniciar threads
        threading.Thread(target=realtime_metrics_task, daemon=True, name='RealtimeMetrics').start()
        threading.Thread(target=connection_cleanup_task, daemon=True, name='ConnectionCleanup').start()
        threading.Thread(target=system_stats_task, daemon=True, name='SystemStats').start()
        
        logger.info("Tareas en segundo plano iniciadas")
    
    def stop_tasks(self):
        """Detiene todas las tareas"""
        self.running = False
        logger.info("Tareas en segundo plano detenidas") 