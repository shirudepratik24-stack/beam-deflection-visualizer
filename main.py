import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
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

load_dotenv()
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
class RecoveryRequest(BaseModel): payment_id: str

def init_db():
 with sqlite3.connect(DB) as c: c.execute("CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY AUTOINCREMENT,payment_id TEXT,action TEXT,confidence REAL,rationale TEXT,outcome TEXT,created_at TEXT)")

def fallback(p):
 r=p["reason"]
 if r=="authentication_required": return {"action":"authentication_reminder","confidence":.94,"rationale":"Issuer authentication is required; remind the customer rather than blindly retrying."}
 if r=="network_error" and p["attempts"]<3: return {"action":"smart_retry","confidence":.88,"rationale":"A transient network error with limited attempts is a reasonable retry candidate."}
 if r=="insufficient_funds": return {"action":"customer_nudge","confidence":.91,"rationale":"The customer likely needs to restore available balance before another attempt."}
 return {"action":"human_review","confidence":.72,"rationale":"Repeated or ambiguous declines should not be blindly retried."}

def ai_decide(p):
 if not os.getenv("OPENAI_API_KEY") or ChatOpenAI is None: return fallback(p),"deterministic_fallback"
 try:
  llm=ChatOpenAI(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),temperature=0)
  prompt=ChatPromptTemplate.from_messages([("system","You are a payment recovery controller. Choose exactly one: smart_retry, customer_nudge, authentication_reminder, human_review. Be conservative. Never claim real payment execution. Return JSON with action, confidence 0-1, rationale."),("human","Payment: {payment}")])
  result=(prompt|llm).invoke({"payment":json.dumps(p)})
  text=result.content if isinstance(result.content,str) else str(result.content)
  data=json.loads(text.replace("```json","").replace("```","").strip())
  if data.get("action") not in {"smart_retry","customer_nudge","authentication_reminder","human_review"}: raise ValueError("invalid action")
  data["confidence"]=max(0,min(1,float(data.get("confidence",0))))
  return data,"langchain_openai"
 except Exception: return fallback(p),"fallback_after_ai_error"

def simulate(action):
 return {"smart_retry":"simulated_retry_queued","customer_nudge":"simulated_message_queued","authentication_reminder":"simulated_authentication_request","human_review":"escalated_to_human"}[action]

@app.on_event("startup")
def startup(): init_db()
@app.get("/api/health")
def health(): return {"status":"ok","ai_configured":bool(os.getenv("OPENAI_API_KEY"))}
@app.get("/api/payments")
def payments(): return PAYMENTS
@app.post("/api/recover")
def recover(req:RecoveryRequest):
 p=next((x for x in PAYMENTS if x["id"]==req.payment_id),None)
 if not p: raise HTTPException(404,"Payment not found")
 decision,engine=ai_decide(p); outcome=simulate(decision["action"]); now=datetime.now(timezone.utc).isoformat()
 with sqlite3.connect(DB) as c: c.execute("INSERT INTO actions(payment_id,action,confidence,rationale,outcome,created_at) VALUES(?,?,?,?,?,?)",(p["id"],decision["action"],decision["confidence"],decision["rationale"],outcome,now))
 return {"payment":p,"decision":decision,"engine":engine,"outcome":outcome,"timestamp":now}
@app.get("/api/history")
def history():
 with sqlite3.connect(DB) as c:
  c.row_factory=sqlite3.Row
  return [dict(x) for x in c.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 50").fetchall()]
@app.get("/")
def home(): return FileResponse(BASE/"Frontend"/"index.html")
