import React, { useEffect, useRef } from 'react';
import anime from 'animejs';
import styles from './AnimatedMetrics.module.css';
import type { MetricsData } from '../types/socket';

interface AnimatedMetricsProps {
  metrics: MetricsData | null;
}

const AnimatedMetrics: React.FC<AnimatedMetricsProps> = ({ metrics }) => {
    const metricsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!metrics || !metricsRef.current) return;

        const counters = metricsRef.current.querySelectorAll('.animated-counter');
        counters.forEach(counter => {
            const targetValue = parseFloat(counter.getAttribute('data-value') || '0');
            anime({
                targets: counter,
                innerHTML: [0, targetValue],
                round: targetValue % 1 === 0 ? 1 : 10, // Round to integer or one decimal place
                duration: 1000,
                easing: 'easeOutExpo'
            });
        });

        const progressBars = metricsRef.current.querySelectorAll('.progress-bar-inner');
        progressBars.forEach(bar => {
            anime({
                targets: bar,
                width: bar.getAttribute('data-width') + '%',
                duration: 800,
                easing: 'easeInOutQuad'
            });
        });

    }, [metrics]);

  return (
    <div ref={metricsRef} className={styles.metricsGrid}>
        <div className={styles.metricItem}>
            <h4>Objects/min</h4>
            <div className={styles.value}>
                <span className="animated-counter" data-value={metrics?.current.throughput_per_minute || 0}>0</span>
            </div>
        </div>
        <div className={styles.metricItem}>
            <h4>Total Objects</h4>
            <div className={styles.value}>
                <span className="animated-counter" data-value={metrics?.current.total_objects || 0}>0</span>
            </div>
        </div>
        <div className={styles.metricItem}>
            <h4>Avg. Confidence</h4>
            <div className={styles.progressBar}>
                <div className="progress-bar-inner" data-width={(metrics?.current.avg_confidence || 0) * 100} />
            </div>
            <div className={styles.progressLabel}>
                <span className="animated-counter" data-value={(metrics?.current.avg_confidence || 0) * 100}>0</span>%
            </div>
        </div>
        <div className={styles.metricItem}>
            <h4>Error Rate</h4>
             <div className={styles.progressBar}>
                <div className="progress-bar-inner" data-width={metrics?.current.error_rate || 0} />
            </div>
             <div className={styles.progressLabel}>
                <span className="animated-counter" data-value={metrics?.current.error_rate || 0}>0</span>%
            </div>
        </div>
    </div>
  );
};

export default AnimatedMetrics; 