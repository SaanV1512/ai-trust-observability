# AI Trust / LLM Observability Backend

FastAPI backend for evaluating AI response trustworthiness.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Download spaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Add your `GENAI_API_KEY` (Google Generative AI API key)

4. **Run the server:**
   ```bash
   cd backend
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### `POST /evaluate`
Evaluates a query and returns trust metrics.

**Request:**
```json
{
  "query": "Who discovered penicillin?"
}
```

**Response:**
```json
{
  "question": "Who discovered penicillin?",
  "answer": "...",
  "trust_score": 0.92,
  "semantic_similarity": 0.88,
  "citation_coverage": 0.83,
  "llm_confidence": 0.79,
  "reasoning_explanation": "...",
  "sources": ["Wikipedia: ...", "..."],
}
```

### `GET /`
Health check endpoint.

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload
```

View API documentation at `http://localhost:8000/docs`

