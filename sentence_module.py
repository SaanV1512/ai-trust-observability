# sentence_module.py
import re
import numpy as np
from sentence_transformers import SentenceTransformer, util

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
    """Compute the maximum cosine similarity between the answer and all evidence texts."""
    if not evidence_texts:
        return 0.0

    # Prepare embeddings
    ans_emb = embedder.encode(answer, convert_to_tensor=True)
    src_embs = embedder.encode(evidence_texts, convert_to_tensor=True)

    sims = util.cos_sim(ans_emb, src_embs)[0].cpu().numpy()
    return float(np.max(sims))  # use max similarity


def compute_citation_coverage(answer: str, evidence_texts: list, threshold: float = 0.6) -> float:
    """Measures what fraction of sentences in the answer are supported by retrieved evidence."""
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
    Includes semantic similarity, citation coverage, weighted trust score, and reasoning.
    """

    evidence_texts = []
    sources = []

    if wikipedia_evidence and wikipedia_evidence.get("summary"):
        text = clean_text(wikipedia_evidence["summary"])
        evidence_texts.append(text)
        sources.append({
            "title": wikipedia_evidence.get("title", "Wikipedia"),
            "url": wikipedia_evidence.get("url", "")
        })

    if duckduckgo_evidence:
        for r in duckduckgo_evidence:
            snippet = clean_text(r.get("snippet", ""))
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

    if trust_score >= 0.8:
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

        # Skip if duplicate or empty
        if not url or not title:
            continue
        if url in seen_urls or title in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title)

        source_list.append({
            "title": title,
            "url": url
        })

    return {
        "question": question,
        "answer": ai_answer,
        "trust_score": trust_score,
        "semantic_similarity": round(semantic_similarity, 2),
        "citation_coverage": round(citation_coverage, 2),
        "llm_confidence": round(llm_confidence or 0, 2),
        "reasoning_explanation": reasoning_explanation,
        "sources": source_list[:5]  # limit to top 5 for UI clarity
    }

