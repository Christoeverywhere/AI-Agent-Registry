"""
Quick smoke-test — run with: python test_platform.py
(server must be running: uvicorn main:app --reload)
"""
import requests

BASE = "http://127.0.0.1:8000"
OK = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

def check(label, condition):
    print(f"  {OK if condition else FAIL}  {label}")

print("\n── REQ 1: Agent Registry ──────────────────────────────")

r = requests.post(f"{BASE}/agents", json={
    "name": "DocParser",
    "description": "Extracts structured data from PDFs",
    "endpoint": "https://api.example.com/parse"
})
check("Register DocParser → 201", r.status_code == 201)
check("Has tags field", "tags" in r.json()["agent"])
print(f"     tags: {r.json()['agent']['tags']}")

r2 = requests.post(f"{BASE}/agents", json={
    "name": "Summarizer",
    "description": "Summarizes long text documents into bullet points",
    "endpoint": "https://api.example.com/summarize"
})
check("Register Summarizer → 201", r2.status_code == 201)

# Idempotent re-register
r3 = requests.post(f"{BASE}/agents", json={
    "name": "DocParser",
    "description": "Extracts structured data from PDFs",
    "endpoint": "https://api.example.com/parse"
})
check("Re-register same name → existing record returned", "already registered" in r3.json()["message"])

r4 = requests.get(f"{BASE}/agents")
check("List agents → 2 agents", r4.json()["count"] == 2)

r5 = requests.get(f"{BASE}/search?q=pdf")
check("Search 'pdf' → finds DocParser", r5.json()["count"] == 1)

r6 = requests.get(f"{BASE}/search?q=PDF")
check("Search 'PDF' (uppercase) → case-insensitive match", r6.json()["count"] == 1)

r7 = requests.get(f"{BASE}/search?q=zzznomatch")
check("Search no-match → 0 results", r7.json()["count"] == 0)

print("\n── REQ 2: Usage Logging ───────────────────────────────")

r8 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentA", "target": "DocParser", "units": 10, "request_id": "abc123"
})
check("Log usage → 201", r8.status_code == 201)

r9 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentA", "target": "DocParser", "units": 10, "request_id": "abc123"
})
check("Duplicate request_id → skipped", r9.json().get("skipped") is True)

r10 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentB", "target": "DocParser", "units": 50, "request_id": "xyz999"
})
check("Second unique usage logged", r10.status_code == 201)

r11 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentA", "target": "Summarizer", "units": 80, "request_id": "sum001"
})
check("Usage for Summarizer logged", r11.status_code == 201)

summary = requests.get(f"{BASE}/usage-summary").json()["summary"]
doc_total = next((x["total_units"] for x in summary if x["agent"] == "DocParser"), 0)
sum_total = next((x["total_units"] for x in summary if x["agent"] == "Summarizer"), 0)
check(f"DocParser total = 60 (not 70 — duplicate ignored)", doc_total == 60)
check(f"Summarizer total = 80", sum_total == 80)

print("\n── REQ 3: Edge Cases ──────────────────────────────────")

r12 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentA", "target": "GhostAgent", "units": 5, "request_id": "ghost1"
})
check("Unknown target → 404", r12.status_code == 404)

r13 = requests.post(f"{BASE}/agents", json={"name": "", "description": "x", "endpoint": "y"})
check("Blank name → 422 validation error", r13.status_code == 422)

r14 = requests.post(f"{BASE}/usage", json={
    "caller": "AgentA", "target": "DocParser", "units": -5, "request_id": "neg1"
})
check("Negative units → 422 validation error", r14.status_code == 422)

print("\n── Done ────────────────────────────────────────────────\n")