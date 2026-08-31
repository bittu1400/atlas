"""Stub renderer.

Rule R3: this stub does not wear the name of the thing it is standing in for.
No Remotion composition is mounted and no node process is spawned — the frames
are a flat ffmpeg colour field. The real renderer is deferred (D57), and
`docs/STATUS.md` says rendering does not exist.

What is real here is the *shape* of the output: the WebVTT captions come from
the persisted TimingPlan, the duration comes from that plan, and the frame size
follows the requested RenderTarget, so a downstream consumer sees a correctly
described artifact rather than a silently vertical one.
"""

import os
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime

from atlas.application.ports.renderer import Renderer
from atlas.application.ports.storage import Storage
from atlas.domain.media.models import RenderArtifact, RenderTarget, Storyboard
from atlas.domain.script.models import TimingPlan
from atlas.platform.logging import get_logger

logger = get_logger("adapters.renderer.stub")

# 9:16 and 16:9 at the resolutions packages/tokens declares.
TARGET_RESOLUTIONS: dict[RenderTarget, tuple[int, int]] = {
    RenderTarget.VERTICAL: (1080, 1920),
    RenderTarget.HORIZONTAL: (1920, 1080),
}


def format_timestamp(seconds: float) -> str:
    """Format seconds as WebVTT timestamp HH:MM:SS.mmm"""
    total_millis = int(round(seconds * 1000))
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def generate_webvtt(timing_plan: TimingPlan) -> str:
    """Generate WebVTT string from TimingPlan caption cues."""
    lines = ["WEBVTT", ""]
    for cue in timing_plan.caption_cues:
        start = format_timestamp(cue.start_seconds)
        end = format_timestamp(cue.end_seconds)
        lines.append(f"{start} --> {end}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


class StubRenderer(Renderer):
    """Produces a placeholder MP4 plus real captions from the persisted TimingPlan."""

    def __init__(self, storage: Storage):
        self.storage = storage

    async def render(
        self,
        storyboard: Storyboard,
        timing_plan: TimingPlan,
        target: RenderTarget,
        run_id: str,
    ) -> RenderArtifact:
        """Render a single aspect ratio target from storyboard and timing plan."""
        webvtt_content = generate_webvtt(timing_plan)
        vtt_key = await self.storage.put(webvtt_content.encode("utf-8"), "text/vtt")

        duration = timing_plan.total_duration_seconds
        width, height = TARGET_RESOLUTIONS[target]

        logger.info(
            "render.stub_invoked",
            run_id=run_id,
            storyboard_id=storyboard.id,
            render_target=target.value,
            resolution=f"{width}x{height}",
            duration_seconds=duration,
            scenes=len(storyboard.scenes),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            audio_path = os.path.join(tmpdir, "audio.wav")
            out_path = os.path.join(tmpdir, "output.mp4")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=black:s={width}x{height}:d={duration}",
                    "-c:v",
                    "libx264",
                    video_path,
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r=48000:cl=stereo:d={duration}",
                    "-c:a",
                    "aac",
                    audio_path,
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    audio_path,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    out_path,
                ],
                check=True,
                capture_output=True,
            )

            with open(out_path, "rb") as f:
                video_bytes = f.read()

        video_key = await self.storage.put(video_bytes, "video/mp4")

        return RenderArtifact(
            id=f"ra_{uuid.uuid4().hex[:8]}",
            run_id=run_id,
            storyboard_id=storyboard.id,
            render_target=target,
            video_storage_key=video_key,
            captions_storage_key=vtt_key,
            duration_seconds=duration,
            file_size_bytes=len(video_bytes),
            metadata={
                "renderer": "StubRenderer",
                "is_stub": True,
                "resolution": f"{width}x{height}",
                "script_id": storyboard.script_id,
                "timing_plan_id": storyboard.timing_plan_id,
                "scene_count": len(storyboard.scenes),
            },
            created_at=datetime.now(UTC),
        )
