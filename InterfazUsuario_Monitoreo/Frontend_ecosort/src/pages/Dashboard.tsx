import { useEffect, useState, useRef } from 'react';
import { useSocket } from '../hooks/useSocket';
import ObjectFlowAnimation from '../components/ObjectFlowAnimation.tsx';
import AnimatedMetrics from '../components/AnimatedMetrics.tsx';
import SystemStatus from '../components/SystemStatus.tsx';
import RealtimeLog from '../components/RealtimeLog.tsx';
import Notifications from '../components/Notifications.tsx';
import styles from './Dashboard.module.css';
import { 
  animate, 
  createTimeline
} from 'animejs';

import type { 
  ClassificationData, 
  MetricsData, 
  NotificationData,
  CriticalAlertData
} from '../types/socket';

const Dashboard = () => {
  const { socket, isConnected } = useSocket();
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [lastClassification, setLastClassification] = useState<ClassificationData | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [notification, setNotification] = useState<NotificationData | CriticalAlertData | null>(null);
  
  const dashboardRef = useRef<HTMLDivElement>(null);
  const wavePathRef = useRef<SVGPathElement>(null);

  // Animación del título
  useEffect(() => {
    const title = document.querySelector(`.${styles.title}`);
    if (!title) return;

    const texts = [
      'Monitoreo de Sistema Activo',
      'Análisis de Datos en Tiempo Real',
      'Clasificación por IA EcoSort',
      'Panel de Control Centralizado',
      'Optimización de Procesos',
    ];
    let currentIndex = 0;
    title.textContent = texts[currentIndex];

    const interval = setInterval(() => {
      currentIndex = (currentIndex + 1) % texts.length;
      
      const tl = createTimeline();

      tl.add(title, {
        opacity: 0,
        translateY: -10,
        duration: 300,
        ease: 'easeInCubic'
      })
      .call(() => {
        if (title) title.textContent = texts[currentIndex];
      })
      .add(title, {
        opacity: 1,
        translateY: [10, 0],
        duration: 300,
        ease: 'easeOutCubic'
      });
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Animación de onda de datos
  useEffect(() => {
    if (!wavePathRef.current) return;

    const path = wavePathRef.current;
    const waveWidth = 800; // Match viewBox width

    const timeline = createTimeline({
      loop: true,
      autoplay: true,
    });
    
    const d1 = `M0,50 C200,80 300,20 400,50 S600,80 800,50 V100 H0 Z`;
    const d2 = `M0,50 C200,20 300,80 400,50 S600,20 800,50 V100 H0 Z`;

    timeline
      .add(path, { d: d1, duration: 2500, ease: 'easeInOutSine' })
      .add(path, { d: d2, duration: 2500, ease: 'easeInOutSine' });

    return () => {
      timeline.cancel();
    }
  }, []);

  // Reacciones dinámicas a cambios de datos
  useEffect(() => {
    if (!metrics) return;
    const metricsCard = document.querySelector(`.${styles.metricsCard}`);
    if(metricsCard) {
      animate(metricsCard, {
        borderColor: ['var(--color-primary)', 'var(--color-border)'],
        duration: 1200,
        ease: 'easeOutExpo'
      });
    }
  }, [metrics]);

  // Efectos para nueva clasificación
  useEffect(() => {
    if (!lastClassification) return;
    const animationCard = document.querySelector(`.${styles.animationCard}`);
    if (animationCard) {
        animate(animationCard, {
            borderColor: ['var(--color-success)', 'var(--color-border)'],
            duration: 1200,
            ease: 'easeOutExpo'
        });
    }
  }, [lastClassification]);

  // Alertas críticas
  useEffect(() => {
    if (!notification) return;
    if ('type' in notification && notification.type === 'critical' && dashboardRef.current) {
      animate(dashboardRef.current, {
        borderColor: ['var(--color-danger)', 'var(--color-bg)'],
        borderWidth: ['0px', '2px'],
        duration: 400,
        loop: 4,
        direction: 'alternate',
        ease: 'linear',
      });
    }
  }, [notification]);

  useEffect(() => {
    if (!socket) return;

    socket.on('metrics_update', (data: MetricsData) => setMetrics(data));
    socket.on('new_classification', (data: ClassificationData) => {
      setLastClassification(data);
      setLog((prevLog) => [`[${new Date().toLocaleTimeString()}] Objeto clasificado: ${data.category} (${(data.confidence * 100).toFixed(1)}%)`, ...prevLog].slice(0, 50));
    });
    socket.on('new_notification', (data: NotificationData) => setNotification(data));
    socket.on('critical_alert', (data: CriticalAlertData) => setNotification(data));

    return () => {
      socket.off('metrics_update');
      socket.off('new_classification');
      socket.off('new_notification');
      socket.off('critical_alert');
    };
  }, [socket]);

  return (
    <div className={styles.dashboard} ref={dashboardRef}>
      <Notifications notification={notification} onClear={() => setNotification(null)} />
      
      <header className={styles.header}>
        <h1 className={styles.title}>Panel de Control</h1>
        <SystemStatus isConnected={isConnected} />
      </header>
      
      <div className={styles.mainGrid}>
        <div className={`${styles.card} ${styles.animationCard}`}>
          <h2 className={styles.cardTitle}>Flujo de Clasificación</h2>
          <ObjectFlowAnimation newClassification={lastClassification} />
        </div>

        <div className={`${styles.card} ${styles.metricsCard}`}>
          <h2 className={styles.cardTitle}>Métricas de Rendimiento</h2>
          <AnimatedMetrics metrics={metrics} />
          
          <div className={styles.dataVisualizer}>
            <svg width="100%" height="80" viewBox="0 0 800 100" preserveAspectRatio="none">
              <defs>
                <linearGradient id="waveGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path ref={wavePathRef} fill="url(#waveGradient)" d="M0,50 C200,20 300,80 400,50 S600,20 800,50 V100 H0 Z" />
            </svg>
          </div>
        </div>

        <div className={`${styles.card} ${styles.logCard}`}>
          <h2 className={styles.cardTitle}>Registro de Actividad</h2>
          <RealtimeLog logEntries={log} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 