import os
import pandas as pd
import numpy as np
import joblib
import warnings
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')

def run_retraining():
    BASE = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.join(BASE, '..')
    DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'ambu_patient_data.csv')
    MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
    RANDOM_SEED = 42

    print("Loading data for retraining from", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    # ── Fix NaN values before processing ─────────────────────────────────────────
    df['comorbidity'] = df['comorbidity'].fillna('None')  # ✅ FIXED
    df = df.dropna(subset=['outcome', 'gender', 'condition', 'mode'])

    # ── Feature engineering ───────────────────────────────────────────────────────
    df_proc = df.copy()
    if 'patient_id' in df_proc.columns:
        df_proc.drop(columns=['patient_id'], inplace=True)

    le_gender    = LabelEncoder()
    le_condition = LabelEncoder()
    le_comorbid  = LabelEncoder()
    le_mode      = LabelEncoder()

    le_gender.fit(["Male", "Female"])
    le_condition.fit(["Cardiac Arrest", "Drug Overdose", "Post-Surgical", "Respiratory Failure", "Stroke/CNS", "Trauma"])
    le_comorbid.fit(["None", "Hypertension", "Diabetes", "COPD", "Heart Disease"])
    le_mode.fit(["Low", "Medium", "High", "Assist Control"])

    df_proc['gender']      = le_gender.transform(df_proc['gender'])
    df_proc['condition']   = le_condition.transform(df_proc['condition'])
    df_proc['comorbidity'] = le_comorbid.transform(df_proc['comorbidity'])
    df_proc['mode']        = le_mode.transform(df_proc['mode'])

    df_proc['spo2_delta']     = df_proc['spo2_30min'] - df_proc['spo2_before']
    df_proc['spo2_slope']     = df_proc['spo2_delta'] / 30
    df_proc['spo2_at_15']     = df_proc['spo2_15min']
    df_proc['age_flag']       = (df_proc['age'] > 70).astype(int)
    df_proc['gcs_flag']       = (df_proc['gcs_score'] < 8).astype(int)
    df_proc['bp_pulse_ratio'] = df_proc['bp_systolic'] / (df_proc['pulse'] + 1)

    FEATURE_COLS = [
        'bpm', 'mode', 'peep', 'lpm',
        'age', 'gender', 'condition', 'comorbidity',
        'pulse', 'bp_systolic', 'bp_diastolic', 'gcs_score', 'cvs_score',
        'spo2_before', 'spo2_5min', 'spo2_10min',
        'spo2_15min',  'spo2_20min', 'spo2_25min', 'spo2_30min',
        'spo2_delta', 'spo2_slope', 'spo2_at_15',
        'age_flag', 'gcs_flag', 'bp_pulse_ratio'
    ]

    X = df_proc[FEATURE_COLS].copy()
    y = df_proc['outcome'].copy()

    # ── Normalize numeric features ────────────────────────────────────────────────
    scaler   = MinMaxScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=FEATURE_COLS)

    # ── Handle class imbalance with SMOTE ─────────────────────────────────────────
    smote = SMOTE(random_state=RANDOM_SEED)
    X_res, y_res = smote.fit_resample(X_scaled, y)

    # ── Train Random Forest ───────────────────────────────────────────────────────
    best_model = RandomForestClassifier(
        n_estimators=100,       
        max_depth=5,            
        class_weight='balanced',
        random_state=RANDOM_SEED
    )
    best_model.fit(X_res, y_res)

    # ── Save Models ───────────────────────────────────────────────────────────────
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(best_model,   os.path.join(MODELS_DIR, 'ambu_rf_model.pkl'))
    joblib.dump(scaler,       os.path.join(MODELS_DIR, 'ambu_scaler.pkl'))
    joblib.dump({
        'gender'      : le_gender,
        'condition'   : le_condition,
        'comorbidity' : le_comorbid,
        'mode'        : le_mode
    }, os.path.join(MODELS_DIR, 'ambu_encoders.pkl'))
    joblib.dump(FEATURE_COLS, os.path.join(MODELS_DIR, 'ambu_feature_cols.pkl'))
    
    print("Retraining completed. Models saved.")

if __name__ == "__main__":
    run_retraining()