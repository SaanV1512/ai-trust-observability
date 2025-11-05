import wikipediaapi
import spacy
import re
import os
from ddgs import DDGS
from langdetect import detect, LangDetectException
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GENAI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent='AI-Trust-Observability-Agent saanvi rihan veda'
)

def is_english(text):
    try:
        if len(text.strip()) < 10:
            return False

        return detect(text) == "en"
    except LangDetectException:
        return False
    
nlp = spacy.load("en_core_web_sm")

WH_WORDS = {"who", "what", "when", "where", "why", "how"}
def extract_topic(question):
    doc = nlp(question)
    for chunk in doc.noun_chunks:
        cleaned = chunk.text.strip().lower()
        if cleaned not in WH_WORDS:
            return chunk.text.title()
    words = [w for w in question.replace("?", "").split() if w.lower() not in WH_WORDS]
    if words:
        topic = " ".join(words).title()
        return topic
    prompt = f"Extract the main topic from this question. Only return the topic.\nQuestion: {question}\nTopic:"
    response = model.generate_content(prompt)
    return response.text.strip()
#fact sentence extraction using NER
# def answer_is_short_fact(ai_answer):
#     doc = nlp(ai_answer)
#     for ent in doc.ents:
#         if ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "EVENT", "WORK_OF_ART"]:
#             return True
#     if len(ai_answer.split()) <= 25:
#         return True
#     return False

# def choose_extraction_model(question, ai_answer):
#     if answer_is_short_fact(ai_answer):
#         return "short"
#     else:
#         return "long"
# def extract_fact_sentence(text):
#     """
#     Extracts the most factual sentence from a longer paragraph.
#     Uses spaCy NER to find sentences containing real entities such as PERSON, DATE, etc.
#     If none found, falls back to the first sentence.
#     """
#     doc = nlp(text)
#
#     # Try to return a sentence with factual entities
#     for sent in doc.sents:
#         labels = [ent.label_ for ent in sent.ents]
#         if any(label in ["PERSON", "ORG", "GPE", "DATE", "EVENT", "WORK_OF_ART"] for label in labels):
#             return sent.text.strip() + "."
#
#     # Fallback: just return first sentence
#     sentences = list(doc.sents)
#     return sentences[0].text.strip() + "." if sentences else text.strip()

def search_wikipedia(query):
    page = wiki.page(query)
    if page.exists():
        return {
            "title": page.title,
            "summary": page.summary[0:2000],  
            "url": page.fullurl
        }
    else:
        return None
def duckduckgo_search(query, max_results=5):
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                snippet = r.get('body', '')
                if not snippet:
                    continue
                try:
                    if detect(snippet) != "en":
                        continue
                except:
                    continue
                results.append({
                    "title": r.get('title'),
                    "snippet": snippet,
                    "url": r.get('href')
                })
    except Exception as e:
        print(f"Error during DuckDuckGo search: {str(e)}")
    return results[:3]  # Return top 3 results

def combined_search(query):
    topic = extract_topic(query)
    wiki_result = search_wikipedia(topic)
    ddg_results = duckduckgo_search(topic)
    return {
        "question": query,
        "topic": topic,
        "wikipedia": wiki_result,
        "duckduckgo": ddg_results
    }