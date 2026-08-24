import React from 'react';
import { Composition } from 'remotion';
import { typography, pacing } from '@atlas/tokens';
import { OriginsComposition } from './components/OriginsComposition';
import { sampleOriginsVideoProps } from './sampleData';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="OriginsVertical"
        component={OriginsComposition as unknown as React.FC<Record<string, unknown>>}
        durationInFrames={pacing.totalFrames}
        fps={pacing.fps}
        width={typography.video.vertical.width}
        height={typography.video.vertical.height}
        defaultProps={{
          ...sampleOriginsVideoProps,
          aspectRatio: 'vertical',
        }}
      />
      <Composition
        id="OriginsHorizontal"
        component={OriginsComposition as unknown as React.FC<Record<string, unknown>>}
        durationInFrames={pacing.totalFrames}
        fps={pacing.fps}
        width={typography.video.horizontal.width}
        height={typography.video.horizontal.height}
        defaultProps={{
          ...sampleOriginsVideoProps,
          aspectRatio: 'horizontal',
        }}
      />
    </>
  );
};
