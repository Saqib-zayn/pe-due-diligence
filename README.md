# PE Due Diligence AI

A full-stack Python web application that evaluates uploaded documents (PDF, DOCX, or TXT) via a retrieval-augmented generation (RAG) pipeline and an AI agent to automatically generate a structured private equity due diligence report complete with financial metric extraction, ML investment scoring, risk analysis, and an executive recommendation.
---

## Prerequisites

- **Python 3.11** (or 3.12) with `pip`
- **Docker** and **docker-compose**
- A valid **Gemini API key** from [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## Setup Instructions

1. **Clone the repository and enter the project directory**

   ```bash
   git clone <repo-url>
   cd pe-due-diligence
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=<your-key>
   ```

5. **Train the ML model** *(required before starting Docker)*

   ```bash
   python train.py
   ```

   This generates `model.pkl` in the project root. The script will print the
   classifier accuracy and a full classification report to stdout.

6. **Start the application with Docker**

   ```bash
   docker-compose up --build
   ```

7. **Open the dashboard**

   Navigate to [http://localhost:8000](http://localhost:8000) in your browser.

---

## Running the Demo

1. Run `python train.py` — review the accuracy metrics in the terminal.
2. Run `docker-compose up --build` — observe FastAPI initialising on port 8000.
3. Open `http://localhost:8000` — note the dark-theme dashboard.
4. Drag `data/sample_novacast.txt` onto the upload zone.
5. Click **Run Analysis** — watch the animated spinner while the agent works.
6. Review the populated results: investment score, financial metrics, risks, and recommendation.

For a direct API test without the browser:

```bash
python test_demo.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.0 Flash (`google-generativeai`) |
| Embeddings | Google `models/embedding-001` |
| Vector store | FAISS (in-memory, `faiss-cpu`) |
| ML scoring | XGBoost + scikit-learn |
| Backend API | FastAPI + uvicorn |
| File parsing | PyMuPDF (PDF), python-docx (DOCX) |
| Frontend | Jinja2 templates + vanilla JS |
| Containerisation | Docker + docker-compose |

---

## ML Model

The investment scoring model is an **XGBoost multi-class classifier** trained on a
synthetic dataset of 500 fictional companies. Each record contains six numeric features:

| Feature | Description |
|---|---|
| `revenue_growth_pct` | Year-on-year revenue growth (%) |
| `ebitda_margin` | EBITDA as a percentage of revenue |
| `debt_to_equity` | Total debt divided by shareholder equity |
| `market_size_bn` | Total addressable market in £bn |
| `founding_year` | Year the company was founded |
| `team_size` | Number of full-time employees |

Labels are derived from a composite rule-based scoring function applied to the
synthetic data, yielding three classes:

- **0 — Pass**: weak fundamentals, not recommended for investment
- **1 — Consider**: mixed signals, warrants further diligence
- **2 — Strong Buy**: strong growth, healthy margins, low leverage

The trained model is serialised to `model.pkl` via `joblib` and loaded at runtime
by the agent to produce a calibrated score out of 100 alongside the class label.
