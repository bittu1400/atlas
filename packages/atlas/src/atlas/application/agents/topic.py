from atlas.application.agents.models import TopicDiscoveryPayload, TopicIdeaItem
from atlas.application.ports.llm import LlmRequest, StructuredLlm
from atlas.domain.focus.models import FocusSnapshot
from atlas.prompts.loader import render_prompt


class TopicDiscoveryAgent:
    """Agent that discovers topics within a Focus area."""

    def __init__(self, llm: StructuredLlm) -> None:
        self.llm = llm

    async def execute(self, focus: FocusSnapshot) -> list[TopicIdeaItem]:
        """Discover topics using the topic_discovery_v1 prompt template."""
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

        request = LlmRequest(
            prompt=prompt_text,
            prompt_version="topic_discovery_v1",
            temperature=0.8,
            max_tokens=2048,
        )

        extracted = await self.llm.extract(request, TopicDiscoveryPayload)
        if not isinstance(extracted.data, TopicDiscoveryPayload):
            from atlas.platform.errors import ExtractionTypeError

            raise ExtractionTypeError(
                expected="TopicDiscoveryPayload", actual=type(extracted.data).__name__
            )
        return list(extracted.data.topics)
