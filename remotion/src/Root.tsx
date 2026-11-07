import React from 'react';
import {Composition, CalculateMetadataFunction} from 'remotion';
import {KineticTitle} from './KineticTitle';
import {Captions} from './Captions';
import {TextReveal} from './TextReveal';
import {ListStack} from './ListStack';

const FPS = 30;
// duration comes from props.durationInSeconds, or a sensible default per composition
const meta = (fallback: (p: any) => number): CalculateMetadataFunction<any> => ({props}) => ({
  durationInFrames: Math.max(1, Math.round((props.durationInSeconds ?? fallback(props)) * FPS)),
});

const common = {fps: FPS, width: 1080, height: 1920, durationInFrames: 150};

export const Root: React.FC = () => (
  <>
    <Composition id="KineticTitle" component={KineticTitle as any} {...common}
      defaultProps={{lines: ['MAKE IT', '*MOVE*', 'ON THE BEAT'], perLine: 1.6}}
      calculateMetadata={meta((p) => (p.lines?.length || 1) * (p.perLine ?? 1.6) + 0.6)} />
    <Composition id="Captions" component={Captions as any} {...common}
      defaultProps={{words: [{w: 'Words', s: 0.2, e: 0.6}, {w: 'light', s: 0.6, e: 1.0}, {w: 'up', s: 1.0, e: 1.3},
        {w: 'as', s: 1.5, e: 1.7}, {w: 'you', s: 1.7, e: 1.9}, {w: 'speak', s: 1.9, e: 2.5}], style: 'pill'}}
      calculateMetadata={meta((p) => (p.words?.length ? p.words[p.words.length - 1].e + 0.6 : 3))} />
    <Composition id="TextReveal" component={TextReveal as any} {...common}
      defaultProps={{kicker: 'New collection', title: 'Autumn 26', subtitle: 'Available from Friday'}}
      calculateMetadata={meta(() => 4)} />
    <Composition id="ListStack" component={ListStack as any} {...common}
      defaultProps={{title: '3 rules of a good hook', items: ['Motion in frame 1', 'Text in 3–7 words', 'Promise you keep']}}
      calculateMetadata={meta((p) => 1 + (p.items?.length || 1) * (p.perItem ?? 1.2) + 1.2)} />
  </>
);
