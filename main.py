"""
main.py — Central ASGI application resolving API traffic and static routing.
"""

import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import AgentOrchestrator
from file_processor import FileProcessor

load_dotenv()

app = FastAPI(title="PE Due Diligence AI")

# CORS middleware — allow all origins for local demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DueDiligenceReport(BaseModel):
    company_summary: str
    financial_metrics: dict
    risks: list
    investment_score: int
    investment_label: str
    recommendation: str
    files_analysed: list


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyse", response_model=DueDiligenceReport)
async def analyse(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    processor = FileProcessor()
    texts_by_file: dict = {}

    for upload in files:
        file_bytes = await upload.read()
        try:
            text = processor.process(upload.filename, file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        texts_by_file[upload.filename] = text

    orchestrator = AgentOrchestrator()
    report = orchestrator.run(texts_by_file)

    return JSONResponse(content=report)
