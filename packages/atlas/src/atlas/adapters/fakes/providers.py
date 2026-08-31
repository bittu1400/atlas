"""Deterministic Provider Doubles (Fakes) for zero-cost, hermetic testing.

As specified in ARCHITECTURE.md §9 and CLAUDE.md:
- Unit and integration tests never touch external networks, GPUs, or paid APIs.
- The full pipeline runs end-to-end against fakes in seconds for $0.
- Fakes return realistic, structurally valid domain objects that satisfy every invariant.
"""

import hashlib
import json
from typing import Any, TypeVar

from atlas.application.ports.embedder import Embedder
from atlas.application.ports.llm import (
    Extracted,
    Llm,
    LlmCapabilities,
    LlmRequest,
    LlmResponse,
    StructuredLlm,
)
from atlas.application.ports.media import (
    ImageCandidate,
    ImageGenerator,
    ImageSearch,
    SoundItem,
    SoundLibrary,
)
from atlas.application.ports.notify import Notifier
from atlas.application.ports.publish import Publisher
from atlas.application.ports.queue import QueueBroker
from atlas.application.ports.renderer import Renderer
from atlas.application.ports.search import Search, SearchResultItem
from atlas.application.ports.sources import SourceFetcher
from atlas.application.ports.speech import Speech
from atlas.application.ports.storage import Storage
from atlas.domain.media.models import RenderArtifact, RenderTarget, Storyboard
from atlas.domain.script.models import TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.ids import generate_id
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class FakeLlm(Llm, StructuredLlm):
    """Deterministic LLM double supporting raw completion and structured extraction."""

    def __init__(self, model_id: str = "fake-frontier-v1") -> None:
        self.model_id = model_id
        self._capabilities = LlmCapabilities(
            tier=2,
            supports_json=True,
            supports_vision=True,
            context_window_tokens=32768,
            rpm_limit=10000,
            rpd_limit=100000,
        )

    @property
    def capabilities(self) -> LlmCapabilities:
        return self._capabilities

    async def complete(self, request: LlmRequest) -> LlmResponse:
        content = f"Deterministic response for: {request.prompt[:40]}..."
        return LlmResponse(
            content=content,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(content.split()),
            latency_ms=10,
            model_id=self.model_id,
            provider="fake",
        )

    async def extract(self, request: LlmRequest, schema: type[T]) -> Extracted:
        # Generate synthetic valid instance of schema
        dummy_data = self._generate_fixture_for_schema(schema, request.prompt)
        raw_json = json.dumps(dummy_data if isinstance(dummy_data, dict) else {})
        validated_instance = schema(**dummy_data) if isinstance(dummy_data, dict) else dummy_data
        return Extracted(
            data=validated_instance,
            input_tokens=len(request.prompt.split()),
            output_tokens=25,
            latency_ms=12,
            raw_response=raw_json,
            model_id="fake-model",
            provider="fake",
        )

    def _generate_fixture_for_schema(self, schema: type[T], _prompt: str) -> Any:
        schema_name = schema.__name__
        if "ExtractionPayload" in schema_name:
            return {
                "claims": [
                    {
                        "text": "SUBJECT_A was recorded by SOURCE_B.",
                        "assertion_type": "fact",
                        "confidence": 0.98,
                    },
                    {
                        "text": "SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C.",
                        "assertion_type": "fact",
                        "confidence": 0.95,
                    },
                ],
                "evidence": [
                    {
                        "locator": "Section 1, Paragraph 2",
                        "quote": "SUBJECT_A was recorded by SOURCE_B.",
                        "stance": "supports",
                        "confidence": 1.0,
                    },
                    {
                        "locator": "Section 3, Paragraph 1",
                        "quote": "SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C.",
                        "stance": "supports",
                        "confidence": 1.0,
                    },
                ],
                "links": [
                    {
                        "claim_index": 0,
                        "evidence_index": 0,
                        "stance": "supports",
                        "notes": "Fixture link",
                    },
                    {
                        "claim_index": 1,
                        "evidence_index": 1,
                        "stance": "supports",
                        "notes": "Fixture link",
                    },
                ],
            }
        if "Verification" in schema_name:
            return {
                "verifications": [
                    {
                        "status": "verified",
                        "stance": "supports",
                        "rationale": "Fixture verdict; no evaluation was performed.",
                        "confidence": 1.0,
                    }
                ],
                "status": "verified",
                "stance": "supports",
                "rationale": "Fixture verdict; no evaluation was performed.",
                "confidence": 1.0,
            }
        if "TopicDiscoveryPayload" in schema_name:
            return {
                "topics": [
                    {
                        "title": "PLACEHOLDER_TOPIC_ALPHA",
                        "rationale": "Fixture topic; no archive was consulted.",
                        "search_queries": [
                            "placeholder query alpha",
                            "placeholder query beta",
                        ],
                        "estimated_novelty": 0.85,
                    }
                ]
            }
        if "StoryAnglePayload" in schema_name:
            return {
                "angles": [
                    {
                        "name": "PLACEHOLDER_ANGLE_ALPHA",
                        "hook": "Placeholder hook for SUBJECT_A.",
                        "narrative_thesis": "Placeholder thesis for SUBJECT_A.",
                        "score": 92.0,
                    }
                ],
                "selected_angle": "PLACEHOLDER_ANGLE_ALPHA",
                "selection_reason": "Fixture selection; no angle was judged.",
            }
        if "ScriptPayload" in schema_name:
            # Fifteen beats of eight words each keeps the fixture inside the
            # 110-150 word pacing budget without asserting anything about the world.
            return {
                "beats": [
                    {
                        "beat_index": index,
                        "text": f"Placeholder beat {index} of fixture script about SUBJECT_A.",
                        "claim_ids": ["claim_01"],
                        "duration_seconds": 4.0,
                        "visual_cue": f"Placeholder visual cue {index}",
                    }
                    for index in range(1, 16)
                ]
            }
        if "QualityJudgePayload" in schema_name:
            return {
                "scores": [
                    {
                        "dimension": "sourcing_integrity",
                        "score": 95.0,
                        "reason": "All claims backed by Tier 0 evidence.",
                    },
                    {
                        "dimension": "hook_strength",
                        "score": 88.0,
                        "reason": "Engaging initial beat.",
                    },
                    {
                        "dimension": "narrative_arc",
                        "score": 85.0,
                        "reason": "Cohesive historical progression.",
                    },
                    {
                        "dimension": "language_craft",
                        "score": 90.0,
                        "reason": "Kinetic, concise sentences.",
                    },
                    {
                        "dimension": "factual_density",
                        "score": 84.0,
                        "reason": "High factual content without clutter.",
                    },
                    {
                        "dimension": "novelty",
                        "score": 86.0,
                        "reason": "Non-obvious historical focus.",
                    },
                    {
                        "dimension": "visual_coherence",
                        "score": 88.0,
                        "reason": "Consistent archival aesthetic cues.",
                    },
                    {
                        "dimension": "technical_compliance",
                        "score": 100.0,
                        "reason": "Strict compliance with 60s pacing.",
                    },
                ]
            }
        if "QualityReport" in schema_name or "DimensionScore" in schema_name:
            return {
                "sourcing_integrity": 95.0,
                "hook_strength": 88.0,
                "narrative_arc": 85.0,
                "language_craft": 90.0,
                "factual_density": 82.0,
                "novelty": 88.0,
                "visual_coherence": 85.0,
                "technical_compliance": 100.0,
            }
        return {}


class FakeEmbedder(Embedder):
    """Deterministic vector embedder returning 128-dimensional hashes."""

    @property
    def dimension(self) -> int:
        return 128

    async def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Convert first 128 bytes (cycling) to normalized floats
        return [(h[i % len(h)] / 255.0) for i in range(128)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class FakeSearch(Search):
    """Deterministic primary source search double."""

    async def search(
        self, query: str, limit: int = 10, _allowlist: list[str] | None = None
    ) -> list[SearchResultItem]:
        return [
            SearchResultItem(
                title=f"Primary Research on {query}",
                url=f"https://openalex.org/W{hashlib.sha256(query.encode()).hexdigest()[:8]}",
                snippet=f"Factual historical findings regarding {query}.",
                source_name="OpenAlex Archive",
            ),
            SearchResultItem(
                title=f"Archival Records of {query}",
                url=f"https://smithsonian.edu/records/{hashlib.sha256(query.encode()).hexdigest()[:6]}",
                snippet=f"Primary museum documentation on {query}.",
                source_name="Smithsonian Institution",
            ),
        ][:limit]


class FakeSourceFetcher(SourceFetcher):
    """Deterministic source fetcher producing real content-addressed bytes."""

    async def fetch(self, url: str) -> tuple[bytes, str, str]:
        content = (
            f"<html><body>Lorem source about SUBJECT_A fetched from {url}. "
            "SUBJECT_A was recorded by SOURCE_B. "
            "SUBJECT_A is described in PLACEHOLDER_DOCUMENT_C.</body></html>"
        ).encode()
        content_hash = hashlib.sha256(content).hexdigest()
        return content, content_hash, "text/html"


class FakeImageSearch(ImageSearch):
    """Deterministic archival image search returning CC-BY and Public Domain items."""

    def __init__(self, candidates: list[ImageCandidate] | None = None) -> None:
        self.custom_candidates = candidates

    async def search_archival(self, query: str, limit: int = 10) -> list[ImageCandidate]:
        if self.custom_candidates is not None:
            return self.custom_candidates[:limit]
        return [
            ImageCandidate(
                id=f"img_{hashlib.sha256(f'{query}_1'.encode()).hexdigest()[:8]}",
                title=f"Archival photograph representing {query}",
                url=f"https://upload.wikimedia.org/wikipedia/commons/demo_{query}.jpg",
                license_id="CC-BY-4.0",
                author="Smithsonian Historical Archive",
                source_archive="Wikimedia Commons",
                preview_url=f"https://upload.wikimedia.org/wikipedia/commons/thumb/demo_{query}.jpg",
                is_ai_generated=False,
            ),
            ImageCandidate(
                id=f"img_{hashlib.sha256(f'{query}_2'.encode()).hexdigest()[:8]}",
                title=f"Public domain artifact from {query}",
                url=f"https://loc.gov/pictures/demo_{query}.jpg",
                license_id="Public Domain",
                author="Library of Congress",
                source_archive="Library of Congress",
                preview_url=f"https://loc.gov/pictures/thumb_{query}.jpg",
                is_ai_generated=False,
            ),
        ][:limit]


class FakeImageGenerator(ImageGenerator):
    """Deterministic AI image generator double."""

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> tuple[bytes, str]:
        content = f"FAKE_IMAGE_BYTES_FOR:{prompt}:{aspect_ratio}".encode()
        return content, "image/png"


class FakeSoundLibrary(SoundLibrary):
    """Deterministic sound library double."""

    async def get_music_bed(self, mood: str) -> SoundItem:
        return SoundItem(
            id="snd_ambient_origins_01",
            name=f"Subtle Archival Ambient ({mood})",
            category="music_bed",
            license_id="CC0",
            url="https://freesound.org/data/previews/demo_bed.mp3",
            duration_seconds=65.0,
        )

    async def get_sfx(self, cue_type: str) -> SoundItem:
        return SoundItem(
            id=f"sfx_{cue_type}_01",
            name=f"Tactile Keystroke Variation ({cue_type})",
            category=cue_type,
            license_id="CC0",
            url="https://freesound.org/data/previews/demo_keystroke.mp3",
            duration_seconds=0.4,
        )


class FakeRenderer(Renderer):
    """Deterministic renderer double storing output blobs."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.last_storyboard: Storyboard | None = None
        self.rendered_artifacts: list[RenderArtifact] = []

    async def render(
        self,
        storyboard: Storyboard,
        timing_plan: TimingPlan,
        target: RenderTarget,
        run_id: str,
    ) -> RenderArtifact:
        self.last_storyboard = storyboard
        # Generate simulated MP4 and WebVTT bytes
        video_bytes = (
            f"SIMULATED_MP4_VIDEO_{target.value}_{run_id}_{len(storyboard.scenes)}scenes".encode()
        )
        captions_bytes = b"WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nKinetic Text Line"

        video_key = await self.storage.put(video_bytes, "video/mp4")
        captions_key = await self.storage.put(captions_bytes, "text/vtt")

        return RenderArtifact(
            id=generate_id("rnd"),
            run_id=run_id,
            storyboard_id=storyboard.id,
            render_target=target,
            video_storage_key=video_key,
            captions_storage_key=captions_key,
            duration_seconds=timing_plan.total_duration_seconds,
            file_size_bytes=len(video_bytes),
            metadata={
                "target": target.value,
                "scenes_rendered": len(storyboard.scenes),
                "fps": 30,
                "loudness_lufs": -14.0,
            },
            created_at=utc_now(),
        )


class FakeNotifier(Notifier):
    """In-memory notification recorder."""

    def __init__(self) -> None:
        self.notifications: list[dict[str, Any]] = []

    async def notify(self, event: str, message: str, payload: dict[str, Any] | None = None) -> None:
        self.notifications.append(
            {"event": event, "message": message, "payload": payload or {}, "timestamp": utc_now()}
        )


class FakePublisher(Publisher):
    """Deterministic publisher double recording publication actions."""

    def __init__(self) -> None:
        self.published_records: list[dict[str, Any]] = []

    async def publish(
        self, artifact: RenderArtifact, channel_id: str, metadata: dict[str, Any]
    ) -> str:
        pub_id = generate_id("pub")
        self.published_records.append(
            {
                "publication_id": pub_id,
                "artifact_id": artifact.id,
                "channel_id": channel_id,
                "metadata": metadata,
                "published_at": utc_now(),
            }
        )
        return pub_id


class FakeSpeech(Speech):
    """Deterministic speech synthesis double (seam)."""

    async def synthesize(self, text: str, _voice_id: str) -> tuple[bytes, float]:
        audio_bytes = f"AUDIO_BYTES_FOR:{text[:30]}".encode()
        return audio_bytes, float(len(text.split()) * 0.4)


class FakeQueueBroker(QueueBroker):
    """In-memory queue broker for direct synchronous dispatch or task queueing."""

    def __init__(self) -> None:
        self.enqueued_tasks: list[dict[str, Any]] = []

    async def enqueue(self, run_id: str, step_name: str | None = None, **kwargs: Any) -> None:
        self.enqueued_tasks.append({"run_id": run_id, "step_name": step_name, "kwargs": kwargs})
