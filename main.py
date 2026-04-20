from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, validator
from typing import Optional
from collections import defaultdict
import uuid
import re

app = FastAPI(title="Agent Discovery & Usage Platform", version="1.0.0")

# ── In-memory storage ──────────────────────────────────────────────────────────
agents: dict[str, dict] = {}          # name → agent record
usage_log: list[dict] = []            # all usage events
seen_request_ids: set[str] = set()    # idempotency guard
usage_totals: dict[str, int] = defaultdict(int)   # target → total units


# ── Models ─────────────────────────────────────────────────────────────────────
class AgentIn(BaseModel):
    name: str
    description: str
    endpoint: str

    @validator("name", "description", "endpoint")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()


class UsageIn(BaseModel):
    caller: str
    target: str
    units: int
    request_id: str

    @validator("caller", "target", "request_id")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()

    @validator("units")
    def positive_units(cls, v):
        if v <= 0:
            raise ValueError("units must be a positive integer")
        return v


# ── Tag extraction (Bonus – Option B: keyword logic) ──────────────────────────
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "of", "to", "from",
    "with", "that", "this", "is", "are", "as", "at", "by", "it", "its",
    "on", "be", "can", "into", "via", "using", "data",
}

def extract_tags(description: str) -> list[str]:
    """
    Simple keyword extraction:
    - lowercase + tokenise on non-alpha
    - remove stopwords and short tokens
    - deduplicate while preserving order
    """
    tokens = re.findall(r"[a-z]+", description.lower())
    seen = set()
    tags = []
    for t in tokens:
        if len(t) > 2 and t not in STOPWORDS and t not in seen:
            seen.add(t)
            tags.append(t)
    return tags


# ── REQ 1: Agent Registry ──────────────────────────────────────────────────────
@app.post("/agents", status_code=201)
def add_agent(body: AgentIn):
    """Register a new agent (idempotent on name)."""
    if body.name in agents:
        # Return existing record – no duplicate, no error
        return {"message": "Agent already registered", "agent": agents[body.name]}

    record = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "description": body.description,
        "endpoint": body.endpoint,
        "tags": extract_tags(body.description),
    }
    agents[body.name] = record
    return {"message": "Agent registered", "agent": record}


@app.get("/agents")
def list_agents():
    """Return all registered agents."""
    return {"count": len(agents), "agents": list(agents.values())}


# ── REQ 1 #3: Search ───────────────────────────────────────────────────────────
@app.get("/search")
def search_agents(q: str = Query(..., min_length=1, description="Search query")):
    """Case-insensitive search across name and description."""
    q_lower = q.lower()
    results = [
        a for a in agents.values()
        if q_lower in a["name"].lower() or q_lower in a["description"].lower()
    ]
    return {"query": q, "count": len(results), "results": results}


# ── REQ 2: Usage Logging ───────────────────────────────────────────────────────
@app.post("/usage", status_code=201)
def log_usage(body: UsageIn):
    """Log a usage event. Duplicate request_id is silently ignored."""
    # Idempotency check
    if body.request_id in seen_request_ids:
        return {"message": "Duplicate request_id – usage not recorded", "skipped": True}

    # Unknown target guard
    if body.target not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Target agent '{body.target}' is not registered."
        )

    seen_request_ids.add(body.request_id)
    event = body.dict()
    usage_log.append(event)
    usage_totals[body.target] += body.units

    return {"message": "Usage logged", "event": event}


@app.get("/usage-summary")
def usage_summary():
    """Return total units consumed per target agent."""
    summary = [
        {"agent": target, "total_units": total}
        for target, total in sorted(usage_totals.items(), key=lambda x: -x[1])
    ]
    return {"summary": summary}


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "agents_registered": len(agents)}