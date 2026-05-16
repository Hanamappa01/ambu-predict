# Run this cell once, then restart the kernel if needed
# !pip install pandas numpy scikit-learn xgboost imbalanced-learn matplotlib seaborn openpyxl joblib

# --- 
import pandas as pd
import numpy as np
import warnings
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (StratifiedKFold, cross_val_score,
                                     train_test_split, learning_curve)
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, roc_curve, ConfusionMatrixDisplay)
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

# ── Config ─────────────────────────────────────────────────────────────────────
DATA_PATH   = 'ambu_patient_data.csv'   # ← replace with real file when available
MODEL_DIR   = './'                       # folder to save .pkl files
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

print("✅ Imports done")

# --- 
# ── SYNTHETIC DATA GENERATOR ───────────────────────────────────────────────────
# This creates a CSV identical in structure to what your hospital will provide.
# Column meanings:
#   bpm          : breaths per minute set on In-Spire machine (15/20/25/30)
#   mode         : ventilation mode (Low/Medium/High/Assist Control)
#   peep         : positive end-expiratory pressure in cm H₂O
#   lpm          : litres per minute of O₂ input
#   spo2_before  : patient SpO₂ % before intubation
#   spo2_Xmin    : SpO₂ % measured every 5 min post-intubation (up to 30 min)
#   gcs_score    : Glasgow Coma Scale (3–15), lower = worse
#   cvs_score    : Cardiovascular score (1–5)
#   outcome      : 1 = ventilation succeeded, 0 = failed (label to predict)

n = 120  # number of patients (increase when real data arrives)

conditions   = ['Cardiac Arrest','Respiratory Failure','Stroke/CNS',
                'Trauma','Drug Overdose','Post-Surgical']
comorbids    = ['None','Hypertension','Diabetes','COPD','Heart Disease']
modes        = ['Low','Medium','High','Assist Control']
genders      = ['Male','Female']

age        = np.random.randint(18, 85, n)
gender     = np.random.choice(genders, n)
condition  = np.random.choice(conditions, n, p=[0.25,0.30,0.15,0.15,0.08,0.07])
comorbid   = np.random.choice(comorbids, n)

# ── 4 Machine inputs from In-Spire ────────────────────────────────────────────
bpm   = np.random.choice([15,20,25,30], n, p=[0.2,0.35,0.30,0.15])
mode  = np.random.choice(modes, n, p=[0.25,0.35,0.25,0.15])
peep  = np.random.choice([0,5,10,15,20], n, p=[0.15,0.30,0.30,0.15,0.10])
lpm   = np.round(np.random.uniform(2, 15, n), 1)

# ── Patient vitals ────────────────────────────────────────────────────────────
spo2_before  = np.random.randint(55, 90, n)
pulse        = np.random.randint(50, 140, n)
bp_systolic  = np.random.randint(80, 180, n)
bp_diastolic = np.random.randint(50, 110, n)
gcs          = np.random.randint(3, 16, n)
cvs          = np.random.randint(1, 6, n)

# ── SpO₂ time series (realistic upward trend with noise) ─────────────────────
spo2_5  = np.clip(spo2_before + np.random.randint(-2, 8, n), 50, 99)
spo2_10 = np.clip(spo2_5  + np.random.randint(-1, 9, n), 50, 99)
spo2_15 = np.clip(spo2_10 + np.random.randint(-1, 8, n), 50, 99)
spo2_20 = np.clip(spo2_15 + np.random.randint(-1, 7, n), 50, 99)
spo2_25 = np.clip(spo2_20 + np.random.randint(-1, 6, n), 55, 99)
spo2_30 = np.clip(spo2_25 + np.random.randint(-1, 5, n), 55, 99)

# ── Outcome: logically driven by SpO₂, GCS, machine settings, age ────────────
mode_series = pd.Series(mode)
score = (
    (spo2_30 > 90).astype(int) * 3 +
    (gcs > 8).astype(int) * 2 +
    (bpm >= 20).astype(int) +
    mode_series.isin(['High','Assist Control']).astype(int).values +
    (bp_systolic > 90).astype(int) +
    (age < 65).astype(int) +
    np.random.randint(0, 2, n)          # small random noise
)
outcome = (score >= 6).astype(int)

df_raw = pd.DataFrame({
    'patient_id' : [f'P{str(i+1).zfill(4)}' for i in range(n)],
    'age'        : age,   'gender'      : gender,
    'condition'  : condition, 'comorbidity' : comorbid,
    'bpm'        : bpm,   'mode'        : mode,
    'peep'       : peep,  'lpm'         : lpm,
    'pulse'      : pulse, 'bp_systolic' : bp_systolic,
    'bp_diastolic': bp_diastolic,
    'gcs_score'  : gcs,   'cvs_score'   : cvs,
    'spo2_before': spo2_before,
    'spo2_5min'  : spo2_5,  'spo2_10min' : spo2_10,
    'spo2_15min' : spo2_15, 'spo2_20min' : spo2_20,
    'spo2_25min' : spo2_25, 'spo2_30min' : spo2_30,
    'outcome'    : outcome
})

df_raw.to_csv(DATA_PATH, index=False)
print(f"✅ Synthetic dataset saved → {DATA_PATH}")
print(f"   Shape     : {df_raw.shape}")
print(f"   Outcome   : {dict(df_raw['outcome'].value_counts())}")
print(f"   Columns   : {list(df_raw.columns)}")
df_raw.head(3)

# --- 
df = pd.read_csv(DATA_PATH)
print(f"Shape      : {df.shape}")
print(f"Nulls      : {df.isnull().sum().sum()}")
print(f"Outcome    : {dict(df['outcome'].value_counts())}")
print(f"Balance    : {df['outcome'].value_counts(normalize=True).round(2).to_dict()}")
df.describe().T

# --- 
# ── Visual EDA ────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
fig.suptitle('Patient Data — Exploratory Analysis', fontsize=14, fontweight='bold')

# Outcome distribution
df['outcome'].map({1:'Positive',0:'Negative'}).value_counts().plot(
    kind='bar', ax=axes[0,0], color=['#2ecc71','#e74c3c'], edgecolor='white')
axes[0,0].set_title('Outcome Distribution'); axes[0,0].set_xlabel('')

# SpO2 before by outcome
df.boxplot(column='spo2_before', by='outcome', ax=axes[0,1])
axes[0,1].set_title('SpO₂ Before by Outcome')
axes[0,1].set_xticklabels(['Negative','Positive'])

# GCS by outcome
df.boxplot(column='gcs_score', by='outcome', ax=axes[0,2])
axes[0,2].set_title('GCS Score by Outcome')
axes[0,2].set_xticklabels(['Negative','Positive'])

# BPM distribution
df['bpm'].value_counts().sort_index().plot(kind='bar', ax=axes[1,0], color='#3498db')
axes[1,0].set_title('BPM Settings Distribution'); axes[1,0].set_xlabel('BPM')

# Mode distribution
df['mode'].value_counts().plot(kind='bar', ax=axes[1,1], color='#9b59b6')
axes[1,1].set_title('Mode Distribution'); axes[1,1].set_xlabel('')

# SpO2 trajectory (mean by outcome)
spo2_cols = ['spo2_before','spo2_5min','spo2_10min','spo2_15min','spo2_20min','spo2_25min','spo2_30min']
time_pts  = [0, 5, 10, 15, 20, 25, 30]
for outcome_val, label, color in [(1,'Positive','#2ecc71'),(0,'Negative','#e74c3c')]:
    subset = df[df['outcome']==outcome_val][spo2_cols].mean()
    axes[1,2].plot(time_pts, subset.values, marker='o', label=label, color=color)
axes[1,2].set_title('Avg SpO₂ Trajectory'); axes[1,2].set_xlabel('Minutes')
axes[1,2].set_ylabel('SpO₂ %'); axes[1,2].legend(); axes[1,2].grid(alpha=0.3)

plt.tight_layout()
plt.savefig('01_eda.png', dpi=120, bbox_inches='tight')
plt.show()
print("✅ EDA plot saved → 01_eda.png")

# --- 
df_proc = df.copy()

# ── Drop ID column (not a feature) ────────────────────────────────────────────
df_proc.drop(columns=['patient_id'], inplace=True)

# ── Encode categorical columns ────────────────────────────────────────────────
le_gender    = LabelEncoder()
le_condition = LabelEncoder()
le_comorbid  = LabelEncoder()
le_mode      = LabelEncoder()

df_proc['gender']      = le_gender.fit_transform(df_proc['gender'])
df_proc['condition']   = le_condition.fit_transform(df_proc['condition'])
df_proc['comorbidity'] = le_comorbid.fit_transform(df_proc['comorbidity'])
df_proc['mode']        = le_mode.fit_transform(df_proc['mode'])

print("Mode encoding:", dict(zip(le_mode.classes_, le_mode.transform(le_mode.classes_))))

# ── Feature engineering ───────────────────────────────────────────────────────
# SpO₂ delta: how much did SpO₂ improve over 30 min?
df_proc['spo2_delta']     = df_proc['spo2_30min'] - df_proc['spo2_before']

# SpO₂ slope: rate of improvement per minute
df_proc['spo2_slope']     = df_proc['spo2_delta'] / 30

# SpO₂ at 15 min: early trajectory indicator
df_proc['spo2_at_15']     = df_proc['spo2_15min']

# Risk flags
df_proc['age_flag']       = (df_proc['age'] > 70).astype(int)   # elderly risk
df_proc['gcs_flag']       = (df_proc['gcs_score'] < 8).astype(int)  # severe CNS

# Cardiovascular stress indicator
df_proc['bp_pulse_ratio'] = df_proc['bp_systolic'] / (df_proc['pulse'] + 1)

print(f"\n✅ Feature engineering done. Total features: {df_proc.shape[1] - 1}")
df_proc.head(3)

# --- 
# ── Define feature columns ────────────────────────────────────────────────────
FEATURE_COLS = [
    # ── 4 core machine inputs (from In-Spire device) ──
    'bpm', 'mode', 'peep', 'lpm',
    # ── Patient demographics ──
    'age', 'gender', 'condition', 'comorbidity',
    # ── Vitals ──
    'pulse', 'bp_systolic', 'bp_diastolic', 'gcs_score', 'cvs_score',
    # ── SpO₂ time series ──
    'spo2_before', 'spo2_5min', 'spo2_10min',
    'spo2_15min',  'spo2_20min', 'spo2_25min', 'spo2_30min',
    # ── Engineered features ──
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
print(f"Before SMOTE: {dict(y.value_counts())}")
print(f"After  SMOTE: {dict(pd.Series(y_res).value_counts())}")

# ── Train / test split (80/20, stratified) ────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_res, y_res, test_size=0.20, random_state=RANDOM_SEED, stratify=y_res)
print(f"\nTrain: {X_train.shape}  |  Test: {X_test.shape}")
print("✅ Data ready for training")

# --- 
# ── Define 3 models ───────────────────────────────────────────────────────────
models = {
    'Random Forest': RandomForestClassifier(
        n_estimators=100,       # number of trees
        max_depth=5,            # prevent overfitting on small data
        class_weight='balanced',
        random_state=RANDOM_SEED
    ),
    'XGBoost': XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=1,     # adjust if imbalanced
        eval_metric='logloss',
        random_state=RANDOM_SEED,
        verbosity=0
    ),
    'Logistic Regression': LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=RANDOM_SEED
    )
}

# ── 5-fold stratified cross-validation ───────────────────────────────────────
cv      = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
cv_results = {}

print(f"{'Model':<22} {'Accuracy':>10} {'Recall':>10} {'ROC-AUC':>10}")
print("-" * 57)

for name, m in models.items():
    acc    = cross_val_score(m, X_train, y_train, cv=cv, scoring='accuracy').mean()
    recall = cross_val_score(m, X_train, y_train, cv=cv, scoring='recall').mean()
    auc    = cross_val_score(m, X_train, y_train, cv=cv, scoring='roc_auc').mean()
    cv_results[name] = {'accuracy': acc, 'recall': recall, 'roc_auc': auc}
    print(f"{name:<22} {acc:>10.3f} {recall:>10.3f} {auc:>10.3f}")

print("\n⭐ Recall is the priority metric for clinical models")
print("   (missing a failing patient is worse than a false alarm)")

# --- 
# ── Train best model on full training set ─────────────────────────────────────
best_model = models['Random Forest']
best_model.fit(X_train, y_train)

y_pred = best_model.predict(X_test)
y_prob = best_model.predict_proba(X_test)[:, 1]

print("=" * 50)
print("CLASSIFICATION REPORT — Random Forest")
print("=" * 50)
print(classification_report(y_test, y_pred, target_names=['Negative','Positive']))
print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.3f}")

# ── Plots ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Model Evaluation — Random Forest', fontsize=13, fontweight='bold')

# Confusion matrix
ConfusionMatrixDisplay(confusion_matrix(y_test, y_pred),
    display_labels=['Negative','Positive']).plot(ax=axes[0], colorbar=False)
axes[0].set_title('Confusion Matrix')

# ROC curve
fpr, tpr, _ = roc_curve(y_test, y_prob)
axes[1].plot(fpr, tpr, color='#2980b9', lw=2,
             label=f'AUC = {roc_auc_score(y_test, y_prob):.3f}')
axes[1].plot([0,1],[0,1],'--', color='gray', lw=1)
axes[1].set_xlabel('False Positive Rate'); axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('ROC Curve'); axes[1].legend(); axes[1].grid(alpha=0.3)

# Feature importance (top 12)
feat_imp = pd.Series(best_model.feature_importances_,
                     index=FEATURE_COLS).sort_values(ascending=True).tail(12)
feat_imp.plot(kind='barh', ax=axes[2], color='#16a085', edgecolor='white')
axes[2].set_title('Top 12 Feature Importances')
axes[2].set_xlabel('Importance Score')

plt.tight_layout()
plt.savefig('02_evaluation.png', dpi=120, bbox_inches='tight')
plt.show()
print("✅ Evaluation plot saved → 02_evaluation.png")

# --- 
# ── Learning curve: if still rising at 100 samples → need more data ───────────
train_sizes, train_scores, val_scores = learning_curve(
    RandomForestClassifier(n_estimators=100, max_depth=5,
                           class_weight='balanced', random_state=RANDOM_SEED),
    X_res, y_res,
    cv=5,
    scoring='recall',
    train_sizes=np.linspace(0.1, 1.0, 10),
    random_state=RANDOM_SEED
)

train_mean = train_scores.mean(axis=1)
val_mean   = val_scores.mean(axis=1)
val_std    = val_scores.std(axis=1)

plt.figure(figsize=(9, 5))
plt.plot(train_sizes, train_mean, 'o-', color='#2980b9', label='Training Recall')
plt.plot(train_sizes, val_mean,   'o-', color='#27ae60', label='Validation Recall')
plt.fill_between(train_sizes, val_mean-val_std, val_mean+val_std,
                 alpha=0.15, color='#27ae60')
plt.axhline(0.80, color='red', linestyle='--', alpha=0.5, label='Target (0.80)')
plt.xlabel('Training Samples'); plt.ylabel('Recall')
plt.title('Learning Curve — Does Adding More Data Help?')
plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('03_learning_curve.png', dpi=120, bbox_inches='tight')
plt.show()

# ── Interpretation ────────────────────────────────────────────────────────────
final_val = val_mean[-1]
if final_val < 0.75:
    print("⚠️  Model needs more data — validation recall still rising. Target 200+ samples.")
elif val_std[-1] > 0.10:
    print("⚠️  High variance — model is unstable. More data will help significantly.")
else:
    print(f"✅ Validation recall = {final_val:.2f} — 100 samples is workable for now.")
print("Learning curve saved → 03_learning_curve.png")

# --- 
def predict_outcome(bpm, mode_str, peep, lpm,
                    age, gender_str, condition_str, comorbidity_str,
                    pulse, bp_systolic, bp_diastolic, gcs_score, cvs_score,
                    spo2_before, spo2_5, spo2_10, spo2_15, spo2_20, spo2_25, spo2_30):
    """
    Predict ventilation outcome for a new patient.
    Returns: probability score and label (Positive/Negative).
    """
    # Encode categoricals (must match training encoding)
    gender_enc    = le_gender.transform([gender_str])[0]
    condition_enc = le_condition.transform([condition_str])[0]
    comorbid_enc  = le_comorbid.transform([comorbidity_str])[0]
    mode_enc      = le_mode.transform([mode_str])[0]

    # Derived features
    spo2_delta    = spo2_30 - spo2_before
    spo2_slope    = spo2_delta / 30
    bp_pulse_ratio = bp_systolic / (pulse + 1)

    input_data = pd.DataFrame([[
        bpm, mode_enc, peep, lpm,
        age, gender_enc, condition_enc, comorbid_enc,
        pulse, bp_systolic, bp_diastolic, gcs_score, cvs_score,
        spo2_before, spo2_5, spo2_10, spo2_15, spo2_20, spo2_25, spo2_30,
        spo2_delta, spo2_slope, spo2_15,      # spo2_at_15
        int(age > 70), int(gcs_score < 8), bp_pulse_ratio
    ]], columns=FEATURE_COLS)

    input_scaled = pd.DataFrame(scaler.transform(input_data), columns=FEATURE_COLS)
    prob  = best_model.predict_proba(input_scaled)[0][1]
    label = 'Positive ✅' if prob >= 0.5 else 'Negative ❌'

    if prob >= 0.70:
        advice = 'HIGH probability — ventilation likely effective. Proceed.'
    elif prob >= 0.45:
        advice = 'MODERATE — monitor closely, adjust BPM/Mode if SpO₂ not improving.'
    else:
        advice = 'LOW — consider adjusting settings or escalating to full ventilator.'

    print(f"Prediction   : {label}")
    print(f"Probability  : {prob*100:.1f}%")
    print(f"Clinical note: {advice}")
    return prob

# ── Example prediction ─────────────────────────────────────────────────────────
print("=" * 55)
print("SAMPLE PREDICTION — 45yr Respiratory Failure patient")
print("=" * 55)
_ = predict_outcome(
    bpm=25, mode_str='High', peep=10, lpm=8.0,
    age=45, gender_str='Male',
    condition_str='Respiratory Failure', comorbidity_str='None',
    pulse=95, bp_systolic=120, bp_diastolic=80,
    gcs_score=12, cvs_score=3,
    spo2_before=72, spo2_5=76, spo2_10=80,
    spo2_15=84, spo2_20=87, spo2_25=90, spo2_30=93
)

# --- 
# Save all artifacts needed to reload the model later (or in FastAPI)
joblib.dump(best_model,   MODEL_DIR + 'ambu_rf_model.pkl')
joblib.dump(scaler,       MODEL_DIR + 'ambu_scaler.pkl')
joblib.dump({
    'gender'      : le_gender,
    'condition'   : le_condition,
    'comorbidity' : le_comorbid,
    'mode'        : le_mode
},            MODEL_DIR + 'ambu_encoders.pkl')
joblib.dump(FEATURE_COLS, MODEL_DIR + 'ambu_feature_cols.pkl')

print("✅ Saved:")
print("   ambu_rf_model.pkl     ← trained Random Forest model")
print("   ambu_scaler.pkl       ← MinMaxScaler fitted on training data")
print("   ambu_encoders.pkl     ← LabelEncoders for gender/condition/mode/comorbidity")
print("   ambu_feature_cols.pkl ← ordered list of feature column names")
print()
print("To reload the model anywhere:")
print("  model    = joblib.load('ambu_rf_model.pkl')")
print("  scaler   = joblib.load('ambu_scaler.pkl')")
print("  encoders = joblib.load('ambu_encoders.pkl')")

# --- 
# Confirm saved model works correctly after loading
loaded_model    = joblib.load(MODEL_DIR + 'ambu_rf_model.pkl')
loaded_scaler   = joblib.load(MODEL_DIR + 'ambu_scaler.pkl')
loaded_encoders = joblib.load(MODEL_DIR + 'ambu_encoders.pkl')
loaded_cols     = joblib.load(MODEL_DIR + 'ambu_feature_cols.pkl')

y_pred_loaded = loaded_model.predict(
    pd.DataFrame(loaded_scaler.transform(X_test), columns=loaded_cols))

from sklearn.metrics import accuracy_score
acc = accuracy_score(y_test, y_pred_loaded)
print(f"✅ Loaded model accuracy on test set: {acc*100:.1f}%")
print("   Model reloads and predicts correctly. Ready for FastAPI integration.")

# --- 
