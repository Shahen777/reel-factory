import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, useCurrentFrame} from 'remotion';
import {Base, src} from './common';

/** Background video or a dark animated gradient, plus optional music. */
export const Background: React.FC<Base & {children?: React.ReactNode}> = (p) => {
  const frame = useCurrentFrame();
  const accent = p.accent || '#ffcc00';
  const transparent = p.background === 'transparent';
  return (
    <AbsoluteFill style={{background: transparent ? 'transparent' : p.background || '#07070b'}}>
      {p.video ? (
        <OffthreadVideo src={src(p.video)} style={{width: '100%', height: '100%', objectFit: 'cover'}} muted={!!p.music} />
      ) : !transparent ? (
        <AbsoluteFill>
          <div style={{position: 'absolute', width: 1000, height: 1000, borderRadius: '50%', filter: 'blur(120px)',
            opacity: 0.35, background: accent, left: -300 + 200 * Math.sin(frame / 60), top: 150 + 250 * Math.cos(frame / 75)}} />
          <div style={{position: 'absolute', width: 1100, height: 1100, borderRadius: '50%', filter: 'blur(140px)',
            opacity: 0.3, background: '#5b3cff', left: 350 + 180 * Math.cos(frame / 70), top: 1000 + 200 * Math.sin(frame / 80)}} />
        </AbsoluteFill>
      ) : null}
      {p.music ? <Audio src={src(p.music)} volume={p.musicVolume ?? 1} /> : null}
      {p.children}
    </AbsoluteFill>
  );
};
