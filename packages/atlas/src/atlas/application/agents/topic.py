from atlas.application.agents.models import TopicDiscoveryPayload, TopicIdeaItem
from atlas.application.policies.quota_policy import RoutingPolicy, TaskKind
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.domain.focus.models import FocusSnapshot
from atlas.platform.quota import QuotaManager
from atlas.prompts.loader import render_prompt


class TopicDiscoveryAgent:
    """Agent that discovers topics within a Focus area."""

    def __init__(self, llm: StructuredLlm, quota_mgr: QuotaManager) -> None:
        self.llm = llm
        self.quota_mgr = quota_mgr

    async def execute(
        self,
        focus: FocusSnapshot,
        run_id: str = "run_unassigned",
        step_id: str | None = None,
    ) -> list[TopicIdeaItem]:
        """Discover topics using the topic_discovery_v1 prompt template.

        This is stage 1 and it runs on every Run, so it is the call most likely
        to exhaust a free tier. It is metered like every other model call
        (Invariant 8); it used to be the one that was not (defect V-02).
        """
        domains = ", ".join([f.value for f in focus.facets if f.dimension == "domain"]) or "General"
        notes_facets = [
            f"{f.dimension}: {f.value}" for f in focus.facets if f.dimension != "domain"
        ]
        notes = "; ".join(notes_facets) if notes_facets else "No additional constraints."

        prompt_text = render_prompt(
            "topic_discovery_v1",
            channel_name="Atlas Documentary Channel",
            domains=domains,
            scope_mode=focus.scope_mode.value,
            notes=notes,
        )

        route = RoutingPolicy.get_route(TaskKind.TOPIC_DISCOVERY)
        await self.quota_mgr.check_rate_limits(route.provider)

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="topic_discovery_v1",
            temperature=route.temperature,
            max_tokens=route.max_tokens or 2048,
        )

        extracted = await self.llm.extract(request, TopicDiscoveryPayload)

        await self.quota_mgr.record_invocation(
            provider=extracted.provider,
            model_id=extracted.model_id,
            prompt_version="topic_discovery_v1",
            parameters={"temperature": route.temperature},
            code_version="phase-5-v1",
            input_tokens=extracted.input_tokens,
            output_tokens=extracted.output_tokens,
            latency_ms=extracted.latency_ms,
            run_id=run_id,
            step_id=step_id,
        )

        if not isinstance(extracted.data, TopicDiscoveryPayload):
            from atlas.platform.errors import ExtractionTypeError

            raise ExtractionTypeError(
                expected="TopicDiscoveryPayload", actual=type(extracted.data).__name__
            )
        return list(extracted.data.topics)
