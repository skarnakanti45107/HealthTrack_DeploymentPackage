from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List
from models import AlertSeverity, AlertStatus

# --- Vital Signs ---
class VitalSignsCreate(BaseModel):
    heart_rate: int = Field(..., gt=0, lt=300)
    blood_pressure_systolic: int = Field(..., gt=50, lt=250)
    blood_pressure_diastolic: int = Field(..., gt=30, lt=150)
    blood_glucose: Optional[float] = None

class VitalSignsResponse(VitalSignsCreate):
    id: int
    patient_id: int
    recorded_at: datetime
    class Config:
        from_attributes = True

# --- Activity Data ---
class ActivityDataCreate(BaseModel):
    steps: int = Field(..., ge=0)
    active_minutes: int = Field(..., ge=0)

class ActivityDataResponse(ActivityDataCreate):
    id: int
    patient_id: int
    recorded_date: datetime
    class Config:
        from_attributes = True

# --- Patient Thresholds ---
class PatientThresholdCreate(BaseModel):
    metric_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class PatientThresholdResponse(PatientThresholdCreate):
    id: int
    patient_id: int
    class Config:
        from_attributes = True

# --- Alerts ---
class AlertResponse(BaseModel):
    id: int
    patient_id: int
    metric_type: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Patient ---
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    date_of_birth: datetime

class PatientResponse(PatientCreate):
    id: int
    class Config:
        from_attributes = True

# --- Risk Assessment ---
class RiskAssessmentResponse(BaseModel):
    patient_id: int
    risk_level: str
    contributing_factors: List[str]
    system_recommendations: List[str]
    assessment_timestamp: datetime
    
    class Config:
        from_attributes = True