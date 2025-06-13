import React, { useRef, useEffect } from 'react';
import styles from './RealtimeLog.module.css';

interface RealtimeLogProps {
  logEntries: string[];
}

const RealtimeLog: React.FC<RealtimeLogProps> = ({ logEntries }) => {
    const logContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Scroll to the top when a new log entry is added
        if(logContainerRef.current) {
            logContainerRef.current.scrollTop = 0;
        }
    }, [logEntries]);

  return (
    <div ref={logContainerRef} className={styles.logContainer}>
      {logEntries.map((entry, index) => (
        <div key={index} className={styles.logEntry}>
          {entry}
        </div>
      ))}
    </div>
  );
};

export default RealtimeLog; 