import React from 'react';
import {staticFile, interpolate, Easing} from 'remotion';

export const FONT_CSS = `
@font-face{font-family:'Display';src:url('${staticFile('fonts/RussoOne-Regular.ttf')}');}
@font-face{font-family:'Sans';src:url('${staticFile('fonts/PTSans-Bold.ttf')}');}
`;

export const Fonts: React.FC = () => <style>{FONT_CSS}</style>;

/** A file prop may be a name inside public/ or an http(s) URL. */
export const src = (p?: string) => (!p ? undefined : /^https?:/.test(p) ? p : staticFile(p));

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const ease = (frame: number, start: number, dur: number) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

/** "*word*" marks an accent word. */
export const splitAccent = (line: string) =>
  line.split(' ').filter(Boolean).map((w) => {
    const acc = /^\*.+\*$/.test(w);
    return {text: acc ? w.slice(1, -1) : w, accent: acc};
  });

export type Base = {
  durationInSeconds?: number;
  accent?: string;
  background?: string; // css color or "transparent"
  video?: string; // background video in public/ or URL
  music?: string;
  musicVolume?: number;
  font?: string; // css font-family, default Display
};
