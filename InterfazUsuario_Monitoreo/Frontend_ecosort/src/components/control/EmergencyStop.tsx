import React, { useState } from 'react';
import styles from './EmergencyStop.module.css';

interface EmergencyStopProps {
    onEmergencyStop: () => void;
}

const EmergencyStop: React.FC<EmergencyStopProps> = ({ onEmergencyStop }) => {
    const [isConfirming, setIsConfirming] = useState(false);

    const handleClick = () => {
        if (isConfirming) {
            onEmergencyStop();
            setIsConfirming(false);
        } else {
            setIsConfirming(true);
            setTimeout(() => setIsConfirming(false), 3000); // Reset after 3 seconds
        }
    };

  return (
    <div className={styles.container}>
      <button onClick={handleClick} className={`${styles.button} ${isConfirming ? styles.confirming : ''}`}>
        {isConfirming ? 'CONFIRM?' : 'EMERGENCY STOP'}
      </button>
      <p className={styles.warningText}>
        Activates immediate system shutdown. Use with extreme caution.
      </p>
    </div>
  );
};

export default EmergencyStop; 