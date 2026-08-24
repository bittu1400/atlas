import { jsx as _jsx } from "react/jsx-runtime";
import { useCurrentFrame } from 'remotion';
export const FilmGrainOverlay = () => {
    const frame = useCurrentFrame();
    const shiftX = (frame * 13) % 100;
    const shiftY = (frame * 17) % 100;
    return (_jsx("div", { style: {
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 5,
            mixBlendMode: 'overlay',
            opacity: 0.18,
            backgroundImage: `radial-gradient(circle at ${shiftX}% ${shiftY}%, rgba(255,255,255,0.4) 0%, transparent 60%), radial-gradient(circle at ${100 - shiftX}% ${100 - shiftY}%, rgba(0,0,0,0.6) 0%, transparent 70%)`,
        } }));
};
