import requests

# API configuration
API_URL = "http://127.0.0.1:8000/patients/"
HEADERS = {
    "Authorization": "Bearer fake-super-secret-token",
    "Content-Type": "application/json"
}

# A list of new mock patients to add to your database
patients_to_add = [
    {
        "first_name": "Amit",
        "last_name": "Patel",
        "email": "amit.patel@patient.com",
        "date_of_birth": "1982-11-05T00:00:00Z"
    },
    {
        "first_name": "Sneha",
        "last_name": "Desai",
        "email": "sneha.d@patient.com",
        "date_of_birth": "1975-08-21T00:00:00Z"
    },
    {
        "first_name": "Vikram",
        "last_name": "Singh",
        "email": "vikram.s@patient.com",
        "date_of_birth": "1990-03-14T00:00:00Z"
    },
    {
        "first_name": "Anjali",
        "last_name": "Gupta",
        "email": "anjali.g@patient.com",
        "date_of_birth": "1965-12-30T00:00:00Z"
    }
]

print("Starting patient registration process...\n")

# Loop through the list and send a POST request for each patient
for patient in patients_to_add:
    response = requests.post(API_URL, json=patient, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Successfully added: {data['first_name']} {data['last_name']} (Patient ID: {data['id']})")
    else:
        print(f"❌ Failed to add {patient['first_name']}. Error: {response.status_code} - {response.text}")

print("\nDatabase seeding complete!")