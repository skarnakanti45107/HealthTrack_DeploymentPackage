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


## Local Installation & Setup

**1. Clone the repository and navigate into the directory:**
```bash
git clone [https://github.com/yourusername/HealthTrack.git](https://github.com/yourusername/HealthTrack.git)
cd HealthTrack
```

**2. Create and activate a secure virtual environment:**
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install the required dependencies:**
```bash
pip install -r requirements.txt
```

**4. Initialize the Database:**
```bash
alembic upgrade head
```

## Running the System

To fully deploy the system locally, you will need to run the backend API and the frontend dashboard on separate terminal instances.

**Terminal 1: Start the FastAPI Backend**
Ensure your virtual environment is active, then launch the Uvicorn server:
```bash
uvicorn main:app --reload
```
*   The backend API will be available at: `http://127.0.0.1:8000`
*   Interactive Swagger UI Documentation: `http://127.0.0.1:8000/docs`

**Terminal 2: Start the Dash Clinical UI**
Open a new terminal, activate the virtual environment, and run the dashboard:
```bash
python dashboard.py
```
*   The Provider Dashboard will be available at: `http://127.0.0.1:8050`

## System Architecture & Data Flow

*   **Ingestion:** Wearable telemetry is posted to standard REST endpoints.
*   **Validation:** Pydantic strictly types and sanitizes the JSON payload.
*   **Inference:** The data is passed to the RAM-cached ML model to extract `risk_level` and `contributing_factors`.
*   **Storage & State Checking:** Data is securely committed via SQLAlchemy. The rule engine evaluates the state to either log an incident or suppress a redundant warning.
*   **Visualization:** The Dash application requests the updated state and visually renders the clinical triage for the provider.
