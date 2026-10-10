import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

class PassageRetriever:
    """
    Hybrid retriever using BM25 and lexical keyword overlap to retrieve relevant passages.
    Handles single-document edge cases where BM25 IDF can be negative.
    """

    def __init__(self, passages: List[Dict[str, Any]]):
        self.passages = passages
        self.corpus = [self._tokenize(p["text"]) for p in passages]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus and any(self.corpus) else None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Lowercase and split into alphanumeric tokens
        return re.findall(r'\w+', text.lower())

    def retrieve(self, claim_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.passages:
            return []

        tokenized_claim = self._tokenize(claim_text)
        if not tokenized_claim:
            return []

        claim_set = set(tokenized_claim)
        
        # Calculate BM25 scores if BM25 model exists
        raw_bm25 = self.bm25.get_scores(tokenized_claim) if self.bm25 else [0.0] * len(self.passages)
        # Clamp negative BM25 scores to 0.0
        clamped_bm25 = [max(0.0, float(s)) for s in raw_bm25]
        max_bm25 = max(clamped_bm25) if clamped_bm25 and max(clamped_bm25) > 0 else 1.0

        results = []

        for idx, passage in enumerate(self.passages):
            passage_tokens = self.corpus[idx]
            passage_set = set(passage_tokens)

            # BM25 component normalized (0.0 to 1.0)
            bm25_normalized = (clamped_bm25[idx] / max_bm25) if max_bm25 > 0 else 0.0

            # Token overlap component (Jaccard / Recall against claim tokens)
            shared_tokens = claim_set.intersection(passage_set)
            # Filter stop words from overlap ratio calculation for higher precision
            meaningful_shared = [t for t in shared_tokens if len(t) > 2 and t not in {"the", "and", "was", "for", "with", "that", "this"}]
            meaningful_claim = [t for t in claim_set if len(t) > 2 and t not in {"the", "and", "was", "for", "with", "that", "this"}]
            
            overlap_ratio = len(meaningful_shared) / len(meaningful_claim) if meaningful_claim else (len(shared_tokens) / len(claim_set) if claim_set else 0.0)

            # Combined score giving strong weight to keyword overlap
            combined_score = round(max(bm25_normalized * 0.5 + overlap_ratio * 0.5, overlap_ratio), 4)

            if combined_score > 0.10:
                results.append({
                    "excerpt": passage["text"],
                    "source_name": passage["source_name"],
                    "page_number": passage.get("page_number", 1),
                    "relevance_score": combined_score,
                    "match_type": "bm25_passage"
                })

        # Sort by relevance descending
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]
