"""Sampler for generating varied keystroke sound effects."""

import random
from typing import TypedDict


class KeystrokeModifier(TypedDict):
    """Struct describing modifiers for a selected keystroke sample."""

    sample_path: str
    volume_modifier: float
    pitch_modifier: float


class KeystrokeSampler:
    """Maintains a pool of distinct CC0 keystroke samples and provides randomized selection."""

    def __init__(self, samples: list[str]):
        """Initialize with at least 5 distinct CC0 keystroke sample paths/URLs."""
        if len(samples) < 5:
            raise ValueError("Must provide at least 5 distinct keystroke samples.")
        self.samples = samples
        self._last_sample = None

    def get_sample(self) -> KeystrokeModifier:
        """Select a sample non-consecutively with randomized velocity and pitch/timbre."""
        # Ensure non-consecutive selection
        available_samples = [s for s in self.samples if s != self._last_sample]

        # Fallback if only one sample was available (shouldn't happen with >= 5, but good practice)
        if not available_samples:
            available_samples = self.samples

        selected_sample = random.choice(available_samples)
        self._last_sample = selected_sample

        # Randomized velocity (±15%) -> 0.85 to 1.15
        velocity = 1.0 + random.uniform(-0.15, 0.15)

        # Randomized pitch/timbre shift (±5%) -> 0.95 to 1.05
        pitch = 1.0 + random.uniform(-0.05, 0.05)

        return KeystrokeModifier(
            sample_path=selected_sample, volume_modifier=velocity, pitch_modifier=pitch
        )
