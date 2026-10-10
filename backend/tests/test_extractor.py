import pytest
from app.core.extractor import ClaimExtractor

def test_extract_claims_basic():
    text = "Amoxicillin is prescribed for pneumonia. The dose is 50mg daily."
    claims = ClaimExtractor.extract_claims(text)
    
    assert len(claims) == 2
    assert claims[0]["claim_id"] == "claim_1"
    assert "prescribed for pneumonia" in claims[0]["text"]
    assert claims[1]["claim_id"] == "claim_2"
    assert "50mg daily" in claims[1]["text"]

def test_extract_claims_character_offsets():
    text = "Claim one. Claim two."
    claims = ClaimExtractor.extract_claims(text)
    
    for claim in claims:
        start = claim["start_char"]
        end = claim["end_char"]
        # Extracted slice should match claim text
        assert text[start:end] == claim["text"]
