import numpy as np
import pandas as pd
from pathlib import Path

def generate_synthetic_dataset(n_samples=1800, seed=42):
    """
    Generates synthetic historical campus infrastructure maintenance data
    for training the Scikit-learn predictive maintenance model.
    
    How it works:
    1. Sets random seed for reproducible dataset generation.
    2. Simulates 8 physical and historical telemetry features based on engineering degradation physics:
       - `age_years`: Uniform distribution between 0.5 and 12 years.
       - `previous_failures`: Poisson distribution modeling component failure rate.
       - `health_score`: Degradation model where age and previous breakdowns decrease health,
         augmented with Gaussian sensor noise and bounded between 15 and 100.
       - `inspection_frequency`: Categorical frequency (1 to 12 inspections per year).
       - `complaint_count`: Poisson distribution scaled inversely with asset health score.
       - `previous_maintenance_count`: Historical servicing frequency scaled by age.
       - `condition_code`: Discrete condition tier (0: Good, 1: Moderate, 2: Poor, 3: Critical).
       - `days_since_last_maintenance`: Days elapsed since previous overhaul (5 to 360 days).
    3. Calculates a continuous Composite Risk Metric weighting low health, breakdown history,
       neglected maintenance intervals, and user complaints.
    4. Categorizes target labels:
       - 'High Risk': Critical health or elevated risk metric -> Predicted failure in 1 to 14 days.
       - 'Medium Risk': Moderate wear -> Maintenance recommended in 15 to 45 days.
       - 'Low Risk': High health and recent service -> Healthy operation for 46 to 120 days.
    5. Saves the resulting DataFrame to `ml/training_data.csv`.
    
    Args:
        n_samples (int): Number of historical telemetry records to simulate (default: 1800).
        seed (int): Random seed for reproducibility.
        
    Returns:
        pd.DataFrame: The generated training dataset.
    """
    np.random.seed(seed)
    
    # Feature distributions
    # 1. Asset Age (years): 0.5 to 12 years
    age_years = np.round(np.random.uniform(0.5, 12.0, n_samples), 1)
    
    # 2. Previous Failures (count): 0 to 10 historical breakdowns
    previous_failures = np.random.poisson(lam=1.5, size=n_samples)
    previous_failures = np.clip(previous_failures, 0, 10)
    
    # 3. Current Health Score (0 - 100)
    # Physical degradation: older assets with multiple breakdowns have lower baseline health
    base_health = 100 - (age_years * 4.5) - (previous_failures * 5)
    noise = np.random.normal(0, 8, n_samples)
    health_score = np.round(np.clip(base_health + noise, 15, 100)).astype(int)
    
    # 4. Inspection Frequency (per year): 1 to 12 cycles
    inspection_frequency = np.random.choice([1, 2, 4, 6, 12], size=n_samples, p=[0.1, 0.3, 0.4, 0.15, 0.05])
    
    # 5. Number of Complaints: 0 to 15 reported campus complaints
    complaint_count = np.random.poisson(lam=np.maximum(0.2, (100 - health_score) / 18), size=n_samples)
    complaint_count = np.clip(complaint_count, 0, 15)
    
    # 6. Previous Maintenance Count: Historical servicing count
    previous_maintenance_count = np.random.poisson(lam=np.maximum(0.5, age_years * 0.7), size=n_samples)
    previous_maintenance_count = np.clip(previous_maintenance_count, 0, 12)
    
    # 7. Condition Code: 0: Good, 1: Moderate, 2: Poor, 3: Critical
    condition_codes = []
    for h in health_score:
        if h >= 80:
            condition_codes.append(0)  # Good
        elif h >= 60:
            condition_codes.append(1)  # Moderate
        elif h >= 40:
            condition_codes.append(2)  # Poor
        else:
            condition_codes.append(3)  # Critical
    condition_code = np.array(condition_codes)
    
    # 8. Days since last maintenance: 5 to 360 days elapsed
    days_since_last_maintenance = np.round(np.random.uniform(5, 360, n_samples)).astype(int)
    
    # Compute synthetic Composite Risk Score (continuous)
    # Higher score = higher probability of failure
    risk_metric = (
        (100 - health_score) * 0.45 +
        (previous_failures * 5.0) +
        (complaint_count * 4.0) +
        (condition_code * 8.0) +
        (days_since_last_maintenance / 30.0 * 2.5) +
        (age_years * 1.5) -
        (inspection_frequency * 1.0)
    )
    
    # Map to 3 risk classes: Low Risk (0), Medium Risk (1), High Risk (2)
    risk_labels = []
    days_to_failure = []
    
    p33 = np.percentile(risk_metric, 50)
    p75 = np.percentile(risk_metric, 78)
    
    for rm, hs in zip(risk_metric, health_score):
        if hs < 45 or rm >= p75:
            risk_labels.append('High Risk')
            # Critical asset: failure imminent within 1 to 14 days
            days_to_failure.append(int(np.clip(np.random.normal(7, 3), 1, 14)))
        elif hs < 70 or rm >= p33:
            risk_labels.append('Medium Risk')
            # Wear developing: failure estimated within 15 to 45 days
            days_to_failure.append(int(np.clip(np.random.normal(25, 7), 15, 45)))
        else:
            risk_labels.append('Low Risk')
            # Healthy asset: maintenance due in 46 to 120 days
            days_to_failure.append(int(np.clip(np.random.normal(75, 15), 46, 120)))
            
    df = pd.DataFrame({
        'age_years': age_years,
        'previous_failures': previous_failures,
        'health_score': health_score,
        'inspection_frequency': inspection_frequency,
        'complaint_count': complaint_count,
        'previous_maintenance_count': previous_maintenance_count,
        'condition_code': condition_code,
        'days_since_last_maintenance': days_since_last_maintenance,
        'risk_level': risk_labels,
        'days_to_failure': days_to_failure
    })
    
    output_path = Path(__file__).parent / 'training_data.csv'
    df.to_csv(output_path, index=False)
    print(f"[+] Synthetic dataset generated with {len(df)} samples saved to {output_path}")
    print(df['risk_level'].value_counts())
    return df

if __name__ == '__main__':
    generate_synthetic_dataset()
