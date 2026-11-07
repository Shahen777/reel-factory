import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {Background} from './Background';
import {Base, Fonts, ease} from './common';

export type TextRevealProps = Base & {
  kicker?: string; // small line above
  title: string;
  subtitle?: string;
  size?: number;
  y?: number;
};

/** Premium title card: a line draws, the title is unmasked from below, tracking settles, subtitle fades up. */
export const TextReveal: React.FC<TextRevealProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const accent = p.accent || '#ffcc00';
  const line = ease(frame, 4, 18);
  const title = ease(frame, 12, 22);
  const sub = ease(frame, 28, 18);
  const kick = ease(frame, 0, 14);
  const out = interpolate(frame, [durationInFrames - 12, durationInFrames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic)});
  const size = p.size ?? 140;
  return (
    <Background {...p}>
      <Fonts />
      <AbsoluteFill style={{alignItems: 'center', opacity: 1 - out, transform: `scale(${1 + out * 0.04})`}}>
        <div style={{position: 'absolute', top: `${(p.y ?? 0.45) * 100}%`, transform: 'translateY(-50%)', width: '86%', textAlign: 'center'}}>
          {p.kicker ? (
            <div style={{fontFamily: 'Sans', fontSize: 40, letterSpacing: 10, color: accent, textTransform: 'uppercase', opacity: kick,
              transform: `translateY(${(1 - kick) * 20}px)`, marginBottom: 26}}>{p.kicker}</div>
          ) : null}
          <div style={{overflow: 'hidden', paddingBottom: 8}}>
            <div style={{fontFamily: p.font || 'Display', fontSize: size, lineHeight: 1.02, color: '#fff', textTransform: 'uppercase',
              letterSpacing: interpolate(title, [0, 1], [30, 2]), transform: `translateY(${(1 - title) * 110}%)`,
              textShadow: '0 14px 40px rgba(0,0,0,.5)'}}>{p.title}</div>
          </div>
          <div style={{height: 8, margin: '26px auto 0', width: `${line * 46}%`, background: accent, borderRadius: 4,
            boxShadow: `0 0 30px ${accent}`}} />
          {p.subtitle ? (
            <div style={{fontFamily: 'Sans', fontSize: 52, color: '#d9dbe6', marginTop: 30, opacity: sub,
              transform: `translateY(${(1 - sub) * 30}px)`, filter: `blur(${(1 - sub) * 6}px)`}}>{p.subtitle}</div>
          ) : null}
        </div>
      </AbsoluteFill>
    </Background>
  );
};
