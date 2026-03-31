"""
RAG Agent Tools
Handles PDF ingestion → chunking → embedding → ChromaDB storage → semantic search.
"""
import hashlib
import os

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL

# Lazy globals (loaded once per process)
_embed_model = None
_chroma_client = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embed_model


def _get_collection():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Text splitting (no LangChain dep needed for this) ──────────────────────────

def _split_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    """Simple recursive character splitter."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ── Public API ─────────────────────────────────────────────────────────────────

def ingest_pdf(file_path: str, filename: str) -> str:
    """
    Parse a PDF, chunk it, embed and upsert into ChromaDB.
    Returns a human-readable status string.
    """
    reader = PdfReader(file_path)
    full_text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    ).strip()

    if not full_text:
        return f"⚠️ Could not extract text from {filename}."

    chunks = _split_text(full_text)
    model = _get_embed_model()
    collection = _get_collection()

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.md5(f"{filename}_{i}".encode()).hexdigest()
        ids.append(doc_id)
        embeddings.append(model.encode(chunk).tolist())
        documents.append(chunk)
        metadatas.append({"source": filename, "chunk": i, "total_chunks": len(chunks)})

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    return f"✅ Ingested **{filename}** → {len(chunks)} chunks stored in vector DB."


def search_documents(query: str, n_results: int = 5) -> str:
    """
    Semantic search over the vector DB.
    Returns formatted context string for the LLM.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return "NO_DOCUMENTS: No policy documents have been uploaded yet. Please ask John to upload a PDF first."

    model = _get_embed_model()
    q_emb = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    if not docs:
        return "No relevant policy content found for that query."

    parts = []
    for doc, meta, dist in zip(docs, metas, dists):
        relevance = round((1 - dist) * 100, 1)
        parts.append(
            f"[Source: {meta['source']} | Relevance: {relevance}%]\n{doc}"
        )

    return "\n\n---\n\n".join(parts)


def list_documents() -> list:
    """Return unique source filenames currently in the vector DB."""
    collection = _get_collection()
    if collection.count() == 0:
        return []
    metas = collection.get(include=["metadatas"])["metadatas"]
    return sorted({m["source"] for m in metas})


def delete_document(filename: str) -> str:
    """Remove all chunks belonging to a specific document."""
    collection = _get_collection()
    results = collection.get(where={"source": filename}, include=["metadatas"])
    ids_to_delete = results["ids"]
    if not ids_to_delete:
        return f"Document '{filename}' not found."
    collection.delete(ids=ids_to_delete)
    return f"Deleted {len(ids_to_delete)} chunks from '{filename}'."
