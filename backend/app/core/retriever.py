import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.text_utils import STOP_WORDS as _SHARED_STOP_WORDS

class PassageRetriever:
    """
    Hybrid retriever using BM25 and weighted lexical keyword overlap.
    Retrieves evidence passages with true semantic relevance and prevents artificial score inflation.
    """

    STOP_WORDS = _SHARED_STOP_WORDS

    def __init__(self, passages: List[Dict[str, Any]], embedder: Optional[Any] = None):
        self.passages = passages
        self.embedder = embedder
        self._vectors = embedder.encode([p["text"] for p in passages]) if embedder and passages else []
        self.corpus = [self._tokenize(p["text"]) for p in passages]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus and any(self.corpus) else None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def retrieve(self, claim_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.passages:
            return []

        tokenized_claim = self._tokenize(claim_text)
        if not tokenized_claim:
            return []

        # Filter out common stop words to focus on meaningful content words
        meaningful_claim_tokens = [t for t in tokenized_claim if t not in PassageRetriever.STOP_WORDS and len(t) > 1]
        claim_set = set(meaningful_claim_tokens) if meaningful_claim_tokens else set(tokenized_claim)

        # Get raw BM25 scores
        raw_bm25 = self.bm25.get_scores(tokenized_claim) if self.bm25 else [0.0] * len(self.passages)
        clamped_bm25 = [max(0.0, float(s)) for s in raw_bm25]
        max_bm25 = max(clamped_bm25) if clamped_bm25 else 0.0

        results = []
        semantic = self._semantic_scores(claim_text)

        for idx, passage in enumerate(self.passages):
            passage_tokens = self.corpus[idx]
            passage_set = set(passage_tokens)

            # Calculate meaningful keyword overlap
            shared_tokens = claim_set.intersection(passage_set)
            overlap_ratio = len(shared_tokens) / len(claim_set) if claim_set else 0.0

            # Calculate numbers overlap if claim contains numeric values
            claim_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', claim_text))
            passage_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', passage["text"]))
            has_num_match = bool(claim_nums and claim_nums.intersection(passage_nums))

            # Proper BM25 scaling without artificially inflating 0-relevance documents
            if max_bm25 > 2.0:
                bm25_score = min(1.0, clamped_bm25[idx] / 10.0)
            elif max_bm25 > 0.0:
                bm25_score = min(1.0, clamped_bm25[idx] / (max_bm25 * 2.0))
            else:
                bm25_score = 0.0

            sim = semantic[idx]
            lexical = 0.0
            if shared_tokens:
                lexical = 0.6 * overlap_ratio + 0.4 * bm25_score
                if has_num_match:
                    lexical = min(1.0, lexical + 0.15)

            # Hybrid: lexical evidence blended with meaning-based similarity (finds paraphrases)
            combined_score = round(0.55 * lexical + 0.45 * sim if self.embedder else lexical, 4)
            lexical_ok = (combined_score >= 0.15 or len(shared_tokens) >= 2) and len(shared_tokens) >= 1
            semantic_ok = bool(self.embedder) and sim >= settings.SEMANTIC_MIN_SIMILARITY
            if lexical_ok or semantic_ok:
                results.append({
                    "excerpt": passage["text"],
                    "source_name": passage["source_name"],
                    "page_number": passage.get("page_number", 1),
                    "relevance_score": max(combined_score, round(sim * 0.8, 4)) if semantic_ok and not lexical_ok else combined_score,
                    "match_type": "bm25_passage" if lexical_ok else "semantic_passage",
                })

        # Sort by relevance descending with deterministic tie-breaker
        results.sort(key=lambda x: (x["relevance_score"], x["source_name"], x.get("page_number", 1)), reverse=True)
        # Deduplicate evidence passages with identical or near-identical text content
        deduped_results = []
        seen_excerpts = set()
        for res in results:
            norm_excerpt = re.sub(r'\s+', ' ', res["excerpt"].strip().lower())
            if norm_excerpt not in seen_excerpts:
                seen_excerpts.add(norm_excerpt)
                deduped_results.append(res)

        return deduped_results[:top_k]

    def _semantic_scores(self, claim_text: str) -> List[float]:
        if not self.embedder or not self._vectors:
            return [0.0] * len(self.passages)
        q = self.embedder.encode([claim_text])[0]
        return [max(0.0, sum(a * b for a, b in zip(q, v))) for v in self._vectors]

    @staticmethod
    def search_web(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Fetches external public web search snippets using DuckDuckGo when document context is absent.
        """
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                for r in ddg_results:
                    snippet = r.get("body", "") or r.get("snippet", "")
                    title = r.get("title", "Public Web")
                    if snippet:
                        results.append({
                            "excerpt": snippet,
                            "source_name": f"Web: {title}",
                            "page_number": 1,
                            "relevance_score": 0.65,
                            "match_type": "web_search"
                        })
            return results
        except Exception:
            return []

