import os
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
    try:
        prompt = f"""
        Quetsion: {question}
        Answer: {ai_answer}

        On a scale from 0 to 1, how confident are you that this answer is factually correct?
        Respond with only a number.
        """
        response = model.generate_content(prompt)
        confidence_text = response.text.strip()
        try:
            confidence_score = float(confidence_text)
        except:
            confidence_score = None
        return confidence_score
    except Exception as e:
        return None

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
