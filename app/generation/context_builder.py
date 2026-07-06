from app.graph.graph_fact import GraphFact
from app.models.chunk import Chunk


def build_context(
    chunks: list[Chunk],
    facts: list[GraphFact] | None = None,
) -> str:
    sections = []

    if facts:
        sections.append("## Graph Facts\n\n" + _render_facts(facts))

    sources = "\n\n".join(
        f"[Source {i}]\n{chunk.text}" for i, chunk in enumerate(chunks, start=1)
    )
    sections.append("## Sources\n\n" + sources)

    return "\n\n".join(sections)


def _render_facts(facts: list[GraphFact]) -> str:
    lines = []
    for fact in facts:
        line = f"- {fact.source} --{fact.relationship_type}--> {fact.target}"
        if fact.description:
            line += f" ({fact.description})"
        lines.append(line)

    return "\n".join(lines)
