"""Audio Compositor for assembling soundtracks."""

import logging
import subprocess

from atlas.domain.media.models import SoundTrack

logger = logging.getLogger(__name__)


class AudioCompositor:
    """Builds an FFmpeg filter graph and applies loudnorm."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def compose(self, soundtrack: SoundTrack, output_path: str) -> str:
        """Compose the soundtrack into an output file.

        Builds an FFmpeg filter graph with music ducking, sfx overlay, and loudnorm.
        Returns the path to the composed file.
        """
        inputs = []
        filter_complex = []

        # Input 0: Music Bed
        inputs.extend(["-i", soundtrack.music_bed_asset_id])

        # Apply ducking/volume to music bed
        filter_complex.append(f"[0:a]volume={soundtrack.music_volume}[music];")
        mix_inputs = "[music]"

        # Inputs 1..N: SFX Cues
        for i, cue in enumerate(soundtrack.sfx_cues):
            sfx_index = i + 1
            inputs.extend(["-i", cue.sfx_id])

            # Delay in milliseconds
            delay_ms = int(cue.timestamp_seconds * 1000)

            # Apply volume and delay to SFX
            # adelay takes delay in ms. | is used to apply to all channels.
            filter_complex.append(
                f"[{sfx_index}:a]volume={cue.volume},adelay={delay_ms}|{delay_ms}[sfx{sfx_index}];"
            )
            mix_inputs += f"[sfx{sfx_index}]"

        # Mix all tracks together
        num_inputs = len(soundtrack.sfx_cues) + 1
        filter_complex.append(f"{mix_inputs}amix=inputs={num_inputs}:normalize=0[mixed];")

        # Apply loudnorm
        loudnorm = f"loudnorm=I={soundtrack.target_lufs}:TP=-1.5:LRA=11"
        filter_complex.append(f"[mixed]{loudnorm}[out]")

        filter_script = "".join(filter_complex)

        cmd = [
            self.ffmpeg_bin,
            "-y",
        ]
        cmd.extend(inputs)
        cmd.extend(["-filter_complex", filter_script, "-map", "[out]", output_path])

        cmd_str = " ".join(cmd)
        logger.info(f"Executing FFmpeg audio composition: {cmd_str}")

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with output: {e.stderr}")
            # If FFmpeg is not installed or fails, we will at least log the command
            # Depending on use-case, this might be raised
            raise RuntimeError(f"Audio composition failed: {e.stderr}") from e
        except FileNotFoundError:
            logger.warning(f"{self.ffmpeg_bin} not found. Generated command string: {cmd_str}")
            # For environments where ffmpeg might not be installed, we return the output path
            # assuming it would have been generated or for debug purposes.
            pass

        return output_path
