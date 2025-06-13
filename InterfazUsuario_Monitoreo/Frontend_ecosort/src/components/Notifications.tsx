import React, { useEffect, useRef } from 'react';
import { animate } from 'animejs';
import styles from './Notifications.module.css';
import type { NotificationData, CriticalAlertData } from '../types/socket';

interface NotificationsProps {
  notification: NotificationData | CriticalAlertData | null;
  onClear: () => void;
}

const Notifications: React.FC<NotificationsProps> = ({ notification, onClear }) => {
  const notificationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (notification && notificationRef.current) {
      // Entrance animation
      animate(notificationRef.current, {
        translateX: ['100%', '0%'],
        opacity: [0, 1],
        duration: 500,
        easing: 'easeOutExpo'
      });

      // Auto-dismiss timer
      const timer = setTimeout(() => {
        if (notificationRef.current) {
          // Exit animation
          animate(notificationRef.current, {
            translateX: ['0%', '100%'],
            opacity: [1, 0],
            duration: 500,
            easing: 'easeInExpo',
            complete: onClear
          });
        }
      }, 5000); // Dismiss after 5 seconds

      return () => clearTimeout(timer);
    }
  }, [notification, onClear]);

  if (!notification) {
    return null;
  }
  
  const isCritical = 'severity' in notification && notification.severity.toLowerCase() === 'critical';
  const notificationClass = isCritical ? styles.critical : styles.warning;


  return (
    <div ref={notificationRef} className={`${styles.notification} ${notificationClass}`}>
      <div className={styles.icon}>
        {isCritical ? '🚨' : '🔔'}
      </div>
      <div className={styles.content}>
        <h4 className={styles.title}>{isCritical ? 'Critical Alert' : 'Notification'}</h4>
        <p className={styles.message}>{notification.message}</p>
      </div>
      <button onClick={onClear} className={styles.closeButton}>&times;</button>
    </div>
  );
};

export default Notifications; 