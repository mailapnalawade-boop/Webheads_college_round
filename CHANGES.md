# What changed in this upgrade

## Detection (backend/app/core)
- `fallback.py` (keyword + hand-written antonym rules, hardcoded test words) **removed**.
- `judge.py` new verdict policy: verified value mismatch -> NLI meaning judgement -> (no model) near-verbatim only, else AMBIGUOUS.
- `nli.py`, `embeddings.py`, `model_registry.py`: lazy, injectable semantic models.
- `entity_check.py`: exact comparison of numbers (units, ranges), years, frequencies, names; context-shift guard.
- `llm_verifier.py`: Gemini must quote the source verbatim; quote verified in code; fabricated quotes are downgraded; cross-checked with the local judge.
- `consistency.py`: internal contradictions via value mismatch, polarity flip and NLI (both directions).
- `confidence.py`: confidence computed from signals, never self-reported.
- `retriever.py`: BM25 + embedding hybrid.

## Structure
- `verifier.py` 677 -> ~330 lines of orchestration only; error mapping, cache, LLM calls moved to their own modules.
- Module-level cache dict replaced with an injectable `LRUCache`.

## API / UI
- New verdict `AMBIGUOUS`; new claim fields `error_category`, `error_span`, `confidence_signals`; `warnings` on the response; `ambiguous_count` in the summary.
- Highlighter underlines the exact wrong words; Ambiguous filter and badge.

## Tests
- `tests/eval`: 67 labeled cases + harness + baseline of the old engine.
- `tests/test_semantic_pipeline.py`: decision-logic tests (scripted stand-in model).
- Tests that need real meaning understanding are marked `requires_nli`.
