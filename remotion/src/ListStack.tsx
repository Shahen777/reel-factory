import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Background} from './Background';
import {Base, Fonts, ease} from './common';

export type ListStackProps = Base & {
  title?: string;
  items: string[];
  perItem?: number; // seconds between items
  numbered?: boolean;
};

/** Title, then items stack in one by one (they stay on screen), each with a springy slide. */
export const ListStack: React.FC<ListStackProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const accent = p.accent || '#ffcc00';
  const per = Math.round((p.perItem ?? 1.2) * fps);
  const head = ease(frame, 0, 16);
  return (
    <Background {...p}>
      <Fonts />
      <AbsoluteFill style={{padding: '300px 110px 0', boxSizing: 'border-box'}}>
        {p.title ? (
          <div style={{fontFamily: p.font || 'Display', fontSize: 104, color: '#fff', textTransform: 'uppercase', lineHeight: 1.02,
            opacity: head, transform: `translateY(${(1 - head) * 40}px)`, marginBottom: 70}}>{p.title}</div>
        ) : null}
        {p.items.map((it, i) => {
          const s = spring({frame: frame - 18 - i * per, fps, config: {damping: 13, stiffness: 160}});
          return (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: 34, marginBottom: 44, opacity: Math.min(1, s * 1.3),
              transform: `translateX(${(1 - s) * -140}px)`}}>
              <div style={{minWidth: 96, height: 96, borderRadius: 26, background: accent, color: '#111', fontFamily: 'Display',
                fontSize: 54, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{p.numbered === false ? '✓' : i + 1}</div>
              <div style={{fontFamily: 'Sans', fontSize: 64, color: '#fff', lineHeight: 1.1}}>{it}</div>
            </div>
          );
        })}
      </AbsoluteFill>
    </Background>
  );
};
