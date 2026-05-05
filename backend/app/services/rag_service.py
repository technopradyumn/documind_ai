"""
RAG Service — production refactor of rag/index.py + rag/chat.py.
Handles PDF ingestion, chunking, embedding, and retrieval via Qdrant.
"""
import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class RagService:
    """Lazy-initialised RAG pipeline. Degrades gracefully if Qdrant is unreachable."""

    def __init__(self):
        self._embeddings = None
        self._splitter = None

    def _get_embeddings(self):
        """Lazy init so the app can start without Qdrant / Google API."""
        if self._embeddings is not None:
            return self._embeddings
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            from app.config import get_settings
            settings = get_settings()
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.gemini_embedding_model,
                google_api_key=settings.gemini_api_key,
            )
            logger.info("Embeddings ready (model=%s).", settings.gemini_embedding_model)
        except Exception as e:
            logger.error("Failed to init embeddings: %s", e)
            raise RuntimeError(f"Embedding model init failed: {e}")
        return self._embeddings

    def _get_splitter(self):
        if self._splitter is not None:
            return self._splitter
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        return self._splitter

    def index_pdf(self, file_path: str, collection_name: str) -> dict:
        """Load → chunk → embed → store in Qdrant. Called by the RQ worker."""
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_qdrant import QdrantVectorStore
        from app.config import get_settings
        settings = get_settings()

        try:
            logger.info("Indexing '%s' → collection '%s'", file_path, collection_name)
            loader = PyPDFLoader(file_path=str(file_path))
            docs = loader.load()
            if not docs:
                raise ValueError(f"No pages could be loaded from {file_path}. Is it a valid PDF?")

            chunks = self._get_splitter().split_documents(docs)
            logger.info("%d pages → %d chunks", len(docs), len(chunks))

            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=self._get_embeddings(),
                url=settings.qdrant_url,
                collection_name=collection_name,
                force_recreate=False,
            )
            return {
                "status": "success",
                "pages": len(docs),
                "chunks": len(chunks),
                "collection": collection_name,
            }
        except Exception as e:
            logger.error("Indexing failed for '%s': %s", file_path, e, exc_info=True)
            raise RuntimeError(f"Indexing failed: {e}")

    def search(self, query: str, collection_name: str, top_k: int = 5) -> str:
        """Retrieve relevant chunks from Qdrant and format for LLM context."""
        from langchain_qdrant import QdrantVectorStore
        from app.config import get_settings
        settings = get_settings()

        try:
            vector_db = QdrantVectorStore.from_existing_collection(
                collection_name=collection_name,
                embedding=self._get_embeddings(),
                url=settings.qdrant_url,
            )
            results = vector_db.similarity_search(query=query, k=top_k)
        except Exception as e:
            logger.error("Qdrant search error: %s", e)
            return f"No documents indexed yet or search failed: {e}"

        if not results:
            return "No relevant content found in the uploaded documents."

        parts = []
        for i, doc in enumerate(results, 1):
            page = doc.metadata.get("page_label", doc.metadata.get("page", "N/A"))
            src = Path(doc.metadata.get("source", "document")).name
            parts.append(f"[Chunk {i}] File: {src} | Page: {page}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection from Qdrant."""
        from qdrant_client import QdrantClient
        from app.config import get_settings
        settings = get_settings()
        try:
            client = QdrantClient(url=settings.qdrant_url)
            client.delete_collection(collection_name=collection_name)
            logger.info("Deleted collection: %s", collection_name)
            return True
        except Exception as e:
            logger.error("Failed to delete collection %s: %s", collection_name, e)
            return False

    def delete_document(self, file_path: str, collection_name: str) -> bool:
        """Delete points associated with a specific file from a collection."""
        from qdrant_client import QdrantClient, models
        from app.config import get_settings
        settings = get_settings()
        try:
            client = QdrantClient(url=settings.qdrant_url)
            # Match by metadata 'source' which is stored in index_pdf
            client.delete(
                collection_name=collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.source",
                            match=models.MatchValue(value=str(file_path)),
                        )
                    ]
                ),
            )
            logger.info("Deleted document points for '%s' from '%s'", file_path, collection_name)
            return True
        except Exception as e:
            logger.error("Failed to delete document %s: %s", file_path, e)
            return False

    def make_search_tool(self, collection_name: str) -> Callable[[str], str]:
        """Return a tool function pre-bound to a Qdrant collection."""
        def _search(query: str) -> str:
            return self.search(query, collection_name)
        return _search


# Singleton
rag_service = RagService()
