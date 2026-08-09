"""
rag.py — Retrieval-Augmented Generation for Mo Saathi
=======================================================
Loads curriculum documents from the knowledge/ directory, chunks them,
embeds them with a local lightweight model, and stores them in a ChromaDB
vector store that persists to backend/data/chroma/.

At query time, the agent calls search() with the student's question.
The returned text is injected into the LLM context as grounding knowledge,
preventing hallucination on curriculum facts.

How it works
------------
1.  load_knowledge_base()  — called once at startup
    - Scans knowledge/ for .txt and .pdf files
    - Splits each file into ~500-character chunks with 50-char overlap
    - Embeds chunks with sentence-transformers (all-MiniLM-L6-v2, ~22 MB)
    - Upserts into ChromaDB (skips docs already indexed by file hash)

2.  search(query, n_results=3)  — called per user turn
    - Embeds the query with the same model
    - Returns the top-n most relevant passages as a single formatted string

The embedding model runs fully offline — no API key required.
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rag")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SRC_DIR = Path(__file__).parent
_KNOWLEDGE_DIR = _SRC_DIR / "knowledge"
_CHROMA_DIR = _SRC_DIR.parent / "data" / "chroma"

# ---------------------------------------------------------------------------
# Module-level singletons — initialised by load_knowledge_base()
# ---------------------------------------------------------------------------
_collection = None          # ChromaDB collection
_embed_model = None         # SentenceTransformer model


# ---------------------------------------------------------------------------
# Text chunking helpers
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks of approximately chunk_size characters.
    Tries to break at sentence boundaries where possible.
    """
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to break at the last period/newline before end
            break_point = text.rfind(".", start, end)
            if break_point == -1 or break_point <= start:
                break_point = end
            else:
                break_point += 1  # include the period
        else:
            break_point = len(text)

        chunks.append(text[start:break_point].strip())
        # Ensure 'start' strictly advances even if the overlap is large
        start = max(start + 1, break_point - overlap)

    return [c for c in chunks if c]


def _file_hash(path: Path) -> str:
    """Return a short MD5 hash of a file's contents for change detection."""
    return hashlib.md5(path.read_bytes()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

async def load_knowledge_base() -> None:
    import asyncio
    await asyncio.to_thread(_load_knowledge_base_sync)

def _load_knowledge_base_sync() -> None:
    """
    Index all documents in backend/src/knowledge/ into ChromaDB.
    Safe to call multiple times — already-indexed chunks are skipped.
    Call once at agent startup.
    """
    global _collection, _embed_model

    # Lazy import so the heavy libraries don't slow down the import chain
    # if RAG is not needed
    import chromadb
    from sentence_transformers import SentenceTransformer

    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading embedding model (all-MiniLM-L6-v2)…")
    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    logger.info(f"Connecting to ChromaDB at {_CHROMA_DIR}")
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    _collection = client.get_or_create_collection(
        name="mo_saathi_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    # Discover files
    files = list(_KNOWLEDGE_DIR.glob("*.txt")) + list(_KNOWLEDGE_DIR.glob("*.pdf"))
    if not files:
        logger.warning(
            f"No knowledge files found in {_KNOWLEDGE_DIR}. "
            "RAG will return empty results."
        )
        return

    total_chunks_added = 0
    for file_path in files:
        file_hash = _file_hash(file_path)
        prefix = f"{file_path.stem}_{file_hash}"

        # Check if this file version is already indexed
        existing = _collection.get(where={"source": file_path.stem}, limit=1)
        if existing["ids"] and any(
            doc_id.startswith(prefix) for doc_id in existing["ids"]
        ):
            logger.info(f"Skipping already-indexed file: {file_path.name}")
            continue

        # Load content
        if file_path.suffix == ".pdf":
            text = _load_pdf(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")

        chunks = _chunk_text(text)
        if not chunks:
            logger.warning(f"No text extracted from {file_path.name}")
            continue

        # Embed and upsert
        embeddings = _embed_model.encode(chunks, show_progress_bar=False).tolist()
        ids = [f"{prefix}_chunk{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_path.stem, "file": file_path.name} for _ in chunks]

        _collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        total_chunks_added += len(chunks)
        logger.info(f"Indexed {len(chunks)} chunks from {file_path.name}")

    logger.info(
        f"Knowledge base ready. "
        f"Total collection size: {_collection.count()} chunks."
    )


def _load_pdf(path: Path) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as e:
        logger.error(f"Failed to read PDF {path.name}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(query: str, n_results: int = 3) -> str:
    """
    Search the knowledge base for passages relevant to the query.

    Returns a formatted string of the top passages, ready to prepend to the
    LLM context. Returns an empty string if the knowledge base is empty
    or not yet loaded.

    This is a synchronous function so it can be called from async context
    without blocking (embedding is fast enough for real-time use).
    """
    if _collection is None or _embed_model is None:
        logger.debug("RAG not loaded yet — skipping retrieval")
        return ""

    if _collection.count() == 0:
        return ""

    try:
        query_embedding = _embed_model.encode([query]).tolist()
        results = _collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, _collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not docs:
            return ""

        # Filter out low-relevance results (cosine distance > 0.7 is poor)
        relevant = [
            (doc, dist)
            for doc, dist in zip(docs, distances)
            if dist < 0.7
        ]

        if not relevant:
            return ""

        logger.info(f"[RAG] Found {len(relevant)} relevant passages for query: '{query[:60]}…'")

        passages = "\n\n".join(
            f"[Passage {i+1}]: {doc}" for i, (doc, _) in enumerate(relevant)
        )
        return f"CURRICULUM REFERENCE (use this to ground your answer):\n{passages}"

    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return ""
