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
                url = r.get('href', '')
                if not snippet or "wikipedia.org" in url.lower():
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