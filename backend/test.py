# test_run.py
from analyser import analyze_question
from sentence_module import generate_trust_report
import json

try:
    question = "Who is the founder of OnlyFans"

    analysis = analyze_question(question)
    report = generate_trust_report(
        analysis["question"],
        analysis["ai_answer"],
        analysis["llm_confidence"],
        analysis["wikipedia_evidence"],
        analysis["duckduckgo_evidence"]
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))

except Exception as e:
    print(f" Error during test: {e}")