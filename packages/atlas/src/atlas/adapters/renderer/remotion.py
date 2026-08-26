"""Remotion Renderer adapter."""

import os
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime

from atlas.application.ports.renderer import Renderer
from atlas.application.ports.storage import Storage
from atlas.domain.media.models import RenderArtifact, RenderTarget, Storyboard
from atlas.domain.script.models import TimingPlan


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


class RemotionRenderer(Renderer):
    """Adapter for rendering compositions into MP4 video and WebVTT captions using Remotion / ffmpeg."""

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
        # Generate WebVTT
        webvtt_content = generate_webvtt(timing_plan)
        vtt_key = await self.storage.put(webvtt_content.encode("utf-8"), "text/vtt")

        # Get total duration
        duration = timing_plan.total_duration_seconds

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "video.mp4")
            audio_path = os.path.join(tmpdir, "audio.wav")
            out_path = os.path.join(tmpdir, "output.mp4")

            # 1. Mock rendering video via apps/renderer/src/render.sh
            # We call it using bash to avoid needing execute permissions
            script_path = os.path.abspath("apps/renderer/src/render.sh")
            if not os.path.exists(script_path):
                # Fallback if script doesn't exist for some reason
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c=blue:s=1080x1920:d={duration}",
                        "-c:v",
                        "libx264",
                        video_path,
                    ],
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["bash", script_path, video_path, str(duration)],
                    check=True,
                    capture_output=True,
                )

            # 2. Mock audio using ffmpeg
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

            # 3. Mux video and audio
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
        file_size = len(video_bytes)

        return RenderArtifact(
            id=f"ra_{uuid.uuid4().hex[:8]}",
            run_id=run_id,
            storyboard_id=storyboard.id,
            render_target=target,
            video_storage_key=video_key,
            captions_storage_key=vtt_key,
            duration_seconds=duration,
            file_size_bytes=file_size,
            metadata={"renderer": "RemotionRenderer", "mocked": True},
            created_at=datetime.now(UTC),
        )
