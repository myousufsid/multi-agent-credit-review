# Multi-Agent AI Credit Review System

A multi-agent credit review support system designed to help small-business banking teams identify potential working-capital concerns and prepare structured information for human credit review.

The system uses specialized Python agents coordinated by a Supervisor Agent to analyze financial information, identify missing documents, and generate an organized review report.

> **Important:** This project uses fictional financial data for demonstration purposes only. It supports human underwriting review and must never independently approve or reject a credit application. All lending decisions remain with human credit officers.

---

## Project Architecture

The system consists of four specialist agents coordinated by a Supervisor Agent.

1. **Cash Flow Agent:** Evaluates liquidity, available credit, upcoming obligations, and potential funding gaps.
2. **Financial Analysis & Risk Agent:** Identifies financial indicators, potential warning signs, and positive factors.
3. **Document Agent:** Checks whether required financial documents have been received.
4. **Underwriting Preparation Agent:** Combines the findings into a structured report for human review.
5. **Supervisor Agent:** Coordinates agent execution, tracks execution status, and handles workflow failures.

Financial calculations are performed using deterministic Python logic rather than relying on an LLM for arithmetic.

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

## Technology Stack

**Backend**
- Python 3.11+
- FastAPI
- Uvicorn
- Decimal-based financial calculations

**Frontend**
- HTML5
- CSS3
- JavaScript

**Testing**
- pytest
- FastAPI Test Client / HTTPX

## Prerequisites

- Python 3.11 or newer
- pip
- A terminal or command prompt
- A modern web browser

## Installation

Clone or download the project and navigate to its backend directory:

```bash
cd multi-agent-credit-review/backend
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

For Windows, activate the environment using:

```bash
venv\Scripts\activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

### 1. Start the Backend

From the `backend/` directory, with the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

The FastAPI server will be available at:

http://127.0.0.1:8000

Keep the terminal running while using the application.

### 2. Open the Frontend

From the project root, open:

```bash
open frontend/index.html
```

This command works on macOS. Alternatively, open `frontend/index.html` directly in a web browser.

The dashboard communicates with the backend API to retrieve and display the credit review report.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks backend availability |
| GET | `/review/demo` | Executes the sample multi-agent credit review workflow |
| GET | `/docs` | Opens interactive FastAPI documentation |

Example health check:

```bash
curl http://127.0.0.1:8000/health
```

Example demo review:

```bash
curl http://127.0.0.1:8000/review/demo
```

Interactive API documentation:

http://127.0.0.1:8000/docs

## Running Tests

From the `backend/` directory, with the virtual environment activated:

```bash
pytest -q
```

The current test suite contains **114 passing tests** covering:

- Financial calculation logic
- Individual specialist agents
- Agent orchestration and workflow execution

## Sample Scenario

The application uses a fictional business called Greenfield Supplies.

Its sample financial information includes:

- Credit line limit: $75,000
- Currently used credit: $68,000
- Bank balance: $19,000
- Upcoming payroll: $34,000
- Upcoming vendor payments: $22,000
- Incoming receivables: $62,000 expected in 30 days

The system calculates financial indicators such as credit utilization, available credit, immediate funding gap, and remaining funding gap.

Incoming receivables are treated as future funds and are not counted as immediately available cash.

## Current MVP Scope and Limitations

The current MVP demonstrates the core multi-agent workflow using fictional JSON data.

**Included:**
- Four specialized agents and a coordinating Supervisor Agent
- Deterministic financial calculations
- Financial findings and supporting evidence
- Required-document status verification
- Consolidated underwriting preparation report
- Interactive frontend dashboard
- API error handling and automated tests

**Not included:**
- Real banking or accounting integrations
- Real customer financial information
- Document OCR or automated document extraction
- Database persistence or user authentication
- Production deployment
- LLM integration

These capabilities may be considered for future development.

## Security, Governance, and Human Oversight

The system is designed as a decision-support tool rather than an autonomous lending system.

Key principles include:

- **Human oversight:** Credit officers retain final lending authority.
- **Explainability:** Findings include supporting financial evidence.
- **Fairness:** The MVP avoids automated credit approval or rejection decisions.
- **Privacy:** Only fictional financial data is used.
- **Accountability:** Agent execution status and workflow failures are tracked.

## Development Progress

| Stage | Scope | Status |
|---|---|---|
| 1 | Project initialization and backend setup | Complete |
| 2 | Financial calculation engine and sample data | Complete |
| 3 | Four specialist agents | Complete |
| 4 | Supervisor orchestration and API integration | Complete |
| 5 | Interactive frontend dashboard | Complete |
| 6 | End-to-end testing, validation, and final polish | Complete |

---

**Project Status:** MVP implementation and validation completed.

**Disclaimer:** This application is an educational demonstration and is not intended for actual lending decisions or production banking use.

See [AGENTS.md](AGENTS.md) for full conventions and business constraints.