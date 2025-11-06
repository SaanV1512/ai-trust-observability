# AI Trust / LLM Observability

Improving explainability and observability in AI/LLM predictions to reduce hallucinations and increase user trust.

## Problem statement

AI Trust (LLM Observability)

Build mechanisms to improve explainability and observability in AI/LLM predictions to reduce hallucinations and gain user trust.

## What this project is

This repository contains a small prototype for LLM observability and trust scoring. It exposes a FastAPI backend that accepts a user question, queries LLMs and evidence sources, computes a trust report (semantic similarity, citation coverage, LLM confidence, reasoning explanation, etc.), and returns structured results which a simple frontend consumes.

This project is intended as a demo / hackathon prototype to show how trust metrics can be calculated and surfaced to users.

# AI Trust / LLM Observability — Run & Use

This README shows how to run the project, where to type a question, where to see the answer and trust metrics, and explains the score types and how they are computed/used.

## Run the project (PowerShell)

1. Install dependencies:

```powershell
python -m pip install -r .\requirements.txt
```

2. Start the backend API (development):

```powershell
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

3. Open the frontend UI:

- Option A (quick): open `frontend/index.html` in your browser.
- Option B (recommended if you want a local server):

```powershell
Push-Location frontend; python -m http.server 5500; Pop-Location
```

Then visit `http://127.0.0.1:5500` in your browser.

## Where to type the question and where results appear

- Type your question in the input labeled "Enter your question" (the text box with id `query`) in the frontend.
- Click the **Get Response** button (or press Enter).
- Results appear on the same page:
  - The AI answer shows under the **Answer** section (`#answer`).
  - The overall Trust Score is shown as a gauge (`#trustPercent`).
  - Supporting metrics are shown as progress bars and percentages:
    - Semantic Similarity (`#semanticVal`)
    - Evidence Support (`#citationVal`)
    - LLM Confidence (`#confidenceVal`)
  - A human-readable reasoning explanation appears under **Reasoning** (`#reasoning`).
  - Sources (citations) are listed in the **Sources** panel (`#sources`).

If the backend is unreachable, the frontend will show a fallback example and a toast message.

## Score types and how they are computed / used

All scores are returned as floats in range [0.0, 1.0] and displayed as percentages in the UI.

1) Semantic Similarity
  - What: Measures how semantically close the AI's answer is to retrieved evidence.
  - How: Uses a SentenceTransformer embedding model (`all-MiniLM-L6-v2`) to compute cosine similarity between the AI answer and sentences/chunks from retrieved evidence. The maximum sentence-level similarity is returned.
  - Use: Indicates content-level alignment between the answer and source texts (helps detect paraphrased but supported claims).

2) Evidence Support (shown as "Evidence Support" / `citation_coverage` in the API)
  - What: Measures how well the core factual claims in the answer are supported by retrieved sources.
  - How: Combines three signals for the primary claim:
    - Entity matching (40%): checks whether key entities/numbers from the primary claim appear in evidence (counts exact and partial matches).
    - Claim semantic similarity (35%): similarity between the primary claim and evidence.
    - Chunk similarity (25%): the best sentence/chunk similarity found in evidence.
  - Result is combined, slightly boosted for strong matches, and rounded to two decimals.
  - Use: Reflects factual coverage — a low score suggests missing or unsupported claims (potential hallucination).

3) LLM Confidence
  - What: The model's self-assessed confidence in its answer (0.0–1.0).
  - How: The pipeline prompts the LLM to self-evaluate the answer and parses a numeric score. If unavailable, a default moderate value is used.
  - Use: Captures the model's expressed certainty; when high but unsupported by evidence, it raises a red flag for overconfidence.

4) Trust Score
  - What: A single composite score reflecting overall trustworthiness (0.0–1.0).
  - How (summary):
    - Compute a weighted base score: 35% * semantic_similarity + 40% * evidence_support + 25% * llm_confidence.
    - Apply penalties when needed:
      - If evidence_support < 0.5, apply a small penalty proportional to the gap.
      - If LLM confidence > 0.8 but semantic_similarity < 0.7, apply a fixed penalty to catch overconfident hallucinations.
      - If any primary metric is very low (<= 0.3), the pipeline uses a stricter scaling.
    - Compute a geometric mean of the three primary metrics and blend it: final trust_score = 0.7 * base_score + 0.3 * geometric_mean (when metrics are > 0.3). This makes the score stricter and avoids high trust when one metric is very low.
  - Use: A high trust score (e.g., >= 0.8) indicates strong alignment with evidence and appropriate confidence; mid-range scores indicate partial support; low scores indicate weak or unsupported answers.

Score thresholds (used for reasoning text):
- >= 0.80: strong alignment and high factual consistency
- 0.65–0.79: generally aligned but may need verification
- 0.50–0.64: partial alignment, verify claims
- 0.35–0.49: weak alignment/uncertain — caution advised
- < 0.35: very weak alignment — likely unreliable

Notes:
- `citation_coverage` in the API is the same signal as Evidence Support (kept for backward compatibility).
- Values are rounded to two decimals in the backend and displayed as percentages in the UI.

## Credits & Tech stack

Core technologies used:
- Backend: Python, FastAPI, uvicorn
- LLMs: Google Generative AI (Gemini) via `google.generativeai` (configured via env var), optional OpenAI imports are present for flexibility
- Search / evidence: DuckDuckGo (`ddgs`) and Wikipedia scraped/summarized via `search_engine.py`
- Embeddings / semantic similarity: `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- Frontend: plain HTML, CSS and vanilla JavaScript (no framework)

Libraries appearing in `requirements.txt` include (not exhaustive): fastapi, uvicorn, sentence-transformers, google-generativeai, ddgs, requests, beautifulsoup4.

Credits
- Project / prototype created as an AI Trust / LLM Observability demo (hackathon prototype). See the `backend` and `frontend` folders for source code.

If you'd like, I can further trim `requirements.txt` to a minimal runtime list or add a short CI/test harness next.