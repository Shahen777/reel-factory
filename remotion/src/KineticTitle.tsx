import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {Background} from './Background';
import {Base, Fonts, splitAccent} from './common';

export type KineticTitleProps = Base & {
  lines: string[]; // "*word*" = accent colour
  perLine?: number; // seconds per line
  size?: number;
  y?: number; // 0..1 vertical centre
  uppercase?: boolean;
  gradient?: boolean; // white -> cream fill
};

/** Letters rise with a springy overshoot, line after line; the previous line flies up and blurs out. */
export const KineticTitle: React.FC<KineticTitleProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const per = Math.round((p.perLine ?? 1.6) * fps);
  const i = Math.min(p.lines.length - 1, Math.floor(frame / per));
  const local = frame - i * per;
  const isLast = i === p.lines.length - 1;
  const outP = isLast ? 0 : interpolate(local, [per - 8, per], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const words = splitAccent(p.lines[i]);
  const accent = p.accent || '#ffcc00';
  const size = p.size ?? 150;
  let letter = 0;
  return (
    <Background {...p}>
      <Fonts />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'absolute', top: `${(p.y ?? 0.45) * 100}%`, transform: `translateY(-50%) translateY(${-outP * 80}px)`,
          width: '84%', textAlign: 'center', fontFamily: p.font || 'Display', fontSize: size, lineHeight: 1.04,
          textTransform: p.uppercase === false ? 'none' : 'uppercase', opacity: 1 - outP, filter: `blur(${outP * 10}px)`}}>
          {words.map((w, wi) => (
            <span key={wi} style={{display: 'inline-block', margin: '0 0.14em', whiteSpace: 'nowrap'}}>
              {w.text.split('').map((ch, ci) => {
                const delay = letter++ * 1.6;
                const s = spring({frame: local - delay, fps, config: {damping: 11, stiffness: 140, mass: 0.6}});
                const color = w.accent ? accent : '#ffffff';
                return (
                  <span key={ci} style={{display: 'inline-block', transform: `translateY(${(1 - s) * 120}px) scale(${0.6 + 0.4 * s})`,
                    opacity: Math.min(1, s * 1.4),
                    ...(p.gradient !== false && !w.accent
                      ? {background: 'linear-gradient(180deg,#ffffff 45%,#ffeccc 100%)', WebkitBackgroundClip: 'text', color: 'transparent'}
                      : {color}),
                    // drop-shadow, not text-shadow: text-shadow shows through gradient-clipped letters and greys them
                    filter: w.accent ? `drop-shadow(0 0 24px ${accent}99)` : 'drop-shadow(0 10px 22px rgba(0,0,0,.5))'}}>
                    {ch}
                  </span>
                );
              })}
            </span>
          ))}
        </div>
      </AbsoluteFill>
    </Background>
  );
};
