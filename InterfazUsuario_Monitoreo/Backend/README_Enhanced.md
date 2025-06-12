# 🚀 EcoSort Backend Enhanced v2.1

## 📋 Descripción General

Backend completamente rediseñado y optimizado para trabajar con frontend React moderno usando **animejs** y animaciones complejas. Incluye todas las características avanzadas para un sistema industrial robusto.

## ✨ Características Enhanced

### 🔐 **Autenticación y Seguridad**
- **JWT Authentication** con roles y permisos granulares
- **Rate Limiting** inteligente por usuario/endpoint
- **API Key Management** para integraciones
- **Security Headers** automáticos
- **Session Management** con refresh tokens

### 📊 **Base de Datos Avanzada**
- **Cache Inteligente** con estrategias LRU optimizadas
- **Índices Optimizados** para queries complejas
- **Batch Processing** para escrituras masivas
- **Nuevas Tablas** para analytics y animaciones
- **Data Validation** robusta

### 🌐 **API REST Mejorada**
- **Validación de Esquemas** con Marshmallow
- **Error Handling** robusto y consistente
- **Response Compression** automática
- **CORS Avanzado** para React apps
- **API Versioning** v2 compatible

### ⚡ **WebSocket Avanzado**
- **Rooms por Permisos** (dashboard, analytics, control, maintenance)
- **Autenticación WebSocket** con JWT
- **Broadcasting Inteligente** de datos
- **Connection Management** con cleanup automático
- **Real-time Metrics** streaming

### 🎨 **Soporte para Animaciones React**
- **Endpoints Específicos** para datos de animación
- **Timeline de Eventos** para animejs
- **Animation State Management**
- **Performance Metrics** para animaciones fluidas
- **Object Tracking** para flujos visuales

### 📈 **Analytics Avanzados**
- **Métricas en Tiempo Real** cada 5 segundos
- **Agregación Inteligente** por minuto/hora/día
- **Trend Analysis** para gráficos
- **Performance Monitoring** del sistema
- **Alert System** proactivo

## 📁 Estructura del Backend Enhanced

```
InterfazUsuario_Monitoreo/Backend/
├── database_enhanced.py          # Base de datos con cache y funcionalidades avanzadas
├── api_enhanced.py               # Clases base para API (Auth, Validation, etc.)
├── api_enhanced_main.py          # Clase principal de API con todos los endpoints
├── websocket_enhanced.py         # Eventos WebSocket y tareas en segundo plano
├── app_enhanced.py               # Aplicación principal que integra todo
├── config_enhanced.py            # Configuración dinámica y validación
├── middleware_enhanced.py        # Middleware para logging, seguridad, etc.
└── README_Enhanced.md            # Esta documentación
```

## 🔧 Instalación y Configuración

### 1. **Dependencias Enhanced**

```bash
# Instalar dependencias adicionales
pip install marshmallow flask-limiter flask-compress PyJWT redis python-jose
```

### 2. **Configuración de Variables de Entorno**

```bash
# .env file
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=False
SECRET_KEY=your-super-secret-jwt-key
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 3. **Iniciar Backend Enhanced**

```bash
# Método 1: Aplicación completa
python InterfazUsuario_Monitoreo/Backend/app_enhanced.py

# Método 2: Solo API
python InterfazUsuario_Monitoreo/Backend/api_enhanced_main.py

# Método 3: Con configuración personalizada
API_HOST=localhost API_PORT=8000 python app_enhanced.py
```

## 🔗 Endpoints API v2

### **Autenticación**
```http
POST /api/v2/auth/login
POST /api/v2/auth/refresh
POST /api/v2/auth/logout
```

### **Dashboard y Analytics**
```http
GET  /api/v2/dashboard/overview
GET  /api/v2/analytics/realtime?minutes=10
GET  /api/v2/analytics/trends?hours=24&metric=all
GET  /api/v2/analytics/performance
```

### **Animaciones para React**
```http
GET  /api/v2/animations/data?type=object_flow&limit=50
POST /api/v2/animations/create
GET  /api/v2/animations/timeline?start=timestamp&end=timestamp
PUT  /api/v2/animations/{id}/update
```

### **Clasificaciones Enhanced**
```http
POST /api/v2/classifications
GET  /api/v2/classifications/recent?limit=100&category=metal
GET  /api/v2/classifications/stats?period=day
GET  /api/v2/classifications/export?format=json
```

### **Notificaciones en Tiempo Real**
```http
GET  /api/v2/notifications?unread_only=true
POST /api/v2/notifications
PUT  /api/v2/notifications/{id}/read
DELETE /api/v2/notifications/{id}
```

### **Control del Sistema**
```http
POST /api/v2/system/control/start
POST /api/v2/system/control/stop
POST /api/v2/system/control/pause
POST /api/v2/system/control/resume
POST /api/v2/system/control/emergency_stop
GET  /api/v2/system/status
```

### **Configuración Dinámica**
```http
GET  /api/v2/config
PUT  /api/v2/config
POST /api/v2/config/reload
GET  /api/v2/config/schema
```

## 🌐 WebSocket Events

### **Conexión y Autenticación**
```javascript
// Conectar con autenticación
const socket = io('http://localhost:5000', {
  auth: {
    token: 'your-jwt-token'
  }
});

// Eventos de conexión
socket.on('connected', (data) => {
  console.log('Conectado:', data.message);
  console.log('Características:', data.features);
});
```

### **Rooms por Permisos**
```javascript
// Unirse a room específico
socket.emit('join_room', { room: 'dashboard' });
socket.emit('join_room', { room: 'analytics' });
socket.emit('join_room', { room: 'control' });     // Requiere permisos
socket.emit('join_room', { room: 'maintenance' }); // Requiere permisos

// Eventos por room
socket.on('joined_room', (data) => {
  console.log(`Unido a ${data.room}, usuarios: ${data.room_size}`);
});
```

### **Datos en Tiempo Real**
```javascript
// Solicitar datos específicos
socket.emit('request_data', {
  type: 'realtime_metrics',
  minutes: 5
});

// Recibir métricas actualizadas cada 5 segundos
socket.on('metrics_update', (data) => {
  updateDashboard(data.data);
  updateAnimations(data.data);
});

// Nuevas clasificaciones para animaciones
socket.on('new_classification', (data) => {
  createObjectAnimation(data.data);
});

// Notificaciones push
socket.on('new_notification', (notification) => {
  showNotification(notification.data);
});
```

### **Control del Sistema**
```javascript
// Eventos de control (solo usuarios autorizados)
socket.on('system_control', (data) => {
  console.log(`Sistema ${data.action} por ${data.user}`);
  updateSystemState(data.state);
});

// Alertas críticas
socket.on('critical_alert', (alert) => {
  showCriticalAlert(alert);
});
```

## 🎨 Integración con React y Anime.js

### **Hook para Datos en Tiempo Real**
```javascript
// useRealtimeData.js
import { useState, useEffect } from 'react';
import { io } from 'socket.io-client';

export const useRealtimeData = (token) => {
  const [data, setData] = useState(null);
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const socketInstance = io('http://localhost:5000', {
      auth: { token }
    });

    socketInstance.on('connected', () => {
      socketInstance.emit('join_room', { room: 'dashboard' });
    });

    socketInstance.on('metrics_update', (newData) => {
      setData(newData.data);
    });

    setSocket(socketInstance);

    return () => socketInstance.close();
  }, [token]);

  return { data, socket };
};
```

### **Componente de Animación con Anime.js**
```javascript
// ObjectFlowAnimation.jsx
import React, { useEffect, useRef } from 'react';
import anime from 'animejs';
import { useRealtimeData } from './hooks/useRealtimeData';

const ObjectFlowAnimation = ({ token }) => {
  const containerRef = useRef();
  const { data, socket } = useRealtimeData(token);

  useEffect(() => {
    if (!socket) return;

    socket.on('new_classification', (classificationData) => {
      // Crear elemento visual para el objeto
      const objectElement = document.createElement('div');
      objectElement.className = `object-${classificationData.data.category}`;
      objectElement.style.position = 'absolute';
      objectElement.style.width = '20px';
      objectElement.style.height = '20px';
      objectElement.style.borderRadius = '50%';
      objectElement.style.backgroundColor = getCategoryColor(classificationData.data.category);
      
      containerRef.current.appendChild(objectElement);

      // Animación con anime.js
      anime({
        targets: objectElement,
        translateX: [0, 800],
        translateY: [250, 250],
        scale: [0.5, 1, 0.8],
        opacity: [0, 1, 0],
        duration: 3000,
        easing: 'easeInOutQuad',
        complete: () => {
          objectElement.remove();
        }
      });

      // Animación de confianza
      if (classificationData.data.confidence > 0.8) {
        anime({
          targets: objectElement,
          scale: [1, 1.2, 1],
          duration: 500,
          easing: 'easeInOutElastic'
        });
      }
    });
  }, [socket]);

  return (
    <div 
      ref={containerRef}
      className="object-flow-container"
      style={{ 
        position: 'relative', 
        width: '100%', 
        height: '500px',
        background: 'linear-gradient(90deg, #f0f0f0 0%, #e0e0e0 100%)'
      }}
    >
      {/* Banda transportadora visual */}
      <div className="conveyor-belt" />
    </div>
  );
};

const getCategoryColor = (category) => {
  const colors = {
    metal: '#silver',
    plastic: '#blue',
    glass: '#green',
    carton: '#brown',
    other: '#gray'
  };
  return colors[category] || '#gray';
};
```

### **Dashboard con Métricas Animadas**
```javascript
// AnimatedMetrics.jsx
import React, { useEffect, useRef } from 'react';
import anime from 'animejs';

const AnimatedMetrics = ({ metrics }) => {
  const metricsRef = useRef();

  useEffect(() => {
    if (!metrics) return;

    // Animar contadores
    anime({
      targets: metricsRef.current.querySelectorAll('.counter'),
      innerHTML: (el) => [0, el.getAttribute('data-value')],
      duration: 1000,
      round: 1,
      easing: 'easeOutExpo'
    });

    // Animar barras de progreso
    anime({
      targets: metricsRef.current.querySelectorAll('.progress-bar'),
      width: (el) => el.getAttribute('data-width') + '%',
      duration: 800,
      easing: 'easeInOutQuad'
    });
  }, [metrics]);

  return (
    <div ref={metricsRef} className="animated-metrics">
      <div className="metric-card">
        <h3>Objetos Procesados</h3>
        <div 
          className="counter" 
          data-value={metrics?.current?.total_objects || 0}
        >
          0
        </div>
      </div>
      
      <div className="metric-card">
        <h3>Confianza Promedio</h3>
        <div className="progress-container">
          <div 
            className="progress-bar"
            data-width={metrics?.current?.avg_confidence * 100 || 0}
          />
        </div>
      </div>
    </div>
  );
};
```

## 📊 Estructura de Datos para Animaciones

### **Clasificación Enhanced**
```json
{
  "id": 12345,
  "timestamp": 1640995200.123,
  "object_uuid": "uuid-4-object",
  "category": "metal",
  "subcategory": "aluminum_can",
  "confidence": 0.95,
  "processing_time_ms": 234.5,
  "bounding_box": {
    "x": 150,
    "y": 200,
    "width": 80,
    "height": 120
  },
  "features_vector": [0.1, 0.8, 0.3, ...],
  "material_composition": {
    "aluminum": 0.9,
    "plastic": 0.1
  },
  "recycling_score": 87.5,
  "diverter_activated": true,
  "diverter_delay_ms": 1500,
  "animation_data": {
    "start_position": {"x": 0, "y": 250},
    "end_position": {"x": 800, "y": 250},
    "diversion_point": {"x": 600, "y": 250},
    "final_bin": "metal_bin"
  }
}
```

### **Evento de Animación**
```json
{
  "id": 67890,
  "timestamp": 1640995200.456,
  "animation_type": "object_flow",
  "object_id": "uuid-4-object",
  "start_position": {"x": 0, "y": 250},
  "end_position": {"x": 800, "y": 250},
  "duration_ms": 3000,
  "easing_function": "easeInOutQuad",
  "properties": {
    "category": "metal",
    "confidence": 0.95,
    "color": "#silver",
    "size": "medium"
  },
  "keyframes": [
    {"time": 0, "x": 0, "y": 250, "scale": 0.5, "opacity": 0},
    {"time": 0.1, "x": 50, "y": 250, "scale": 1, "opacity": 1},
    {"time": 0.7, "x": 600, "y": 250, "scale": 1, "opacity": 1},
    {"time": 0.8, "x": 650, "y": 200, "scale": 0.8, "opacity": 0.8},
    {"time": 1, "x": 700, "y": 150, "scale": 0.5, "opacity": 0}
  ]
}
```

### **Métricas en Tiempo Real**
```json
{
  "timestamp": 1640995200.789,
  "period_minutes": 5,
  "current": {
    "total_objects": 156,
    "avg_confidence": 0.87,
    "avg_processing_time": 245.6,
    "error_rate": 2.1,
    "throughput_per_minute": 31.2
  },
  "timeline": [
    {
      "minute_bucket": 27350353,
      "objects_processed": 32,
      "avg_confidence": 0.89,
      "efficiency_score": 94.2,
      "active_diversions": 3
    }
  ],
  "trends": {
    "efficiency_trend": "up",
    "confidence_trend": "stable",
    "throughput_trend": "up"
  },
  "alerts": [
    {
      "type": "performance",
      "severity": "medium",
      "message": "Processing time above normal"
    }
  ]
}
```

## 🔧 Configuración para Producción

### **Docker Compose Enhanced**
```yaml
version: '3.8'
services:
  ecosort-backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=5000
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
      - CORS_ORIGINS=https://ecosort-app.com,https://dashboard.ecosort.com
    depends_on:
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl

volumes:
  redis_data:
```

### **Nginx para WebSocket**
```nginx
upstream backend {
    server ecosort-backend:5000;
}

server {
    listen 80;
    server_name api.ecosort.com;

    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }
}
```

## 🚀 Deployment y Escalabilidad

### **Características de Escalabilidad**
- **Redis** para cache distribuido
- **Load Balancing** con sticky sessions para WebSocket
- **Database Sharding** por rangos de tiempo
- **CDN Integration** para assets estáticos
- **Health Checks** automáticos

### **Monitoreo y Observabilidad**
- **Prometheus Metrics** endpoints
- **Structured Logging** con correlation IDs
- **Performance Tracing** con OpenTelemetry
- **Real-time Alerts** via WebSocket
- **Dashboard Analytics** para operadores

## 📚 Recursos Adicionales

### **Testing**
```bash
# Tests unitarios
python -m pytest tests/test_enhanced_api.py -v

# Tests de integración
python -m pytest tests/test_websocket_integration.py -v

# Load testing
artillery run tests/load_test_config.yml
```

### **Documentación de API**
- **OpenAPI 3.0** spec disponible en `/api/v2/docs`
- **Interactive Swagger UI** en `/api/v2/swagger`
- **WebSocket Events** documentados en `/api/v2/websocket-docs`

### **Ejemplos de Frontend**
- **React Hooks** para WebSocket
- **Anime.js Integrations** para animaciones fluidas
- **State Management** con Redux Toolkit
- **Real-time Charts** con Chart.js/D3.js

---

## 🎯 Próximos Pasos

1. **Implementar** los archivos enhanced según esta documentación
2. **Configurar** el frontend React con los hooks proporcionados
3. **Testear** las animaciones con anime.js
4. **Desplegar** en producción con la configuración Docker
5. **Monitorear** el rendimiento y optimizar según sea necesario

¡El backend enhanced está diseñado para ser altamente performante, escalable y específicamente optimizado para frontends React modernos con animaciones complejas! 