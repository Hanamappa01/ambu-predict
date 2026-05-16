# AmbuPredict API

FastAPI backend for NeuO In-Spire ventilation outcome prediction.

## Project Structure

```
ambu_project/
│
├── ambu_api/               ← FastAPI backend (this folder)
│   ├── main.py             ← API routes & prediction logic
│   ├── requirements.txt    ← Python dependencies
│   └── README.md
│
├── ambu_rf_model.pkl       ← Trained Random Forest model
├── ambu_scaler.pkl         ← MinMaxScaler
├── ambu_encoders.pkl       ← LabelEncoders (mode/gender/condition/comorbidity)
├── ambu_feature_cols.pkl   ← Ordered feature column list
│
└── AmbuPredict_ML_Pipeline.ipynb   ← Training notebook
```

## Setup & Run

```bash
# 1. Install dependencies
pip install -r ambu_api/requirements.txt

# 2. Start the server (from project root — where .pkl files live)
uvicorn ambu_api.main:app --reload --port 8000

# 3. Open interactive API docs
http://localhost:8000/docs
```

## API Endpoints

| Method | Route            | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/`              | Health check                       |
| GET    | `/meta`          | Valid dropdown values for frontend |
| POST   | `/predict`       | Predict single patient outcome     |
| POST   | `/batch-predict` | Predict up to 50 patients at once  |

## Example Request — /predict

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "bpm": 25,
    "mode": "High",
    "peep": 10,
    "lpm": 8.0,
    "age": 45,
    "gender": "Male",
    "condition": "Respiratory Failure",
    "comorbidity": "None",
    "pulse": 95,
    "bp_systolic": 120,
    "bp_diastolic": 80,
    "gcs_score": 12,
    "cvs_score": 3,
    "spo2_before": 72,
    "spo2_5min": 76,
    "spo2_10min": 80,
    "spo2_15min": 84,
    "spo2_20min": 87,
    "spo2_25min": 90,
    "spo2_30min": 93
  }'
```

## Example Response

```json
{
  "probability": 0.87,
  "probability_pct": 87.0,
  "outcome": "Positive",
  "risk_level": "HIGH",
  "clinical_advice": "High probability of effective ventilation. Proceed with current settings.",
  "top_factors": [
    {"feature": "spo2_30min", "importance": 0.166},
    {"feature": "spo2_20min", "importance": 0.127},
    {"feature": "spo2_25min", "importance": 0.108},
    {"feature": "gcs_score",  "importance": 0.069},
    {"feature": "spo2_at_15", "importance": 0.070}
  ]
}
```

## Replacing Synthetic Data with Real Data

When hospital data is received from sir:
1. Open `AmbuPredict_ML_Pipeline.ipynb`
2. Change `DATA_PATH = 'your_real_data.csv'`
3. Skip the synthetic data generator cell
4. Re-run all cells — new `.pkl` files are auto-saved
5. Restart the FastAPI server — it loads fresh models on startup

## Risk Level Thresholds

| Risk Level | Probability | Clinical Action                              |
|------------|-------------|----------------------------------------------|
| HIGH       | ≥ 70%       | Proceed. Monitor SpO₂ every 5 min.           |
| MODERATE   | 45–69%      | Monitor closely. Adjust if SpO₂ not rising.  |
| LOW        | < 45%       | Adjust BPM/Mode/PEEP or escalate to full ventilator. |
