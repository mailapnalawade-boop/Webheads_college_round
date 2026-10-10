"""Evaluation harness.  Usage (from backend/):

    python -m tests.eval.run                 # current engine, semantic models if installed
    python -m tests.eval.run --no-models     # force the model-free (entity + near-verbatim) mode
    python -m tests.eval.run --legacy        # the previous keyword/antonym engine, for before/after
    python -m tests.eval.run --verbose       # show every wrong answer

Exit code is non-zero if a safety gate fails (see GATES).
"""
import argparse
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

from app.core.judge import SemanticJudge
from app.core.model_registry import registry
from app.core.parser import DocumentParser
from app.core.retriever import PassageRetriever
from app.schemas.audit import DocumentInput, VerdictEnum
from tests.eval.cases import CASES

GATES = {"missed_error_rate_max": 0.05, "false_alarm_rate_max": 0.10, "contradiction_recall_min_with_nli": 0.80}


def label(verdict) -> str:
    v = verdict.value if hasattr(verdict, "value") else str(verdict)
    return {"SUPPORTED": "SUPPORTED", "CONTRADICTED": "CONTRADICTED"}.get(v, "UNCERTAIN")


def build_runner(use_legacy: bool):
    if use_legacy:
        from tests.eval.legacy_baseline import DeterministicVerifier

        def run(retriever, claim):
            ev = retriever.retrieve(claim, top_k=3)
            verdict, conf, _ = DeterministicVerifier.verify_claim(claim, ev)
            return verdict, conf, None
        return run
    judge = SemanticJudge(registry.nli, registry.embedder)

    def run(retriever, claim):
        j = judge.judge(claim, retriever.retrieve(claim, top_k=3))
        return j.verdict, j.confidence, j.span.text if j.span else None
    return run


def evaluate(use_legacy: bool) -> Tuple[List[dict], Dict[str, float]]:
    runner = build_runner(use_legacy)
    rows = []
    for tag, source, claim, expected, err_text in CASES:
        passages = DocumentParser.parse_documents([DocumentInput(filename="src.txt", content=source)])
        verdict, conf, span = runner(PassageRetriever(passages, embedder=None if use_legacy else registry.embedder), claim)
        rows.append({"tag": tag, "claim": claim, "expected": expected, "got": label(verdict), "raw": verdict,
                     "conf": conf, "span": span, "err_text": err_text})
    return rows, summarize(rows)


def summarize(rows: List[dict]) -> Dict[str, float]:
    err = [r for r in rows if r["expected"] == "CONTRADICTED"]
    ok = [r for r in rows if r["expected"] == "SUPPORTED"]
    flagged = [r for r in rows if r["got"] == "CONTRADICTED"]
    spans = [r for r in err if r["err_text"] and r["got"] == "CONTRADICTED"]
    pct = lambda n, d: (n / d) if d else 0.0  # noqa: E731
    return {
        "accuracy": pct(sum(r["expected"] == r["got"] for r in rows), len(rows)),
        "contradiction_recall": pct(sum(r["got"] == "CONTRADICTED" for r in err), len(err)),
        "contradiction_precision": pct(sum(r["expected"] == "CONTRADICTED" for r in flagged), len(flagged)),
        "missed_error_rate": pct(sum(r["got"] == "SUPPORTED" for r in err), len(err)),       # wrong claim passed as true
        "false_alarm_rate": pct(sum(r["got"] == "CONTRADICTED" for r in ok), len(ok)),        # correct claim called wrong
        "support_recall": pct(sum(r["got"] == "SUPPORTED" for r in ok), len(ok)),
        "unsupported_wrongly_flagged": pct(sum(r["got"] != "UNCERTAIN" for r in rows if r["expected"] == "UNCERTAIN"),
                                            sum(r["expected"] == "UNCERTAIN" for r in rows)),
        "span_exact": pct(sum(r["span"] == r["err_text"] for r in spans), len(spans)),
    }


def print_report(rows, m, title: str, verbose: bool) -> None:
    print(f"\n=== {title}  ({len(rows)} cases) ===")
    for k, v in m.items():
        print(f"  {k:30s} {v:6.1%}")
    by_tag = defaultdict(list)
    for r in rows:
        by_tag[r["tag"]].append(r["expected"] == r["got"])
    print("\n  accuracy by case type:")
    for tag, hits in by_tag.items():
        print(f"    {tag:12s} {sum(hits):2d}/{len(hits):2d}")
    print("\n  calibration (is higher confidence really more often right?):")
    for lo, hi in ((0.0, 0.5), (0.5, 0.75), (0.75, 0.9), (0.9, 1.01)):
        bucket = [r for r in rows if lo <= r["conf"] < hi]
        if bucket:
            acc = sum(r["expected"] == r["got"] for r in bucket) / len(bucket)
            print(f"    confidence {lo:.2f}-{min(hi, 1):.2f}: n={len(bucket):2d}  actually right {acc:5.1%}")
    wrong = [r for r in rows if r["expected"] != r["got"] and (verbose or r["got"] == "SUPPORTED" and r["expected"] == "CONTRADICTED")]
    if wrong:
        print("\n  " + ("all wrong answers:" if verbose else "DANGEROUS misses (wrong claim passed as supported):"))
        for r in wrong:
            print(f"    [{r['tag']}] expected {r['expected']}, got {r['got']}: {r['claim']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", action="store_true")
    ap.add_argument("--no-models", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.no_models:
        registry.override(None, None)
    rows, m = evaluate(args.legacy)
    mode = "LEGACY keyword/antonym engine" if args.legacy else (
        f"current engine, NLI={getattr(registry.nli, 'name', 'not loaded')}")
    print_report(rows, m, mode, args.verbose)
    if args.legacy:
        return 0
    failures = []
    if m["missed_error_rate"] > GATES["missed_error_rate_max"]:
        failures.append("missed_error_rate")
    if m["false_alarm_rate"] > GATES["false_alarm_rate_max"]:
        failures.append("false_alarm_rate")
    if registry.nli and m["contradiction_recall"] < GATES["contradiction_recall_min_with_nli"]:
        failures.append("contradiction_recall")
    print("\n  GATES:", "PASS" if not failures else "FAIL -> " + ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
