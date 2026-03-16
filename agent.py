"""
agent.py — High-level orchestrator dictating the analytical sequence of events.
"""

import os
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv

from rag import RAGPipeline
from tools import analyse_risks, extract_financial_metrics, predict_investment_score

load_dotenv()

SUMMARY_PROMPT = """
You are a senior private equity analyst preparing a final investment committee report.
Using the information provided below, write a concise but thorough company summary
(3–5 paragraphs) and a clear investment recommendation.

Financial Metrics:
{metrics}

Top Risks Identified:
{risks}

Investment Score: {score} / 100  ({label})

Supporting Document Excerpts:
{context}

Provide:
1. A professional company_summary paragraph (3–5 sentences).
2. A clear, actionable recommendation paragraph explaining whether the investment
   committee should pass, consider, or pursue this opportunity and why.

Return ONLY a valid JSON object with two keys: "company_summary" and "recommendation".
No markdown fences.
"""


class AgentOrchestrator:
    """Orchestrates the full due-diligence analytical pipeline."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Please configure it in your .env file."
            )
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.5-flash")

    def run(
        self, texts_by_file: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute the full due-diligence pipeline.

        Args:
            texts_by_file: Mapping of {filename: extracted_text}.

        Returns:
            DueDiligenceReport dictionary.
        """
        # Step 1 — Ingest all documents into the shared RAG index
        rag = RAGPipeline()
        for text in texts_by_file.values():
            rag.ingest(text)

        # Step 2 — Extract financial metrics
        financial_chunks = rag.retrieve(
            "revenue growth EBITDA margin debt equity market size founding year team size"
        )
        metrics = extract_financial_metrics(financial_chunks, self._model)

        # Step 3 — Analyse risks
        risk_chunks = rag.retrieve(
            "business risks challenges threats competitive landscape supply chain"
        )
        risks = analyse_risks(risk_chunks, self._model)

        # Step 4 — Predict investment score via ML model
        score, label = predict_investment_score(metrics)

        # Step 5 — Generate final summary and recommendation via Gemini
        all_chunks = rag.retrieve("company overview business description operations")
        context_text = "\n\n---\n\n".join(all_chunks)

        prompt = SUMMARY_PROMPT.format(
            metrics=metrics,
            risks=risks,
            score=score,
            label=label,
            context=context_text,
        )
        summary_response = self._model.generate_content(prompt)
        raw = summary_response.text.strip()

        import json
        import re

        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            summary_data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            summary_data = json.loads(match.group(0)) if match else {}

        company_summary = summary_data.get("company_summary", "Summary not available.")
        recommendation = summary_data.get("recommendation", "Recommendation not available.")

        return {
            "company_summary": company_summary,
            "financial_metrics": metrics,
            "risks": risks,
            "investment_score": score,
            "investment_label": label,
            "recommendation": recommendation,
            "files_analysed": list(texts_by_file.keys()),
        }
