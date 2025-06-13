# 🌟 EcoSort Frontend v2.1 - Enhanced Edition

<div align="center">

[![React](https://img.shields.io/badge/React-19.1.0-blue?logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8.3-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.3.5-646CFF?logo=vite)](https://vitejs.dev/)
[![Anime.js](https://img.shields.io/badge/Anime.js-3.2.2-FF6B6B?logo=javascript)](https://animejs.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4.3-FF6384?logo=chart.js)](https://www.chartjs.org/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-4.7.5-010101?logo=socket.io)](https://socket.io/)

**Frontend moderno y reactivo para el sistema industrial de clasificación de residuos EcoSort**

*Interfaz de usuario avanzada con animaciones complejas, monitoreo en tiempo real y control industrial*

</div>

---

## 🚀 Características Principales

### ✨ **Nuevas Funcionalidades v2.1**

- **🎨 Animaciones Complejas**: Sistema de animaciones fluidas con Anime.js para visualización de flujo de objetos
- **📊 Dashboard en Tiempo Real**: Monitoreo completo con métricas actualizadas cada segundo
- **🔐 Autenticación Avanzada**: Sistema de login con JWT y protección de rutas
- **📈 Analytics Avanzados**: Gráficos interactivos con Chart.js y análisis de tendencias
- **🎛️ Control Industrial**: Panel de control completo para operación del sistema
- **🌐 WebSocket Integration**: Comunicación bidireccional en tiempo real con el backend
- **🎯 TypeScript**: Tipado fuerte para mejor desarrollo y mantenimiento
- **📱 Responsive Design**: Interfaz adaptable a diferentes tamaños de pantalla

### 🏭 **Funcionalidades Industriales**

- **🤖 Visualización de Clasificación**: Animaciones de objetos moviéndose por la banda transportadora
- **📦 Monitoreo de Categorías**: Seguimiento visual de metal, plástico, vidrio, cartón y otros
- **⚡ Tiempo Real**: Actualizaciones instantáneas de estado y métricas
- **🎯 Alta Precisión**: Visualización de confianza de clasificación y estadísticas
- **🔧 Control de Actuadores**: Interfaz para control de desviadores y banda transportadora
- **📏 Sensores Inteligentes**: Monitoreo de niveles de tolva y estados del sistema
- **📈 Análisis de Rendimiento**: Gráficos de throughput, confianza y distribución

---

## 📦 Instalación y Configuración

### Prerrequisitos

- **Node.js 18+** con npm
- **Backend EcoSort** ejecutándose en puerto 5000
- **Navegador moderno** con soporte para ES2020+

### Instalación

```bash
# Navegar al directorio del frontend
cd InterfazUsuario_Monitoreo/Frontend_ecosort

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Construir para producción
npm run build

# Vista previa de build
npm run preview
```

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Backend API URL
VITE_API_URL=http://localhost:5000

# WebSocket URL
VITE_SOCKET_URL=http://localhost:5000

# Configuración de desarrollo
VITE_DEV_MODE=true

# Configuración de animaciones
VITE_ANIMATION_SPEED=1.0
VITE_ENABLE_ANIMATIONS=true
```

---

## 📁 Estructura del Proyecto

```
Frontend_ecosort/
├── public/                          # Assets estáticos
├── src/
│   ├── components/                  # Componentes reutilizables
│   │   ├── auth/                   # Componentes de autenticación
│   │   │   ├── RequireAuth.tsx     # Protección de rutas
│   │   │   └── RequireAuth.module.css
│   │   ├── dashboard/              # Componentes del dashboard
│   │   │   ├── SystemStatus.tsx    # Estado del sistema
│   │   │   ├── AnimatedMetrics.tsx # Métricas animadas
│   │   │   ├── ObjectFlowAnimation.tsx # Animación principal
│   │   │   ├── Notifications.tsx   # Sistema de notificaciones
│   │   │   ├── RealtimeLog.tsx     # Log en tiempo real
│   │   │   └── *.module.css        # Estilos modulares
│   │   ├── analytics/              # Componentes de análisis
│   │   │   ├── BaseChart.tsx       # Configuración base de gráficos
│   │   │   ├── ThroughputChart.tsx # Gráfico de throughput
│   │   │   ├── ConfidenceTrendChart.tsx # Tendencias de confianza
│   │   │   ├── ClassificationDoughnut.tsx # Distribución por categorías
│   │   │   ├── TrendIndicators.tsx # Indicadores de tendencia
│   │   │   └── *.module.css
│   │   ├── control/                # Componentes de control
│   │   │   ├── ControlPanel.tsx    # Panel de control principal
│   │   │   ├── SystemStateIndicator.tsx # Indicador de estado
│   │   │   ├── EmergencyStop.tsx   # Botón de emergencia
│   │   │   └── *.module.css
│   │   └── layout/                 # Componentes de layout
│   │       ├── Layout.tsx          # Layout principal
│   │       └── Layout.module.css
│   ├── hooks/                      # Hooks personalizados
│   │   ├── useAuth.tsx            # Hook de autenticación
│   │   ├── useSocket.tsx          # Hook de WebSocket
│   │   ├── useAnalyticsData.tsx   # Hook de datos analíticos
│   │   └── useSystemControl.tsx   # Hook de control del sistema
│   ├── pages/                      # Páginas principales
│   │   ├── Login.tsx              # Página de login
│   │   ├── Dashboard.tsx          # Dashboard principal
│   │   ├── Analytics.tsx          # Página de análisis
│   │   ├── Control.tsx            # Página de control
│   │   └── *.module.css
│   ├── styles/                     # Estilos globales
│   │   └── index.css              # Estilos base y variables CSS
│   ├── types/                      # Definiciones de tipos
│   │   └── socket.ts              # Tipos para WebSocket
│   ├── App.tsx                     # Componente raíz
│   ├── main.tsx                    # Punto de entrada
│   └── vite-env.d.ts              # Tipos de Vite
├── package.json                    # Dependencias y scripts
├── tsconfig.json                   # Configuración TypeScript
├── vite.config.ts                  # Configuración Vite
└── README.md                       # Esta documentación
```

---

## 🧩 Componentes Principales

### 🔐 Sistema de Autenticación

#### `useAuth.tsx`
Hook principal para manejo de autenticación con JWT:

```typescript
const { user, login, logout, isAuthenticated } = useAuth();

// Login con credenciales
await login('admin', 'password');

// Logout
logout();

// Verificar autenticación
if (isAuthenticated) {
  // Usuario autenticado
}
```

#### `RequireAuth.tsx`
Componente para proteger rutas que requieren autenticación:

```typescript
<RequireAuth>
  <ProtectedComponent />
</RequireAuth>
```

### 📊 Dashboard en Tiempo Real

#### `SystemStatus.tsx`
Muestra el estado de conexión con el backend:
- **Conectado**: Indicador verde con pulso
- **Desconectado**: Indicador rojo
- **Reconectando**: Indicador amarillo animado

#### `AnimatedMetrics.tsx`
Métricas del sistema con animaciones Anime.js:
- Contadores animados para objetos procesados
- Barras de progreso para confianza promedio
- Indicadores de rendimiento con efectos visuales

#### `ObjectFlowAnimation.tsx`
**Componente estrella** - Animación compleja de flujo de objetos:

```typescript
// Características principales:
- Banda transportadora visual animada
- Objetos que se mueven con física realista
- Colores específicos por categoría de residuo
- Efectos de escala y rotación
- Animaciones de desviación hacia tolvas
- Partículas y efectos especiales
```

#### `Notifications.tsx`
Sistema de notificaciones con animaciones de entrada/salida:
- Notificaciones toast animadas
- Auto-dismiss configurable
- Diferentes tipos: info, warning, error, success

#### `RealtimeLog.tsx`
Log de eventos en tiempo real:
- Scroll automático
- Animaciones de fade-in para nuevos eventos
- Filtrado por tipo de evento

### 📈 Analytics Avanzados

#### `BaseChart.tsx`
Configuración base para todos los gráficos:
- Tema oscuro consistente
- Configuración responsive
- Animaciones suaves
- Tooltips personalizados

#### `ThroughputChart.tsx`
Gráfico de línea para throughput:
- Objetos procesados por minuto
- Tendencias temporales
- Zoom y pan interactivo

#### `ConfidenceTrendChart.tsx`
Tendencias de confianza de clasificación:
- Porcentajes de confianza en el tiempo
- Líneas de umbral
- Indicadores de calidad

#### `ClassificationDoughnut.tsx`
Distribución por categorías:
- Gráfico de dona interactivo
- Colores específicos por material
- Porcentajes y conteos

#### `TrendIndicators.tsx`
Indicadores de tendencia:
- Flechas direccionales
- Colores semánticos
- Animaciones de cambio

### 🎛️ Control Industrial

#### `ControlPanel.tsx`
Panel principal de control del sistema:
- Botones para start/stop/pause/resume
- Estados visuales claros
- Confirmaciones de acciones críticas

#### `SystemStateIndicator.tsx`
Indicador visual del estado del sistema:
- Estados: idle, running, paused, error, maintenance
- Colores y animaciones específicas
- Información contextual

#### `EmergencyStop.tsx`
Botón de parada de emergencia:
- Diseño prominente y accesible
- Confirmación de acción
- Animaciones de alerta

---

## 🎣 Hooks Personalizados

### `useSocket.tsx`
Hook para manejo de WebSocket con el backend:

```typescript
const { socket, isConnected, joinRoom, leaveRoom } = useSocket(token);

// Unirse a room específico
joinRoom('dashboard');

// Escuchar eventos
useEffect(() => {
  if (socket) {
    socket.on('metrics_update', handleMetricsUpdate);
    socket.on('new_classification', handleNewClassification);
    
    return () => {
      socket.off('metrics_update');
      socket.off('new_classification');
    };
  }
}, [socket]);
```

### `useAnalyticsData.tsx`
Hook especializado para datos analíticos:

```typescript
const { 
  metricsData, 
  isLoading, 
  error, 
  refreshData 
} = useAnalyticsData(token);

// Datos incluyen:
// - Timeline de métricas
// - Distribución por categorías
// - Tendencias de rendimiento
// - Indicadores de calidad
```

### `useSystemControl.tsx`
Hook para control del sistema:

```typescript
const { 
  systemStatus, 
  startSystem, 
  stopSystem, 
  pauseSystem, 
  resumeSystem, 
  emergencyStop,
  isLoading 
} = useSystemControl(token);

// Ejecutar comandos
await startSystem();
await pauseSystem();
await emergencyStop();
```

---

## 🎨 Sistema de Animaciones

### Anime.js Integration

El sistema utiliza **Anime.js 3.2.2** para animaciones complejas y fluidas:

#### Animaciones de Objetos
```typescript
// Animación de objeto moviéndose por la banda
anime({
  targets: objectElement,
  translateX: [0, 800],
  translateY: [250, 250],
  scale: [0.5, 1, 0.8],
  opacity: [0, 1, 0],
  rotate: [0, 360],
  duration: 3000,
  easing: 'easeInOutQuad',
  complete: () => {
    // Cleanup después de animación
    objectElement.remove();
  }
});
```

#### Animaciones de Métricas
```typescript
// Contadores animados
anime({
  targets: '.counter',
  innerHTML: [0, targetValue],
  duration: 1000,
  round: 1,
  easing: 'easeOutExpo'
});

// Barras de progreso
anime({
  targets: '.progress-bar',
  width: targetWidth + '%',
  duration: 800,
  easing: 'easeInOutQuad'
});
```

#### Efectos Especiales
- **Partículas**: Efectos de partículas para clasificaciones exitosas
- **Pulsos**: Animaciones de pulso para estados activos
- **Transiciones**: Transiciones suaves entre estados
- **Morphing**: Transformaciones de formas y colores

### Configuración de Rendimiento

```css
/* Optimizaciones CSS para animaciones */
.animated-element {
  will-change: transform, opacity;
  transform: translateZ(0); /* Forzar aceleración hardware */
  backface-visibility: hidden;
}

/* Variables CSS para consistencia */
:root {
  --animation-duration-fast: 0.2s;
  --animation-duration-normal: 0.5s;
  --animation-duration-slow: 1s;
  --animation-easing: cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

## 🌐 Integración WebSocket

### Conexión y Autenticación

```typescript
// Conexión con autenticación JWT
const socket = io('http://localhost:5000', {
  auth: {
    token: jwtToken
  },
  transports: ['websocket', 'polling']
});

// Manejo de eventos de conexión
socket.on('connect', () => {
  console.log('Conectado al backend');
});

socket.on('disconnect', () => {
  console.log('Desconectado del backend');
});
```

### Rooms y Eventos

#### Dashboard Room
```typescript
// Unirse al room del dashboard
socket.emit('join_room', { room: 'dashboard' });

// Eventos del dashboard
socket.on('metrics_update', (data) => {
  // Actualizar métricas en tiempo real
  updateDashboardMetrics(data);
});

socket.on('new_classification', (data) => {
  // Crear nueva animación de objeto
  createObjectAnimation(data);
});

socket.on('system_status_change', (data) => {
  // Actualizar estado del sistema
  updateSystemStatus(data);
});
```

#### Analytics Room
```typescript
// Unirse al room de analytics
socket.emit('join_room', { room: 'analytics' });

// Eventos de analytics
socket.on('analytics_update', (data) => {
  // Actualizar gráficos y métricas
  updateAnalyticsCharts(data);
});

socket.on('trend_change', (data) => {
  // Actualizar indicadores de tendencia
  updateTrendIndicators(data);
});
```

#### Control Room
```typescript
// Unirse al room de control (requiere permisos)
socket.emit('join_room', { room: 'control' });

// Eventos de control
socket.on('system_command_result', (data) => {
  // Resultado de comando ejecutado
  handleCommandResult(data);
});

socket.on('emergency_alert', (data) => {
  // Alerta de emergencia
  showEmergencyAlert(data);
});
```

### Manejo de Errores y Reconexión

```typescript
// Manejo de errores
socket.on('error', (error) => {
  console.error('Error de WebSocket:', error);
  showNotification('Error de conexión', 'error');
});

// Reconexión automática
socket.on('reconnect', (attemptNumber) => {
  console.log(`Reconectado después de ${attemptNumber} intentos`);
  showNotification('Conexión restaurada', 'success');
});

socket.on('reconnect_error', (error) => {
  console.error('Error de reconexión:', error);
  showNotification('Error de reconexión', 'error');
});
```

---

## 💻 Desarrollo

### Scripts Disponibles

```bash
# Desarrollo
npm run dev          # Servidor de desarrollo con HMR
npm run build        # Build para producción
npm run preview      # Vista previa del build
npm run lint         # Linting con ESLint
```

### Configuración de Desarrollo

#### Vite Configuration
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  }
});
```

### Estándares de Código

#### Convenciones de Naming
- **Componentes**: PascalCase (`SystemStatus.tsx`)
- **Hooks**: camelCase con prefijo `use` (`useSocket.tsx`)
- **Archivos CSS**: kebab-case con `.module.css` (`system-status.module.css`)
- **Variables**: camelCase (`isConnected`)
- **Constantes**: UPPER_SNAKE_CASE (`API_BASE_URL`)

---

## 🚀 Deployment

### Build para Producción

```bash
# Crear build optimizado
npm run build

# Los archivos se generan en dist/
# - index.html
# - assets/
#   - *.js (JavaScript minificado)
#   - *.css (CSS minificado)
#   - *.woff2 (Fuentes)
```

### Variables de Entorno para Producción

```env
# .env.production
VITE_API_URL=https://api.ecosort.com
VITE_SOCKET_URL=https://api.ecosort.com
VITE_DEV_MODE=false
VITE_ANIMATION_SPEED=1.0
VITE_ENABLE_ANIMATIONS=true
```

---

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. WebSocket No Conecta
```bash
# Verificar backend
curl http://localhost:5000/api/status

# Verificar configuración
console.log(import.meta.env.VITE_SOCKET_URL);

# Verificar token
console.log(localStorage.getItem('ecosort_token'));
```

#### 2. Animaciones Lentas
```typescript
// Reducir complejidad de animaciones
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
if (reducedMotion.matches) {
  // Desactivar animaciones complejas
  anime.set(targets, { duration: 0 });
}
```

#### 3. Errores de Build
```bash
# Limpiar cache
rm -rf node_modules package-lock.json
npm install

# Verificar versiones
npm ls

# Build con debug
npm run build -- --debug
```

---

## 🤝 Contribución

### Proceso de Desarrollo

1. **Fork** del repositorio
2. **Crear branch**: `git checkout -b feature/nueva-funcionalidad`
3. **Desarrollar** siguiendo estándares
4. **Tests**: Asegurar que todo funciona
5. **Commit**: Mensajes descriptivos
6. **Push**: `git push origin feature/nueva-funcionalidad`
7. **Pull Request** con descripción detallada

### Estándares de Commit

```bash
# Formato de commits
feat: agregar nueva funcionalidad
fix: corregir bug
docs: actualizar documentación
style: cambios de formato
refactor: refactorización de código
test: agregar tests
chore: tareas de mantenimiento

# Ejemplos
feat: agregar animación de partículas para clasificaciones exitosas
fix: corregir reconexión automática de WebSocket
docs: actualizar README con nuevas funcionalidades
```

---

## 📚 Recursos Adicionales

### Documentación de Dependencias

- **[React 19](https://react.dev/)** - Framework principal
- **[TypeScript](https://www.typescriptlang.org/)** - Tipado estático
- **[Vite](https://vitejs.dev/)** - Build tool y dev server
- **[Anime.js](https://animejs.com/)** - Librería de animaciones
- **[Chart.js](https://www.chartjs.org/)** - Gráficos interactivos
- **[Socket.IO Client](https://socket.io/docs/v4/client-api/)** - WebSocket client
- **[React Router](https://reactrouter.com/)** - Routing

### Tutoriales y Guías

- [Anime.js Tutorial](https://animejs.com/documentation/) - Guía completa de animaciones
- [Chart.js Getting Started](https://www.chartjs.org/docs/latest/getting-started/) - Configuración de gráficos
- [Socket.IO Client Guide](https://socket.io/docs/v4/client-initialization/) - Integración WebSocket
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/) - Patrones TypeScript

---

## 👥 Autores y Contribuidores

### Equipo Principal
- **Gabriel Calderón** - *Arquitectura del Sistema y Backend Integration*
- **Elias Bautista** - *Animaciones y Visualización*
- **Cristian Hernandez** - *UI/UX y Componentes*

### Colaboradores Frontend v2.1
- **Sistema de Animaciones** - Implementación completa con Anime.js
- **Dashboard en Tiempo Real** - WebSocket integration y métricas
- **Analytics Avanzados** - Gráficos interactivos y análisis
- **Control Industrial** - Interfaz de control y monitoreo
- **Autenticación JWT** - Sistema de login y protección de rutas
- **TypeScript Integration** - Tipado fuerte y mejor DX

---

<div align="center">

**⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub ⭐**

**Hecho con ❤️ para un futuro más limpio y sostenible**

*Frontend moderno para el sistema industrial de clasificación de residuos más avanzado*

</div>
