import uuid
from dataclasses import replace

import pytest

from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from app.graph_store.neo4j_graph_store import Neo4jGraphStore
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
