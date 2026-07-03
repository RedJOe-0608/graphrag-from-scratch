from app.models.chunk import Chunk


def build_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"[Source {i}]\n{chunk.text}" for i, chunk in enumerate(chunks, start=1)
    )
