# RecoverAI — Agentic Payment Recovery Engine

A Razorpay AI Buildathon project for the **AI Revenue Recovery** track. RecoverAI analyzes failed payment context and chooses a bounded recovery action using LangChain + OpenAI, with a deterministic fallback when AI is unavailable.

## What it demonstrates
- LangChain structured output for payment recovery decisions
- Conservative AI: the model recommends only four bounded actions
- Deterministic safety fallback when the model/API fails
- Simulated payment actions — no real money movement
- SQLite audit trail for every recovery action
- FastAPI API + browser dashboard
- KPIs: amount at risk, amount recovered, recovery rate, agent actions

## Run locally
1. Install Python 3.10+.
2. `python -m venv .venv`
3. Windows: `.venv\\Scripts\\activate` (macOS/Linux: `source .venv/bin/activate`)
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your OpenAI key. Never commit `.env`.
6. `uvicorn main:app --reload`
7. Open http://127.0.0.1:8000

## API
- `GET /api/health`
- `GET /api/payments`
- `GET /api/payments/{payment_id}`
- `POST /api/analyze/{payment_id}`
- `POST /api/recover/{payment_id}`
- `GET /api/metrics`

## Architecture
Browser → FastAPI → LangChain decision chain → policy-bounded action simulator → SQLite audit log → dashboard.

In production, the simulator would be replaced with authenticated Razorpay APIs/webhooks, with idempotency, approval controls, observability, and merchant-specific recovery policies.

## Demo story
Select a failed payment, click **Analyze**, show the AI decision and recovery probability, then click **Recover**. Refresh the dashboard to show the audit trail and updated KPIs.
