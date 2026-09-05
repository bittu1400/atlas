import { OriginsVideoProps } from './types';

// Layout fixture for `remotion preview`, and nothing else.
//
// It carries the SHAPE of a video — beat count, frame arithmetic, scene pairing,
// attribution rows — and no content. Rule R4: a fixture must never read as a
// fact. This file previously held eleven beats of Rosetta Stone history, with
// claim IDs and named archives attached, and the operator dashboard rendered it
// in a panel labelled "rendering engine". A fixture that reads like a fact is
// exactly how the 2026-08-29 incident put invented history in front of a human.
//
// The Python-side guard (`test_guard_7_no_plausible_history_in_fakes`) parses
// Python only; `tests/unit/test_no_fabrication.py` now scans this file too.

export const sampleOriginsVideoProps: OriginsVideoProps = {
  title: "PLACEHOLDER_TITLE — layout fixture, not a video",
  aspectRatio: "vertical",
  durationInFrames: 720,
  fps: 30,
  beats: [
    {
      id: "beat-01",
      beatIndex: 1,
      text: "PLACEHOLDER_BEAT_01: SUBJECT_01 was recorded by SOURCE_01.",
      startFrame: 0,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_01"],
      emphasisWords: ["SUBJECT_01"]
    },
    {
      id: "beat-02",
      beatIndex: 2,
      text: "PLACEHOLDER_BEAT_02: SUBJECT_02 was recorded by SOURCE_02.",
      startFrame: 120,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_02"],
      emphasisWords: ["SUBJECT_02"]
    },
    {
      id: "beat-03",
      beatIndex: 3,
      text: "PLACEHOLDER_BEAT_03: SUBJECT_03 was recorded by SOURCE_03.",
      startFrame: 240,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_03"],
      emphasisWords: ["SUBJECT_03"]
    },
    {
      id: "beat-04",
      beatIndex: 4,
      text: "PLACEHOLDER_BEAT_04: SUBJECT_04 was recorded by SOURCE_04.",
      startFrame: 360,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_04"],
      emphasisWords: ["SUBJECT_04"]
    },
    {
      id: "beat-05",
      beatIndex: 5,
      text: "PLACEHOLDER_BEAT_05: SUBJECT_05 was recorded by SOURCE_05.",
      startFrame: 480,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_05"],
      emphasisWords: ["SUBJECT_05"]
    },
    {
      id: "beat-06",
      beatIndex: 6,
      text: "PLACEHOLDER_BEAT_06: SUBJECT_06 was recorded by SOURCE_06.",
      startFrame: 600,
      durationFrames: 120,
      claimIds: ["PLACEHOLDER_CLAIM_06"],
      emphasisWords: ["SUBJECT_06"]
    }
  ],
  scenes: [
    {
      id: "scene-01",
      sceneIndex: 1,
      beatId: "beat-01",
      assetTitle: "PLACEHOLDER_ASSET_01",
      assetAuthor: "PLACEHOLDER_CREATOR_01",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-in"
    },
    {
      id: "scene-02",
      sceneIndex: 2,
      beatId: "beat-02",
      assetTitle: "PLACEHOLDER_ASSET_02",
      assetAuthor: "PLACEHOLDER_CREATOR_02",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-out"
    },
    {
      id: "scene-03",
      sceneIndex: 3,
      beatId: "beat-03",
      assetTitle: "PLACEHOLDER_ASSET_03",
      assetAuthor: "PLACEHOLDER_CREATOR_03",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-in"
    },
    {
      id: "scene-04",
      sceneIndex: 4,
      beatId: "beat-04",
      assetTitle: "PLACEHOLDER_ASSET_04",
      assetAuthor: "PLACEHOLDER_CREATOR_04",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-out"
    },
    {
      id: "scene-05",
      sceneIndex: 5,
      beatId: "beat-05",
      assetTitle: "PLACEHOLDER_ASSET_05",
      assetAuthor: "PLACEHOLDER_CREATOR_05",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-in"
    },
    {
      id: "scene-06",
      sceneIndex: 6,
      beatId: "beat-06",
      assetTitle: "PLACEHOLDER_ASSET_06",
      assetAuthor: "PLACEHOLDER_CREATOR_06",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false,
      panDirection: "zoom-out"
    }
  ],
  attributions: [
    {
      assetId: "PLACEHOLDER_ASSET_01",
      title: "PLACEHOLDER_ASSET_01",
      creator: "PLACEHOLDER_CREATOR_01",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_01",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    },
    {
      assetId: "PLACEHOLDER_ASSET_02",
      title: "PLACEHOLDER_ASSET_02",
      creator: "PLACEHOLDER_CREATOR_02",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_02",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    },
    {
      assetId: "PLACEHOLDER_ASSET_03",
      title: "PLACEHOLDER_ASSET_03",
      creator: "PLACEHOLDER_CREATOR_03",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_03",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    },
    {
      assetId: "PLACEHOLDER_ASSET_04",
      title: "PLACEHOLDER_ASSET_04",
      creator: "PLACEHOLDER_CREATOR_04",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_04",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    },
    {
      assetId: "PLACEHOLDER_ASSET_05",
      title: "PLACEHOLDER_ASSET_05",
      creator: "PLACEHOLDER_CREATOR_05",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_05",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    },
    {
      assetId: "PLACEHOLDER_ASSET_06",
      title: "PLACEHOLDER_ASSET_06",
      creator: "PLACEHOLDER_CREATOR_06",
      sourceUrl: "https://example.invalid/PLACEHOLDER_ASSET_06",
      license: "PLACEHOLDER_LICENSE",
      isAiGenerated: false
    }
  ],
  showAttributionCard: true
};
