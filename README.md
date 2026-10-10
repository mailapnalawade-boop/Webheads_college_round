# Second Opinion — Explainable AI Answer Auditor

> Built for **BIT N BUILD CRCE Hackathon**.

**Second Opinion** is a lightweight, claim-level AI Answer Auditor that verifies AI-generated text against reference document evidence (PDF/TXT) or public web sources. It provides transparent claim classifications (`SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`), identifies internal discrepancies, highlights text passages interactively, and operates with a **100% offline deterministic fallback** when no API keys are available.

---

## 🌟 Key Features

1. **Atomic Claim Extraction**: Automatically parses raw AI text into fine-grained factual claims with exact character positioning.
2. **PyMuPDF Document Ingestion**: Parses uploaded PDF and text documents into structured context passages with page and line tracking.
3. **BM25 Hybrid Retrieval**: Pinpoints exact ground-truth evidence passages matching each claim.
4. **Explainable Claim Classification**: Categorizes claims into `SUPPORTED` (green), `CONTRADICTED` (red), and `INSUFFICIENT_EVIDENCE` (amber) with transparent justifications.
5. **Internal Discrepancy Engine**: Flags mutual self-contradictions across claims within the same answer.
6. **Dual Mode Execution**:
   - **Gemini 2.5 Flash API**: Live LLM explanation mode when API key is provided.
   - **BM25 & Lexical Rule Fallback**: 100% offline, free, deterministic mode that runs without external API dependencies.
7. **Interactive Claim Highlighter**: Color-coded answer text overlay with click-to-evidence navigation.
8. **Exportable PDF Reports**: Downloadable claim audit summary report for presentation and documentation.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm

### 1. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run backend API server on http://localhost:8000
python run.py
```

### 2. Frontend Setup (React + Vite)
```bash
cd frontend
npm install

# Run frontend dev server on http://localhost:5173
npm run dev
```

### 3. One-Click Launch (Windows)
Double-click `start.bat` in the project root to launch both backend and frontend servers simultaneously.

---

## 🧪 Testing

Run the automated test suite verifying claim extraction, passage retrieval, and deterministic verification:
```bash
cd backend
.\venv\Scripts\python.exe -m pytest
```

---

## 📁 Architecture Overview

```
Second Opinion/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # REST Endpoints (/api/audit, /api/sample, /api/health)
│   │   ├── core/
│   │   │   ├── extractor.py       # Atomic claim sentence extractor
│   │   │   ├── parser.py          # PyMuPDF & text document chunker
│   │   │   ├── retriever.py       # BM25 passage retriever
│   │   │   ├── fallback.py        # 100% offline deterministic verification engine
│   │   │   └── verifier.py        # Gemini 2.5 Flash + Fallback orchestrator
│   │   └── schemas/audit.py       # Pydantic data contracts
│   └── tests/                     # Pytest suite
├── frontend/                      # React + Vite Glassmorphism UI
└── start.bat                      # One-click Windows runner
```

---

## How claims are judged (meaning, not words)

1. **Retrieve** - BM25 plus sentence embeddings find the relevant passages, so paraphrases ("car" / "automobile") are found.
2. **Read the meaning** - a local NLI model (`cross-encoder/nli-deberta-v3-small`) reads each source sentence together with the claim and decides *entails / contradicts / unrelated*. With a Gemini key, Gemini also judges the claim and must quote the source verbatim; code verifies that the quote really exists, otherwise the verdict is downgraded.
3. **Verify hard facts** - numbers (with unit conversion and ranges), years, frequencies and names are compared exactly, because neural models can miss a swapped number. A verified mismatch is reported with the exact wrong words.
4. **Cross-check** - if the meaning model, the value check and Gemini disagree, the claim becomes **AMBIGUOUS** with lowered confidence instead of a guess.

Verdicts: `SUPPORTED`, `CONTRADICTED` (a genuine error), `INSUFFICIENT_EVIDENCE` (source is silent), `AMBIGUOUS` (partial/conflicting evidence, *not* an error), `LOGICAL_INCONSISTENCY`.
Each flagged claim carries `error_category`, `error_span` (answer[start:end] is verified to equal the text) and `confidence_signals` explaining the confidence.

**First run:** the NLI and embedding models (~200 MB) download once from Hugging Face. Without them (no internet or no `sentence-transformers`) the app still works but is conservative: it only calls a claim SUPPORTED when the source states it almost verbatim, and it reports an **AMBIGUOUS** result plus a warning instead of guessing. Set `SO_ENABLE_SEMANTIC_MODELS=0` to turn the models off.

## Evaluation

```bash
cd backend
python -m tests.eval.run              # current engine (uses the models if installed)
python -m tests.eval.run --no-models  # model-free mode
python -m tests.eval.run --legacy     # the previous keyword/antonym engine, for before/after
python -m pytest                      # tests needing the real model are marked requires_nli and run when it is installed
```
Reports precision/recall, the missed-error rate (a wrong claim passed as supported), the false-alarm rate, exact-span accuracy and a calibration table. The command exits non-zero if a safety gate fails.
