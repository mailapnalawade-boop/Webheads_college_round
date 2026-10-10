import re
from typing import List, Dict, Any

class ClaimExtractor:
    """
    Decomposes raw text into atomic factual claims with character position tracking.
    Uses robust sentence boundary detection and heuristic clause splitting.
    """

    @staticmethod
    def extract_claims(text: str) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        claims = []
        # Match sentences or bullet points while preserving character offset
        # Handles bullet markers, numbered lists, standard punctuation (. ! ?)
        pattern = re.compile(r'(?:[^\.\!\?\n]+[\.\!\?\n]+|\S[^\.\!\?\n]*$)')
        
        raw_matches = list(pattern.finditer(text))
        
        claim_index = 1
        for match in raw_matches:
            raw_segment = match.group()
            start_char = match.start()
            
            # Clean text (remove leading bullet points, numbers, markdown formatting)
            cleaned_text = re.sub(r'^[ \t]*[\*\-\+\d\.\)\s]+', '', raw_segment).strip()
            
            # Skip empty, ultra-short, or conversational filler lines
            if len(cleaned_text) < 5 or cleaned_text.lower() in [
                "in conclusion", "for example", "note that", "summary", "as mentioned"
            ]:
                continue
            
            # Adjust offset for leading whitespace trimmed
            offset_start = start_char + raw_segment.find(cleaned_text[0]) if cleaned_text and raw_segment.find(cleaned_text[0]) != -1 else start_char
            offset_end = offset_start + len(cleaned_text)

            claims.append({
                "claim_id": f"claim_{claim_index}",
                "text": cleaned_text,
                "start_char": offset_start,
                "end_char": offset_end
            })
            claim_index += 1

        return claims
