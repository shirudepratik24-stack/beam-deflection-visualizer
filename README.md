# RecoverAI — Agentic Payment Recovery Engine

Razorpay AI Buildathon project for **AI Revenue Recovery**.

RecoverAI analyzes failed payments, estimates recovery potential, selects a safe recovery action with LangChain, simulates the action, and records an auditable outcome.

## What it demonstrates

- LangChain + OpenAI structured decision making
- Tool-style payment recovery actions
- Explicit safety boundary: the demo never moves real money
- SQLite audit trail
- FastAPI backend
- Browser dashboard
- Failure handling and deterministic fallback

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux
```

Put your OpenAI API key in `.env` as `OPENAI_API_KEY=...`.

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

## Architecture

```text
Failed Payment -> Recovery Agent -> Risk/Context Analysis -> Action Selection
                                      |                     |
                                      v                     v
                                  Audit DB           Safe Simulator
                                      \_____________________/
                                                |
                                           Dashboard
```

## Demo flow

1. Open the dashboard.
2. Select a failed payment.
3. Click **Recover payment**.
4. LangChain produces a structured recovery decision.
5. The safe simulator executes the selected action.
6. The result and decision are written to SQLite.

## Buildathon positioning

**Problem:** failed payments create avoidable revenue leakage.

**AI judgment:** the model decides among retry, customer nudge, authentication reminder, or human review; simple validation and safety checks remain deterministic code.

**Failure recovery:** if the AI call fails, the system uses a conservative deterministic fallback instead of crashing or inventing a payment outcome.

**Important:** this repository is a hackathon demonstration. It does not connect to production payment rails and does not execute real refunds, captures, or retries.
