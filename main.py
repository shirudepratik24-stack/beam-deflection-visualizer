import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    ChatOpenAI = None
    ChatPromptTemplate = None

BASE = Path(__file__).parent
DB = BASE / "recoverai.db"

app = FastAPI(title="RecoverAI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(BASE / "Frontend")), name="static")

PAYMENTS = [
    {"id":"pay_1001","customer":"Aarav Mehta","amount":2499,"currency":"INR","reason":"insufficient_funds","attempts":1,"days":0,"email":"aarav@example.com"},
    {"id":"pay_1002","customer":"Priya Shah","amount":8999,"currency":"INR","reason":"authentication_required","attempts":1,"days":1,"email":"priya@example.com"},
    {"id":"pay_1003","customer":"Rohan Patil","amount":1499,"currency":"INR","reason":"network_error","attempts":2,"days":0,"email":"rohan@example.com"},
    {"id":"pay_1004","customer":"Neha Kulkarni","amount":12999,"currency":"INR","reason":"card_declined","attempts":3,"days":3,"email":"neha@example.com"},
    {"id":"pay_1005","customer":"Vikram Joshi","amount":3999,"currency":"INR","reason":"insufficient_funds","attempts":1,"days":2,"email":"vikram@example.com"},
]

class RecoveryRequest(BaseModel):
    payment_id: str


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id TEXT, action TEXT, confidence REAL, rationale TEXT, outcome TEXT, created_at TEXT)")


def fallback(payment):
    reason = payment["reason"]
    if reason == "authentication_required":
        return {"action":"authentication_reminder","confidence":0.94,"rationale":"The issuer requires customer authentication; an authentication reminder is safer than blind retries."}
    if reason == "network_error" and payment["attempts"] < 3:
        return {"action":"smart_retry","confidence":0.88,"rationale":"A transient network failure with limited attempts is a reasonable retry candidate."}
    if reason == "insufficient_funds":
        return {"action":"customer_nudge","confidence":0.91,"rationale":"The customer likely needs to restore available balance before another attempt."}
    return {"action":"human_review","confidence":0.72,"rationale":"Repeated or ambiguous declines should not be blindly retried."}


def ai_decide(payment):
    if not os.getenv("OPENAI_API_KEY") or ChatOpenAI is None:
        return fallback(payment), "deterministic_fallback"
    try:
        llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a payment recovery controller. Choose exactly one action: smart_retry, customer_nudge, authentication_reminder, human_review. Never claim a real payment was executed. Prefer conservative actions. Return JSON with action, confidence (0-1), rationale."),
            ("human", "Payment context: {payment}")
        ])
        result = (prompt | llm).invoke({"payment": json.dumps(payment)})
        text = result.content if isinstance(result.content, str) else str(result.content)
        data = json.loads(text.replace("```json", "").replace("```", "").strip())
        allowed = {"smart_retry","customer_nudge","authentication_reminder","human_review"}
        if data.get("action") not in allowed:
            raise ValueError("invalid action")
        data["confidence"] = max(0, min(1, float(data.get("confidence", 0))))
        return data, "langchain_openai"
    except Exception:
        return fallback(payment), "fallback_after_ai_error"


def simulate(action, payment):
    outcomes = {
        "smart_retry": "simulated_retry_queued",
        "customer_nudge": "simulated_message_queued",
        "authentication_reminder": "simulated_authentication_request",
        "human_review": "escalated_to_human",
    }
    return outcomes[action]


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status":"ok","ai_configured":bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/api/payments")
def payments():
    return PAYMENTS


@app.post("/api/recover")
def recover(req: RecoveryRequest):
    payment = next((p for p in PAYMENTS if p["id"] == req.payment_id), None)
    if not payment:
        raise HTTPException(404, "Payment not found")
    decision, engine = ai_decide(payment)
    outcome = simulate(decision["action"], payment)
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO actions(payment_id,action,confidence,rationale,outcome,created_at) VALUES(?,?,?,?,?,?)", (payment["id"], decision["action"], decision["confidence"], decision["rationale"], outcome, now))
    return {"payment":payment,"decision":decision,"engine":engine,"outcome":outcome,"timestamp":now}


@app.get("/api/history")
def history():
    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        return [dict(x) for x in c.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 50").fetchall()]


@app.get("/")
def home():
    return FileResponse(BASE / "Frontend" / "index.html")
