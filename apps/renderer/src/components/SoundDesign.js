import { jsx as _jsx } from "react/jsx-runtime";
export const SoundDesign = ({ musicTrackUrl }) => {
    // In Remotion, audio can be played using <Audio src={...} /> or Web Audio API.
    // When no remote file is provided, it operates in simulated silent mode with volume tags.
    if (!musicTrackUrl) {
        return null;
    }
    return (_jsx("div", { style: { display: 'none' } }));
};
