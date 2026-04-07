"""
Medical knowledge RAG retriever — Chroma hybrid retrieval
=========================================================
Retrieval architecture:
  Query → [Dense kNN (Chroma cosine)] + [BM25 keyword]
        → Reciprocal Rank Fusion (k=60)
        → jina-reranker-v2-base-multilingual
        → Top-n results

Components:
  - Chroma PersistentClient: local vector store
  - BM25Okapi (rank_bm25): in-memory keyword index
  - Jina AI jina-embeddings-v3: multilingual embeddings (en/zh/ms/ta)
  - Jina AI jina-reranker-v2-base-multilingual: cross-encoder reranking

Silently degrades to empty string when Chroma or API is unavailable.
"""
from __future__ import annotations

# WSL SQLite compatibility: Chroma requires sqlite3 >= 3.35.0
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

# Windows WMI compatibility
try:
    import platform as _platform
    _platform.system()
except OSError:
    _platform.system = lambda: "Windows"  # type: ignore[assignment]

import concurrent.futures
import os
import threading

import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

load_dotenv()

CHROMA_DIR       = Path(__file__).parent / "chroma_db"
EMBED_MODEL      = "jina-embeddings-v3"
RERANK_MODEL     = "jina-reranker-v2-base-multilingual"
RRF_K            = 60
TOP_WINDOW       = 20   # candidates per retrieval path fed into RRF
RERANK_WINDOW    = 5    # candidates passed from RRF to reranker
RERANK_THRESHOLD = 0.3  # minimum reranker score to inject context

_JINA_BASE = "https://api.jina.ai/v1"
_JINA_KEY  = os.getenv("JINA_API_KEY", "")

_TAMIL_REWRITE_PROMPT = (
    "Translate the following medical query to English. "
    "Output only the translated query, nothing else."
)


# ── Jina AI API calls ─────────────────────────────────────────────

def _jina_embed(texts: list[str]) -> list[list[float]]:
    """Call Jina AI embedding API, return list of vectors."""
    resp = requests.post(
        f"{_JINA_BASE}/embeddings",
        headers={"Authorization": f"Bearer {_JINA_KEY}", "Content-Type": "application/json"},
        json={"model": EMBED_MODEL, "input": texts},
        timeout=8,
    )
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in data]


def _jina_rerank(query: str, documents: list[str], top_n: int) -> list[tuple[float, str]]:
    """Call Jina AI reranker API, return [(score, text), ...] sorted desc."""
    resp = requests.post(
        f"{_JINA_BASE}/rerank",
        headers={"Authorization": f"Bearer {_JINA_KEY}", "Content-Type": "application/json"},
        json={"model": RERANK_MODEL, "query": query, "documents": documents, "top_n": top_n},
        timeout=8,
    )
    resp.raise_for_status()
    return [(r["relevance_score"], documents[r["index"]]) for r in resp.json()["results"]]


# ── Retriever ─────────────────────────────────────────────────────

class MedicalRetriever:
    def __init__(self):
        self._ready:      bool = False
        self._init_lock        = threading.Lock()
        self._collection       = None
        self._bm25             = None
        self._bm25_docs: list  = []

    def _init(self):
        if self._ready:
            return
        with self._init_lock:
            if self._ready:
                return
            try:
                import chromadb
                from chromadb.config import Settings

                client = chromadb.PersistentClient(
                    path=str(CHROMA_DIR),
                    settings=Settings(anonymized_telemetry=False),
                )
                self._collection = client.get_or_create_collection(
                    name="medical_chunks",
                    metadata={"hnsw:space": "cosine"},
                )

                if self._collection.count() == 0:
                    self._index_knowledge_base()
                else:
                    print(f"[RAG] Chroma ready: {self._collection.count()} chunks")

                self._build_bm25_index()
                self._ready = True
                print("[RAG] Retriever ready | Jina AI embedding + reranker")

            except ImportError as e:
                print(f"[RAG] Missing dependency ({e}): pip install chromadb rank-bm25")
            except Exception as e:
                print(f"[RAG] Init failed: {e}, RAG degraded")

    def _index_knowledge_base(self):
        """Chunk knowledge base, embed via Jina AI, write to Chroma."""
        from chatbot.memory.rag.loader import load_all_chunks

        chunks = load_all_chunks()
        if not chunks:
            print("[RAG] Knowledge base empty, skipping indexing")
            return

        texts = [c["text"] for c in chunks]
        print(f"[RAG] Embedding {len(texts)} chunks via Jina AI...")

        embeddings = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            embeddings.extend(_jina_embed(texts[i: i + batch_size]))
            print(f"[RAG] Progress: {min(i + batch_size, len(texts))}/{len(texts)}")

        self._collection.add(
            ids       = [c["id"]       for c in chunks],
            embeddings= embeddings,
            documents = [c["text"]     for c in chunks],
            metadatas = [c["metadata"] for c in chunks],
        )
        print(f"[RAG] Indexed {len(chunks)} chunks")

    def _build_bm25_index(self):
        """Load all docs from Chroma, build in-memory BM25 index."""
        from rank_bm25 import BM25Okapi

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                data = ex.submit(self._collection.get, include=["documents"]).result(timeout=30)
        except concurrent.futures.TimeoutError:
            print("[RAG] BM25 build timed out, degrading to pure dense retrieval")
            return
        except Exception as e:
            print(f"[RAG] BM25 build failed ({e}), degrading to pure dense retrieval")
            return

        docs = data["documents"]
        self._bm25_docs = list(zip(data["ids"], docs))
        self._bm25      = BM25Okapi([doc.lower().split() for doc in docs])
        print(f"[RAG] BM25 index built: {len(docs)} chunks")

    def retrieve(self, query: str, n: int = 3, lang: str = "") -> str:
        """
        Hybrid retrieval (Dense + BM25 + RRF + reranker).
        Returns reference text; empty string on failure or low relevance.
        """
        self._init()
        if not self._ready:
            return ""
        try:
            from chatbot.memory.rag.lang_detect import detect_lang, LANG_CODE
            lang_code = LANG_CODE.get(lang, lang) if lang else detect_lang(query)

            retrieval_query = query
            if lang_code == "ta":
                retrieval_query = self._rewrite_to_english(query)
                print(f"[RAG] Tamil rewritten → {retrieval_query!r}")

            docs = self._hybrid_search(retrieval_query, n)
            return "\n\n".join(docs) if docs else ""
        except Exception as e:
            print(f"[RAG] Retrieval failed: {e}")
            return ""

    def _rewrite_to_english(self, query: str) -> str:
        try:
            from chatbot.utils.llm_factory import call_sealion
            return call_sealion(_TAMIL_REWRITE_PROMPT, query, reasoning=False).strip() or query
        except Exception as e:
            print(f"[RAG] Tamil rewrite failed ({e})")
            return query

    def _hybrid_search(self, query: str, n: int) -> list[str]:
        query_vec  = _jina_embed([query])[0]
        candidates = self._rrf_merge(
            self._dense_search(query_vec),
            self._bm25_search(query),
            RERANK_WINDOW,
        )
        return self._rerank(query, candidates, n)

    def _dense_search(self, query_vec: list[float]) -> list[tuple]:
        n_results = min(TOP_WINDOW, self._collection.count())
        results   = self._collection.query(
            query_embeddings=[query_vec],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return [
            (results["ids"][0][i], results["documents"][0][i], 1.0 - results["distances"][0][i])
            for i in range(len(results["ids"][0]))
        ]

    def _bm25_search(self, query: str) -> list[tuple]:
        if not self._bm25:
            return []
        scores  = self._bm25.get_scores(query.lower().split())
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:TOP_WINDOW]
        return [
            (self._bm25_docs[i][0], self._bm25_docs[i][1], scores[i])
            for i in top_idx if scores[i] > 0
        ]

    @staticmethod
    def _rrf_merge(dense_rows: list, bm25_rows: list, n: int) -> list[str]:
        scores: dict[str, float] = {}
        texts:  dict[str, str]   = {}
        for rank, (doc_id, text, _) in enumerate(dense_rows, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            texts[doc_id]  = text
        for rank, (doc_id, text, _) in enumerate(bm25_rows, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            texts[doc_id]  = text
        return [texts[doc_id] for doc_id in sorted(scores, key=scores.get, reverse=True)[:n]]

    def _rerank(self, query: str, candidates: list[str], n: int) -> list[str]:
        if not candidates:
            return []
        try:
            ranked = _jina_rerank(query, candidates, top_n=n)
            if not ranked or ranked[0][0] < RERANK_THRESHOLD:
                print(f"[RAG] Reranker score {ranked[0][0] if ranked else 0:.3f} below threshold, skipping")
                return []
            return [text for _, text in ranked]
        except Exception as e:
            print(f"[RAG] Reranker failed ({e}), using RRF results")
            return candidates[:n]


# ── Singleton ─────────────────────────────────────────────────────

_retriever: Optional[MedicalRetriever] = None
_retriever_lock = threading.Lock()


def get_retriever() -> MedicalRetriever:
    global _retriever
    if _retriever is None:
        with _retriever_lock:
            if _retriever is None:
                _retriever = MedicalRetriever()
    return _retriever
