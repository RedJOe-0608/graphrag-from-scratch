from app.config.schema_loader import load_graph_schema
from app.extraction.ollama_extractor import OllamaExtractor
from app.models.chunk import Chunk


def test_ollama_extractor():
    schema = load_graph_schema("config/graph.yaml")

    extractor = OllamaExtractor(schema)

    chunk = Chunk(
        id="chunk_1",
        document_id="doc_1",
        text="""
        OpenAI released GPT-4 in 2023.

        Sam Altman is the CEO of OpenAI.

        Microsoft invested billions of dollars into OpenAI.
        """,
    )

    knowledge = extractor.extract(chunk)

    # Basic sanity checks
    assert len(knowledge.entities) > 0
    assert len(knowledge.relationships) > 0

    # Verify expected entities exist
    entity_names = {entity.name for entity in knowledge.entities}

    assert "OpenAI" in entity_names
    assert "Sam Altman" in entity_names
    assert "Microsoft" in entity_names
    assert "GPT-4" in entity_names

    print("\n========== ENTITIES ==========")
    for entity in knowledge.entities:
        print(entity)

    print("\n======= RELATIONSHIPS ========")
    for relationship in knowledge.relationships:
        print(relationship)