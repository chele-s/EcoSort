import { useState, useEffect } from 'react';
import { useSocket } from './useSocket';
import type { MetricsData } from '../types/socket';

export const useAnalyticsData = () => {
  const { socket, isConnected } = useSocket();
  const [analyticsData, setAnalyticsData] = useState<MetricsData | null>(null);

  useEffect(() => {
    if (socket && isConnected) {
      
      // Join the analytics room to receive specific data
      socket.emit('join_room', { room: 'analytics' });
      console.log("Joined 'analytics' room.");

      // Initial data request (optional, if backend supports it)
      socket.emit('request_data', {
          type: 'realtime_metrics',
          minutes: 60 // Fetch data for the last hour
      });
      
      const handleMetricsUpdate = (data: MetricsData) => {
        setAnalyticsData(data);
      };

      socket.on('metrics_update', handleMetricsUpdate);

      return () => {
        socket.off('metrics_update', handleMetricsUpdate);
        // It's good practice to leave the room when the component unmounts
        socket.emit('leave_room', { room: 'analytics' });
        console.log("Left 'analytics' room.");
      };
    }
  }, [socket, isConnected]);

  return { analyticsData, isConnected };
}; 