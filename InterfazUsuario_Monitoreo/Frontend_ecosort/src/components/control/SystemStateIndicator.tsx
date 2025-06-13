import React from 'react';
import styles from './SystemStateIndicator.module.css';
import type { SystemStatus } from '../../hooks/useSystemControl';

interface SystemStateIndicatorProps {
  state: SystemStatus['state'];
}

const stateConfig = {
    running: { text: 'Running', className: 'running' },
    idle: { text: 'Idle', className: 'idle' },
    paused: { text: 'Paused', className: 'paused' },
    error: { text: 'Error', className: 'error' },
    recovering: { text: 'Recovering', className: 'recovering' },
    maintenance: { text: 'Maintenance', className: 'maintenance' },
    shutting_down: { text: 'Shutting Down', className: 'shuttingDown' },
    shutdown: { text: 'Shutdown', className: 'shutdown' },
    initializing: { text: 'Initializing', className: 'initializing' },
};

const SystemStateIndicator: React.FC<SystemStateIndicatorProps> = ({ state }) => {
  const config = stateConfig[state] || stateConfig.idle;

  return (
    <div className={`${styles.indicatorContainer} ${styles[config.className]}`}>
      <span className={styles.light}></span>
      <span className={styles.text}>{config.text}</span>
    </div>
  );
};

export default SystemStateIndicator; 