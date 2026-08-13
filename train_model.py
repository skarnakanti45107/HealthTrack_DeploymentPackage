import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

print("Loading historical patient data...")
# Load the dataset we just generated
df = pd.read_csv('synthetic_patient_risk_data.csv')

# 1. Define Features (X) and Target (y)
# We drop patient_id because it has no medical predictive value
X = df[['age', 'steps_per_day', 'active_minutes', 'heart_rate', 'sys_bp', 'dia_bp', 'blood_glucose']]
y = df['risk_level']

# 2. Split the data into Training and Testing sets (80% train, 20% test)
# This directly satisfies the "testing approach" requirement for your documentation
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 3. Initialize and Train the Pattern Recognition Model
print("Training the Random Forest Risk Assessment Model...")
rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
rf_model.fit(X_train, y_train)

# 4. Evaluate Model Accuracy (Crucial for your 30% Evaluation Criteria)
predictions = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print("\n" + "="*50)
print(f" MODEL TRAINING COMPLETE")
print(f" OVERALL ACCURACY: {accuracy * 100:.2f}%")
print("="*50)

print("\n--- Detailed Classification Report ---")
# This shows how well it identifies each specific risk level
print(classification_report(y_test, predictions))

# 5. Risk Factor Identification (Extracting Feature Importance)
print("\n--- Risk Factor Influence (Feature Importance) ---")
feature_importances = pd.DataFrame({
    'Metric': X.columns,
    'Influence_Score': rf_model.feature_importances_
}).sort_values(by='Influence_Score', ascending=False)

print(feature_importances.to_string(index=False))

# 6. Save the trained model to disk for API integration
model_filename = 'health_risk_model.pkl'
joblib.dump(rf_model, model_filename)
print(f"\n Predictive model successfully saved as '{model_filename}'")