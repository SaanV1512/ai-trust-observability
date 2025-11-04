import wikipediaapi
from duckduckgo_search import DDGS

wiki = wikipediaapi.Wikipedia('en')

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
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get('title'),
                "snippet": r.get('body'),
                "url": r.get('href')
            })
    return results
def combined_search(query):
    wiki_result = search_wikipedia(query)
    ddg_results = duckduckgo_search(query)
    return {
        "question": query,
        "wikipedia": wiki_result,
        "duckduckgo": ddg_results
    }