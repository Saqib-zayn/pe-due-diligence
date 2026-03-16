"""
tools.py — Standalone business-logic functions used by the agent as tools.
"""

import json
import re
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Tool 1 — extract_financial_metrics
# ---------------------------------------------------------------------------

FINANCIAL_EXTRACTION_PROMPT = """
You are a financial analyst. Analyse the following text excerpts from an investment document
and extract the six financial metrics listed below. Return ONLY a valid JSON object with
exactly these keys. If a value cannot be determined from the text, use null.

Keys to extract:
- revenue_growth_pct   (float, e.g. 18.4)
- ebitda_margin        (float, e.g. 19.5)
- debt_to_equity       (float, e.g. 0.53)
- market_size_bn       (float, in billions, e.g. 18.6)
- founding_year        (integer, e.g. 2009)
- team_size            (integer, e.g. 312)

Text excerpts:
{context}

Return ONLY the JSON object, no markdown fences, no explanation.
"""


def extract_financial_metrics(chunks: List[str], model: Any) -> Dict[str, Any]:
    """Prompt the LLM to extract six financial fields from the retrieved chunks.

    Args:
        chunks: List of text chunks from the RAG retrieval.
        model: Configured Gemini GenerativeModel instance.

    Returns:
        Dictionary with the six financial metric keys.
    """
    context = "\n\n---\n\n".join(chunks)
    prompt = FINANCIAL_EXTRACTION_PROMPT.format(context=context)
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip any accidental markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        metrics = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract a JSON object substring
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        metrics = json.loads(match.group(0)) if match else {}

    # Ensure all expected keys are present
    for key in (
        "revenue_growth_pct",
        "ebitda_margin",
        "debt_to_equity",
        "market_size_bn",
        "founding_year",
        "team_size",
    ):
        metrics.setdefault(key, None)

    return metrics


# ---------------------------------------------------------------------------
# Tool 2 — analyse_risks
# ---------------------------------------------------------------------------

RISK_ANALYSIS_PROMPT = """
You are a seasoned private equity risk analyst. Read the following text excerpts from an
investment document and identify the top 5 most significant business risks.

Return ONLY a valid JSON array of exactly 5 strings, each string being a concise risk
description (one sentence each). No markdown, no explanation outside the JSON array.

Text excerpts:
{context}

Return ONLY the JSON array.
"""


def analyse_risks(chunks: List[str], model: Any) -> List[str]:
    """Prompt the LLM to identify the top 5 business risks from the retrieved chunks.

    Args:
        chunks: List of text chunks from the RAG retrieval.
        model: Configured Gemini GenerativeModel instance.

    Returns:
        List of 5 risk description strings.
    """
    context = "\n\n---\n\n".join(chunks)
    prompt = RISK_ANALYSIS_PROMPT.format(context=context)
    response = model.generate_content(prompt)
    raw = response.text.strip()

    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        risks = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        risks = json.loads(match.group(0)) if match else []

    if not isinstance(risks, list):
        risks = []

    # Pad to 5 items if fewer were returned
    while len(risks) < 5:
        risks.append("Insufficient data to determine additional risk.")

    return risks[:5]


# ---------------------------------------------------------------------------
# Tool 3 — predict_investment_score
# ---------------------------------------------------------------------------

LABEL_MAP = {0: "Pass", 1: "Consider", 2: "Strong Buy"}

# Score bands that map model class to a 0-100 scale
SCORE_RANGE = {0: (5, 35), 1: (40, 65), 2: (70, 100)}

FEATURE_COLS = [
    "revenue_growth_pct",
    "ebitda_margin",
    "debt_to_equity",
    "market_size_bn",
    "founding_year",
    "team_size",
]

FEATURE_DEFAULTS = {
    "revenue_growth_pct": 10.0,
    "ebitda_margin": 15.0,
    "debt_to_equity": 0.8,
    "market_size_bn": 5.0,
    "founding_year": 2010,
    "team_size": 100,
}


def predict_investment_score(metrics: Dict[str, Any]) -> Tuple[int, str]:
    """Load model.pkl and generate an investment score and label.

    Args:
        metrics: Dictionary of financial metrics from extract_financial_metrics.

    Returns:
        Tuple of (score_out_of_100, label_string).
    """
    clf = joblib.load("model.pkl")

    # Replace None values with sensible defaults
    clean = {
        k: (metrics.get(k) if metrics.get(k) is not None else FEATURE_DEFAULTS[k])
        for k in FEATURE_COLS
    }

    X = pd.DataFrame([clean])[FEATURE_COLS]
    predicted_class = int(clf.predict(X)[0])
    proba = clf.predict_proba(X)[0]
    class_confidence = float(proba[predicted_class])

    low, high = SCORE_RANGE[predicted_class]
    score = int(round(low + (high - low) * class_confidence))
    score = max(low, min(high, score))

    label = LABEL_MAP[predicted_class]
    return score, label
