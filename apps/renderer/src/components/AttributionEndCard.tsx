import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { AspectRatio, getVideoConfig } from '@atlas/tokens';
import { RenderAttribution } from '../types';

interface AttributionEndCardProps {
  attributions: RenderAttribution[];
  aspectRatio: AspectRatio;
  durationFrames?: number;
}

export const AttributionEndCard: React.FC<AttributionEndCardProps> = ({
  attributions,
  aspectRatio,
}) => {
  const frame = useCurrentFrame();
  const config = getVideoConfig(aspectRatio);

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const hasAi = attributions.some((a) => a.isAiGenerated);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 11, 14, 0.96)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px',
        opacity,
        zIndex: 20,
      }}
    >
      <div
        style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: `${config.fontSizeTitle}px`,
          color: '#d4af37',
          marginBottom: '16px',
          letterSpacing: '1px',
        }}
      >
        Atlas : Origins
      </div>
      <div
        style={{
          color: '#94a3b8',
          fontSize: `${config.fontSizeAttribution}px`,
          fontFamily: 'Inter, sans-serif',
          marginBottom: '32px',
          textAlign: 'center',
        }}
      >
        Verified Primary Archival Sources & Provenance
      </div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          maxWidth: '85%',
        }}
      >
        {attributions.map((attr) => (
          <div
            key={attr.assetId}
            style={{
              background: 'rgba(22, 25, 34, 0.8)',
              border: '1px solid #2d3345',
              padding: '12px 18px',
              borderRadius: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div
                style={{
                  color: '#f8fafc',
                  fontSize: `${config.fontSizeAttribution}px`,
                  fontWeight: 600,
                  fontFamily: 'Inter, sans-serif',
                }}
              >
                {attr.title}
              </div>
              <div
                style={{
                  color: '#64748b',
                  fontSize: `${Math.round(config.fontSizeAttribution * 0.85)}px`,
                }}
              >
                {attr.creator}
              </div>
            </div>
            <span
              style={{
                color: attr.isAiGenerated ? '#f59e0b' : '#10b981',
                fontSize: `${Math.round(config.fontSizeAttribution * 0.85)}px`,
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 600,
              }}
            >
              {attr.license}
            </span>
          </div>
        ))}
      </div>

      {hasAi && (
        <div
          style={{
            marginTop: '24px',
            color: '#f59e0b',
            fontSize: '13px',
            fontFamily: 'Inter, sans-serif',
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            padding: '6px 14px',
            borderRadius: '4px',
          }}
        >
          ✦ Contains AI-generated imagery (Human-approved per Invariant 9)
        </div>
      )}
    </div>
  );
};
