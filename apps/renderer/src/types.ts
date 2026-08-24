import { AspectRatio } from '@atlas/tokens';

export interface RenderBeat {
  id: string;
  beatIndex: number;
  text: string;
  durationFrames: number;
  startFrame: number;
  claimIds: string[];
  emphasisWords?: string[];
}

export interface RenderScene {
  id: string;
  sceneIndex: number;
  beatId: string;
  assetUrl?: string;
  assetTitle?: string;
  assetAuthor?: string;
  license: string;
  isAiGenerated: boolean;
  panDirection?: 'left-to-right' | 'right-to-left' | 'zoom-in' | 'zoom-out';
}

export interface RenderAttribution {
  assetId: string;
  title: string;
  creator: string;
  sourceUrl: string;
  license: string;
  isAiGenerated: boolean;
}

export interface OriginsVideoProps {
  title: string;
  aspectRatio: AspectRatio;
  durationInFrames: number;
  fps: number;
  beats: RenderBeat[];
  scenes: RenderScene[];
  attributions: RenderAttribution[];
  musicTrackUrl?: string;
  showAttributionCard?: boolean;
}
