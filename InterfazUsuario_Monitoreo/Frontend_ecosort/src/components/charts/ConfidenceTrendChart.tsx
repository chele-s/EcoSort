import React from 'react';
import { Line } from 'react-chartjs-2';
import { getChartOptions } from './BaseChart';
import type { MetricsData } from '../../types/socket';

interface ConfidenceTrendChartProps {
  data: MetricsData['timeline'];
}

const ConfidenceTrendChart: React.FC<ConfidenceTrendChartProps> = ({ data }) => {
  const options = getChartOptions('Average Confidence') as any;
  
  // Custom options to format Y-axis as percentage
  if (options.scales?.y) {
    const { ticks, ...restOfY } = options.scales.y;
    options.scales.y = {
      ...restOfY,
      max: 1,
      min: 0,
      ticks: {
          ...ticks,
          callback: (value: string | number) => `${Number(value) * 100}%`,
      }
    };
  }

  const chartData = {
    labels: data.map((d: { minute_bucket: number }) => new Date(d.minute_bucket * 1000).toLocaleTimeString()),
    datasets: [
      {
        label: 'Average Confidence',
        data: data.map((d: { avg_confidence: number }) => d.avg_confidence),
        borderColor: '#3effdc',
        backgroundColor: 'rgba(62, 255, 220, 0.2)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  return <Line options={options} data={chartData} />;
};

export default ConfidenceTrendChart; 