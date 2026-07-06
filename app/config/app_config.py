from dataclasses import dataclass


@dataclass
class Neo4jConfig:
    uri: str
    username: str
    password: str


@dataclass
class OllamaConfig:
    model: str
    host: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    collection_name: str

@dataclass
class KeywordConfig:
    index_path: str

@dataclass
class AppConfig:
    neo4j: Neo4jConfig
    ollama: OllamaConfig
    qdrant: QdrantConfig
    keyword: KeywordConfig