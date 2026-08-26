"""Audio adapters."""

from .compositor import AudioCompositor
from .freesound import FreesoundLibrary
from .keystroke_sampler import KeystrokeModifier, KeystrokeSampler

__all__ = [
    "FreesoundLibrary",
    "KeystrokeSampler",
    "KeystrokeModifier",
    "AudioCompositor",
]
