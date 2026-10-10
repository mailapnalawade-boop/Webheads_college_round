import pytest
from app.core.retriever import PassageRetriever

def test_bm25_retriever():
    passages = [
        {"id": "p1", "text": "Amoxicillin dosage for adults is 500mg three times daily.", "source_name": "doc1.txt"},
        {"id": "p2", "text": "Pneumonia patients require bed rest and fluids.", "source_name": "doc2.txt"}
    ]
    retriever = PassageRetriever(passages)
    
    results = retriever.retrieve("Amoxicillin dose 500mg", top_k=1)
    
    assert len(results) == 1
    assert results[0]["source_name"] == "doc1.txt"
    assert results[0]["relevance_score"] > 0.0
