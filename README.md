# HealthTrack: AI-Driven Remote Patient Monitoring

HealthTrack is a comprehensive, microservice-inspired healthcare platform designed to eliminate the "clinical blind spot." By integrating simulated IoMT (Internet of Medical Things) telemetry, an in-memory machine learning triage engine, and a reactive clinical dashboard, this system shifts chronic disease management from a reactive model to a proactive, data-driven methodology.

## Core Features

*   **Real-Time Data Ingestion:** A high-throughput FastAPI backend capable of processing physiological payloads in sub-25ms latency.
*   **AI Risk Assessment Engine:** Integrates a Scikit-Learn Random Forest Classifier (98.6% accuracy) cached entirely in RAM via `joblib` for zero-I/O, sub-millisecond clinical triage.
*   **Alert Fatigue Mitigation:** An intelligent database rule engine that actively suppresses duplicate, non-critical physiological warnings while guaranteeing immediate bypass for severe, acute anomalies.
*   **Interactive Clinical Dashboard:** A Plotly Dash frontend providing real-time gauge charting, historical dual-line BP trends, and dynamic color-coded UI rendering based on AI risk outputs.
*   **HIPAA-Compliant Architecture:** Enforces strictly stateless JWT (JSON Web Token) authentication, Role-Based Access Control (RBAC), and SQLAlchemy parameterized query sanitization.

## Technology Stack

*   **Backend:** Python 3, FastAPI, Uvicorn (ASGI)
*   **Data Science & ML:** Scikit-Learn, Joblib, NumPy
*   **Database:** SQLite / SQL Server, SQLAlchemy (ORM), Alembic
*   **Frontend UI:** Dash by Plotly
*   **Security:** OAuth2, Passlib (bcrypt), Pydantic

## Project Structure

```text
healthtrack/
├── main.py                 # FastAPI application, routing, and security
├── dashboard.py            # Dash frontend clinical workspace
├── models.py               # SQLAlchemy database schemas and constraints
├── schemas.py              # Pydantic data validation and sanitization
├── database.py             # Database connection pooling and session config
├── health_risk_model.pkl   # Serialized Random Forest ML model
├── alembic/                # Database migration scripts
├── requirements.txt        # Production dependencies
└── README.md               # System documentation
