from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, CheckConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from database import Base

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    
    vital_signs = relationship("VitalSigns", back_populates="patient", cascade="all, delete-orphan")
    activity_data = relationship("ActivityData", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    thresholds = relationship("PatientThreshold", back_populates="patient", cascade="all, delete-orphan")

class PatientThreshold(Base):
    __tablename__ = "patient_thresholds"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    metric_name = Column(String(50), nullable=False) # e.g., 'heart_rate', 'blood_pressure_systolic'
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    
    patient = relationship("Patient", back_populates="thresholds")

class VitalSigns(Base):
    __tablename__ = "vital_signs"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    heart_rate = Column(Integer, nullable=False)
    blood_pressure_systolic = Column(Integer, nullable=False)
    blood_pressure_diastolic = Column(Integer, nullable=False)
    blood_glucose = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 

    __table_args__ = (
        CheckConstraint('heart_rate > 0 AND heart_rate < 300', name='check_hr_range'),
        CheckConstraint('blood_pressure_systolic > 50 AND blood_pressure_systolic < 250', name='check_bps_range'),
        CheckConstraint('blood_pressure_diastolic > 30 AND blood_pressure_diastolic < 150', name='check_bpd_range'),
    )
    patient = relationship("Patient", back_populates="vital_signs")

class ActivityData(Base):
    __tablename__ = "activity_data"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    steps = Column(Integer, nullable=False)
    active_minutes = Column(Integer, nullable=False)
    recorded_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('steps >= 0', name='check_steps_positive'),
        CheckConstraint('active_minutes >= 0', name='check_active_mins_positive'),
    )
    patient = relationship("Patient", back_populates="activity_data")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    metric_type = Column(String(50), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    message = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="alerts")