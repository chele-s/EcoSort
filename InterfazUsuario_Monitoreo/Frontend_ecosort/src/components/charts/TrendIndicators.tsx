import React from 'react';
import styles from './TrendIndicators.module.css';
import type { MetricsData } from '../../types/socket';

interface TrendIndicatorsProps {
  trends: MetricsData['trends'];
}

const TrendIcon = ({ trend }: { trend: 'up' | 'down' | 'stable' }) => {
    if (trend === 'up') return <span className={`${styles.icon} ${styles.up}`}>▲</span>;
    if (trend === 'down') return <span className={`${styles.icon} ${styles.down}`}>▼</span>;
    return <span className={`${styles.icon} ${styles.stable}`}>▬</span>;
}

const TrendIndicators: React.FC<TrendIndicatorsProps> = ({ trends }) => {
  return (
    <div className={styles.trendsGrid}>
        <div className={styles.trendItem}>
            <div className={styles.trendInfo}>
                <h4>Efficiency</h4>
                <p>System operational effectiveness</p>
            </div>
            <div className={styles.trendVisual}>
                <TrendIcon trend={trends.efficiency_trend} />
                <span className={styles.trendText}>{trends.efficiency_trend}</span>
            </div>
        </div>
        <div className={styles.trendItem}>
            <div className={styles.trendInfo}>
                <h4>Confidence</h4>
                <p>Average classification accuracy</p>
            </div>
            <div className={styles.trendVisual}>
                <TrendIcon trend={trends.confidence_trend} />
                <span className={styles.trendText}>{trends.confidence_trend}</span>
            </div>
        </div>
        <div className={styles.trendItem}>
            <div className={styles.trendInfo}>
                <h4>Throughput</h4>
                <p>Objects processed per minute</p>
            </div>
            <div className={styles.trendVisual}>
                <TrendIcon trend={trends.throughput_trend} />
                <span className={styles.trendText}>{trends.throughput_trend}</span>
            </div>
        </div>
    </div>
  );
};

export default TrendIndicators; 