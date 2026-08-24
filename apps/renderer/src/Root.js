import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { Composition } from 'remotion';
import { typography, pacing } from '@atlas/tokens';
import { OriginsComposition } from './components/OriginsComposition';
import { sampleOriginsVideoProps } from './sampleData';
export const Root = () => {
    return (_jsxs(_Fragment, { children: [_jsx(Composition, { id: "OriginsVertical", component: OriginsComposition, durationInFrames: pacing.totalFrames, fps: pacing.fps, width: typography.video.vertical.width, height: typography.video.vertical.height, defaultProps: {
                    ...sampleOriginsVideoProps,
                    aspectRatio: 'vertical',
                } }), _jsx(Composition, { id: "OriginsHorizontal", component: OriginsComposition, durationInFrames: pacing.totalFrames, fps: pacing.fps, width: typography.video.horizontal.width, height: typography.video.horizontal.height, defaultProps: {
                    ...sampleOriginsVideoProps,
                    aspectRatio: 'horizontal',
                } })] }));
};
