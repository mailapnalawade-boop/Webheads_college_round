"""Deterministic comparison of hard facts (numbers, years, frequencies, proper names).

This is a *safety net* beside the semantic models: neural NLI is known to miss swapped
numbers and names, while exact value comparison cannot. It never says a claim is true;
it can only report a verified mismatch between a claim and a source sentence.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.text_utils import content_stems, mask_spans

NUMBER, YEAR, FREQUENCY, NAME = "NUMBER", "YEAR", "FREQUENCY", "NAME"

_SCALES = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "trillion": 1e12}
# unit -> (dimension, factor to base unit)
_UNITS = {
    "%": ("pct", 1), "percent": ("pct", 1), "mg": ("mass", 1), "mcg": ("mass", 1e-3), "g": ("mass", 1e3),
    "kg": ("mass", 1e6), "lb": ("mass", 4.5359e5), "lbs": ("mass", 4.5359e5), "ml": ("vol", 1), "l": ("vol", 1e3),
    "mm": ("len", 1), "cm": ("len", 10), "m": ("len", 1e3), "km": ("len", 1e6),
    "second": ("time", 1), "minute": ("time", 60), "min": ("time", 60), "hour": ("time", 3600),
    "hr": ("time", 3600), "day": ("time", 86400), "week": ("time", 604800), "month": ("time", 2.6e6),
    "year": ("time", 3.15e7), "dollar": ("cur_usd", 1), "usd": ("cur_usd", 1), "rupee": ("cur_inr", 1),
    "euro": ("cur_eur", 1), "celsius": ("temp_c", 1), "fahrenheit": ("temp_f", 1),
}
_FREQ_WORDS = {"once": 1, "twice": 2, "thrice": 3}
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_PERIOD = r"(?:day|daily|week|weekly|month|monthly|year|yearly|hour|hourly)"
_FREQ_RE = re.compile(
    rf"\b(?P<w>once|twice|thrice)\b(?=\s+(?:a|per|each|every)?\s*{_PERIOD})"
    rf"|\b(?P<n>\d+|{'|'.join(_NUM_WORDS)})\s+times\b", re.IGNORECASE)
_UNIT_PATTERN = (r"%|percent|per\s?cent|mcg|mg|kg|g|ml|l|mm|cm|km|m|lbs?|"
                 r"hours?|hrs?|minutes?|mins?|seconds?|days?|weeks?|months?|years?|dollars?|usd|rupees?|euros?|"
                 r"degrees?\s+celsius|degrees?\s+fahrenheit|celsius|fahrenheit")
_NUM_RE = re.compile(
    rf"(?P<cur>[$₹€£])?(?<![\w.])(?P<int>\d{{1,3}}(?:,\d{{3}})+|\d+)(?P<dec>\.\d+)?"
    rf"(?:\s*(?P<scale>thousand|million|billion|trillion|bn|mn|k)\b)?"
    rf"(?:\s*(?P<unit>{_UNIT_PATTERN})(?![A-Za-z]))?", re.IGNORECASE)
_TITLES = re.compile(r"\b(?:Dr|Mr|Mrs|Ms|Prof|Professor|Sir)\.?\s+(?=[A-Z])")
_NAME_RE = re.compile(
    r"\b[A-Z][A-Za-z'’\-]*(?:\s+(?:(?:of|de|del|la|van|von)\s+)?[A-Z][A-Za-z'’\-]*)*")
_LEADING_NON_NAMES = frozenset(w.lower() for w in (
    "The A An In On At This That These Those It He She They We I Our Their His Her Its According However But And Or If "
    "When While After Before Since During Overall Also There Here Some Many Most All Each Every No Not Yes For From To "
    "By With Is Are Was Were Do Does Did Can Could Should Would May Might Must Will What Which Who How Why Where "
    "Because Although Though Thus Therefore Hence So Then").split())
_REL_SIGNS = ".!?\n:\"'(["


@dataclass(frozen=True)
class Entity:
    kind: str
    text: str
    start: int
    end: int
    value: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
    dimension: str = ""
    norm: str = ""
    weak: bool = False


@dataclass(frozen=True)
class Mismatch:
    kind: str
    claim_entity: Entity
    source_entity: Entity


@dataclass
class EntityComparison:
    mismatches: List[Mismatch]
    context_overlap: int
    related: bool
    context_shift: bool = False  # year/name AND number differ together: probably a different situation, not an error

    @property
    def has_verified_mismatch(self) -> bool:
        return self.related and bool(self.mismatches)


def extract_entities(text: str) -> List[Entity]:
    entities: List[Entity] = []
    taken: List[Tuple[int, int]] = []
    for m in _FREQ_RE.finditer(text):
        word = (m.group("w") or m.group("n")).lower()
        value = _FREQ_WORDS.get(word) or _NUM_WORDS.get(word) or int(word)
        entities.append(Entity(FREQUENCY, m.group(0), m.start(), m.end(), value=float(value), norm=f"{value}x"))
        taken.append((m.start(), m.end()))
    entities.extend(_extract_numbers(text, taken))
    entities = _merge_ranges(text, entities)
    entities.extend(_extract_names(text, taken))
    return sorted(entities, key=lambda e: e.start)


def _extract_numbers(text: str, taken: List[Tuple[int, int]]) -> List[Entity]:
    found: List[Entity] = []
    for m in _NUM_RE.finditer(text):
        if any(m.start() < e and s < m.end() for s, e in taken):
            continue
        value = float((m.group("int") + (m.group("dec") or "")).replace(",", ""))
        scale = (m.group("scale") or "").lower()
        value *= _SCALES.get(scale, 1)
        unit_raw = re.sub(r"\s+", " ", (m.group("unit") or "")).lower()
        unit_key = _unit_key(unit_raw, m.group("cur"))
        dim, factor = _UNITS.get(unit_key, ("", 1))
        is_year = (not dim and not scale and "," not in m.group("int") and not m.group("dec")
                   and 1000 <= value <= 2100 and len(m.group("int")) == 4)
        base = value * factor
        found.append(Entity(YEAR if is_year else NUMBER, m.group(0).strip(), m.start(), m.start() + len(m.group(0).rstrip()),
                            value=base, dimension=dim, norm=f"{base:g}{dim}"))
    return found


def _unit_key(unit: str, currency: Optional[str]) -> str:
    if currency:
        return {"$": "dollar", "₹": "rupee", "€": "euro", "£": "dollar"}[currency]
    unit = unit.replace("per cent", "percent")
    for name in ("celsius", "fahrenheit"):
        if name in unit:
            return name
    unit = re.sub(r"s$", "", unit) if unit not in ("lbs",) else unit
    return unit


def _merge_ranges(text: str, entities: List[Entity]) -> List[Entity]:
    nums = sorted((e for e in entities if e.kind == NUMBER), key=lambda e: e.start)
    others = [e for e in entities if e.kind != NUMBER]
    merged: List[Entity] = []
    i = 0
    while i < len(nums):
        cur = nums[i]
        nxt = nums[i + 1] if i + 1 < len(nums) else None
        if nxt and re.fullmatch(r"\s*(?:to|-|–|—)\s*", text[cur.end:nxt.start]) and \
                (not cur.dimension or not nxt.dimension or cur.dimension == nxt.dimension):
            low, high = sorted((cur.value, nxt.value))
            dim = cur.dimension or nxt.dimension
            merged.append(Entity(NUMBER, text[cur.start:nxt.end], cur.start, nxt.end, value=low, low=low, high=high,
                                 dimension=dim, norm=f"{low:g}-{high:g}{dim}"))
            i += 2
        else:
            merged.append(cur)
            i += 1
    return merged + others


def _extract_names(text: str, taken: List[Tuple[int, int]]) -> List[Entity]:
    cleaned = _TITLES.sub(lambda m: " " * len(m.group(0)), text)
    names: List[Entity] = []
    for m in _NAME_RE.finditer(cleaned):
        words = list(re.finditer(r"\S+", m.group(0)))
        while words and words[0].group(0).lower() in _LEADING_NON_NAMES:
            words.pop(0)
        if not words:
            continue
        start, end = m.start() + words[0].start(), m.start() + words[-1].end()
        if any(start < e and s < end for s, e in taken):
            continue
        surface = cleaned[start:end].replace("’s", "").replace("'s", "")
        prefix = cleaned[:start].rstrip()
        at_sentence_start = (not prefix) or prefix[-1] in _REL_SIGNS
        titled = re.search(r"\b(?:Dr|Mr|Mrs|Ms|Prof|Professor|Sir)\.?\s+$", text[:start]) is not None
        weak = at_sentence_start and len(words) == 1 and not titled  # a title proves it is a person's name
        names.append(Entity(NAME, surface, start, end, norm=surface.lower(), weak=weak))
    return names


def _values_equal(c: Entity, s: Entity) -> bool:
    if c.kind != s.kind:
        return False
    if c.kind == NAME:
        return _names_match(c.norm, s.norm)
    if c.kind == NUMBER and c.dimension and s.dimension and c.dimension != s.dimension:
        return False
    if c.value is None or s.value is None:
        return False
    s_low, s_high = (s.low, s.high) if s.low is not None else (s.value, s.value)
    c_low, c_high = (c.low, c.high) if c.low is not None else (c.value, c.value)
    tol = 1e-9 + 1e-6 * max(abs(c.value), abs(s.value))
    return c_high >= s_low - tol and c_low <= s_high + tol


def _names_match(a: str, b: str) -> bool:
    ta, tb = set(re.findall(r"\w+", a)), set(re.findall(r"\w+", b))
    return bool(ta and tb) and (ta <= tb or tb <= ta)


def _compatible(c: Entity, s: Entity) -> bool:
    if c.kind == NAME:
        return not c.weak and not s.weak
    if c.kind == NUMBER:
        return not c.dimension or not s.dimension or c.dimension == s.dimension
    return True


def _present_in(entity: Entity, other_text: str) -> bool:
    """Is the entity's surface form already stated in the other text (so it cannot be a mismatch)?"""
    if entity.kind != NAME:
        return False
    return re.search(rf"\b{re.escape(entity.norm)}\b", other_text.lower()) is not None


def compare_entities(claim: str, source: str) -> EntityComparison:
    claim_ents, source_ents = extract_entities(claim), extract_entities(source)
    mismatches: List[Mismatch] = []
    for kind in (NUMBER, YEAR, FREQUENCY, NAME):
        c_all = [e for e in claim_ents if e.kind == kind]
        s_all = [e for e in source_ents if e.kind == kind]
        c_open = [c for c in c_all if not any(_values_equal(c, s) for s in s_all) and not _present_in(c, source)]
        s_open = [s for s in s_all if not any(_values_equal(c, s) for c in c_all) and not _present_in(s, claim)]
        for c in c_open:
            partner = next((s for s in s_open if _compatible(c, s)), None)
            if partner:
                mismatches.append(Mismatch(kind, c, partner))
    # Context = words shared once the *conflicting* values are blanked out. Shared names/topics
    # (e.g. the drug, the tower) count as context: they prove both texts talk about the same thing.
    c_ctx = set(content_stems(mask_spans(claim, [(m.claim_entity.start, m.claim_entity.end) for m in mismatches])))
    s_ctx = set(content_stems(mask_spans(source, [(m.source_entity.start, m.source_entity.end) for m in mismatches])))
    overlap = len(c_ctx & s_ctx)
    kinds = {m.kind for m in mismatches}
    context_shift = bool(kinds & {YEAR, NAME}) and bool(kinds & {NUMBER, FREQUENCY})
    related = overlap >= min(2, max(1, len(c_ctx))) and not context_shift
    return EntityComparison(mismatches, overlap, related, context_shift)


def entity_masked(text: str) -> str:
    """Text with all numbers/years/frequencies/names blanked, so only the wording around them remains."""
    return mask_spans(text, [(e.start, e.end) for e in extract_entities(text)])


def all_values_matched(claim: str, source: str) -> bool:
    """Every number/year/frequency/name in the claim is present, with an equal value, in the source."""
    c_ents, s_ents = extract_entities(claim), extract_entities(source)
    if not c_ents:
        return False
    return all(any(_values_equal(c, s) for s in s_ents) or _present_in(c, source) for c in c_ents)
