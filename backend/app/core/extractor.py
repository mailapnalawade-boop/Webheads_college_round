import re
from typing import List, Dict, Any

class ClaimExtractor:
    """
    Decomposes raw text into atomic factual claims with precise character position tracking.
    Filters out section headings, document titles, formatting artifacts, questions, page numbers, and non-claim text.
    """

    HEADING_PATTERNS = [
        r'^\s*#{1,6}\s+',                                            # Markdown headers (# Header)
        r'^\s*(?:section|chapter|part|principle|rule|guideline|policy|article|appendix)\s+[0-9ivxlcdm\.]+', # Section 1, Principle 2, Rule III
        r'^\s*(?:[IVXLCDM]+\.|\d+(?:\.\d+)*)\s+[A-Z]',               # I. Code of Conduct, 1.1 Executive Summary
        r'^\s*(?:table of contents|executive summary|introduction|conclusion|overview|background|abstract|references|appendix|methods|results|discussion|notes|disclaimer|copyright|terms of use)\s*:?\s*$'
    ]

    NON_CLAIM_FILLERS = {
        "in conclusion", "for example", "note that", "summary", "as mentioned",
        "table of contents", "executive summary", "introduction", "overview",
        "references", "appendix", "background", "abstract", "all rights reserved",
        "terms of service", "privacy policy", "disclaimer"
    }

    @staticmethod
    def extract_claims(text: str) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        claims = []
        seen_texts = set()

        # Match sentences or bullet points while preserving character offset
        pattern = re.compile(r'(?:[^\.\!\?\n]+[\.\!\?\n]+|\S[^\.\!\?\n]*$)')
        raw_matches = list(pattern.finditer(text))
        
        claim_index = 1
        for match in raw_matches:
            raw_segment = match.group()
            start_char = match.start()
            
            # Clean text (remove leading markdown bullets, numbers, dashes)
            cleaned_text = re.sub(r'^[ \t]*[\*\-\+\d\.\)\s]+', '', raw_segment).strip()
            # Clean trailing markdown artifacts
            cleaned_text = re.sub(r'[\*\_\#]+$', '', cleaned_text).strip()
            
            # Skip empty or ultra-short segments
            if len(cleaned_text) < 8:
                continue

            cleaned_lower = cleaned_text.lower().strip(":")

            # Skip common non-claim fillers or headings
            if cleaned_lower in ClaimExtractor.NON_CLAIM_FILLERS:
                continue

            # Skip questions (not factual assertions)
            if cleaned_text.endswith("?"):
                continue

            # Skip section headings matching heading patterns
            if any(re.match(pattern, raw_segment, re.IGNORECASE) for pattern in ClaimExtractor.HEADING_PATTERNS):
                continue
            if any(re.match(pattern, cleaned_text, re.IGNORECASE) for pattern in ClaimExtractor.HEADING_PATTERNS):
                continue

            # Skip lines ending with colon that act as headers (e.g. "Key Findings:", "Section 1:")
            if cleaned_text.endswith(":") and len(cleaned_text.split()) <= 5:
                continue

            # Skip short noun-only section titles without main verbs
            words = re.findall(r'\b[a-zA-Z]{2,}\b', cleaned_text)
            has_verb = re.search(r'\b(is|are|was|were|has|have|had|should|must|can|could|will|would|may|might|increase|increased|decreased|shows|showed|found|reported|stated|contains|causes|caused|recommends|recommended|requires|required|prohibits|allows|allowed|prefers|preferred)\b', cleaned_text, re.IGNORECASE)
            
            if len(words) <= 4 and not has_verb:
                continue

            # Calculate precise start and end character offsets
            sub_pos = raw_segment.find(cleaned_text)
            offset_start = start_char + sub_pos if sub_pos != -1 else start_char
            offset_end = offset_start + len(cleaned_text)

            # Avoid duplicate claims
            norm_key = cleaned_lower
            if norm_key in seen_texts:
                continue
            seen_texts.add(norm_key)

            claims.append({
                "claim_id": f"claim_{claim_index}",
                "text": cleaned_text,
                "start_char": offset_start,
                "end_char": offset_end
            })
            claim_index += 1

        return claims


