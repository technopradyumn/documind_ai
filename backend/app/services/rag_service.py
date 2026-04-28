"""
RAG Service — production refactor of rag/index.py + rag/chat.py.
Handles PDF ingestion, chunking, embedding, and retrieval via Qdrant.
"""
import logging
from pathlib import Path
from typing import Callable

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RagService:
    def __init__(self):
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

    def index_pdf(self, file_path: str, collection_name: str) -> dict:
        """Load → chunk → embed → store in Qdrant. Called by the RQ worker."""
        logger.info("Indexing '%s' → collection '%s'", file_path, collection_name)
        loader = PyPDFLoader(file_path=file_path)
        docs = loader.load()
        chunks = self._splitter.split_documents(docs)
        logger.info("%d pages → %d chunks", len(docs), len(chunks))

        QdrantVectorStore.from_documents(
            documents=chunks,
            embedding=self._embeddings,
            url=settings.qdrant_url,
            collection_name=collection_name,
        )
        return {
            "status": "success",
            "pages": len(docs),
            "chunks": len(chunks),
            "collection": collection_name,
        }

    def search(self, query: str, collection_name: str, top_k: int = 5) -> str:
        """Retrieve relevant chunks from Qdrant and format for LLM context."""
        try:
            vector_db = QdrantVectorStore.from_existing_collection(
                collection_name=collection_name,
                embedding=self._embeddings,
                url=settings.qdrant_url,
            )
            results = vector_db.similarity_search(query=query, k=top_k)
        except Exception as e:
            logger.error("Qdrant search error: %s", e)
            return f"Error searching documents: {e}"

        if not results:
            return "No relevant content found in the uploaded documents."

        parts = []
        for i, doc in enumerate(results, 1):
            page = doc.metadata.get("page_label", doc.metadata.get("page", "N/A"))
            src = Path(doc.metadata.get("source", "document")).name
            parts.append(f"[Chunk {i}] File: {src} | Page: {page}\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)

    def make_search_tool(self, collection_name: str) -> Callable[[str], str]:
        """Return a tool function pre-bound to a Qdrant collection."""
        def _search(query: str) -> str:
            return self.search(query, collection_name)
        return _search


# Singleton
rag_service = RagService()
