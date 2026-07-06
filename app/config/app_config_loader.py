import yaml

from app.config.app_config import (
    AppConfig,
    KeywordConfig,
    Neo4jConfig,
    OllamaConfig,
    QdrantConfig,
    RerankConfig,
)


def load_app_config(path: str) -> AppConfig:
    with open(path, "r") as file:
        config = yaml.safe_load(file)

    return AppConfig(
        neo4j=Neo4jConfig(**config["neo4j"]),
        ollama=OllamaConfig(**config["ollama"]),
        qdrant=QdrantConfig(**config["qdrant"]),
        keyword=KeywordConfig(**config["keyword"]),
        reranker=RerankConfig(**config["reranker"])
    )