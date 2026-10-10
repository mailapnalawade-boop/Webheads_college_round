"""Shared, model-free text helpers: sentence splitting, tokenisation, negation."""
import re
from typing import List, Tuple

STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "of", "off", "over", "under",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "should", "would", "could", "ought", "this", "that",
    "these", "those", "can", "will", "may", "must", "it", "its", "they", "them",
    "as", "than", "then", "there", "their", "which", "who", "whom", "also",
})

NEGATION_TOKENS = frozenset({
    "not", "no", "never", "cannot", "none", "neither", "nor", "without", "nobody", "nothing",
})
_CONTRACTED_NEGATION = re.compile(r"\b\w+n['’]t\b", re.IGNORECASE)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n+")
_WORD = re.compile(r"[A-Za-z0-9]+(?:[.,][0-9]+)*")


_ABBREVIATIONS = frozenset({
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs", "etc", "inc", "ltd", "co", "corp", "no", "fig",
    "e.g", "i.e", "approx", "dept", "est", "mt", "gen", "col", "sen", "rep", "gov", "u.s", "u.k",
})


def _ends_with_abbreviation(text_before: str) -> bool:
    token = re.search(r"([A-Za-z.]+)\.$", text_before)
    if not token:
        return False
    word = token.group(1).lower()
    return word in _ABBREVIATIONS or (len(word) == 1 and word.isalpha())  # initials such as "J. K. Rowling"


def split_sentences(text: str) -> List[Tuple[str, int, int]]:
    """Split text into (sentence, start, end) tuples, preserving offsets. Abbreviation-aware."""
    sentences: List[Tuple[str, int, int]] = []
    cursor = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        if match.group(0).strip() == "" and text[match.start() - 1:match.start()] == "." \
                and _ends_with_abbreviation(text[cursor:match.start()]):
            continue
        _append_sentence(text, cursor, match.start(), sentences)
        cursor = match.end()
    _append_sentence(text, cursor, len(text), sentences)
    return sentences


def _append_sentence(text: str, start: int, end: int, out: List[Tuple[str, int, int]]) -> None:
    chunk = text[start:end]
    stripped = chunk.strip()
    if stripped:
        offset = start + (len(chunk) - len(chunk.lstrip()))
        out.append((stripped, offset, offset + len(stripped)))


def stem(word: str) -> str:
    """Very light suffix stripping so 'prescribed'/'prescribes' compare equal."""
    w = word.lower()
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    for suffix, min_len in (("ing", 6), ("ed", 5), ("es", 5), ("s", 4)):
        if len(w) >= min_len and w.endswith(suffix) and not w.endswith("ss"):
            return w[: -len(suffix)]
    return w


def content_stems(text: str) -> List[str]:
    """Lower-cased stemmed content words (no stop-words, no negations)."""
    tokens = (m.group(0).lower() for m in _WORD.finditer(text))
    return [stem(t) for t in tokens
            if t not in STOP_WORDS and t not in NEGATION_TOKENS and len(t) > 1]


def negation_count(text: str) -> int:
    words = re.findall(r"[a-z]+", text.lower())
    return sum(1 for w in words if w in NEGATION_TOKENS) + len(_CONTRACTED_NEGATION.findall(text))


def negation_parity_differs(a: str, b: str) -> bool:
    return (negation_count(a) % 2) != (negation_count(b) % 2)


def containment(claim: str, source: str) -> float:
    """Share of the claim's content stems found in the source. Retrieval/triage signal only."""
    claim_stems = set(content_stems(claim))
    if not claim_stems:
        return 0.0
    return len(claim_stems & set(content_stems(source))) / len(claim_stems)


def mask_spans(text: str, spans: List[Tuple[int, int]]) -> str:
    """Blank out character spans (used to compare context words without entities)."""
    chars = list(text)
    for start, end in spans:
        for i in range(max(0, start), min(len(chars), end)):
            chars[i] = " "
    return "".join(chars)


def bigram_overlap(claim: str, source: str) -> float:
    """Share of the claim's adjacent content-word pairs that also occur in the source (detects swapped roles)."""
    stems = content_stems(claim)
    pairs = list(zip(stems, stems[1:]))
    if not pairs:
        return 1.0
    src = content_stems(source)
    src_pairs = set(zip(src, src[1:]))
    return sum(p in src_pairs for p in pairs) / len(pairs)
