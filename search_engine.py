import os
import re
import requests
import wikipedia  # has .search()
import spacy
from bs4 import BeautifulSoup
from ddgs import DDGS
from langdetect import detect, LangDetectException
import wikipediaapi
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("GENAI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent='AI-Trust-Observability-Agent saanvi rihan veda'
)

def clean_text(text: str) -> str:
    """Clean text by removing HTML, references, and extra spaces."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[[0-9]+\]", "", text)
    text = re.sub(r"http\S+", "", text)
    return text.strip()

def is_english(text: str) -> bool:
    """Detect if text is English and long enough to be meaningful."""
    try:
        if len(text.strip()) < 10:
            return False
        return detect(text) == "en"
    except LangDetectException:
        return False

# Load spaCy model for topic extraction
nlp = spacy.load("en_core_web_sm")

WH_WORDS = {"who", "what", "when", "where", "why", "how"}

def extract_topic(question: str) -> str:
    """
    Extract the main topic or search phrase from a question using Gemini.
    Returns a short noun phrase like 'discovery of penicillin' or 'capital of India'.
    """
    try:
        prompt = f"""
        Extract the main topic or search phrase from the following question.
        Do NOT answer the question. 
        Return only a short, descriptive phrase (2–6 words) suitable for a search query.

        Examples:
        - Who discovered penicillin? → discovery of penicillin
        - What is the capital of India? → capital of India
        - Who founded Tesla? → founder of Tesla
        - When was Python created? → creation of Python
        - Who wrote Harry Potter? → author of Harry Potter

        Question: {question}
        Topic:
        """
        response = model.generate_content(prompt)
        topic = (response.text or "").strip(" \n.:").lower()
        return topic
    except Exception as e:
        print(f"⚠️ Gemini topic extraction error: {e}")
        return question.strip()


def search_wikipedia(query: str, max_chars: int = 3000) -> dict:
    """
    Fetch richer and context-aware content from Wikipedia.
    - Avoids disambiguation pages
    - Searches again with related keywords if needed
    - Returns both summary and factual full text
    """
    page = wiki.page(query)

    # If the page doesn't exist or looks generic, try searching manually
    if not page.exists() or "may refer to" in (page.summary or "").lower():
        try:
            search_results = wikipedia.search(query)  # uses the other library
        except Exception:
            search_results = []

        if search_results:
            for title in search_results:
                if "disambiguation" in title.lower():
                    continue
                if query.lower() in title.lower() or len(title.split()) > 1:
                    new_page = wiki.page(title)
                    if new_page.exists():
                        page = new_page
                        break
        else:
            return None

    text = page.text or ""
    summary = page.summary or ""

    # Use the most relevant paragraphs based on the query words
    keywords = [word for word in query.lower().split() if len(word) > 3]
    paragraphs = text.split("\n")
    relevant_paragraphs = []

    for p in paragraphs:
        lower_p = p.lower()
        if any(k in lower_p for k in keywords):
            relevant_paragraphs.append(p)
        if len(" ".join(relevant_paragraphs)) > max_chars:
            break

    if not relevant_paragraphs:
        relevant_paragraphs = [summary if summary else text[:max_chars]]

    full_text = clean_text(" ".join(relevant_paragraphs)[:max_chars])

    return {
        "title": page.title,
        "summary": clean_text(summary[:1000]),
        "full_text": full_text,
        "url": page.fullurl
    }

def duckduckgo_search(query: str, max_results: int = 5) -> list:
    """
    Fetch richer DuckDuckGo results:
      - summary: search snippet
      - full_text: first 1–2 paragraphs fetched from webpage
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "").strip()
                url = r.get("href", "").strip()
                snippet = clean_text(r.get("body", ""))  # short snippet from search results

                if not title or not url or not snippet:
                    continue

                # Skip non-English snippets
                try:
                    if detect(snippet) != "en":
                        continue
                except Exception:
                    continue

                # Try fetching webpage for richer context
                full_text = ""
                try:
                    response = requests.get(url, timeout=4)
                    soup = BeautifulSoup(response.text, "html.parser")
                    paras = soup.find_all("p")
                    if paras:
                        full_text = " ".join(p.get_text() for p in paras[:2])
                        full_text = clean_text(full_text)
                except Exception:
                    pass  # fallback if page fetch fails

                results.append({
                    "title": title,
                    "summary": snippet,
                    "full_text": full_text,
                    "url": url
                })

    except Exception as e:
        print(f"⚠️ DuckDuckGo search error: {str(e)}")

    # Remove duplicate URLs
    seen = set()
    unique_results = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    return unique_results[:max_results]

def combined_search(query: str) -> dict:
    """Combine Wikipedia and DuckDuckGo evidence for a given query."""
    topic = extract_topic(query)
    wiki_result = search_wikipedia(topic)
    ddg_results = duckduckgo_search(topic)
    return {
        "question": query,
        "topic": topic,
        "wikipedia": wiki_result,
        "duckduckgo": ddg_results
    }

if __name__ == "__main__":
    q = "Who discovered penicillin?"
    data = combined_search(q)
    from pprint import pprint
    pprint(data)
