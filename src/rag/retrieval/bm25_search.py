import os
import pickle
import re

from rank_bm25 import BM25Okapi

from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class BM25Searcher:
    """
    Local Sparse Keyword Searcher using Rank-BM25.
    Features metadata pre-filtering, clean text tokenization, and graceful error handling.
    """
    def __init__(self, corpus_path: str = "data/processed/bm25_corpus.pkl"):
        self.corpus_path = corpus_path
        self.corpus: list[Document] = []
        self._load_corpus()

    def _load_corpus(self) -> None:
        """
        Loads the compiled unified corpus from disk.
        """
        if not os.path.exists(self.corpus_path):
            logger.warning(f"BM25 corpus file not found at '{self.corpus_path}'. Sparse search will be disabled.")
            self.corpus = []
            return

        try:
            with open(self.corpus_path, "rb") as f:
                self.corpus = pickle.load(f)
            logger.info(f"Successfully loaded {len(self.corpus)} documents into BM25 index.")
        except Exception as e:
            logger.error(f"Failed to deserialize BM25 corpus: {e}")
            self.corpus = []

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenizes text by converting to lowercase and extraction of alphanumeric words.
        """
        if not text:
            return []
        text_lower = text.lower()
        # Find alphanumeric words (removes punctuation)
        words = re.findall(r'\b\w+\b', text_lower)
        return words

    def search(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        department: str | None = None,
        doc_type: str | None = None
    ) -> list[Document]:
        """
        Executes sparse keyword search on the pre-filtered corpus.
        Safe execution boundary: catches all exceptions and logs them without throwing.
        """
        if not query.strip() or not self.corpus:
            return []

        try:
            # 1. Pre-filtering the corpus by metadata attributes
            filtered_corpus: list[Document] = []
            for doc in self.corpus:
                meta = doc.metadata or {}
                
                # Check category filter
                if category and meta.get("category") != category:
                    continue
                
                # Check department filter
                if department and meta.get("department_id") != department.strip().lower():
                    # Handle fallback matching
                    if meta.get("department") != department.strip().lower():
                        continue
                
                # Check doc type filter
                if doc_type and meta.get("type") != doc_type:
                    continue
                
                filtered_corpus.append(doc)

            if not filtered_corpus:
                logger.debug(f"BM25: Pre-filtering resulted in empty corpus for filters (cat={category}, dept={department}, type={doc_type}).")
                return []

            # 2. Tokenize corpus and query
            tokenized_corpus = [self._tokenize(doc.page_content) for doc in filtered_corpus]
            query_tokens = self._tokenize(query)

            if not query_tokens:
                return []

            # 3. Instantiate BM25Okapi dynamically on the filtered subset
            bm25 = BM25Okapi(tokenized_corpus)
            scores = bm25.get_scores(query_tokens)

            # 4. Compile results with scores
            ranked_results = []
            for idx, score in enumerate(scores):
                # We only keep items with keyword overlap (score > 0)
                if score > 0.0:
                    original_doc = filtered_corpus[idx]
                    
                    # Create a copy of the document and update metadata with score
                    metadata = original_doc.metadata.copy()
                    metadata.update({
                        "score": float(score),
                        "search_type": "sparse"
                    })
                    
                    doc_copy = Document(page_content=original_doc.page_content, metadata=metadata)
                    ranked_results.append((score, doc_copy))

            # 5. Sort by score in descending order
            ranked_results.sort(key=lambda x: x[0], reverse=True)
            top_docs = [item[1] for item in ranked_results[:limit]]
            
            logger.debug(f"BM25: Sparse search retrieved {len(top_docs)} matches for query: '{query}'")
            return top_docs

        except Exception as e:
            logger.error(f"Error during BM25 search: {e}")
            # Fault-tolerant response: return empty list on failure
            return []
