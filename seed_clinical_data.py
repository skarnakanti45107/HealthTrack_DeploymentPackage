import requests
import random
import time

# API configuration
API_URL = "http://127.0.0.1:8000"
HEADERS = {
    "Authorization": "Bearer fake-super-secret-token",
    "Content-Type": "application/json"
}

print("Fetching all registered patients from the database...")
# Get the list of all patients
response = requests.get(f"{API_URL}/patients/", headers=HEADERS)

if response.status_code == 200:
    patients = response.json()
    print(f"Found {len(patients)} patients. Generating clinical data...\n")
    
    for patient in patients:
        patient_id = patient['id']
        
        # 1. Generate realistic randomized vitals
        vitals_payload = {
            "heart_rate": random.randint(55, 125),
            "blood_pressure_systolic": random.randint(100, 160),
            "blood_pressure_diastolic": random.randint(65, 95),
            "blood_glucose": round(random.uniform(85.0, 180.0), 1)
        }
        
        # 2. Generate realistic randomized activity data
        activity_payload = {
            "steps": random.randint(1500, 12000),
            "active_minutes": random.randint(10, 90)
        }
        
        # 3. Send the POST requests to your API
        res_vitals = requests.post(f"{API_URL}/patients/{patient_id}/vitals/", json=vitals_payload, headers=HEADERS)
        res_activity = requests.post(f"{API_URL}/patients/{patient_id}/activity/", json=activity_payload, headers=HEADERS)
        
        if res_vitals.status_code == 200 and res_activity.status_code == 200:
            print(f" Successfully seeded data for {patient['first_name']} {patient['last_name']} (ID: {patient_id})")
        else:
            print(f" Failed to seed data for Patient ID: {patient_id}")
            
        # Add a tiny delay so we don't overwhelm the local server
        time.sleep(0.2)
        
    print("\n All patient clinical data seeded successfully! You can now run Risk Reports for anyone.")
else:
    print(f" Failed to fetch patients. Ensure your server is running. Status: {response.status_code}")