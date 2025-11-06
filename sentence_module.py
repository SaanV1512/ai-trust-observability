
import re
import numpy as np
from sentence_transformers import SentenceTransformer, util

# Initialize SentenceTransformer model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def clean_text(text: str) -> str:
    """Cleans and simplifies text for embedding."""
    if not text:
        return ""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\\u[0-9A-Fa-f]{4}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .-—–…")


def compute_semantic_similarity(answer: str, evidence_texts: list) -> float:
    """Compute max cosine similarity between answer and sentences in evidence."""
    if not evidence_texts:
        return 0.0

    ans_emb = embedder.encode(answer, convert_to_tensor=True)

    max_sim = 0.0
    for evidence in evidence_texts:
        # Split evidence into sentences
        sentences = re.split(r"[.!?]", evidence)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            continue
        src_embs = embedder.encode(sentences, convert_to_tensor=True)
        sims = util.cos_sim(ans_emb, src_embs)[0].cpu().numpy()
        max_sim = max(max_sim, float(np.max(sims)))

    return max_sim


def compute_citation_coverage(answer: str, evidence_texts: list, threshold: float = 0.65) -> float:
    """
    Measures what fraction of sentences in the answer are supported by retrieved evidence.
    Each sentence is compared against all evidence, and considered supported if any match ≥ threshold.
    """
    if not evidence_texts:
        return 0.0

    sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
    if not sentences:
        return 0.0

    supported = 0
    for s in sentences:
        sim = compute_semantic_similarity(s, evidence_texts)
        if sim >= threshold:
            supported += 1

    return round(supported / len(sentences), 2)

def generate_trust_report(
    question: str,
    ai_answer: str,
    llm_confidence: float,
    wikipedia_evidence: dict,
    duckduckgo_evidence: list
) -> dict:
    """
    Generate a factual trust report by analyzing the AI's answer against retrieved evidence.
    Uses Wikipedia and DuckDuckGo 'full_text' when available for richer embeddings.
    """
    evidence_texts = []
    sources = []

    #  Prefer full_text from Wikipedia (fallback to summary)
    if wikipedia_evidence:
        text = clean_text(
            wikipedia_evidence.get("full_text") or wikipedia_evidence.get("summary", "")
        )
        if text:
            evidence_texts.append(text)
        sources.append({
            "title": wikipedia_evidence.get("title", "Wikipedia"),
            "url": wikipedia_evidence.get("url", "")
        })

    #  Use full_text from DuckDuckGo if available (fallback to snippet)
    if duckduckgo_evidence:
        for r in duckduckgo_evidence:
            snippet = clean_text(r.get("full_text") or r.get("snippet", ""))
            if snippet:
                evidence_texts.append(snippet)
            sources.append({
                "title": r.get("title", "DuckDuckGo Source"),
                "url": r.get("url", "")
            })

    semantic_similarity = compute_semantic_similarity(ai_answer, evidence_texts)
    citation_coverage = compute_citation_coverage(ai_answer, evidence_texts)
    trust_score = round(
        0.4 * semantic_similarity + 0.3 * citation_coverage + 0.3 * (llm_confidence or 0),
        2
    )

    if trust_score >= 0.7:
        reasoning_explanation = (
            "The AI’s answer strongly aligns with credible evidence, "
            "showing high factual consistency and confidence."
        )
    elif trust_score >= 0.4:
        reasoning_explanation = (
            "The AI’s answer partially aligns with retrieved sources, "
            "indicating moderate factual reliability."
        )
    else:
        reasoning_explanation = (
            "The AI’s answer shows weak alignment with verified information "
            "or lacks confidence, suggesting low reliability."
        )

    source_list = []
    seen_urls = set()
    seen_titles = set()

    for s in sources:
        url = s.get("url", "").strip()
        title = s.get("title", "").strip()

        if not url or not title:
            continue
        if url in seen_urls or title in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title)

        source_list.append({"title": title, "url": url})

    return {
        "question": question,
        "answer": ai_answer,
        "trust_score": trust_score,
        "semantic_similarity": round(semantic_similarity, 2),
        "citation_coverage": round(citation_coverage, 2),
        "llm_confidence": round(llm_confidence or 0, 2),
        "reasoning_explanation": reasoning_explanation,
        "sources": source_list[:5]  # limit for clarity
    }

