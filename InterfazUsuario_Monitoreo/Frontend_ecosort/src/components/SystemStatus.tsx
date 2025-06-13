import React from 'react';
import styles from './SystemStatus.module.css';

interface SystemStatusProps {
  isConnected: boolean;
  // In the future, we can pass the detailed system state here
  // systemState: string; 
}

const SystemStatus: React.FC<SystemStatusProps> = ({ isConnected }) => {
  const statusText = isConnected ? 'Connected' : 'Connecting...';
  const statusClass = isConnected ? styles.connected : styles.disconnected;

  return (
    <div className={styles.status}>
      <span className={`${styles.indicator} ${statusClass}`}></span>
      <span className={styles.statusText}>{statusText}</span>
    </div>
  );
};

export default SystemStatus; 