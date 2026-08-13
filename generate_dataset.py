print("Script is starting...")
import pandas as pd
import numpy as np
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

NUM_RECORDS = 5000

# 1. Generate Base Demographics & Lifestyle
data = {
    'patient_id': range(1, NUM_RECORDS + 1),
    'age': np.random.randint(18, 90, NUM_RECORDS),
    'steps_per_day': np.random.normal(5000, 2500, NUM_RECORDS).clip(0, 15000).astype(int),
    'active_minutes': np.random.normal(30, 20, NUM_RECORDS).clip(0, 120).astype(int)
}
df = pd.DataFrame(data)

# 2. Generate Vitals with Physiological Correlations
# Older age and lower activity slightly increase baseline vitals
age_factor = (df['age'] - 30) * 0.15
activity_factor = (5000 - df['steps_per_day']) * 0.002

df['heart_rate'] = np.random.normal(75, 12, NUM_RECORDS) + age_factor + activity_factor
df['heart_rate'] = df['heart_rate'].clip(40, 200).astype(int)

df['sys_bp'] = np.random.normal(120, 15, NUM_RECORDS) + (age_factor * 2) + activity_factor
df['sys_bp'] = df['sys_bp'].clip(80, 220).astype(int)

df['dia_bp'] = np.random.normal(80, 10, NUM_RECORDS) + age_factor + activity_factor
df['dia_bp'] = df['dia_bp'].clip(50, 130).astype(int)

df['blood_glucose'] = np.random.normal(100, 20, NUM_RECORDS) + (age_factor * 1.5)
df['blood_glucose'] = df['blood_glucose'].clip(70, 300).round(1)

# 3. Define the Expert System Rules to Label the Data (Target Variable)
def calculate_risk_label(row):
    risk_score = 0
    
    # Age factor
    if row['age'] > 65: risk_score += 1
    
    # Vitals thresholds
    if row['heart_rate'] > 100 or row['heart_rate'] < 50: risk_score += 2
    if row['heart_rate'] > 120 or row['heart_rate'] < 40: risk_score += 3
    
    if row['sys_bp'] > 140 or row['dia_bp'] > 90: risk_score += 2
    if row['sys_bp'] > 180 or row['dia_bp'] > 120: risk_score += 3
    
    if row['blood_glucose'] > 140: risk_score += 2
    if row['blood_glucose'] > 200: risk_score += 3
    
    # Lifestyle factor
    if row['steps_per_day'] < 2000: risk_score += 1
    
    # Categorize based on accumulated points
    if risk_score >= 6:
        return 'Critical'
    elif risk_score >= 4:
        return 'High'
    elif risk_score >= 2:
        return 'Moderate'
    else:
        return 'Low'

# Apply the labeling function
df['risk_level'] = df.apply(calculate_risk_label, axis=1)

# 4. Save to CSV
df.to_csv('synthetic_patient_risk_data.csv', index=False)
print(f" Successfully generated dataset with {NUM_RECORDS} records.")
print("\nClass Distribution:")
print(df['risk_level'].value_counts())