import tokensRaw from '../tokens.json';

export interface Palette {
  background: {
    base: string;
    subtle: string;
    surface: string;
    elevated: string;
    overlay: string;
  };
  border: {
    subtle: string;
    default: string;
    focus: string;
  };
  brand: {
    primary: string;
    primaryHover: string;
    primaryLight: string;
    gold: string;
    parchment: string;
    ink: string;
  };
  text: {
    primary: string;
    secondary: string;
    muted: string;
    inverse: string;
  };
  status: {
    success: string;
    warning: string;
    danger: string;
    info: string;
    suspended: string;
  };
  license: {
    publicDomain: string;
    creativeCommons: string;
    aiGenerated: string;
    restricted: string;
  };
}

export interface VideoLayoutConfig {
  width: number;
  height: number;
  fontSizeDisplay: number;
  fontSizeTitle: number;
  fontSizeBody: number;
  fontSizeAttribution: number;
  maxCharsPerLine: number;
  safeMargins: {
    top: number;
    bottom: number;
    left: number;
    right: number;
  };
}

export interface TypographyTokens {
  fonts: {
    display: string;
    sans: string;
    mono: string;
  };
  video: {
    vertical: VideoLayoutConfig;
    horizontal: VideoLayoutConfig;
  };
}

export interface PacingTokens {
  targetDurationSeconds: number;
  fps: number;
  totalFrames: number;
  wordBudget: { min: number; max: number };
  beatsBudget: { min: number; max: number };
  secondsPerBeat: { min: number; max: number };
  wordsPerBeat: { min: number; max: number };
  linesPerBeat: { min: number; max: number };
  distinctImages: { min: number; max: number };
}

export interface AudioTokens {
  targetLoudnessLufs: number;
  loudnessTolerance: number;
  keystrokeVariationMs: number;
}

export interface Tokens {
  name: string;
  version: string;
  palette: Palette;
  typography: TypographyTokens;
  pacing: PacingTokens;
  audio: AudioTokens;
}

export const tokens: Tokens = tokensRaw as Tokens;
export const palette = tokens.palette;
export const typography = tokens.typography;
export const pacing = tokens.pacing;
export const audio = tokens.audio;

export type AspectRatio = 'vertical' | 'horizontal';

export function getVideoConfig(aspectRatio: AspectRatio): VideoLayoutConfig {
  return aspectRatio === 'vertical'
    ? typography.video.vertical
    : typography.video.horizontal;
}

export function isTextWithinSafeMargins(
  text: string,
  aspectRatio: AspectRatio
): boolean {
  const config = getVideoConfig(aspectRatio);
  const lines = text.split('\n');
  return lines.every((line) => line.length <= config.maxCharsPerLine);
}
