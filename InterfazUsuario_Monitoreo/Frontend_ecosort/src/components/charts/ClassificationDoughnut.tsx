import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { getChartOptions } from './BaseChart';
import type { MetricsData } from '../../types/socket';

interface ClassificationDoughnutProps {
  data: MetricsData['distribution'];
}

const categoryColors = {
  metal: 'rgba(192, 192, 192, 0.7)',
  plastic: 'rgba(54, 162, 235, 0.7)',
  glass: 'rgba(75, 192, 192, 0.7)',
  carton: 'rgba(210, 166, 121, 0.7)',
  other: 'rgba(108, 117, 125, 0.7)',
};

const categoryBorderColors = {
  metal: 'rgb(192, 192, 192)',
  plastic: 'rgb(54, 162, 235)',
  glass: 'rgb(75, 192, 192)',
  carton: 'rgb(210, 166, 121)',
  other: 'rgb(108, 117, 125)',
}


const ClassificationDoughnut: React.FC<ClassificationDoughnutProps> = ({ data }) => {
  const options = getChartOptions('Classification Distribution');
  options.plugins.legend.position = 'right';

  const labels = Object.keys(data);
  const chartData = {
    labels,
    datasets: [
      {
        label: '# of Objects',
        data: Object.values(data),
        backgroundColor: labels.map((label: string) => categoryColors[label as keyof typeof categoryColors] || categoryColors.other),
        borderColor: labels.map((label: string) => categoryBorderColors[label as keyof typeof categoryBorderColors] || categoryBorderColors.other),
        borderWidth: 1,
      },
    ],
  };

  return <Doughnut options={options} data={chartData} />;
};

export default ClassificationDoughnut; 