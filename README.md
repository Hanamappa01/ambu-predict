# AmbuPredict — ML Ventilation Outcome Predictor
### NeuO In-Spire Resuscitator Automation System

Predicts whether bag valve mask ventilation will succeed for a patient,
based on In-Spire machine settings + patient vitals + SpO₂ trajectory.

---

## Project Structure

```
AmbuPredict_Project/
│
├── ambu_frontend.html          ← Open this in browser (no server needed)
│
├── ambu_api/
│   ├── main.py                 ← FastAPI backend (all prediction routes)
│   ├── requirements.txt        ← Python dependencies
│   └── README.md               ← API documentation
│
├── models/
│   ├── ambu_rf_model.pkl       ← Trained Random Forest model
│   ├── ambu_scaler.pkl         ← MinMaxScaler
│   ├── ambu_encoders.pkl       ← LabelEncoders (mode/gender/condition/comorbidity)
│   └── ambu_feature_cols.pkl   ← Ordered feature column names
│
├── data/
│   └── ambu_patient_data.csv   ← Synthetic dataset (120 patients)
│
├── notebook/
│   └── AmbuPredict_ML_Pipeline.ipynb  ← Full training pipeline
│
└── README.md                   ← This file
```

---

## Quick Start

### Step 1 — Install dependencies
```bash
pip install -r ambu_api/requirements.txt
```

### Step 2 — Start the API
```bash
# Run from the AmbuPredict_Project/ folder
uvicorn ambu_api.main:app --reload --port 8000
```

### Step 3 — Open the frontend
Just open `ambu_frontend.html` in your browser.
The frontend auto-detects if the API is running:
- **API Online** → real ML predictions from your trained model
- **API Offline** → Demo Mode (simulated predictions, good for presentations)

### Step 4 — View API docs
```
http://localhost:8000/docs
```

---

## API Endpoints

| Method | Route            | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/`              | Health check                       |
| GET    | `/meta`          | Valid dropdown values              |
| POST   | `/predict`       | Single patient prediction          |
| POST   | `/batch-predict` | Up to 50 patients at once          |

---

## Replacing Synthetic Data with Real Hospital Data

When data arrives from sir:
1. Open `notebook/AmbuPredict_ML_Pipeline.ipynb`
2. Change `DATA_PATH = 'your_real_data.csv'` in Cell 1
3. Skip the synthetic data generator cell (Cell 2)
4. Run all remaining cells — new `.pkl` files save to the project root
5. Move new `.pkl` files to `models/` folder
6. Restart uvicorn — it loads the fresh model automatically

---

## Model Details

- **Algorithm**: Random Forest (100 trees, max_depth=5, class_weight=balanced)
- **Validator**: XGBoost (cross-checked in notebook)
- **Baseline**: Logistic Regression (for clinical audit / interpretability)
- **CV**: 5-fold Stratified K-Fold
- **Priority metric**: Recall (minimize missed failures — clinically safer)
- **Training data**: 120 synthetic patients (replace with real data)
- **Certification**: Model designed to complement NeuO IEC 60601 device

---

## Risk Level Thresholds

| Risk    | Probability | Action                                         |
|---------|-------------|------------------------------------------------|
| HIGH    | ≥ 70%       | Proceed. Monitor SpO₂ every 5 min.             |
| MODERATE| 45–69%      | Monitor closely. Adjust if SpO₂ not rising.    |
| LOW     | < 45%       | Adjust settings or escalate to full ventilator.|
