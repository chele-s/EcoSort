import React, { useEffect, useRef } from 'react';
import { animate, utils, createTimeline } from 'animejs';
import styles from './ObjectFlowAnimation.module.css';
import type { ClassificationData } from '../types/socket';

interface ObjectFlowAnimationProps {
  newClassification: ClassificationData | null;
}

const getCategoryStyle = (category: string) => {
    const styles: { [key: string]: { background: string; boxShadow: string; } } = {
        metal: { background: 'linear-gradient(145deg, #c4c4c4, #9a9a9a)', boxShadow: '0 0 15px #d1d1d1' },
        plastic: { background: 'linear-gradient(145deg, #3a7bd5, #3a60d5)', boxShadow: '0 0 15px #3a7bd5' },
        glass: { background: 'linear-gradient(145deg, #42f49b, #2fcc7f)', boxShadow: '0 0 15px #42f49b' },
        carton: { background: 'linear-gradient(145deg, #d2a679, #b98a5a)', boxShadow: '0 0 15px #d2a679' },
        other: { background: 'linear-gradient(145deg, #6c757d, #5a6268)', boxShadow: '0 0 15px #6c757d' }
    };
    return styles[category] || styles['other'];
};


const ObjectFlowAnimation: React.FC<ObjectFlowAnimationProps> = ({ newClassification }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const beltRef = useRef<HTMLDivElement>(null);

    // Belt animation
    useEffect(() => {
        if (!beltRef.current) return;
        animate(beltRef.current, {
            backgroundPosition: '-200px 0px',
            duration: 2000,
            easing: 'linear',
            loop: true
        });
    }, []);

    // Object animation
    useEffect(() => {
        if (!newClassification || !containerRef.current) return;

        const objectEl = document.createElement('div');
        objectEl.className = styles.object;
        const style = getCategoryStyle(newClassification.category);
        objectEl.style.background = style.background;
        objectEl.style.boxShadow = style.boxShadow;

        containerRef.current.appendChild(objectEl);

        const { animation_data } = newClassification;
        const containerWidth = containerRef.current.clientWidth;
        const containerHeight = containerRef.current.clientHeight;

        const startX = (animation_data.start_position.x / 100) * containerWidth;
        const startY = (animation_data.start_position.y / 100) * containerHeight;
        
        const diversionPointX = (animation_data.diversion_point.x / 100) * containerWidth;
        const diversionPointY = (animation_data.diversion_point.y / 100) * containerHeight;
        
        const endX = (animation_data.end_position.x / 100) * containerWidth;
        const endY = (animation_data.end_position.y / 100) * containerHeight;

        const tl = createTimeline({
            onComplete: () => {
                objectEl.remove();
            }
        });

        tl.add(objectEl, {
            translateX: [startX, diversionPointX],
            translateY: [startY, diversionPointY],
            opacity: [0, 1],
            scale: [0, 1.2, 1],
            rotate: [() => utils.random(-360, 360), () => utils.random(-360, 360)],
            duration: 2000,
            easing: 'easeInQuad'
        })
        .add(objectEl, {
            translateX: [diversionPointX, endX],
            translateY: [diversionPointY, endY],
            opacity: [1, 0],
            scale: [1, 0.5],
            rotate: '+=360',
            duration: 1000,
            easing: 'easeOutQuad'
        });

    }, [newClassification]);

  return (
    <div ref={containerRef} className={styles.animationContainer}>
        <div ref={beltRef} className={styles.conveyorBelt}></div>
    </div>
  );
};

export default ObjectFlowAnimation; 