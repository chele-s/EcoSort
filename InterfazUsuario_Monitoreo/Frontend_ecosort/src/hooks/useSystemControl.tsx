import { useState, useEffect, useCallback } from 'react';
import { useSocket } from './useSocket';
import { useAuth } from './useAuth';

// Based on the main_sistema_banda.py get_status() method
export interface SystemStatus {
  state: 'initializing' | 'idle' | 'running' | 'paused' | 'error' | 'recovering' | 'maintenance' | 'shutting_down' | 'shutdown';
  uptime_seconds: number;
  metrics: {
    objects_processed: number;
    // other metrics...
  };
  // other status properties...
}

const API_URL = 'http://localhost:5000/api/v2'; // Using v2 from README_Enhanced

export const useSystemControl = () => {
  const { socket, isConnected } = useSocket();
  const { token } = useAuth();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sendCommand = useCallback(async (command: string) => {
    setError(null);
    try {
      const response = await fetch(`${API_URL}/system/control/${command}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || `Command ${command} failed`);
      }
      // The state will be updated via WebSocket broadcast,
      // but we can pre-emptively fetch the status for faster UI feedback.
      const data = await response.json();
      setStatus(data.status);

    } catch (e: any) {
      setError(e.message);
    }
  }, [token]);

  // Fetch initial status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/system/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch system status');
        const data = await response.json();
        setStatus(data);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStatus();
  }, [token]);

  // Listen for real-time updates
  useEffect(() => {
    if (socket && isConnected) {
      const handleSystemEvent = (data: { state: SystemStatus }) => {
        setStatus(data.state);
      };
      
      socket.on('system_event', handleSystemEvent);
      // Also listening to 'system_control' as per README
      socket.on('system_control', handleSystemEvent);

      return () => {
        socket.off('system_event', handleSystemEvent);
        socket.off('system_control', handleSystemEvent);
      };
    }
  }, [socket, isConnected]);

  return {
    status,
    isLoading,
    error,
    start: () => sendCommand('start'),
    stop: () => sendCommand('stop'),
    pause: () => sendCommand('pause'),
    resume: () => sendCommand('resume'),
    emergencyStop: () => sendCommand('emergency_stop'),
  };
}; 