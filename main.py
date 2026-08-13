from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import models, schemas, crud
from database import engine, get_db
import logging
import asyncio
import random
import joblib
import numpy as np
import pandas as pd
from functools import lru_cache

logger = logging.getLogger(__name__)

# Initialize DB
models.Base.metadata.create_all(bind=engine)
# Load Machine Learning Model
try:
    risk_model = joblib.load("health_risk_model.pkl")
    logger.info("Successfully loaded health_risk_model.pkl")
except Exception as e:
    logger.error(f"Failed to load ML model: {e}")
    risk_model = None

app = FastAPI(
    title="HealthTrack API",
    description="API for Remote Patient Monitoring System with Real-Time Alerts",
    version="1.1.0"
)

import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate how long it took
    process_time = time.time() - start_time
    process_time_ms = round(process_time * 1000, 2)
    
    # Add timing to the response headers and print it to the terminal
    response.headers["X-Process-Time"] = str(process_time_ms)
    print(f"Endpoint: {request.method} {request.url.path} - Completed in: {process_time_ms} ms")
    
    return response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- NEW: Fake Login Route for Swagger UI ---
@app.post("/token", include_in_schema=False)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # This automatically gives Swagger the exact token it needs to let you in
    return {"access_token": "fake-super-secret-token", "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != "fake-super-secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "Dr. Smith"

def send_alert_notification(alerts: List[models.Alert]):
    for alert in alerts:
        payload = {
            "patient_id": alert.patient_id,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.created_at.isoformat()
        }
        if alert.severity == models.AlertSeverity.CRITICAL:
            logger.warning(f"URGENT PAGER TRIGGERED: {payload}")
        else:
            logger.info(f"Notification queued: {payload}")

# --- Patients ---

@app.get("/patients/", response_model=List[schemas.PatientResponse], tags=["Patients"])
def get_all_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    return db.query(models.Patient).offset(skip).limit(limit).all()

@app.post("/patients/", response_model=schemas.PatientResponse, tags=["Patients"])
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    return crud.create_patient(db, patient)

@app.get("/patients/{patient_id}", response_model=schemas.PatientResponse, tags=["Patients"])
def read_patient(patient_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

# --- Thresholds ---
@app.post("/patients/{patient_id}/thresholds/", response_model=schemas.PatientThresholdResponse, tags=["Thresholds"])
def set_patient_threshold(patient_id: int, threshold: schemas.PatientThresholdCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if not crud.get_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.create_patient_threshold(db, threshold, patient_id)

# --- Vitals & Activity ---
@app.post("/patients/{patient_id}/vitals/", response_model=schemas.VitalSignsResponse, tags=["Vital Signs"])
def create_vitals_for_patient(patient_id: int, vitals: schemas.VitalSignsCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if not crud.get_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_vital, new_alerts = crud.create_vital_sign(db=db, vital_sign=vitals, patient_id=patient_id)
    
    if new_alerts:
        background_tasks.add_task(send_alert_notification, new_alerts)
        
    return db_vital

@app.post("/patients/{patient_id}/activity/", response_model=schemas.ActivityDataResponse, tags=["Activity"])
def create_activity_for_patient(patient_id: int, activity: schemas.ActivityDataCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if not crud.get_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_activity, new_alerts = crud.create_activity_data(db=db, activity=activity, patient_id=patient_id)
    
    if new_alerts:
        background_tasks.add_task(send_alert_notification, new_alerts)
        
    return db_activity

# --- Alerts Management ---
@app.get("/alerts/", response_model=List[schemas.AlertResponse], tags=["Alerts"])
def get_alerts(patient_id: int = None, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    return crud.get_active_alerts(db, patient_id=patient_id)

@app.patch("/alerts/{alert_id}/acknowledge", response_model=schemas.AlertResponse, tags=["Alerts"])
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    alert = crud.acknowledge_alert(db, alert_id, user)
    if not alert:
        raise HTTPException(status_code=404, detail="Active alert not found")
    return alert

# --- WebSocket Real-Time Stream ---
@app.websocket("/ws/vitals/{patient_id}")
async def websocket_vitals(websocket: WebSocket, patient_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    
    # Ensure patient actually exists before streaming
    patient = crud.get_patient(db, patient_id)
    if not patient:
        await websocket.close()
        return

    try:
        while True:
            # Generate simulated live telemetry for the selected patient
            live_data = {
                "heart_rate": random.randint(55, 115),
                "blood_pressure_systolic": random.randint(110, 135),
                "blood_pressure_diastolic": random.randint(70, 85),
                "recorded_at": datetime.now().strftime("%H:%M:%S")
            }
            
            await websocket.send_json(live_data)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from patient {patient_id} vital stream.")

from fastapi.responses import RedirectResponse
@app.get("/", include_in_schema=False)


# --- In-Memory Caching Optimization ---
@lru_cache(maxsize=128)
def cached_risk_prediction(age, steps, active_mins, hr, sys_bp, dia_bp, glucose):
    """
    Caches the ML model output. If the exact same vitals are passed, 
    it returns the saved result in 0.001ms instead of recalculating!
    """
    features = pd.DataFrame([[
        age, steps, active_mins, hr, sys_bp, dia_bp, glucose
    ]], columns=['age', 'steps_per_day', 'active_minutes', 'heart_rate', 'sys_bp', 'dia_bp', 'blood_glucose'])
    
    return str(risk_model.predict(features)[0])

# --- Analytics & Risk Assessment ---
@app.get("/patients/{patient_id}/risk-assessment", response_model=schemas.RiskAssessmentResponse, tags=["Analytics"])
def get_patient_risk_assessment(patient_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if not risk_model:
        raise HTTPException(status_code=500, detail="Risk prediction model is offline.")

    # 1. Fetch Patient & Latest Data
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    latest_vitals = db.query(models.VitalSigns).filter(models.VitalSigns.patient_id == patient_id).order_by(models.VitalSigns.recorded_at.desc()).first()
    latest_activity = db.query(models.ActivityData).filter(models.ActivityData.patient_id == patient_id).order_by(models.ActivityData.recorded_date.desc()).first()

    if not latest_vitals or not latest_activity:
        raise HTTPException(status_code=400, detail="Insufficient historical data to generate risk assessment.")

    # 2. Extract Features (Bulletproof Date Handling)
    try:
        # Check if SQLite returned a string instead of a datetime object
        if isinstance(patient.date_of_birth, str):
            dob_string = patient.date_of_birth.replace('Z', '+00:00')
            dob = datetime.fromisoformat(dob_string).replace(tzinfo=None)
        else:
            dob = patient.date_of_birth.replace(tzinfo=None)
            
        now = datetime.now().replace(tzinfo=None)
        age = (now - dob).days // 365
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        age = 45 # Safe fallback if date parsing entirely fails

    # Use a Pandas DataFrame so the model recognizes the feature names
    features = pd.DataFrame([[
        age, 
        latest_activity.steps, 
        latest_activity.active_minutes, 
        latest_vitals.heart_rate, 
        latest_vitals.blood_pressure_systolic, 
        latest_vitals.blood_pressure_diastolic, 
        latest_vitals.blood_glucose or 100.0
    ]], columns=['age', 'steps_per_day', 'active_minutes', 'heart_rate', 'sys_bp', 'dia_bp', 'blood_glucose'])

    # 3. Predict Risk Level
    prediction = cached_risk_prediction(
        age, 
        latest_activity.steps, 
        latest_activity.active_minutes, 
        latest_vitals.heart_rate, 
        latest_vitals.blood_pressure_systolic, 
        latest_vitals.blood_pressure_diastolic, 
        latest_vitals.blood_glucose or 100.0
    )

    # 4. Identify Contributing Factors (Rule-Based Mapping)
    factors = []
    if latest_vitals.heart_rate > 100 or latest_vitals.heart_rate < 50:
        factors.append(f"Abnormal Heart Rate: {latest_vitals.heart_rate} BPM")
    if latest_vitals.blood_pressure_systolic > 140 or latest_vitals.blood_pressure_diastolic > 90:
        factors.append(f"Elevated Blood Pressure: {latest_vitals.blood_pressure_systolic}/{latest_vitals.blood_pressure_diastolic} mmHg")
    if latest_vitals.blood_glucose and latest_vitals.blood_glucose > 140:
        factors.append(f"Hyperglycemia Risk: {latest_vitals.blood_glucose} mg/dL")
    if latest_activity.steps < 3000:
        factors.append(f"Sedentary Lifestyle: Only {latest_activity.steps} steps recorded")
    
    if not factors:
        factors.append("No immediate acute data anomalies detected.")

    # 5. Generate Automated System Recommendations
    recommendations = []
    if prediction == "Critical":
        recommendations.append("[SYSTEM GENERATED] Immediate clinical intervention required. Dispatch on-call physician.")
        recommendations.append("[SYSTEM GENERATED] Administer stat ECG and comprehensive metabolic panel.")
    elif prediction == "High":
        recommendations.append("[SYSTEM GENERATED] Schedule urgent telehealth consultation within 24 hours.")
        if "Elevated Blood Pressure" in str(factors):
            recommendations.append("[SYSTEM GENERATED] Review current antihypertensive medication dosage.")
    elif prediction == "Moderate":
        recommendations.append("[SYSTEM GENERATED] Monitor vitals daily. Patient should hydrate and increase light physical activity.")
    else:
        recommendations.append("[SYSTEM GENERATED] Maintain current care plan. Reassess in 30 days.")

    return {
        "patient_id": patient_id,
        "risk_level": prediction,
        "contributing_factors": factors,
        "system_recommendations": recommendations,
        "assessment_timestamp": datetime.now(timezone.utc)
    }


def redirect_to_docs():
    return RedirectResponse(url="/docs")