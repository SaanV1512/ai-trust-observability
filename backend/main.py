"""
FastAPI backend for AI Trust / LLM Observability Dashboard
Handles evaluation requests and returns trust metrics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add backend directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyser import analyze_question
from sentence_module import generate_trust_report

app = FastAPI(
    title="AI Trust / LLM Observability API",
    description="API for evaluating AI response trustworthiness",
    version="1.0.0"
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class SourceItem(BaseModel):
    title: str
    url: str


class EvaluationResponse(BaseModel):
    question: str
    answer: str
    trust_score: float
    semantic_similarity: float
    citation_coverage: float
    llm_confidence: float
    reasoning_explanation: str
    sources: List[SourceItem]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "AI Trust / LLM Observability API is running"}


@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_query(request: QueryRequest):
    """
    Evaluate a query and return trust metrics.
    
    Args:
        request: QueryRequest containing the user's question
        
    Returns:
        EvaluationResponse with trust score, metrics, and sources
    """
    try:
        # Validate query
        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Analyze the question
        analysis = analyze_question(query)
        
        # Generate trust report
        report = generate_trust_report(
            analysis["question"],
            analysis["ai_answer"],
            analysis["llm_confidence"],
            analysis["wikipedia_evidence"],
            analysis["duckduckgo_evidence"]
        )
        
        # Format sources as objects with title and url
        formatted_sources = []
        for source in report.get("sources", []):
            title = source.get("title", "Unknown Source")
            url = source.get("url", "")
            if title or url:  # Only add if we have at least title or url
                formatted_sources.append({
                    "title": title,
                    "url": url
                })
        
        # Return response matching frontend format
        res = {
            "question": report["question"],
            "answer": report["answer"],
            "trust_score": report["trust_score"],
            "semantic_similarity": report["semantic_similarity"],
            "citation_coverage": report["citation_coverage"],
            "llm_confidence": report["llm_confidence"],
            "reasoning_explanation": report["reasoning_explanation"],
            "sources": formatted_sources
        }
        print(res)
        return res
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

