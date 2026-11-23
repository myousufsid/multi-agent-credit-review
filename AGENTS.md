# AGENTS.md — Multi-Agent AI Credit Review System

## Project Purpose

A multi-agent AI system that assists small-business banking teams by preparing structured underwriting information for human review. The system analyzes fictional financial data, identifies potential working-capital concerns, checks document availability, and consolidates findings into a structured report for a human underwriter, who makes the final credit decision.

> **Critical constraint:** This application must never independently approve or reject credit. Every output is advisory only and must be reviewed by a qualified human before any lending decision is made.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Agents | Python modules (expandable to LLM integration) |
| Frontend | Plain HTML, CSS, JavaScript (ES6) |
| Testing | pytest |

---

## Project Structure

```text
multi-agent-credit-review/
├── AGENTS.md
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── cash_flow_agent.py
│   │   │   ├── financial_risk_agent.py
│   │   │   ├── document_agent.py
│   │   │   ├── underwriting_agent.py
│   │   │   └── supervisor_agent.py
│   │   ├── services/
│   │   │   └── financial_calculations.py
│   │   └── data/
│   │       ├── __init__.py
│   │       ├── sample_business.json
│   │       └── sample_documents.json
│   └── tests/
│       ├── __init__.py
│       ├── test_financial_calculations.py
│       ├── test_agents.py
│       └── test_supervisor.py
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

---

## Coding Conventions

- **Python:** Follow PEP 8. Use type hints on all function signatures.
- **FastAPI:** Keep API responsibilities organized and maintain `main.py` as the application entry point.
- **Agents:** Each specialist agent lives in its own module under `backend/app/agents/`.
- **Frontend:** Vanilla JS only — no build toolchain until complexity demands it.
- **Naming:** `snake_case` for Python, `camelCase` for JavaScript, `kebab-case` for CSS classes.
- **Comments:** Explain *why*, not *what*. Keep functions small and focused.
- **Tests:** Every agent and service function must have at least one pytest test.

---

## Staged Development Workflow

| Stage | Scope | Status |
|---|---|---|
| 1 — Init | Project scaffold, FastAPI setup, frontend foundation | Complete |
| 2 — Financial Calculations | Deterministic financial calculation engine and sample data | Complete |
| 3 — Agents | Four specialist agents for cash flow, financial risk, document verification, and underwriting preparation | Complete |
| 4 — Orchestration | Supervisor Agent, workflow coordination, and API integration | Complete |
| 5 — Frontend | Interactive credit review dashboard | Complete |
| 6 — Validation | End-to-end testing, error handling, documentation, and final validation | Complete |
| Future — LLM Integration | Optional LLM capabilities within the existing agent architecture | Deferred |

> The current MVP is complete. When extending the project, preserve existing functionality and work incrementally. Do not introduce future-stage features unless explicitly requested.

---

## Key Business Constraints

1. **Human-in-the-loop always:** The system prepares information; humans make all lending decisions.
2. **Fictional data only:** No real applicant PII or actual financial records.
3. **No autonomous decisions:** Agent outputs are advisory findings, not credit approvals or rejections.
4. **Audit-friendly:** Every agent action and finding should be traceable and explainable.
5. **Deterministic financial calculations:** Python-based calculations remain responsible for financial arithmetic. Never rely on an LLM for financial calculations.
6. **LLM integration is deferred:** The current MVP must work without an LLM API key or external LLM calls. Future LLM capabilities may be introduced through clearly defined integration points without making the existing system dependent on an LLM.
7. **Privacy and fairness:** Preserve data privacy, minimize sensitive information exposure, and avoid unsupported or discriminatory conclusions.
8. **Human oversight and accountability:** LLM-generated or agent-generated findings must remain reviewable, explainable, and subject to human oversight.