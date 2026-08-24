export const sampleOriginsVideoProps = {
    title: "The Decipherment of the Rosetta Stone",
    aspectRatio: "vertical",
    durationInFrames: 1800, // 60 seconds at 30 fps
    fps: 30,
    beats: [
        {
            id: "beat-1",
            beatIndex: 1,
            text: "July 1799. French soldiers uncover a granodiorite slab near Rashid.",
            startFrame: 0,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-001"],
            emphasisWords: ["1799", "granodiorite slab"]
        },
        {
            id: "beat-2",
            beatIndex: 2,
            text: "Carved with three scripts: Ancient Greek, Demotic, and Egyptian Hieroglyphs.",
            startFrame: 120,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-002"],
            emphasisWords: ["three scripts"]
        },
        {
            id: "beat-3",
            beatIndex: 3,
            text: "For fourteen centuries, hieroglyphs were thought to be pure mystical symbols.",
            startFrame: 240,
            durationFrames: 135, // 4.5s
            claimIds: ["CLM-003"],
            emphasisWords: ["fourteen centuries"]
        },
        {
            id: "beat-4",
            beatIndex: 4,
            text: "Thomas Young notices royal names are enclosed inside oval loops called cartouches.",
            startFrame: 375,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-004"],
            emphasisWords: ["cartouches"]
        },
        {
            id: "beat-5",
            beatIndex: 5,
            text: "He isolates the letters for 'Ptolemy' — proving hieroglyphs spell phonetic sounds.",
            startFrame: 495,
            durationFrames: 135, // 4.5s
            claimIds: ["CLM-005"],
            emphasisWords: ["Ptolemy", "phonetic sounds"]
        },
        {
            id: "beat-6",
            beatIndex: 6,
            text: "1822. Jean-François Champollion receives copies of the Abu Simbel inscriptions.",
            startFrame: 630,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-006"],
            emphasisWords: ["1822", "Champollion"]
        },
        {
            id: "beat-7",
            beatIndex: 7,
            text: "He recognizes the cartouche of 'Ramesses' from the Coptic word for sun: 'Ra'.",
            startFrame: 750,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-007"],
            emphasisWords: ["Ramesses", "Ra"]
        },
        {
            id: "beat-8",
            beatIndex: 8,
            text: "He sprints into the Académie des Inscriptions, shouts 'Je tiens mon affaire!', and collapses.",
            startFrame: 870,
            durationFrames: 135, // 4.5s
            claimIds: ["CLM-008"],
            emphasisWords: ["Je tiens mon affaire!"]
        },
        {
            id: "beat-9",
            beatIndex: 9,
            text: "Hieroglyphs were not silent pictures. They were a spoken alphabet.",
            startFrame: 1005,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-009"],
            emphasisWords: ["spoken alphabet"]
        },
        {
            id: "beat-10",
            beatIndex: 10,
            text: "Three millennia of lost Egyptian history unlocked in a single moment.",
            startFrame: 1125,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-010"],
            emphasisWords: ["Three millennia"]
        },
        {
            id: "beat-11",
            beatIndex: 11,
            text: "Every primary source verified. Deciphered through evidence.",
            startFrame: 1245,
            durationFrames: 120, // 4.0s
            claimIds: ["CLM-011"],
            emphasisWords: ["verified", "evidence"]
        }
    ],
    scenes: [
        {
            id: "scene-1",
            sceneIndex: 1,
            beatId: "beat-1",
            assetTitle: "Rosetta Stone granodiorite slab",
            assetAuthor: "British Museum Collection (Archival Scan)",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-in"
        },
        {
            id: "scene-2",
            sceneIndex: 2,
            beatId: "beat-2",
            assetTitle: "Close-up of Greek and Demotic inscriptions",
            assetAuthor: "Wikimedia Commons / CC-Zero Archive",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "left-to-right"
        },
        {
            id: "scene-3",
            sceneIndex: 3,
            beatId: "beat-3",
            assetTitle: "Horapollo Hieroglyphica 1505 Woodcut",
            assetAuthor: "Bibliothèque nationale de France",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-out"
        },
        {
            id: "scene-4",
            sceneIndex: 4,
            beatId: "beat-4",
            assetTitle: "Ptolemy Cartouche diagram, Thomas Young 1814",
            assetAuthor: "Royal Society Philosophical Transactions",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-in"
        },
        {
            id: "scene-5",
            sceneIndex: 5,
            beatId: "beat-5",
            assetTitle: "Phonetic alphabet table comparison",
            assetAuthor: "Library of Congress Rare Book Division",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "right-to-left"
        },
        {
            id: "scene-6",
            sceneIndex: 6,
            beatId: "beat-6",
            assetTitle: "Portrait of Jean-François Champollion by Léon Cogniet (1831)",
            assetAuthor: "Musée du Louvre, Paris",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-in"
        },
        {
            id: "scene-7",
            sceneIndex: 7,
            beatId: "beat-7",
            assetTitle: "Abu Simbel Temple Wall Rubbing",
            assetAuthor: "Egyptian Antiquities Service Archival Plate",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "left-to-right"
        },
        {
            id: "scene-8",
            sceneIndex: 8,
            beatId: "beat-8",
            assetTitle: "Lettre à M. Dacier, original publication 1822",
            assetAuthor: "Firmin Didot Père et Fils",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-out"
        },
        {
            id: "scene-9",
            sceneIndex: 9,
            beatId: "beat-9",
            assetTitle: "Hieroglyphic alphabet chart by Champollion",
            assetAuthor: "Grammaire égyptienne (1836)",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-in"
        },
        {
            id: "scene-10",
            sceneIndex: 10,
            beatId: "beat-10",
            assetTitle: "Karnak Hypostyle Hall early archival photograph",
            assetAuthor: "Francis Frith (1857)",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "right-to-left"
        },
        {
            id: "scene-11",
            sceneIndex: 11,
            beatId: "beat-11",
            assetTitle: "Rosetta Stone full context",
            assetAuthor: "Public Domain Reference",
            license: "Public Domain",
            isAiGenerated: false,
            panDirection: "zoom-out"
        }
    ],
    attributions: [
        {
            assetId: "ast-1",
            title: "Rosetta Stone Granodiorite Plate",
            creator: "British Museum / Wikimedia Commons",
            sourceUrl: "https://commons.wikimedia.org/wiki/File:Rosetta_Stone.jpg",
            license: "Public Domain (PDM)",
            isAiGenerated: false
        },
        {
            assetId: "ast-2",
            title: "Portrait of Jean-François Champollion",
            creator: "Léon Cogniet (1831) / Musée du Louvre",
            sourceUrl: "https://commons.wikimedia.org/wiki/File:Champollion.jpg",
            license: "Public Domain (PDM)",
            isAiGenerated: false
        },
        {
            assetId: "ast-3",
            title: "Grammaire égyptienne original plates",
            creator: "Champollion (1836) / BnF Gallica",
            sourceUrl: "https://gallica.bnf.fr/ark:/12148/bpt6k10508535",
            license: "Public Domain",
            isAiGenerated: false
        }
    ],
    showAttributionCard: true
};
