import os
import re
import openai
import pandas as pd
import google.generativeai as genai
from ddgs import DDGS
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from search_engine import combined_search

genai.configure(api_key=os.getenv("GENAI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def get_ai_answer(question):
    try:
        response = model.generate_content(question)
        return response.text.strip()
    except Exception as e:
        return f"Error generating AI answer: {str(e)}"

def get_llm_confidence(question, ai_answer):
    """
    Get realistic LLM confidence score by asking the model to self-assess
    with more nuanced criteria including uncertainty, specificity, and evidence.
    """
    try:
        prompt = f"""You are evaluating the confidence level of an AI-generated answer.

Question: {question}
Answer: {ai_answer}

Consider:
1. How specific and factual is this answer? (vs vague or speculative)
2. Are there any qualifiers like "might", "possibly", "approximately" that indicate uncertainty?
3. Does the answer directly address the question or go off-topic?
4. Are there any red flags suggesting the answer might be incorrect?

Rate your confidence on a scale from 0.0 to 1.0 where:
- 0.9-1.0: Highly confident, specific, factual answer (e.g., "Alexander Fleming in 1928")
- 0.7-0.89: Confident but with some uncertainty or qualifiers
- 0.5-0.69: Moderate confidence, some speculation or vague language
- 0.3-0.49: Low confidence, many qualifiers or uncertainty
- 0.0-0.29: Very low confidence, highly speculative or unclear

Return ONLY a number between 0.0 and 1.0 (e.g., 0.85, not "0.85/1.0" or "85%").
"""
        response = model.generate_content(prompt)
        confidence_text = response.text.strip()
        # Extract first float number from response
        match = re.search(r'0?\.\d+|1\.0|0', confidence_text)
        if match:
            confidence_score = float(match.group())
            # Clamp to valid range
            confidence_score = max(0.0, min(1.0, confidence_score))
        else:
            # Default to moderate confidence if parsing fails
            confidence_score = 0.65
        return confidence_score
    except Exception as e:
        # Return moderate confidence on error rather than None
        return 0.65

def analyze_question(question):
    ai_answer = get_ai_answer(question)
    evidence = combined_search(question)
    llm_confidence = get_llm_confidence(question, ai_answer)
    return {
        "question": question,
        "ai_answer": ai_answer,
        "llm_confidence": llm_confidence,
        "wikipedia_evidence": evidence.get("wikipedia"),
        "duckduckgo_evidence": evidence.get("duckduckgo")
    }

#manual testing
if __name__ == "__main__":
    sample_question = "Who discovered penicillin?"
    analysis_result = analyze_question(sample_question)
    print(analysis_result)