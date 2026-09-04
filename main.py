import json, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()
DB = Path('recoverai.db')
app = FastAPI(title='RecoverAI', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

PAYMENTS = [
 {'id':'pay_1001','customer':'Aarav Sharma','email':'aarav@example.com','amount':2499,'reason':'insufficient_funds','attempts':1,'days_since':1},
 {'id':'pay_1002','customer':'Priya Patil','email':'priya@example.com','amount':8999,'reason':'authentication_required','attempts':1,'days_since':2},
 {'id':'pay_1003','customer':'Rahul Joshi','email':'rahul@example.com','amount':1499,'reason':'network_error','attempts':2,'days_since':1},
 {'id':'pay_1004','customer':'Sneha Kulkarni','email':'sneha@example.com','amount':12999,'reason':'card_expired','attempts':1,'days_since':5},
 {'id':'pay_1005','customer':'Vikram Singh','email':'vikram@example.com','amount':5999,'reason':'insufficient_funds','attempts':2,'days_since':3},
]

class Decision(BaseModel):
    action: Literal['smart_retry','customer_nudge','authentication_reminder','human_review']
    recovery_probability: float = Field(ge=0, le=1)
    priority: Literal['low','medium','high','critical']
    reason: str
    next_step: str


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, payment_id TEXT, action TEXT, outcome TEXT, created_at TEXT, source TEXT, details TEXT)')
init_db()


def deterministic(p):
    if p['reason']=='authentication_required': return Decision(action='authentication_reminder', recovery_probability=.82, priority='high', reason='The issuer requires customer authentication before another successful attempt.', next_step='Ask the customer to complete authentication, then retry.')
    if p['reason']=='card_expired': return Decision(action='human_review', recovery_probability=.18, priority='critical', reason='An expired card should not be retried automatically.', next_step='Request an updated payment method or route to support.')
    if p['reason']=='network_error' and p['attempts'] < 3: return Decision(action='smart_retry', recovery_probability=.68, priority='medium', reason='Transient network failures can recover on a controlled retry.', next_step='Retry once with exponential backoff.')
    if p['reason']=='insufficient_funds': return Decision(action='customer_nudge', recovery_probability=.54, priority='high', reason='A balance-related failure is more likely to recover after customer action.', next_step='Notify the customer and offer a retry window.')
    return Decision(action='human_review', recovery_probability=.25, priority='medium', reason='No safe automated recovery policy matched this case.', next_step='Send to operations for review.')


def decide(p):
    key = os.getenv('OPENAI_API_KEY')
    if not key: return deterministic(p), 'fallback'
    try:
        llm = ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'), temperature=0)
        prompt = ChatPromptTemplate.from_messages([('system','You are a conservative payment recovery controller. Never invent payment facts. Choose exactly one bounded action. Do not authorize refunds, transfers, or irreversible actions. Return structured output.'),('human','Payment: {payment}')])
        chain = prompt | llm.with_structured_output(Decision)
        return chain.invoke({'payment': json.dumps(p)}), 'langchain'
    except Exception:
        return deterministic(p), 'fallback'


def record(payment_id, action, outcome, source, details):
    with sqlite3.connect(DB) as c:
        c.execute('INSERT INTO audit VALUES (?,?,?,?,?,?,?)',(str(uuid.uuid4()),payment_id,action,outcome,datetime.now(timezone.utc).isoformat(),source,json.dumps(details)))

@app.get('/api/health')
def health(): return {'status':'ok','service':'RecoverAI'}

@app.get('/api/payments')
def payments(): return PAYMENTS

@app.get('/api/payments/{payment_id}')
def payment(payment_id: str):
    p=next((x for x in PAYMENTS if x['id']==payment_id),None)
    if not p: raise HTTPException(404,'Payment not found')
    return p

@app.post('/api/analyze/{payment_id}')
def analyze(payment_id: str):
    p=next((x for x in PAYMENTS if x['id']==payment_id),None)
    if not p: raise HTTPException(404,'Payment not found')
    d,source=decide(p)
    return {'payment':p,'decision':d.model_dump(),'source':source}

@app.post('/api/recover/{payment_id}')
def recover(payment_id: str):
    p=next((x for x in PAYMENTS if x['id']==payment_id),None)
    if not p: raise HTTPException(404,'Payment not found')
    d,source=decide(p)
    outcomes={'smart_retry':'recovered','customer_nudge':'message_sent','authentication_reminder':'authentication_requested','human_review':'queued_for_human'}
    outcome=outcomes[d.action]
    record(payment_id,d.action,outcome,source,{'amount':p['amount'],'reason':p['reason']})
    return {'payment_id':payment_id,'amount':p['amount'],'decision':d.model_dump(),'outcome':outcome,'source':source}

@app.get('/api/metrics')
def metrics():
    with sqlite3.connect(DB) as c:
        rows=c.execute('SELECT action,outcome,details FROM audit ORDER BY created_at DESC').fetchall()
    recovered=sum(json.loads(r[2]).get('amount',0) for r in rows if r[1]=='recovered')
    at_risk=sum(p['amount'] for p in PAYMENTS)
    return {'payments':len(PAYMENTS),'at_risk':at_risk,'actions':len(rows),'recovered':recovered,'recovery_rate':round(recovered/at_risk,4) if at_risk else 0,'audit':[{'action':r[0],'outcome':r[1],'details':json.loads(r[2])} for r in rows]}

app.mount('/', StaticFiles(directory='Frontend', html=True), name='frontend')
