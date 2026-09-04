"""The adapters the production `Container` actually wires.

Before this file existed, `LocalStorage` was the only one of them any test
touched (defect V-07). That is how `LoggingNotifier` shipped raising
`TypeError` on every gate suspension: the 122-test suite injected `FakeNotifier`
everywhere, so the production notifier was never called once.

Network-backed adapters — `WikipediaSearch`, `HttpSourceFetcher`,
`WikimediaCommonsSearch`, `InternetArchiveSearch`, `OllamaEmbedder`,
`GeminiLlm`, `FreesoundLibrary` — are still uncovered here on purpose: a unit
test never touches the network, and the cassette machinery `ARCHITECTURE.md` §9
describes does not exist yet. That gap is recorded in `docs/STATUS.md` §3.
"""

import shutil

import pytest
from atlas.adapters.container import Container, MissingProviderCredentialError
from atlas.adapters.images.stub_generator import PLACEHOLDER_PREFIX, StubImageGenerator
from atlas.adapters.notify.logging_notifier import LoggingNotifier
from atlas.adapters.publish.stub import StubPublisher
from atlas.adapters.renderer.stub import StubRenderer, generate_webvtt
from atlas.adapters.storage.local import LocalStorage
from atlas.domain.media.models import (
    MotionTreatment,
    RenderTarget,
    Scene,
    Storyboard,
)
from atlas.domain.script.models import BeatTiming, CaptionCue, TimingPlan
from atlas.platform.clock import utc_now
from atlas.platform.config import clear_settings_cache


def _timing_plan() -> TimingPlan:
    return TimingPlan(
        id="tp_adapter_probe",
        script_id="scr_adapter_probe",
        beat_timings=[
            BeatTiming(
                beat_id="beat_01",
                start_time_seconds=0.0,
                end_time_seconds=2.0,
                word_count=4,
                reading_pace_wps=2.0,
            ),
            BeatTiming(
                beat_id="beat_02",
                start_time_seconds=2.0,
                end_time_seconds=4.0,
                word_count=4,
                reading_pace_wps=2.0,
            ),
        ],
        caption_cues=[
            CaptionCue(start_seconds=0.0, end_seconds=2.0, text="PLACEHOLDER_CUE_ONE"),
            CaptionCue(start_seconds=2.0, end_seconds=4.0, text="PLACEHOLDER_CUE_TWO"),
        ],
        created_at=utc_now(),
    )


def _storyboard() -> Storyboard:
    return Storyboard(
        id="stb_adapter_probe",
        script_id="scr_adapter_probe",
        timing_plan_id="tp_adapter_probe",
        scenes=[
            Scene(
                id="scn_01",
                scene_index=1,
                beat_id="beat_01",
                asset_id="ast_01",
                motion_treatment=MotionTreatment.SLOW_ZOOM_IN,
                start_time_seconds=0.0,
                duration_seconds=2.0,
            ),
            Scene(
                id="scn_02",
                scene_index=2,
                beat_id="beat_02",
                asset_id="ast_02",
                motion_treatment=MotionTreatment.SLOW_ZOOM_OUT,
                start_time_seconds=2.0,
                duration_seconds=2.0,
            ),
        ],
        created_at=utc_now(),
    )


@pytest.mark.asyncio
async def test_logging_notifier_emits_without_colliding_with_the_log_event_key() -> None:
    """Defect V-01: `logger.info("...", event=event)` collided with structlog's own key.

    The production pipeline calls this on every gate suspension and on
    completion, so the collision crashed every real Run at stage 2 of 18.
    """
    notifier = LoggingNotifier()

    await notifier.notify(
        "gate_suspension",
        "Run 'run_probe' suspended",
        {"run_id": "run_probe", "stage": "topic_selection"},
    )
    # A payload carrying structlog's own reserved keys must not crash either.
    await notifier.notify("run_completed", "done", {"event": "x", "timestamp": "y"})
    await notifier.notify("run_completed", "done", None)


@pytest.mark.asyncio
async def test_stub_publisher_marks_its_id_as_a_stub() -> None:
    """Rule R3: a stub external ID must be obviously not a real video ID."""
    from atlas.domain.media.models import RenderArtifact

    artifact = RenderArtifact(
        id="ra_probe",
        run_id="run_probe",
        storyboard_id="stb_adapter_probe",
        render_target=RenderTarget.VERTICAL,
        video_storage_key="sha256/deadbeef",
        captions_storage_key="sha256/cafebabe",
        duration_seconds=4.0,
        file_size_bytes=1,
        metadata={},
        created_at=utc_now(),
    )
    external_id = await StubPublisher().publish(artifact, "origins", {"run_id": "run_probe"})
    assert external_id.startswith("stub:")


@pytest.mark.asyncio
async def test_stub_image_generator_returns_obviously_synthetic_bytes() -> None:
    """Rule R3/R4: placeholder bytes must never look like an image a human made."""
    content, mime = await StubImageGenerator().generate_image("PLACEHOLDER_PROMPT")
    assert content.startswith(PLACEHOLDER_PREFIX)
    assert mime == "image/png"


def test_webvtt_is_built_from_the_timing_plan_cues() -> None:
    """Captions are computed from the persisted plan, never invented."""
    vtt = generate_webvtt(_timing_plan())
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.000" in vtt
    assert "PLACEHOLDER_CUE_ONE" in vtt


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="StubRenderer shells out to ffmpeg")
@pytest.mark.asyncio
async def test_stub_renderer_honours_the_requested_render_target(tmp_path: str) -> None:
    """Defect B8's regression guard, against the adapter the container wires.

    `FakeRenderer` is what every other test uses, so this is the only place the
    real ffmpeg invocation runs.
    """
    storage = LocalStorage(root_dir=str(tmp_path))
    renderer = StubRenderer(storage)
    storyboard, timing_plan = _storyboard(), _timing_plan()

    by_target = {}
    for target in (RenderTarget.VERTICAL, RenderTarget.HORIZONTAL):
        artifact = await renderer.render(storyboard, timing_plan, target, "run_probe")
        by_target[target] = artifact

    assert by_target[RenderTarget.VERTICAL].metadata["resolution"] == "1080x1920"
    assert by_target[RenderTarget.HORIZONTAL].metadata["resolution"] == "1920x1080"

    for artifact in by_target.values():
        assert artifact.duration_seconds == timing_plan.total_duration_seconds
        assert artifact.storyboard_id == storyboard.id
        assert artifact.file_size_bytes > 0
        captions = (await storage.get(artifact.captions_storage_key)).decode("utf-8")
        assert captions.startswith("WEBVTT")
        assert "PLACEHOLDER_CUE_TWO" in captions


def test_container_wires_the_production_adapters_without_a_session() -> None:
    """The production container builds, and resolves no port to a fake (rule R2).

    `Container` had no test at all, which is why nothing noticed that the
    adapter it wires for notification could not be called.
    """
    container = Container()

    assert type(container.renderer).__name__ == "StubRenderer"
    assert type(container.publisher).__name__ == "StubPublisher"
    assert type(container.notifier).__name__ == "LoggingNotifier"
    assert type(container.search).__name__ == "WikipediaSearch"
    assert type(container.source_fetcher).__name__ == "HttpSourceFetcher"
    assert type(container.embedder).__name__ == "OllamaEmbedder"

    for name in ("renderer", "publisher", "notifier", "search", "source_fetcher", "embedder"):
        assert "fakes" not in type(getattr(container, name)).__module__


def test_container_reads_the_ollama_base_url_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defect V-05: Compose sets OLLAMA_URL and the container used to ignore it."""
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    clear_settings_cache()
    try:
        assert Container().embedder.base_url == "http://ollama:11434"
    finally:
        clear_settings_cache()


def test_container_names_the_missing_credential_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: str
) -> None:
    """Defect V-06: credentials come from Settings, which reads `.env` too."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ATLAS_GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # away from the repo's own .env
    clear_settings_cache()
    try:
        with pytest.raises(MissingProviderCredentialError) as exc_info:
            _ = Container().llm
        assert exc_info.value.variable_name == "GEMINI_API_KEY"
    finally:
        clear_settings_cache()


def test_container_loads_a_credential_supplied_only_by_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The credential path resolves without `os.getenv` in the container."""
    monkeypatch.setenv("GEMINI_API_KEY", "PLACEHOLDER_NOT_A_REAL_KEY")
    clear_settings_cache()
    try:
        assert Container().llm is not None
    finally:
        clear_settings_cache()
