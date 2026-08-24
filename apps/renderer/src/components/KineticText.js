import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { interpolate, useCurrentFrame } from 'remotion';
import { getVideoConfig } from '@atlas/tokens';
export const KineticText = ({ beat, aspectRatio, }) => {
    const frame = useCurrentFrame();
    const config = getVideoConfig(aspectRatio);
    // Smooth entry and exit animations
    const opacity = interpolate(frame, [0, 10, beat.durationFrames - 10, beat.durationFrames], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    const translateY = interpolate(frame, [0, 12], [24, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    // Split text into words and highlight emphasis words
    const words = beat.text.split(' ');
    const wordsToReveal = Math.min(words.length, Math.floor(interpolate(frame, [0, Math.min(30, beat.durationFrames * 0.4)], [1, words.length], {
        extrapolateRight: 'clamp',
    })));
    return (_jsxs("div", { style: {
            position: 'absolute',
            top: config.safeMargins.top,
            bottom: config.safeMargins.bottom,
            left: config.safeMargins.left,
            right: config.safeMargins.right,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10,
            opacity,
            transform: `translateY(${translateY}px)`,
            pointerEvents: 'none',
        }, children: [_jsxs("div", { style: {
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center',
                    marginBottom: '20px',
                }, children: [_jsxs("span", { style: {
                            background: 'rgba(234, 88, 12, 0.2)',
                            border: '1px solid rgba(234, 88, 12, 0.4)',
                            color: '#fb923c',
                            fontFamily: 'Inter, sans-serif',
                            fontSize: `${Math.round(config.fontSizeAttribution * 0.9)}px`,
                            fontWeight: 700,
                            padding: '3px 10px',
                            borderRadius: '4px',
                            textTransform: 'uppercase',
                            letterSpacing: '1.5px',
                        }, children: ["BEAT ", beat.beatIndex] }), beat.claimIds.map((cid) => (_jsx("span", { style: {
                            background: 'rgba(212, 175, 55, 0.15)',
                            border: '1px solid rgba(212, 175, 55, 0.3)',
                            color: '#d4af37',
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: `${Math.round(config.fontSizeAttribution * 0.8)}px`,
                            padding: '2px 8px',
                            borderRadius: '4px',
                        }, children: cid }, cid)))] }), _jsx("div", { style: {
                    fontFamily: "'Playfair Display', Georgia, serif",
                    fontSize: `${config.fontSizeTitle}px`,
                    lineHeight: 1.25,
                    color: '#f8fafc',
                    textAlign: 'center',
                    textShadow: '0 4px 18px rgba(0,0,0,0.85)',
                    maxWidth: '100%',
                }, children: words.map((word, idx) => {
                    const isEmphasis = beat.emphasisWords?.some((ew) => word.toLowerCase().includes(ew.toLowerCase()));
                    const isVisible = idx < wordsToReveal;
                    return (_jsx("span", { style: {
                            display: 'inline-block',
                            marginRight: '10px',
                            opacity: isVisible ? 1 : 0.1,
                            transform: isVisible ? 'scale(1)' : 'scale(0.95)',
                            transition: 'opacity 0.1s, transform 0.1s',
                            color: isEmphasis ? '#d4af37' : '#f8fafc',
                            fontWeight: isEmphasis ? 700 : 500,
                        }, children: word }, `${word}-${idx}`));
                }) })] }));
};
