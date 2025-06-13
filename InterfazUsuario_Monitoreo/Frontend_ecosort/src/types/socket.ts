export interface ClassificationData {
  id: number;
  timestamp: number;
  object_uuid: string;
  category: 'metal' | 'plastic' | 'glass' | 'carton' | 'other';
  confidence: number;
  animation_data: {
    start_position: { x: number; y: number };
    end_position: { x: number; y: number };
    diversion_point: { x: number; y: number };
    final_bin: string;
  };
}

export interface MetricsData {
  timestamp: number;
  current: {
    total_objects: number;
    avg_confidence: number;
    avg_processing_time: number;
    error_rate: number;
    throughput_per_minute: number;
  };
  timeline: {
      minute_bucket: number;
      objects_processed: number;
      avg_confidence: number;
      efficiency_score: number;
      active_diversions: number;
  }[];
  distribution: {
      [key: string]: number;
  };
  trends: {
    efficiency_trend: 'up' | 'down' | 'stable';
    confidence_trend: 'up' | 'down' | 'stable';
    throughput_trend: 'up' | 'down' | 'stable';
  };
}

export interface NotificationData {
  id: number;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: number;
}

export interface SystemStateData {
  action: string;
  user: string;
  state: string;
}

export interface CriticalAlertData {
    type: string;
    severity: string;
    message: string;
} 