file_path = 'index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

content_check = ''.join(lines)
if 'nav-summary' in content_check:
    print("Already patched!")
    exit()

# 1. Add nav item after nav-predictor line
for i, line in enumerate(lines):
    if 'id="nav-predictor">Predictor</div>' in line:
        lines.insert(i+1, '      <div class="nav-item" onclick="switchTab(\'summary\')" id="nav-summary">&#128202; Data Summary</div>\n')
        print(f"nav item added at line {i+1}")
        break

# 2. Add summary HTML before </body>
summary_html = '''
    <div id="summary-section" style="display:none;">
      <div class="home-hero" style="margin-bottom:30px;">
        <h1 style="font-size:36px;">&#128202; Data Summary</h1>
        <p style="color:var(--muted);">Overview of all patient data used to train the model</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:30px;">
        <div class="home-card" style="text-align:center;padding:20px;">
          <div style="font-size:40px;font-weight:800;color:var(--accent);" id="stat-mongo">-</div>
          <div style="color:var(--muted);margin-top:6px;">Patients in DB</div>
        </div>
        <div class="home-card" style="text-align:center;padding:20px;">
          <div style="font-size:40px;font-weight:800;color:#4ade80;" id="stat-positive">-</div>
          <div style="color:var(--muted);margin-top:6px;">Positive Outcomes</div>
        </div>
        <div class="home-card" style="text-align:center;padding:20px;">
          <div style="font-size:40px;font-weight:800;color:var(--danger);" id="stat-negative">-</div>
          <div style="color:var(--muted);margin-top:6px;">Negative Outcomes</div>
        </div>
        <div class="home-card" style="text-align:center;padding:20px;">
          <div style="font-size:40px;font-weight:800;color:var(--warn);" id="stat-avg-age">-</div>
          <div style="color:var(--muted);margin-top:6px;">Avg. Age</div>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-bottom:30px;flex-wrap:wrap;">
        <button class="btn-predict" onclick="downloadAllData()" style="flex:1;min-width:200px;">&#11015; Download All Patient Data (CSV)</button>
        <button class="btn-predict" onclick="loadSummary()" style="flex:1;min-width:200px;background:linear-gradient(135deg,#334155,#475569);">&#128260; Refresh</button>
      </div>
      <div class="home-card" style="margin-bottom:20px;">
        <h3>Condition Breakdown</h3>
        <div id="condition-breakdown" style="margin-top:10px;">Click Refresh to load...</div>
      </div>
      <div class="home-card" style="margin-bottom:20px;">
        <h3>Gender Breakdown</h3>
        <div id="gender-breakdown" style="margin-top:10px;">Click Refresh to load...</div>
      </div>
      <div class="home-card">
        <h3>Recently Added Patients</h3>
        <div id="recent-patients" style="margin-top:10px;overflow-x:auto;">Click Refresh to load...</div>
      </div>
    </div>
'''
for i, line in enumerate(lines):
    if '</body>' in line:
        lines.insert(i, summary_html + '\n')
        print(f"summary HTML added before </body>")
        break

# 3. Add nav-summary remove in switchTab
for i, line in enumerate(lines):
    if "document.getElementById('nav-predictor').classList.remove('active');" in line:
        lines.insert(i+1, "      document.getElementById('nav-summary').classList.remove('active');\n")
        print(f"nav-summary remove added")
        break

# 4. Add summary-section hide in switchTab
for i, line in enumerate(lines):
    if "document.getElementById('predictor-section').style.display = 'none';" in line:
        lines.insert(i+1, "      document.getElementById('summary-section').style.display = 'none';\n")
        print(f"summary-section hide added")
        break

# 5. Add summary case - find spo2 label line
for i, line in enumerate(lines):
    if "SpO\u2082 Readings Post-Intubation" in line or "Readings Post-Intubation" in line:
        new_case = "      } else if (tab === 'summary') {\n        document.getElementById('nav-summary').classList.add('active');\n        document.getElementById('summary-section').style.display = 'block';\n        loadSummary();\n"
        lines.insert(i+1, new_case)
        print(f"summary case added in switchTab")
        break

# 6. Add JS before Enter key shortcut
summary_js = """
    async function loadSummary() {
      try {
        const resp = await fetch(`${API}/patients/all`);
        const json = await resp.json();
        const pts = json.patients || [];
        document.getElementById('stat-mongo').textContent = pts.length;
        document.getElementById('stat-positive').textContent = pts.filter(p=>p.outcome===1).length;
        document.getElementById('stat-negative').textContent = pts.filter(p=>p.outcome===0).length;
        document.getElementById('stat-avg-age').textContent = pts.length ? Math.round(pts.reduce((s,p)=>s+p.age,0)/pts.length) : '-';
        const condMap = {};
        pts.forEach(p => { condMap[p.condition] = (condMap[p.condition]||0)+1; });
        document.getElementById('condition-breakdown').innerHTML = Object.entries(condMap).sort((a,b)=>b[1]-a[1]).map(([c,n]) =>
          `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="width:160px;font-size:14px;">${c}</div>
            <div style="flex:1;background:rgba(255,255,255,0.05);border-radius:4px;height:18px;overflow:hidden;">
              <div style="width:${Math.round(n/pts.length*100)}%;background:linear-gradient(90deg,var(--accent),var(--accent2));height:100%;border-radius:4px;"></div>
            </div>
            <div style="width:24px;color:var(--accent);font-weight:600;">${n}</div>
          </div>`).join('') || '<p style="color:var(--muted)">No data yet</p>';
        const genMap = {};
        pts.forEach(p => { genMap[p.gender] = (genMap[p.gender]||0)+1; });
        document.getElementById('gender-breakdown').innerHTML = Object.entries(genMap).map(([g,n]) =>
          `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="width:80px;font-size:14px;">${g}</div>
            <div style="flex:1;background:rgba(255,255,255,0.05);border-radius:4px;height:18px;overflow:hidden;">
              <div style="width:${Math.round(n/pts.length*100)}%;background:linear-gradient(90deg,#a855f7,#ec4899);height:100%;border-radius:4px;"></div>
            </div>
            <div style="width:24px;color:#a855f7;font-weight:600;">${n}</div>
          </div>`).join('') || '<p style="color:var(--muted)">No data yet</p>';
        const recent = pts.slice(-10).reverse();
        document.getElementById('recent-patients').innerHTML = !recent.length
          ? '<p style="color:var(--muted)">No patients added yet.</p>'
          : `<table class="home-table"><thead><tr><th>Age</th><th>Gender</th><th>Condition</th><th>BPM</th><th>SpO2 Before</th><th>SpO2 30min</th><th>Outcome</th><th>Date</th></tr></thead><tbody>
            ${recent.map(p=>`<tr><td>${p.age}</td><td>${p.gender}</td><td>${p.condition}</td><td>${p.bpm}</td><td>${p.spo2_before}%</td><td>${p.spo2_30min}%</td>
            <td style="color:${p.outcome===1?'#4ade80':'var(--danger)'};font-weight:600;">${p.outcome===1?'Positive':'Negative'}</td>
            <td style="color:var(--muted);font-size:12px;">${p.added_at?p.added_at.split('T')[0]:'-'}</td></tr>`).join('')}
            </tbody></table>`;
      } catch(e) {
        document.getElementById('condition-breakdown').innerHTML = '<p style="color:var(--danger)">Cannot reach API. Refresh after 30 seconds.</p>';
      }
    }

    async function downloadAllData() {
      try {
        const resp = await fetch(`${API}/patients/all`);
        if (!resp.ok) throw new Error('API not reachable');
        const json = await resp.json();
        if (!json.patients || !json.patients.length) { alert('No data in MongoDB yet!'); return; }
        const headers = ['age','gender','condition','comorbidity','bpm','mode','peep','lpm','pulse','bp_systolic','bp_diastolic','gcs_score','cvs_score','spo2_before','spo2_5min','spo2_10min','spo2_15min','spo2_20min','spo2_25min','spo2_30min','outcome','added_at'];
        let csv = headers.join(',') + '\\n';
        json.patients.forEach(p => { csv += headers.map(h=>`"${p[h]??''}"`).join(',') + '\\n'; });
        const blob = new Blob([csv], {type:'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AmbuPredict_Data_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } catch(e) { alert('Download failed: ' + e.message); }
    }
"""
for i, line in enumerate(lines):
    if '// Enter key shortcut' in line:
        lines.insert(i, summary_js + '\n')
        print(f"JS functions added")
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done! Summary tab added successfully.")
