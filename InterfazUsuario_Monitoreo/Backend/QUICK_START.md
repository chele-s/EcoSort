# 🚀 EcoSort Backend Enhanced v2.1 - Quick Start

## ⚡ Instalación Rápida

### 1. Dependencias Enhanced
```bash
pip install marshmallow flask-limiter flask-compress PyJWT python-jose
```

### 2. Ejecutar Demo
```bash
cd InterfazUsuario_Monitoreo\Backend
python example_enhanced_usage.py
```

### 3. Verificar que funciona
✅ Si ves el output con emojis y datos JSON, ¡está funcionando!

---

## 🔧 Configuración para React Frontend

### 1. **Instalar dependencias de React:**
```bash
npm install socket.io-client animejs axios
```

### 2. **Hook para datos en tiempo real:**
```javascript
// src/hooks/useRealtimeData.js
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

    socketInstance.on('new_classification', (classData) => {
      // Aquí puedes triggear animaciones con anime.js
      console.log('Nueva clasificación:', classData.data);
    });

    setSocket(socketInstance);
    return () => socketInstance.close();
  }, [token]);

  return { data, socket };
};
```

### 3. **Componente con animaciones:**
```javascript
// src/components/ObjectFlowAnimation.jsx
import React, { useEffect, useRef } from 'react';
import anime from 'animejs';
import { useRealtimeData } from '../hooks/useRealtimeData';

const ObjectFlowAnimation = ({ token }) => {
  const containerRef = useRef();
  const { socket } = useRealtimeData(token);

  useEffect(() => {
    if (!socket) return;

    socket.on('new_classification', (data) => {
      // Crear elemento visual
      const obj = document.createElement('div');
      obj.className = `object-${data.data.category}`;
      obj.style.cssText = `
        position: absolute;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: ${getCategoryColor(data.data.category)};
      `;
      
      containerRef.current.appendChild(obj);

      // Animar con anime.js
      anime({
        targets: obj,
        translateX: [0, 800],
        translateY: [250, 250],
        scale: [0.5, 1, 0.8],
        opacity: [0, 1, 0],
        duration: 3000,
        easing: 'easeInOutQuad',
        complete: () => obj.remove()
      });
    });
  }, [socket]);

  return (
    <div 
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '500px',
        background: 'linear-gradient(90deg, #f0f0f0 0%, #e0e0e0 100%)',
        border: '2px solid #ddd',
        borderRadius: '8px'
      }}
    >
      <div style={{
        position: 'absolute',
        bottom: '10px',
        left: '10px',
        fontSize: '12px',
        color: '#666'
      }}>
        Banda Transportadora - Esperando objetos...
      </div>
    </div>
  );
};

const getCategoryColor = (category) => {
  const colors = {
    metal: '#C0C0C0',
    plastic: '#4A90E2',
    glass: '#50E3C2',
    carton: '#D0844C',
    other: '#9B9B9B'
  };
  return colors[category] || '#9B9B9B';
};

export default ObjectFlowAnimation;
```

---

## 🔐 Autenticación JWT

### 1. **Login Component:**
```javascript
// src/components/Login.jsx
import React, { useState } from 'react';
import axios from 'axios';

const Login = ({ onLogin }) => {
  const [credentials, setCredentials] = useState({
    username: 'operator',
    password: 'operator123'
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('http://localhost:5000/api/v2/auth/login', credentials);
      
      if (response.data.success) {
        const { tokens, user } = response.data.data;
        localStorage.setItem('access_token', tokens.access_token);
        onLogin(tokens.access_token, user);
      }
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        placeholder="Username"
        value={credentials.username}
        onChange={(e) => setCredentials({...credentials, username: e.target.value})}
      />
      <input
        type="password"
        placeholder="Password"
        value={credentials.password}
        onChange={(e) => setCredentials({...credentials, password: e.target.value})}
      />
      <button type="submit">Login</button>
    </form>
  );
};

export default Login;
```

### 2. **Usuarios de demostración:**
```
admin / admin123       - Acceso completo
operator / operator123 - Control y lectura
viewer / viewer123     - Solo lectura
maintenance / maint123 - Configuración y mantenimiento
```

---

## 📊 Dashboard con Métricas en Tiempo Real

```javascript
// src/components/Dashboard.jsx
import React from 'react';
import { useRealtimeData } from '../hooks/useRealtimeData';
import ObjectFlowAnimation from './ObjectFlowAnimation';

const Dashboard = ({ token }) => {
  const { data } = useRealtimeData(token);

  return (
    <div style={{ padding: '20px' }}>
      <h1>🚀 EcoSort Dashboard Enhanced</h1>
      
      {/* Métricas en tiempo real */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '20px' }}>
        <MetricCard 
          title="Objetos/Min"
          value={data?.current?.objects_per_minute || 0}
          color="#4A90E2"
        />
        <MetricCard 
          title="Confianza Promedio"
          value={`${((data?.current?.avg_confidence || 0) * 100).toFixed(1)}%`}
          color="#50E3C2"
        />
        <MetricCard 
          title="Eficiencia"
          value={`${(100 - (data?.current?.error_rate || 0)).toFixed(1)}%`}
          color="#7ED321"
        />
        <MetricCard 
          title="Throughput"
          value={data?.current?.throughput_per_minute || 0}
          color="#F5A623"
        />
      </div>

      {/* Animación de flujo de objetos */}
      <div style={{ marginBottom: '20px' }}>
        <h2>🎨 Flujo de Objetos en Tiempo Real</h2>
        <ObjectFlowAnimation token={token} />
      </div>
    </div>
  );
};

const MetricCard = ({ title, value, color }) => (
  <div style={{
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    borderLeft: `4px solid ${color}`
  }}>
    <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#666' }}>{title}</h3>
    <div style={{ fontSize: '24px', fontWeight: 'bold', color: color }}>{value}</div>
  </div>
);

export default Dashboard;
```

---

## 🎯 App Principal

```javascript
// src/App.jsx
import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';

function App() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Verificar token existente
    const savedToken = localStorage.getItem('access_token');
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const handleLogin = (accessToken, userData) => {
    setToken(accessToken);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      {!token ? (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh'
        }}>
          <div style={{
            background: 'white',
            padding: '40px',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ textAlign: 'center', marginBottom: '30px' }}>
              🚀 EcoSort Enhanced
            </h2>
            <Login onLogin={handleLogin} />
          </div>
        </div>
      ) : (
        <div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'white',
            padding: '10px 20px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <span>Bienvenido, {user?.username} ({user?.role})</span>
            <button onClick={handleLogout}>Logout</button>
          </div>
          <Dashboard token={token} />
        </div>
      )}
    </div>
  );
}

export default App;
```

---

## 🚀 Próximos Pasos

### 1. **Implementar Backend Completo:**
```bash
# Los archivos están creados, implementar según la documentación
# Usar los ejemplos de database_enhanced.py y api_enhanced.py
```

### 2. **Iniciar Backend Enhanced:**
```bash
# Cuando esté implementado:
python InterfazUsuario_Monitoreo/Backend/app_enhanced.py
```

### 3. **Iniciar Frontend React:**
```bash
npm start
```

### 4. **Testear Integración:**
- Login con usuarios de demo
- Ver métricas en tiempo real
- Observar animaciones de objetos
- Probar WebSocket en tiempo real

---

## 📚 Recursos

- **Demo ejecutable:** `example_enhanced_usage.py`
- **Documentación completa:** `ENHANCED_SUMMARY.md`
- **Archivos enhanced:** `database_enhanced.py`, `api_enhanced.py`
- **Ejemplos React:** Los componentes de arriba

**¡Backend Enhanced listo para crear experiencias increíbles con React + Anime.js!** 🌟 