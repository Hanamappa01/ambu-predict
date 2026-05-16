import os

file_path = r'c:\neuorigami\anti inspire\ambu_frontend.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add "Add Patient" to nav
nav_home = '<div class="nav-item active" onclick="switchTab(\'home\')" id="nav-home">Home</div>'
nav_add = '<div class="nav-item" onclick="switchTab(\'add\')" id="nav-add">Add Patient</div>'
content = content.replace(nav_home, nav_home + '\n    ' + nav_add)

# 2. Add Export button to history
btn_clear = '<button class="btn-clear-hist" onclick="clearHistory()" style="margin-left:8px;">Clear</button>'
btn_export = '<button class="btn-clear-hist" onclick="exportHistory()" style="margin-left:8px; border-color: var(--accent); color: var(--accent);">Export to Excel</button>'
content = content.replace(btn_clear, btn_clear + '\n      ' + btn_export)

# 3. Add "Add Patient" Section HTML
# We will just duplicate the predictor section content, but change the ID and button
# To keep it simple, we'll construct the HTML manually for the form
# We can just reuse the same form by toggling visibility of the Outcome field!
# Actually, the predictor section already contains all fields. Let's just add an outcome dropdown at the bottom of predictor section, hidden by default.

outcome_field = '''
  <div class="card" id="outcome-card" style="display:none; margin-bottom: 20px; border-color: var(--accent);">
    <div class="card-title">Actual Outcome</div>
    <div class="field" style="margin-bottom:0;">
      <label>Did the ventilation succeed?</label>
      <select id="actual-outcome">
        <option value="1">Positive (Success)</option>
        <option value="0">Negative (Failure)</option>
      </select>
    </div>
  </div>
'''
action_row = '<div class="action-row">'
content = content.replace(action_row, outcome_field + '\n  ' + action_row)

btn_predict = '<button class="btn-predict" id="predict-btn" onclick="runPrediction()" style="flex:1;">\n      Run Prediction\n    </button>'
btn_add = '<button class="btn-predict" id="add-btn" onclick="addPatientAndRetrain()" style="flex:1; display:none; background: linear-gradient(135deg, var(--warn), #f97316);">\n      Add & Retrain\n    </button>'
content = content.replace(btn_predict, btn_predict + '\n    ' + btn_add)

# 4. Modify switchTab in JS
js_tab_old = '''function switchTab(tab) {
  document.getElementById('nav-home').classList.remove('active');
  document.getElementById('nav-predictor').classList.remove('active');
  document.getElementById('home-section').style.display = 'none';
  document.getElementById('predictor-section').style.display = 'none';
  
  if (tab === 'home') {
    document.getElementById('nav-home').classList.add('active');
    document.getElementById('home-section').style.display = 'block';
  } else {
    document.getElementById('nav-predictor').classList.add('active');
    document.getElementById('predictor-section').style.display = 'block';
  }
}'''

js_tab_new = '''function switchTab(tab) {
  document.getElementById('nav-home').classList.remove('active');
  document.getElementById('nav-predictor').classList.remove('active');
  document.getElementById('nav-add').classList.remove('active');
  document.getElementById('home-section').style.display = 'none';
  document.getElementById('predictor-section').style.display = 'none';
  document.getElementById('outcome-card').style.display = 'none';
  document.getElementById('predict-btn').style.display = 'none';
  document.getElementById('add-btn').style.display = 'none';
  document.getElementById('result-panel').style.display = 'none';
  
  if (tab === 'home') {
    document.getElementById('nav-home').classList.add('active');
    document.getElementById('home-section').style.display = 'block';
  } else if (tab === 'predictor') {
    document.getElementById('nav-predictor').classList.add('active');
    document.getElementById('predictor-section').style.display = 'block';
    document.getElementById('predict-btn').style.display = 'block';
  } else if (tab === 'add') {
    document.getElementById('nav-add').classList.add('active');
    document.getElementById('predictor-section').style.display = 'block';
    document.getElementById('outcome-card').style.display = 'block';
    document.getElementById('add-btn').style.display = 'block';
  }
}'''
content = content.replace(js_tab_old, js_tab_new)

# 5. Add Export JS function
export_js = '''
function exportHistory() {
  if (predHistory.length === 0) {
    alert('No predictions to export!');
    return;
  }
  const headers = ['Time', 'Age', 'Gender', 'Condition', 'BPM', 'Mode', 'SpO2_Before', 'SpO2_30min', 'Probability', 'Risk_Level', 'Outcome'];
  let csv = headers.join(',') + '\\n';
  predHistory.forEach(item => {
    const d = item.formData;
    const row = [
      item.time, d.age, d.gender, d.condition, d.bpm, d.mode,
      d.spo2_before, d.spo2_30min,
      item.data.probability_pct + '%', item.data.risk_level, item.data.outcome
    ].map(v => '"' + v + '"').join(',');
    csv += row + '\\n';
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', 'AmbuPredict_History.csv');
  a.click();
}
'''

# 6. Add "addPatientAndRetrain" JS function
add_js = '''
async function addPatientAndRetrain() {
  const btn    = document.getElementById('add-btn');
  const errBox = document.getElementById('error-box');
  errBox.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Retraining...';

  const formData = getFormData();
  formData.outcome = parseInt(document.getElementById('actual-outcome').value);

  try {
    const resp = await fetch(`${API}/add_patient`, {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify(formData),
      signal : AbortSignal.timeout(15000)
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    alert('✅ ' + data.message);
    switchTab('predictor');
  } catch (e) {
    errBox.style.display = 'block';
    errBox.textContent = '⚠️  ' + e.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Add & Retrain';
  }
}
'''

content = content.replace('// ── Run prediction ─────────────────────────────────────────────────────────', export_js + '\n' + add_js + '\n// ── Run prediction ─────────────────────────────────────────────────────────')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Frontend updated!")
