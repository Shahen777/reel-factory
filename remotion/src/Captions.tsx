import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Background} from './Background';
import {Base, Fonts} from './common';

export type Word = {w: string; s: number; e: number};
export type CaptionsProps = Base & {
  words: Word[]; // from `reel subtitles --srt-only` (<out>.words.json) or `reel watch` (words.json)
  wordsPerPhrase?: number;
  y?: number;
  size?: number;
  style?: 'pill' | 'pop' | 'clean';
  uppercase?: boolean;
};

const phrases = (words: Word[], n: number) => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    const gap = i > 0 ? w.s - words[i - 1].e : 0;
    if (cur.length && (cur.length >= n || gap > 0.6 || /[.!?…]$/.test(words[i - 1].w))) {
      out.push(cur);
      cur = [];
    }
    cur.push(w);
  });
  if (cur.length) out.push(cur);
  return out;
};

/** Word-by-word captions: the spoken word gets a sliding accent pill (or pops), phrases pop in. */
export const Captions: React.FC<CaptionsProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const accent = p.accent || '#ffd400';
  const ph = phrases(p.words || [], p.wordsPerPhrase ?? 3);
  // a phrase stays until the next one starts, but at most 0.5 s after its last word
  const cur = ph.find((g, i) => {
    const next = ph[i + 1]?.[0].s ?? 1e9;
    return t >= g[0].s - 0.05 && t < Math.min(next - 0.05, g[g.length - 1].e + 0.5);
  });
  const style = p.style || 'pill';
  const size = p.size ?? 78;
  return (
    <Background {...p}>
      <Fonts />
      {cur ? (
        <AbsoluteFill style={{alignItems: 'center'}}>
          <div style={{position: 'absolute', top: `${(p.y ?? 0.7) * 100}%`, transform: `translateY(-50%) scale(${0.85 + 0.15 * spring({frame: frame - Math.round(cur[0].s * fps), fps, config: {damping: 12, stiffness: 180}})})`,
            width: '82%', textAlign: 'center', fontFamily: style === 'clean' ? 'Sans' : p.font || 'Display', fontSize: size, lineHeight: 1.25,
            textTransform: p.uppercase === false || style === 'clean' ? 'none' : 'uppercase'}}>
            {cur.map((w, i) => {
              const active = t >= w.s && t < w.e + 0.05;
              const pop = spring({frame: frame - Math.round(w.s * fps), fps, config: {damping: 10, stiffness: 220}});
              const base: React.CSSProperties = {display: 'inline-block', margin: '0 0.12em', padding: '0 0.18em', borderRadius: 18,
                color: '#fff', WebkitTextStroke: style === 'clean' ? undefined : '3px rgba(0,0,0,.85)', paintOrder: 'stroke fill',
                textShadow: '0 8px 24px rgba(0,0,0,.55)'};
              if (style === 'pill' && active) Object.assign(base, {background: accent, color: '#111', WebkitTextStroke: '0px', textShadow: 'none',
                transform: `scale(${1 + 0.08 * pop})`});
              if (style === 'pop') Object.assign(base, {color: active ? accent : '#fff', transform: `scale(${active ? 1 + 0.15 * pop : 1})`});
              if (style === 'clean') Object.assign(base, {background: 'rgba(0,0,0,.55)', color: active ? accent : '#fff'});
              return <span key={i} style={base}>{w.w}</span>;
            })}
          </div>
        </AbsoluteFill>
      ) : null}
    </Background>
  );
};
