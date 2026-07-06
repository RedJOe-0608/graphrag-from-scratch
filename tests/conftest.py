import uuid
from dataclasses import replace

import pytest

from app.config.app_config import KeywordConfig
from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from app.graph_store.neo4j_graph_store import Neo4jGraphStore
from app.keyword_store.bm25_keyword_store import BM25KeywordStore
from app.vector_store.qdrant_vector_store import QdrantVectorStore

@pytest.fixture
def app_config():
    return load_app_config("config/app.yaml")

@pytest.fixture
def graph_schema():
    return load_graph_schema("config/graph.yaml")

@pytest.fixture
def vector_store(app_config):
    
    test_config = replace(app_config.qdrant, collection_name=f"test_{uuid.uuid4().hex}")

    store = QdrantVectorStore(config=test_config)
    if store.client.collection_exists(store.collection_name):
        store.client.delete_collection(store.collection_name)
    yield store
    if store.client.collection_exists(store.collection_name):
        store.client.delete_collection(store.collection_name)


@pytest.fixture
def graph_store(app_config, graph_schema):

    store = Neo4jGraphStore(config=app_config.neo4j, schema=graph_schema)
    store.clear()
    yield store
    store.clear()


@pytest.fixture
def keyword_store(tmp_path):
    # tmp_path is a fresh per-test directory, so each test gets an isolated
    # index file that pytest cleans up automatically. No external services.
    index_path = str(tmp_path / "bm25.pkl")
    return BM25KeywordStore(config=KeywordConfig(index_path=index_path))
