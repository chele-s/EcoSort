import React from 'react';
import { useSystemControl } from '../hooks/useSystemControl';
import styles from './Control.module.css';
import ControlPanel from '../components/control/ControlPanel';
import SystemStateIndicator from '../components/control/SystemStateIndicator';
import EmergencyStop from '../components/control/EmergencyStop';

const Control = () => {
  const { status, isLoading, error, start, stop, pause, resume, emergencyStop } = useSystemControl();

  if (isLoading) {
    return <div className={styles.centered}>Loading System Status...</div>;
  }
  
  if (error) {
    return <div className={`${styles.centered} ${styles.error}`}>Error: {error}</div>;
  }

  if (!status) {
    return <div className={styles.centered}>Could not retrieve system status.</div>;
  }

  return (
    <div className={styles.controlPage}>
      <header className={styles.header}>
        <h1 className={styles.title}>System Control Panel</h1>
        <SystemStateIndicator state={status.state} />
      </header>
      
      <div className={styles.controlGrid}>
        <div className={styles.mainControls}>
          <ControlPanel 
            status={status.state}
            onStart={start}
            onStop={stop}
            onPause={pause}
            onResume={resume}
          />
        </div>
        <div className={styles.safetyControls}>
            <EmergencyStop onEmergencyStop={emergencyStop} />
        </div>
        <div className={styles.configPanel}>
            <h3 className={styles.panelTitle}>System Configuration</h3>
            <p className={styles.panelText}>Dynamic configuration options will be available here in a future update.</p>
        </div>
      </div>
    </div>
  );
};

export default Control; 