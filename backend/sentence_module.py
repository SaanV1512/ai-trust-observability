
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


def extract_key_entities(text: str) -> set:
    """Extract key entities (proper nouns, numbers, important phrases) from text."""
    # Remove markdown formatting
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'__', '', text)
    
    # Extract capitalized words (likely proper nouns)
    proper_nouns = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))
    
    # Extract numbers and years
    numbers = set(re.findall(r'\b\d{4}\b|\b\d+\.?\d*\b', text))
    
    # Filter out common words
    common_words = {'The', 'This', 'They', 'It', 'When', 'Where', 'What', 'Who', 'How', 'Why', 'If', 'But', 'And', 'Or', 'To', 'For', 'In', 'On', 'At', 'By'}
    proper_nouns = {p for p in proper_nouns if p not in common_words and len(p) > 2}
    
    return proper_nouns | numbers


def compute_evidence_support(answer: str, question: str, evidence_texts: list) -> float:
    """
    Measures how well the core factual claims in the answer are supported by evidence.
    Focuses on verifying the main claim (not sentence-by-sentence coverage).
    
    Strategy:
    1. Extract the primary claim (first sentence or key phrase)
    2. Check if key entities from answer appear in evidence
    3. Verify semantic similarity of core claim with evidence
    4. Combine entity matching + semantic similarity for final score
    """
    if not evidence_texts:
        return 0.0
    
    if not answer or not answer.strip():
        return 0.0
    
    # Extract the primary claim - usually the first sentence that directly answers
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
    if not sentences:
        return 0.0
    
    # The primary claim is typically the first sentence (direct answer)
    primary_claim = sentences[0]
    
    # If first sentence is very short, include second sentence too
    if len(primary_claim.split()) < 8 and len(sentences) > 1:
        primary_claim = sentences[0] + " " + sentences[1]
    
    # Extract key entities from the primary claim
    answer_entities = extract_key_entities(primary_claim)
    
    # Combine all evidence into one text for entity matching
    combined_evidence = " ".join(evidence_texts).lower()
    
    # Entity matching score: how many key entities appear in evidence
    entity_matches = 0
    if answer_entities:
        for entity in answer_entities:
            # Check if entity (or its variations) appears in evidence
            entity_lower = entity.lower()
            if entity_lower in combined_evidence:
                entity_matches += 1
            else:
                # Check for partial matches (e.g., "Larry Page" might appear as "Page" or "Larry")
                words = entity.split()
                if any(word.lower() in combined_evidence for word in words if len(word) > 3):
                    entity_matches += 0.5  # Partial credit
    
        entity_score = min(1.0, entity_matches / len(answer_entities)) if answer_entities else 0.0
    else:
        entity_score = 0.5  # No entities to check, default moderate
    
    # Semantic similarity of primary claim with evidence
    claim_similarity = compute_semantic_similarity(primary_claim, evidence_texts)
    
    # Also check if any specific evidence chunk strongly supports the claim
    # Split evidence into chunks and find best match
    max_chunk_similarity = 0.0
    for evidence in evidence_texts:
        # Split into sentences/chunks
        chunks = re.split(r"[.!?]\s+", evidence)
        chunks = [c.strip() for c in chunks if len(c.strip()) > 20]
        
        if chunks:
            chunk_embs = embedder.encode(chunks, convert_to_tensor=True)
            claim_emb = embedder.encode(primary_claim, convert_to_tensor=True)
            chunk_sims = util.cos_sim(claim_emb, chunk_embs)[0].cpu().numpy()
            max_chunk_similarity = max(max_chunk_similarity, float(np.max(chunk_sims)))
    
    # Combine scores: entity matching (40%), claim similarity (35%), chunk similarity (25%)
    # This ensures we check both factual accuracy (entities) and semantic alignment
    evidence_support = (
        0.40 * entity_score +
        0.35 * claim_similarity +
        0.25 * max_chunk_similarity
    )
    
    # Boost score if entity matching is very high (strong factual support)
    if entity_score >= 0.8 and claim_similarity >= 0.6:
        evidence_support = min(1.0, evidence_support * 1.1)
    
    return round(evidence_support, 2)

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
    evidence_support = compute_evidence_support(ai_answer, question, evidence_texts)
    llm_conf = llm_confidence or 0.65  # Default to moderate if None
    
    # Stricter trust score calculation with penalties
    # Evidence support is most important (40%), then semantic similarity (35%), then LLM confidence (25%)
    base_score = 0.35 * semantic_similarity + 0.40 * evidence_support + 0.25 * llm_conf
    
    # Penalty system: reduce score if evidence support is very low
    if evidence_support < 0.5:
        penalty = 0.15 * (0.5 - evidence_support)  # Up to 7.5% penalty
        base_score -= penalty
    
    # Penalty if semantic similarity is low despite high confidence (potential hallucination)
    if llm_conf > 0.8 and semantic_similarity < 0.7:
        penalty = 0.1  # 10% penalty for overconfidence
        base_score -= penalty
    
    # Use geometric mean for stricter scoring (requires all metrics to be decent)
    # This prevents high scores when one metric is very low
    if semantic_similarity > 0.3 and evidence_support > 0.3 and llm_conf > 0.3:
        geometric_mean = (semantic_similarity * evidence_support * llm_conf) ** (1/3)
        # Blend weighted average (70%) with geometric mean (30%) for balanced strictness
        trust_score = round(0.7 * base_score + 0.3 * geometric_mean, 2)
    else:
        # If any metric is very low, use stricter calculation
        trust_score = round(base_score * 0.8, 2)  # 20% penalty
    
    # Clamp to valid range
    trust_score = max(0.0, min(1.0, trust_score))

    # More nuanced reasoning explanations
    if trust_score >= 0.80:
        reasoning_explanation = (
            "The AI's answer strongly aligns with credible evidence, "
            "showing high factual consistency, good evidence support, and appropriate confidence."
        )
    elif trust_score >= 0.65:
        reasoning_explanation = (
            "The AI's answer aligns well with retrieved sources, "
            "though some parts may need verification or lack strong evidence."
        )
    elif trust_score >= 0.50:
        reasoning_explanation = (
            "The AI's answer partially aligns with verified information, "
            "indicating moderate factual reliability. Some claims may need additional verification."
        )
    elif trust_score >= 0.35:
        reasoning_explanation = (
            "The AI's answer shows weak alignment with retrieved sources or exhibits uncertainty. "
            "Caution is advised as some information may be incorrect or unverified."
        )
    else:
        reasoning_explanation = (
            "The AI's answer shows very weak alignment with verified information, "
            "high uncertainty, or lacks supporting evidence. This answer should be treated with significant skepticism."
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
        "citation_coverage": round(evidence_support, 2),  # Keep name for backward compatibility, but it's now evidence_support
        "llm_confidence": round(llm_confidence or 0, 2),
        "reasoning_explanation": reasoning_explanation,
        "sources": source_list[:5]  # limit for clarity
    }
