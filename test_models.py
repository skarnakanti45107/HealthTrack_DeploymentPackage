import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from database import Base
import models, schemas, crud

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_alert_generation(db):
    # 1. Create Patient
    patient = models.Patient(
        first_name="Alert", last_name="Test", 
        email="alert@test.com", date_of_birth=datetime(1980, 1, 1, tzinfo=timezone.utc)
    )
    db.add(patient)
    db.commit()

    # 2. Submit Abnormal Vitals (HR 140 is > 120, triggering CRITICAL)
    vitals_schema = schemas.VitalSignsCreate(
        heart_rate=140, blood_pressure_systolic=120, blood_pressure_diastolic=80
    )
    _, alerts = crud.create_vital_sign(db, vitals_schema, patient.id)
    
    assert len(alerts) > 0
    assert alerts[0].severity == models.AlertSeverity.CRITICAL
    assert alerts[0].metric_type == "heart_rate"

def test_alert_suppression(db):
    patient = models.Patient(
        first_name="Suppress", last_name="Test", 
        email="suppress@test.com", date_of_birth=datetime(1980, 1, 1, tzinfo=timezone.utc)
    )
    db.add(patient)
    db.commit()

    # Submit WARNING Vitals (HR 110 is > 100 but < 120)
    vitals_schema = schemas.VitalSignsCreate(
        heart_rate=110, blood_pressure_systolic=120, blood_pressure_diastolic=80
    )
    _, alerts1 = crud.create_vital_sign(db, vitals_schema, patient.id)
    assert len(alerts1) == 1 # First warning generated

    # Submit WARNING Vitals again immediately
    _, alerts2 = crud.create_vital_sign(db, vitals_schema, patient.id)
    assert len(alerts2) == 0 # Suppressed to prevent fatigue