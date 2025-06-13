import React from 'react';
import { useAnalyticsData } from '../hooks/useAnalyticsData';
import styles from './Analytics.module.css';
import ThroughputChart from '../components/charts/ThroughputChart';
import ConfidenceTrendChart from '../components/charts/ConfidenceTrendChart';
import ClassificationDoughnut from '../components/charts/ClassificationDoughnut';
import TrendIndicators from '../components/charts/TrendIndicators';

const Analytics = () => {
  const { analyticsData, isConnected } = useAnalyticsData();

  if (!isConnected) {
    return (
      <div className={styles.loading}>
        <h2>Connecting to Analytics Service...</h2>
      </div>
    );
  }

  if (!analyticsData) {
    return (
        <div className={styles.loading}>
            <h2>Awaiting Analytics Data...</h2>
        </div>
    );
  }

  return (
    <div className={styles.analyticsPage}>
      <header className={styles.header}>
        <h1 className={styles.title}>System Analytics</h1>
        <p className={styles.subtitle}>Deep dive into system performance and trends.</p>
      </header>
      <div className={styles.analyticsGrid}>
        <div className={`${styles.chartCard} ${styles.area1}`}>
          <ThroughputChart data={analyticsData.timeline} />
        </div>
        <div className={`${styles.chartCard} ${styles.area2}`}>
          <ConfidenceTrendChart data={analyticsData.timeline} />
        </div>
        <div className={`${styles.chartCard} ${styles.area3}`}>
            <ClassificationDoughnut data={analyticsData.distribution} />
        </div>
        <div className={`${styles.chartCard} ${styles.area4}`}>
            <TrendIndicators trends={analyticsData.trends} />
        </div>
      </div>
    </div>
  );
};

export default Analytics; 