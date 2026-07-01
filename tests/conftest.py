import uuid
import pytest
from app.vector_store.qdrant_vector_store import QdrantVectorStore


@pytest.fixture
def vector_store():
    store = QdrantVectorStore(collection_name=f"test_{uuid.uuid4().hex}")
    if store.client.collection_exists(store.collection_name):
        store.client.delete_collection(store.collection_name)
    yield store
    if store.client.collection_exists(store.collection_name):
        store.client.delete_collection(store.collection_name)
