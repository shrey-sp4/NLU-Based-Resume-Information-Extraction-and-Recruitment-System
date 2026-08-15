from __future__ import annotations

import json
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

from src.explainability.report_builder import (
    build_explainability_report,
    get_available_resumes,
    PREDICTIONS_DIR,
    SECTIONS_DIR,
)
from src.extract_structured_information import process_resume

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Extraction Explainability Dashboard</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-amber: #fbbf24;
            --badge-bg: #0284c7;
        }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 24px;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { margin: 0; font-size: 24px; color: var(--accent-blue); }
        .subtitle { font-size: 14px; color: var(--text-muted); }
        .controls {
            background: var(--card-bg);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            margin-bottom: 24px;
            display: flex;
            gap: 16px;
            align-items: center;
            flex-wrap: wrap;
        }
        select, input[type="file"], button {
            background: #0f172a;
            color: var(--text-main);
            border: 1px solid var(--card-border);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        button {
            background: var(--badge-bg);
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover { opacity: 0.9; }
        .flags-container {
            background: #451a03;
            border: 1px solid #78350f;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
        }
        .flags-title { font-weight: bold; color: var(--accent-amber); margin-bottom: 8px; }
        .flag-item {
            background: #27272a;
            border-left: 4px solid var(--accent-amber);
            padding: 8px 12px;
            margin-bottom: 6px;
            border-radius: 4px;
            font-size: 13px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(550px, 1fr));
            gap: 20px;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .card-title { font-weight: bold; color: var(--accent-blue); }
        .badge {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
        }
        .badge-match { background: #166534; color: #86efac; }
        .badge-mismatch { background: #991b1b; color: #fca5a5; }
        .badge-nogt { background: #334155; color: #cbd5e1; }
        .field-row {
            margin-bottom: 12px;
            padding: 8px;
            background: #0f172a;
            border-radius: 6px;
        }
        .field-name { font-weight: 600; color: var(--accent-blue); font-size: 13px; }
        .field-val { font-size: 14px; margin: 4px 0; font-family: monospace; color: #e2e8f0; }
        .field-source { font-size: 12px; color: var(--text-muted); font-style: italic; }
        .field-reason { font-size: 12px; color: var(--accent-amber); margin-top: 4px; }
        .sub-entry {
            border-left: 2px solid var(--accent-blue);
            padding-left: 10px;
            margin-bottom: 10px;
        }
        pre { font-size: 12px; color: #93c5fd; overflow-x: auto; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Resume Extraction Explainability Dashboard</h1>
                <div class="subtitle">Inspect parsed entity values, raw text source spans, and rule-based diagnostic reasons</div>
            </div>
        </header>

        <div class="controls">
            <label for="resumeSelect">Select Resume:</label>
            <select id="resumeSelect" onchange="loadReport(this.value)">
                {% for r in resumes %}
                <option value="{{ r.file_name }}" {% if loop.first %}selected{% endif %}>
                    {{ r.base_name }} {% if r.has_ground_truth %}[Ground Truth GT]{% else %}[Unseen Resume]{% endif %}
                </option>
                {% endfor %}
            </select>
            <button onclick="loadReport(document.getElementById('resumeSelect').value)">Inspect Resume</button>
        </div>

        <div id="flagsBox" class="flags-container" style="display:none;">
            <div class="flags-title">⚠️ Diagnostic Rule Flags Detected</div>
            <div id="flagsList"></div>
        </div>

        <div id="reportContent" class="grid"></div>
    </div>

    <script>
        function loadReport(resumeName) {
            fetch('/api/report/' + resumeName)
                .then(r => r.json())
                .then(data => renderReport(data))
                .catch(err => alert("Error loading report: " + err));
        }

        function renderReport(data) {
            const flagsBox = document.getElementById('flagsBox');
            const flagsList = document.getElementById('flagsList');
            const content = document.getElementById('reportContent');

            if (data.flags && data.flags.length > 0) {
                flagsBox.style.display = 'block';
                flagsList.innerHTML = data.flags.map(f => `
                    <div class="flag-item">
                        <strong>[${f.field}] ${f.flag}:</strong> ${f.description}
                    </div>
                `).join('');
            } else {
                flagsBox.style.display = 'none';
            }

            const r = data.field_reports;
            let html = '';

            // Personal Details Card
            html += `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">👤 Personal Details</div>
                    </div>
                    ${renderField('Name', r.personal_name)}
                    ${renderField('Email', r.personal_email)}
                    ${renderField('Phone', r.personal_phone)}
                </div>
            `;

            // Education Card
            html += `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🎓 Education Entries (${r.education.entry_count})</div>
                    </div>
            `;
            if (r.education.entries.length === 0) {
                html += `<div class="field-reason">No education entries extracted. Text snippet: ${r.education.section_text.substring(0, 100)}</div>`;
            } else {
                r.education.entries.forEach(e => {
                    html += `
                        <div class="sub-entry">
                            <div style="font-weight:600;font-size:12px;color:#cbd5e1;">Entry ${e.entry_index}</div>
                            ${renderSub('Degree', e.degree)}
                            ${renderSub('Institution', e.institution)}
                            ${renderSub('Year', e.graduation_year)}
                            ${renderSub('CGPA', e.cgpa)}
                            <div class="field-source">Source: "${e.raw_text}"</div>
                        </div>
                    `;
                });
            }
            html += `</div>`;

            // Experience Card
            html += `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💼 Experience Entries (${r.experience.entry_count})</div>
                    </div>
            `;
            if (r.experience.entries.length === 0) {
                html += `<div class="field-reason">No experience entries extracted. Text snippet: ${r.experience.section_text.substring(0, 100)}</div>`;
            } else {
                r.experience.entries.forEach(e => {
                    html += `
                        <div class="sub-entry">
                            <div style="font-weight:600;font-size:12px;color:#cbd5e1;">Entry ${e.entry_index}</div>
                            ${renderSub('Job Title', e.job_title)}
                            ${renderSub('Institution', e.institution)}
                            ${renderSub('Dates', e.dates)}
                            <div class="field-source">Source: "${e.raw_text}"</div>
                        </div>
                    `;
                });
            }
            html += `</div>`;

            // Text Sections Card
            html += `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🛠️ Skills, Projects & Summary</div>
                    </div>
                    ${renderField('Skills', r.skills)}
                    ${renderField('Projects', r.projects)}
                    ${renderField('Summary', r.summary)}
                    ${renderField('Research Interests', r.research_interests)}
                </div>
            `;

            content.innerHTML = html;
        }

        function renderField(name, f) {
            let badge = '';
            if (f.gt_match_status === 'MATCH') badge = '<span class="badge badge-match">GT Match</span>';
            else if (f.gt_match_status === 'MISMATCH') badge = `<span class="badge badge-mismatch">GT: ${f.gt_value}</span>`;

            let valStr = Array.isArray(f.value) ? f.value.join(', ') : f.value;
            return `
                <div class="field-row">
                    <div style="display:flex;justify-content:space-between;">
                        <span class="field-name">${name}</span>
                        ${badge}
                    </div>
                    <div class="field-val">${valStr}</div>
                    <div class="field-source">Line: "${f.source_line || f.source_snippet}"</div>
                    ${f.reason_if_empty ? `<div class="field-reason">Reason: ${f.reason_if_empty}</div>` : ''}
                </div>
            `;
        }

        function renderSub(label, sub) {
            return `
                <div style="margin:2px 0;">
                    <span style="color:#94a3b8;font-size:12px;">${label}:</span>
                    <span style="font-family:monospace;font-size:13px;color:#38bdf8;">${sub.value}</span>
                    ${sub.reason_if_empty ? `<span class="field-reason"> (${sub.reason_if_empty})</span>` : ''}
                </div>
            `;
        }

        document.addEventListener('DOMContentLoaded', () => {
            const sel = document.getElementById('resumeSelect');
            if (sel && sel.value) loadReport(sel.value);
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    resumes = get_available_resumes()
    return render_template_string(HTML_TEMPLATE, resumes=resumes)

@app.route("/api/report/<resume_name>")
def api_report(resume_name: str):
    try:
        report = build_explainability_report(resume_name)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    print("Starting Explainability Web Server on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=False)
