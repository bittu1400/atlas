import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { interpolate, useCurrentFrame } from 'remotion';
export const ArchivalVisual = ({ scene, durationFrames, }) => {
    const frame = useCurrentFrame();
    // Ken Burns subtle pan/zoom effect
    const scale = interpolate(frame, [0, durationFrames], scene.panDirection === 'zoom-out' ? [1.12, 1.0] : [1.0, 1.12], { extrapolateRight: 'clamp' });
    const translateX = interpolate(frame, [0, durationFrames], scene.panDirection === 'left-to-right'
        ? [-20, 20]
        : scene.panDirection === 'right-to-left'
            ? [20, -20]
            : [0, 0], { extrapolateRight: 'clamp' });
    return (_jsxs("div", { style: {
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            overflow: 'hidden',
            backgroundColor: '#0a0b0e',
        }, children: [_jsx("div", { style: {
                    width: '100%',
                    height: '100%',
                    transform: `scale(${scale}) translate(${translateX}px, 0px)`,
                    transformOrigin: 'center center',
                    background: `
            radial-gradient(ellipse at center, rgba(30, 25, 20, 0.7) 0%, rgba(10, 11, 14, 0.95) 85%),
            linear-gradient(135deg, #1c1917 0%, #0f172a 50%, #171717 100%)
          `,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '40px',
                }, children: _jsxs("div", { style: {
                        border: '1px solid rgba(212, 175, 55, 0.3)',
                        borderRadius: '8px',
                        padding: '24px',
                        maxWidth: '80%',
                        background: 'rgba(16, 18, 23, 0.65)',
                        backdropFilter: 'blur(4px)',
                        textAlign: 'center',
                    }, children: [_jsx("div", { style: {
                                color: '#d4af37',
                                fontSize: '14px',
                                letterSpacing: '3px',
                                textTransform: 'uppercase',
                                marginBottom: '10px',
                                fontFamily: 'Inter, sans-serif',
                            }, children: scene.isAiGenerated ? '✦ Synthetic Asset' : '🏛 Primary Archive' }), _jsx("div", { style: {
                                color: '#f8fafc',
                                fontSize: '18px',
                                fontWeight: 600,
                                fontFamily: "'Playfair Display', Georgia, serif",
                                marginBottom: '6px',
                            }, children: scene.assetTitle || 'Archival Plate' }), _jsxs("div", { style: {
                                color: '#94a3b8',
                                fontSize: '12px',
                                fontFamily: 'Inter, sans-serif',
                            }, children: [scene.assetAuthor, " \u2022 ", scene.license] })] }) }), _jsx("div", { style: {
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none',
                    boxShadow: 'inset 0 0 160px rgba(0, 0, 0, 0.85)',
                } })] }));
};
