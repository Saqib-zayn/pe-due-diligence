"""
rag.py — Manages document chunking, vectorisation, and semantic search via FAISS.
"""

import time
from typing import List

import numpy as np
import google.generativeai as genai
import faiss


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "models/gemini-embedding-001"
TOP_K = 5
# Brief delay between embedding API calls to respect free-tier rate limits
EMBED_DELAY_SECONDS = 0.5


class RAGPipeline:
    """Ingests text documents into a FAISS index and supports semantic retrieval."""

    def __init__(self):
        self._chunks: List[str] = []
        self._index: faiss.Index | None = None
        self._dimension: int | None = None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def _split_into_chunks(self, text: str) -> List[str]:
        """Slice text into overlapping fixed-size chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunks.append(text[start:end])
            start += CHUNK_SIZE - CHUNK_OVERLAP
        return chunks

    def _embed_text(self, text: str) -> List[float]:
        """Embed a single text string using the Google embedding model."""
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    def ingest(self, text: str) -> None:
        """Chunk the supplied text, embed each chunk, and add to the FAISS index.

        Chunks from multiple documents are all accumulated in a single shared index.
        """
        new_chunks = self._split_into_chunks(text)
        embeddings = []

        for i, chunk in enumerate(new_chunks):
            embedding = self._embed_text(chunk)
            embeddings.append(embedding)
            # Throttle to avoid hitting embedding API rate limits
            if i < len(new_chunks) - 1:
                time.sleep(EMBED_DELAY_SECONDS)

        vectors = np.array(embeddings, dtype=np.float32)

        if self._index is None:
            self._dimension = vectors.shape[1]
            self._index = faiss.IndexFlatL2(self._dimension)

        self._index.add(vectors)
        self._chunks.extend(new_chunks)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = TOP_K) -> List[str]:
        """Embed a query and return the top-k most semantically relevant chunks.

        Args:
            query: Plain English search query.
            top_k: Number of chunks to return (default 5).

        Returns:
            List of the most relevant text chunk strings.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query",
        )
        query_vec = np.array([result["embedding"]], dtype=np.float32)

        k = min(top_k, self._index.ntotal)
        _, indices = self._index.search(query_vec, k)

        return [self._chunks[i] for i in indices[0] if i < len(self._chunks)]
