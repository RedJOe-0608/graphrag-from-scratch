from app.embeddings.embedder import Embedder
from ollama import ResponseError, embed

from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk

class OllamaEmbedder(Embedder):
    def __init__(self,model: str = "nomic-embed-text") -> None:
        self.model = model # through this constructor fn, we can easily swap the embedding model.

    def embed_chunk(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:

        chunk_texts = [chunk.text for chunk in chunks]
        try:
            response = embed(
                model=self.model,
                input=chunk_texts
            )

            # This is the response structure of ollama
            # {
            #     "model": "nomic-embed-text",
            #     "embeddings": [
            #         [...],
            #         [...]
            #     ]
            # }

            embedded_chunks = []

            for chunk, embedding in zip(chunks,response.embeddings,strict=True):
                embedded_chunks.append(
                    EmbeddedChunk(
                        chunk=chunk,
                        embedding=embedding
                    )
                )

            return embedded_chunks

        except ResponseError as e:
            raise RuntimeError(f"Failed to generate embeddings: {e}") from e

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        try:
            response = embed(model=self.model, input=texts)
            return response.embeddings
        except ResponseError as e:
            raise RuntimeError(f"Failed to generate embeddings {e}") from e

            
        
