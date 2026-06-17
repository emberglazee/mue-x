"""MUE-X REST API — Control and monitor the agent from anywhere.

Usage:
    python -m mue serve
    uvicorn mue.api:app --host 127.0.0.1 --port 8791
"""

import json
from pathlib import Path

from fastapi import FastAPI, Query

from mue.evo.core import MueAgent

app = FastAPI(title="MUE-X API", version="1.0.0", docs_url="/api/docs")


def _agent():
    work_dir = Path(__file__).resolve().parent
    return MueAgent(str(work_dir))


@app.get("/api/status")
def get_status():
    a = _agent()
    return a.state


@app.post("/api/evolve")
def trigger_evolve():
    a = _agent()
    result = a.chat("/mue evolve")
    return {"ok": True, "response": result.get("response", "")}


@app.post("/api/mine")
def trigger_mine(query: str = Query("AI agent patterns")):
    a = _agent()
    result = a._handle_mine_command(query)
    return {"ok": True, "result": result}


@app.post("/api/reflect")
def trigger_reflect():
    a = _agent()
    result = a._handle_reflect_command()
    return {"ok": True, "response": result.get("response", "")}


@app.get("/api/genes")
def list_genes():
    a = _agent()
    return {"genes": a.state.get("genes", [])}
