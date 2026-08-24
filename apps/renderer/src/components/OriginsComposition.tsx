import React from 'react';
import { Sequence } from 'remotion';
import { OriginsVideoProps } from '../types';
import { ArchivalVisual } from './ArchivalVisual';
import { KineticText } from './KineticText';
import { FilmGrainOverlay } from './FilmGrainOverlay';
import { SoundDesign } from './SoundDesign';
import { AttributionEndCard } from './AttributionEndCard';

export const OriginsComposition: React.FC<OriginsVideoProps> = ({
  aspectRatio,
  durationInFrames,
  beats,
  scenes,
  attributions,
  musicTrackUrl,
  showAttributionCard = true,
}) => {
  const attributionCardDuration = 150; // 5 seconds at 30 fps
  const beatsDuration = showAttributionCard
    ? Math.max(0, durationInFrames - attributionCardDuration)
    : durationInFrames;

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#0a0b0e',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <FilmGrainOverlay />
      <SoundDesign musicTrackUrl={musicTrackUrl} />

      {/* Render each Beat and its associated Scene */}
      {beats.map((beat, idx) => {
        const scene = scenes.find((s) => s.beatId === beat.id) || scenes[idx % scenes.length];

        return (
          <Sequence
            key={beat.id}
            from={beat.startFrame}
            durationInFrames={beat.durationFrames}
          >
            {scene && (
              <ArchivalVisual
                scene={scene}
                durationFrames={beat.durationFrames}
              />
            )}
            <KineticText beat={beat} aspectRatio={aspectRatio} />
          </Sequence>
        );
      })}

      {/* Optional Attribution End Card */}
      {showAttributionCard && (
        <Sequence
          from={beatsDuration}
          durationInFrames={attributionCardDuration}
        >
          <AttributionEndCard
            attributions={attributions}
            aspectRatio={aspectRatio}
            durationFrames={attributionCardDuration}
          />
        </Sequence>
      )}
    </div>
  );
};
