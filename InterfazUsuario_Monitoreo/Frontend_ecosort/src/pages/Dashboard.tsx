import { useEffect, useState } from 'react';
import { useSocket } from '../hooks/useSocket';
import ObjectFlowAnimation from '../components/ObjectFlowAnimation.tsx';
import AnimatedMetrics from '../components/AnimatedMetrics.tsx';
import SystemStatus from '../components/SystemStatus.tsx';
import RealtimeLog from '../components/RealtimeLog.tsx';
import Notifications from '../components/Notifications.tsx';
import styles from './Dashboard.module.css';

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

  useEffect(() => {
    if (!socket) return;

    // Listen for metrics updates
    socket.on('metrics_update', (data: MetricsData) => {
      setMetrics(data);
    });

    // Listen for new classifications for the animation
    socket.on('new_classification', (data: ClassificationData) => {
      setLastClassification(data);
      setLog((prevLog: string[]) => [`[${new Date().toLocaleTimeString()}] New object classified: ${data.category} (${(data.confidence * 100).toFixed(1)}%)`, ...prevLog].slice(0, 50));
    });

    // Listen for push notifications
    socket.on('new_notification', (data: NotificationData) => {
        setNotification(data);
    });
    
    // Listen for critical alerts
    socket.on('critical_alert', (data: CriticalAlertData) => {
        setNotification(data);
    });

    return () => {
      socket.off('metrics_update');
      socket.off('new_classification');
      socket.off('new_notification');
      socket.off('critical_alert');
    };
  }, [socket]);

  return (
    <div className={styles.dashboard}>
      <Notifications notification={notification} onClear={() => setNotification(null)} />
      <header className={styles.header}>
        <h1 className={styles.title}>Real-Time Monitoring</h1>
        <SystemStatus isConnected={isConnected} />
      </header>
      
      <div className={styles.mainGrid}>
        <div className={`${styles.card} ${styles.animationCard}`}>
          <h2 className={styles.cardTitle}>Conveyor Flow</h2>
          <ObjectFlowAnimation newClassification={lastClassification} />
        </div>

        <div className={`${styles.card} ${styles.metricsCard}`}>
            <h2 className={styles.cardTitle}>Live Metrics</h2>
            <AnimatedMetrics metrics={metrics} />
        </div>

        <div className={`${styles.card} ${styles.logCard}`}>
            <h2 className={styles.cardTitle}>Event Log</h2>
            <RealtimeLog logEntries={log} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 