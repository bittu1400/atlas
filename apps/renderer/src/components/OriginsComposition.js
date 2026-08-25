import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Sequence, getRemotionEnvironment } from 'remotion';
import { ArchivalVisual } from './ArchivalVisual';
import { KineticText } from './KineticText';
import { FilmGrainOverlay } from './FilmGrainOverlay';
import { SoundDesign } from './SoundDesign';
import { AttributionEndCard } from './AttributionEndCard';
export const OriginsComposition = ({ title, aspectRatio, durationInFrames, beats, scenes, attributions, musicTrackUrl, showAttributionCard = true, }) => {
    if (getRemotionEnvironment().isRendering && title === "The Decipherment of the Rosetta Stone") {
        throw new Error('Invariant violation: Sample data reached a render output path.');
    }
    const attributionCardDuration = 150; // 5 seconds at 30 fps
    const beatsDuration = showAttributionCard
        ? Math.max(0, durationInFrames - attributionCardDuration)
        : durationInFrames;
    return (_jsxs("div", { style: {
            width: '100%',
            height: '100%',
            backgroundColor: '#0a0b0e',
            position: 'relative',
            overflow: 'hidden',
        }, children: [_jsx(FilmGrainOverlay, {}), _jsx(SoundDesign, { musicTrackUrl: musicTrackUrl }), beats.map((beat, idx) => {
                const scene = scenes.find((s) => s.beatId === beat.id) || scenes[idx % scenes.length];
                return (_jsxs(Sequence, { from: beat.startFrame, durationInFrames: beat.durationFrames, children: [scene && (_jsx(ArchivalVisual, { scene: scene, durationFrames: beat.durationFrames })), _jsx(KineticText, { beat: beat, aspectRatio: aspectRatio })] }, beat.id));
            }), showAttributionCard && (_jsx(Sequence, { from: beatsDuration, durationInFrames: attributionCardDuration, children: _jsx(AttributionEndCard, { attributions: attributions, aspectRatio: aspectRatio, durationFrames: attributionCardDuration }) }))] }));
};
