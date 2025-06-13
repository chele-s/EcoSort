import React from 'react';
import styles from './ControlPanel.module.css';
import type { SystemStatus } from '../../hooks/useSystemControl';

interface ControlPanelProps {
    status: SystemStatus['state'];
    onStart: () => void;
    onStop: () => void;
    onPause: () => void;
    onResume: () => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({ status, onStart, onStop, onPause, onResume }) => {
    
    const canStart = ['idle', 'stopped', 'shutdown'].includes(status);
    const canStop = ['running', 'paused', 'error'].includes(status);
    const canPause = status === 'running';
    const canResume = status === 'paused';

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>Operational Controls</h3>
      <div className={styles.buttonGrid}>
        <button onClick={onStart} disabled={!canStart} className={`${styles.button} ${styles.start}`}>
            START
        </button>
        <button onClick={onStop} disabled={!canStop} className={`${styles.button} ${styles.stop}`}>
            STOP
        </button>
        <button onClick={onPause} disabled={!canPause} className={`${styles.button} ${styles.pause}`}>
            PAUSE
        </button>
        <button onClick={onResume} disabled={!canResume} className={`${styles.button} ${styles.resume}`}>
            RESUME
        </button>
      </div>
    </div>
  );
};

export default ControlPanel; 