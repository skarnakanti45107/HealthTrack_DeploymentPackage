from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta, timezone
import models, schemas
import logging

logger = logging.getLogger(__name__)

# --- Patient CRUD ---
def get_patient(db: Session, patient_id: int):
    try:
        return db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching patient {patient_id}: {e}")
        return None

def get_patients(db: Session, skip: int = 0, limit: int = 100):
    try:
        # The offset and limit handle the pagination optimization!
        return db.query(models.Patient).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching patients list: {e}")
        return []

def create_patient(db: Session, patient: schemas.PatientCreate):
    try:
        db_patient = models.Patient(**patient.model_dump())
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        logger.info(f"Created patient ID: {db_patient.id}")
        return db_patient
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during patient creation: {e}")
        raise e

# --- Thresholds CRUD ---
def create_patient_threshold(db: Session, threshold: schemas.PatientThresholdCreate, patient_id: int):
    db_threshold = models.PatientThreshold(**threshold.model_dump(), patient_id=patient_id)
    db.add(db_threshold)
    db.commit()
    db.refresh(db_threshold)
    return db_threshold

def get_patient_thresholds(db: Session, patient_id: int):
    return db.query(models.PatientThreshold).filter(models.PatientThreshold.patient_id == patient_id).all()

# --- Alert Evaluation Engine ---
def check_and_create_alert(db: Session, patient_id: int, metric_name: str, value: float, generated_alerts: list):
    # 1. Fetch custom thresholds, fallback to clinical defaults if none exist
    threshold = db.query(models.PatientThreshold).filter(
        models.PatientThreshold.patient_id == patient_id, 
        models.PatientThreshold.metric_name == metric_name
    ).first()
    
    min_val = threshold.min_value if threshold and threshold.min_value is not None else get_default_min(metric_name)
    max_val = threshold.max_value if threshold and threshold.max_value is not None else get_default_max(metric_name)

    severity = None
    message = ""

    # 2. Pattern & Threshold Rules
    if value > max_val * 1.2 or value < min_val * 0.8:
        severity = models.AlertSeverity.CRITICAL
        message = f"Critical: {metric_name} is severely out of bounds at {value}."
    elif value > max_val or value < min_val:
        severity = models.AlertSeverity.WARNING
        message = f"Warning: {metric_name} is out of normal bounds at {value}."

    # 3. Alert Suppression Logic (Reduce Fatigue)
    if severity:
        recent_alert = db.query(models.Alert).filter(
            models.Alert.patient_id == patient_id,
            models.Alert.metric_type == metric_name,
            models.Alert.status == models.AlertStatus.ACTIVE,
            models.Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
        ).first()

        # Suppress WARNINGS if a similar active alert exists in the last hour. Always allow CRITICAL.
        if recent_alert and severity == models.AlertSeverity.WARNING:
            logger.info(f"Alert suppressed for {metric_name} (Patient {patient_id}) due to recent active alert.")
            return

        new_alert = models.Alert(
            patient_id=patient_id,
            metric_type=metric_name,
            severity=severity,
            message=message
        )
        db.add(new_alert)
        generated_alerts.append(new_alert)

def get_default_min(metric: str):
    defaults = {"heart_rate": 60, "blood_pressure_systolic": 90, "blood_pressure_diastolic": 60, "steps": 1000}
    return defaults.get(metric, 0)

def get_default_max(metric: str):
    defaults = {"heart_rate": 100, "blood_pressure_systolic": 120, "blood_pressure_diastolic": 80, "steps": 20000}
    return defaults.get(metric, 9999)

# --- Vitals & Activity CRUD ---
def get_vitals_by_date_range(db: Session, patient_id: int, start_date: datetime, end_date: datetime):
    return db.query(models.VitalSigns).filter(
        models.VitalSigns.patient_id == patient_id,
        models.VitalSigns.recorded_at >= start_date,
        models.VitalSigns.recorded_at <= end_date
    ).all()

def create_vital_sign(db: Session, vital_sign: schemas.VitalSignsCreate, patient_id: int):
    db_vital = models.VitalSigns(**vital_sign.model_dump(), patient_id=patient_id)
    db.add(db_vital)
    
    generated_alerts = []
    check_and_create_alert(db, patient_id, "heart_rate", vital_sign.heart_rate, generated_alerts)
    check_and_create_alert(db, patient_id, "blood_pressure_systolic", vital_sign.blood_pressure_systolic, generated_alerts)
    
    db.commit()
    db.refresh(db_vital)
    return db_vital, generated_alerts

def create_activity_data(db: Session, activity: schemas.ActivityDataCreate, patient_id: int):
    db_activity = models.ActivityData(**activity.model_dump(), patient_id=patient_id)
    db.add(db_activity)
    
    generated_alerts = []
    # Pattern Detection: Too few steps indicating abnormal behavior/bedridden trend
    check_and_create_alert(db, patient_id, "steps", activity.steps, generated_alerts)
    
    db.commit()
    db.refresh(db_activity)
    return db_activity, generated_alerts

# --- Alert Management CRUD ---
def get_active_alerts(db: Session, patient_id: int = None):
    query = db.query(models.Alert).filter(models.Alert.status == models.AlertStatus.ACTIVE)
    if patient_id:
        query = query.filter(models.Alert.patient_id == patient_id)
    return query.order_by(models.Alert.severity.desc(), models.Alert.created_at.desc()).all()

def acknowledge_alert(db: Session, alert_id: int, user: str):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if alert and alert.status == models.AlertStatus.ACTIVE:
        alert.status = models.AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user
        db.commit()
        db.refresh(alert)
    return alert