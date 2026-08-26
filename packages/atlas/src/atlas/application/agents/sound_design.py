from atlas.application.ports.media import SoundLibrary
from atlas.domain.media.models import SfxCue, SoundTrack
from atlas.domain.script.models import TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id


class SoundDesignAgent:
    """Agent that creates a complete audio composition plan."""

    def __init__(self, sound_library: SoundLibrary) -> None:
        self.sound_library = sound_library

    async def compose(
        self, storyboard_id: str, timing_plan: TimingPlan, mood: str = "ambient"
    ) -> SoundTrack:
        """Generate SFX cues and select a music bed based on the TimingPlan."""
        music_bed = await self.sound_library.get_music_bed(mood)

        sfx_cues: list[SfxCue] = []

        for bt in timing_plan.beat_timings:
            # Add keystroke sound at the start of each text beat
            keystroke = await self.sound_library.get_sfx("keystroke")
            sfx_cues.append(
                SfxCue(
                    sfx_id=keystroke.id,
                    timestamp_seconds=bt.start_time_seconds,
                    volume=0.8,
                    cue_type="keystroke",
                )
            )

            # Add a transition whoosh at the end of the beat (if it's not the very end of the video)
            if bt.end_time_seconds < timing_plan.total_duration_seconds - 0.5:
                whoosh = await self.sound_library.get_sfx("transition")
                sfx_cues.append(
                    SfxCue(
                        sfx_id=whoosh.id,
                        timestamp_seconds=bt.end_time_seconds,
                        volume=0.5,
                        cue_type="transition",
                    )
                )

        return SoundTrack(
            id=generate_id("snd"),
            storyboard_id=storyboard_id,
            music_bed_asset_id=music_bed.id,
            music_volume=0.25,
            sfx_cues=sfx_cues,
            target_lufs=-14.0,
            created_at=utc_now(),
        )
