import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler } from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export const getChartOptions = (title: string) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as 'top' | 'bottom' | 'left' | 'right',
      labels: {
        color: '#a8a8b3',
        font: {
          family: "'Inter', sans-serif",
        },
      },
    },
    title: {
      display: true,
      text: title,
      color: '#e1e1e6',
      font: {
        size: 16,
        family: "'Inter', sans-serif",
      },
    },
    tooltip: {
      backgroundColor: '#202330',
      titleColor: '#e1e1e6',
      bodyColor: '#a8a8b3',
      borderColor: '#2a2e40',
      borderWidth: 1,
    }
  },
  scales: {
    x: {
      ticks: {
        color: '#737380',
        font: {
          family: "'Inter', sans-serif",
        },
      },
      grid: {
        color: 'rgba(42, 46, 64, 0.5)',
      },
    },
    y: {
      ticks: {
        color: '#737380',
        font: {
          family: "'Inter', sans-serif",
        },
      },
      grid: {
        color: 'rgba(42, 46, 64, 0.5)',
      },
    },
  },
}); 