import React from 'react';
import { Line } from 'react-chartjs-2';
import { getChartOptions } from './BaseChart';
import type { MetricsData } from '../../types/socket';

interface ThroughputChartProps {
  data: MetricsData['timeline'];
}

const ThroughputChart: React.FC<ThroughputChartProps> = ({ data }) => {
  const options = getChartOptions('System Throughput');

  const chartData = {
    labels: data.map(d => new Date(d.minute_bucket * 1000).toLocaleTimeString()),
    datasets: [
      {
        label: 'Objects Processed',
        data: data.map(d => d.objects_processed),
        borderColor: '#00a8ff',
        backgroundColor: 'rgba(0, 168, 255, 0.2)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  return <Line options={options} data={chartData} />;
};

export default ThroughputChart; 