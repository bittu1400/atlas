import React, { useState, Suspense, lazy } from 'react';
import { OriginsComposition, sampleOriginsVideoProps } from '@atlas/renderer';
import { typography, pacing, AspectRatio } from '@atlas/tokens';
import { Smartphone, Monitor, Shield } from 'lucide-react';

const Player = lazy(() =>
  import('@remotion/player').then((mod) => ({ default: mod.Player }))
);

export const VideoPlayerPreview: React.FC = () => {
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('vertical');
  const [showSafeAreas, setShowSafeAreas] = useState(true);

  const config =
    aspectRatio === 'vertical'
      ? typography.video.vertical
      : typography.video.horizontal;

  return (
    <div className="bg-[#161922] border border-[#272b38] rounded-xl p-6 shadow-xl space-y-6">
      {/* Studio Header & Aspect Ratio Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#272b38] pb-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2 font-display">
            Remotion Composition Preview
            <span className="text-xs font-mono font-normal text-amber-400 bg-amber-950/60 border border-amber-800/40 px-2 py-0.5 rounded">
              ORIGINS : 60s
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Synchronous on-screen kinetic text and archival visual rendering engine
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Safe Area Toggle */}
          <button
            onClick={() => setShowSafeAreas(!showSafeAreas)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-all cursor-pointer ${
              showSafeAreas
                ? 'bg-orange-950/60 border-orange-500 text-orange-300'
                : 'bg-[#1e2230] border-[#2d3345] text-slate-400'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            Safe Margins {showSafeAreas ? 'ON' : 'OFF'}
          </button>

          {/* Aspect Ratio Switcher */}
          <div className="flex bg-[#1e2230] border border-[#2d3345] p-1 rounded-lg">
            <button
              onClick={() => setAspectRatio('vertical')}
              className={`px-3 py-1.5 text-xs font-semibold rounded flex items-center gap-1.5 transition-all cursor-pointer ${
                aspectRatio === 'vertical'
                  ? 'bg-amber-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Smartphone className="w-3.5 h-3.5" />
              9:16 Vertical
            </button>
            <button
              onClick={() => setAspectRatio('horizontal')}
              className={`px-3 py-1.5 text-xs font-semibold rounded flex items-center gap-1.5 transition-all cursor-pointer ${
                aspectRatio === 'horizontal'
                  ? 'bg-amber-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Monitor className="w-3.5 h-3.5" />
              16:9 Landscape
            </button>
          </div>
        </div>
      </div>

      {/* Main Video Viewport */}
      <div className="flex justify-center items-center bg-[#0a0b0e] border border-[#272b38] rounded-xl p-4 overflow-hidden relative min-h-[500px]">
        <div
          style={{
            width: aspectRatio === 'vertical' ? '320px' : '640px',
            aspectRatio: aspectRatio === 'vertical' ? '9/16' : '16/9',
            position: 'relative',
            borderRadius: '8px',
            overflow: 'hidden',
            boxShadow: '0 20px 50px rgba(0,0,0,0.9)',
          }}
        >
          <Suspense
            fallback={
              <div className="flex items-center justify-center w-full h-full text-slate-400 font-mono text-xs">
                Loading Studio Player...
              </div>
            }
          >
            <Player
              component={OriginsComposition as unknown as React.FC<Record<string, unknown>>}
              durationInFrames={pacing.totalFrames}
              fps={pacing.fps}
              compositionWidth={config.width}
              compositionHeight={config.height}
              style={{
                width: '100%',
                height: '100%',
              }}
              controls
              autoPlay={false}
              loop
              inputProps={{
                ...sampleOriginsVideoProps,
                aspectRatio,
              }}
            />
          </Suspense>

          {/* Safe Margins Visual Guide Overlay */}
          {showSafeAreas && (
            <div
              style={{
                position: 'absolute',
                top: `${(config.safeMargins.top / config.height) * 100}%`,
                bottom: `${(config.safeMargins.bottom / config.height) * 100}%`,
                left: `${(config.safeMargins.left / config.width) * 100}%`,
                right: `${(config.safeMargins.right / config.width) * 100}%`,
                border: '1px dashed rgba(249, 115, 22, 0.6)',
                pointerEvents: 'none',
                zIndex: 40,
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'flex-start',
                padding: '4px',
              }}
            >
              <span className="bg-orange-950/80 text-orange-400 font-mono text-[9px] px-1 rounded border border-orange-800/60">
                Safe Text Area
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Video Spec Telemetry Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="bg-[#1e2230] border border-[#2d3345] p-3 rounded-lg">
          <span className="text-slate-400 block text-[11px]">Resolution</span>
          <span className="font-bold text-white">
            {config.width} × {config.height}
          </span>
        </div>
        <div className="bg-[#1e2230] border border-[#2d3345] p-3 rounded-lg">
          <span className="text-slate-400 block text-[11px]">Frames & FPS</span>
          <span className="font-bold text-amber-400">
            {pacing.totalFrames} frames @ {pacing.fps} fps (60.0s)
          </span>
        </div>
        <div className="bg-[#1e2230] border border-[#2d3345] p-3 rounded-lg">
          <span className="text-slate-400 block text-[11px]">Loudness Target</span>
          <span className="font-bold text-emerald-400">−14.0 LUFS (±1.0)</span>
        </div>
        <div className="bg-[#1e2230] border border-[#2d3345] p-3 rounded-lg">
          <span className="text-slate-400 block text-[11px]">Captions Output</span>
          <span className="font-bold text-slate-200">WebVTT Frame-Aligned</span>
        </div>
      </div>
    </div>
  );
};
