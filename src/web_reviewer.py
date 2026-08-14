import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import parse_qs, urlparse

# Ensure src is on pythonpath if run directly
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sectioning.qc_engine import run_qc_analysis, load_jsonl, save_jsonl

DEFAULT_MACHINE_PATH = Path("data/section_annotations/section_line_annotations.jsonl")
DEFAULT_HUMAN_PATH = Path("data/section_annotations/human_annotations.jsonl")
DEFAULT_SUSPICIOUS_PATH = Path("data/section_annotations/suspicious_qc_queue.jsonl")
DEFAULT_STRATIFIED_PATH = Path("data/section_annotations/stratified_qc_sample.jsonl")
DEFAULT_QC_DECISIONS_PATH = Path("data/section_annotations/qc_decisions.jsonl")

CANONICAL_SECTIONS = [
    "education",
    "experience",
    "skills",
    "projects",
    "publications",
    "certifications",
    "research_interests",
    "achievements",
    "personal_details",
    "summary",
    "references",
    "responsibilities",
    "memberships",
    "patents",
    "declaration",
    "other",
]

# Global state
STATE = {
    "machine_records": [],
    "human_annotations": {},
    "qc_decisions": {},
    "active_mode": "suspicious",  # 'suspicious', 'stratified', 'all'
    "active_queue": [],
    "resume_page_map": {},
    "key_to_index": {},
}


def make_key(record: dict) -> str:
    return record.get("_key") or f"{record.get('resume_id')}|p{record.get('page_number')}|l{record.get('line_number')}|i{record.get('line_index')}"


def load_qc_decisions(path: Path = DEFAULT_QC_DECISIONS_PATH) -> Dict[str, dict]:
    if not path.exists():
        return {}
    decisions = {}
    for rec in load_jsonl(path):
        if "_key" in rec:
            decisions[rec["_key"]] = rec
    return decisions


def save_qc_decision(decision: dict, path: Path = DEFAULT_QC_DECISIONS_PATH) -> None:
    STATE["qc_decisions"][decision["_key"]] = decision
    save_jsonl(path, list(STATE["qc_decisions"].values()))


def init_state(mode: str = "suspicious"):
    # First, run QC analysis if files don't exist
    if not DEFAULT_SUSPICIOUS_PATH.exists() or not DEFAULT_STRATIFIED_PATH.exists():
        run_qc_analysis()

    machine_recs = load_jsonl(DEFAULT_MACHINE_PATH)
    human_recs = load_jsonl(DEFAULT_HUMAN_PATH)
    qc_decisions = load_qc_decisions(DEFAULT_QC_DECISIONS_PATH)

    STATE["machine_records"] = machine_recs
    STATE["human_annotations"] = {r["_key"]: r for r in human_recs if "_key" in r}
    STATE["qc_decisions"] = qc_decisions

    page_map = {}
    for r in machine_recs:
        key = (r.get("resume_id"), r.get("page_number", 1))
        page_map.setdefault(key, []).append(r)
    STATE["resume_page_map"] = page_map

    set_queue_mode(mode)


def set_queue_mode(mode: str):
    STATE["active_mode"] = mode
    if mode == "suspicious":
        queue = load_jsonl(DEFAULT_SUSPICIOUS_PATH)
    elif mode == "stratified":
        queue = load_jsonl(DEFAULT_STRATIFIED_PATH)
    else:
        # 'all' candidate lines
        queue = [r for r in STATE["machine_records"] if r.get("machine_suggested_heading") is not None]

    STATE["active_queue"] = queue
    STATE["key_to_index"] = {make_key(r): i for i, r in enumerate(queue)}


def get_candidate_payload(candidate_idx: int) -> dict:
    queue = STATE["active_queue"]
    if not queue:
        return {"error": "No records in current queue mode."}

    candidate_idx = max(0, min(candidate_idx, len(queue) - 1))
    target_rec = queue[candidate_idx]
    target_key = make_key(target_rec)

    resume_id = target_rec.get("resume_id")
    page_num = target_rec.get("page_number", 1)
    page_lines = STATE["resume_page_map"].get((resume_id, page_num), [])

    human_ann = STATE["human_annotations"].get(target_key, {})
    qc_dec = STATE["qc_decisions"].get(target_key, {})

    m_rec = next((r for r in STATE["machine_records"] if make_key(r) == target_key), target_rec)

    formatted_page_lines = []
    for r in page_lines:
        r_key = make_key(r)
        formatted_page_lines.append({
            "_key": r_key,
            "line_number": r.get("line_number"),
            "line_index": r.get("line_index"),
            "text": r.get("text"),
            "is_target": (r_key == target_key),
            "human_annotation": STATE["human_annotations"].get(r_key),
            "qc_decision": STATE["qc_decisions"].get(r_key),
        })

    return {
        "index": candidate_idx,
        "total_candidates": len(queue),
        "mode": STATE["active_mode"],
        "reviewed_count": len(STATE["qc_decisions"]),
        "canonical_sections": CANONICAL_SECTIONS,
        "candidate": {
            "_key": target_key,
            "resume_id": resume_id,
            "page_number": page_num,
            "line_number": target_rec.get("line_number"),
            "line_index": target_rec.get("line_index"),
            "text": m_rec.get("text"),
            "human_is_heading": human_ann.get("is_heading"),
            "human_section_label": human_ann.get("section_label"),
            "machine_suggested_section": target_rec.get("machine_suggested_section") or m_rec.get("machine_suggested_section") or "other",
            "machine_confidence": target_rec.get("machine_confidence") or m_rec.get("machine_confidence") or 0.0,
            "flag_code": target_rec.get("flag_code"),
            "flag_severity": target_rec.get("flag_severity"),
            "flag_reason": target_rec.get("flag_reason"),
            "all_flags": target_rec.get("all_flags", []),
            "human_annotation": human_ann,
            "qc_decision": qc_dec,
        },
        "page_lines": formatted_page_lines,
    }


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intelligent Resume Section Quality Control</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --accent-primary: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: var(--bg-dark); color: var(--text-primary); height: 100vh; display: flex; flex-direction: column; }

        header { background: var(--bg-card); border-bottom: 1px solid var(--border-color); padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
        .header-title h1 { font-size: 1.1rem; font-weight: 600; color: var(--accent-primary); }
        .mode-selector button { background: #334155; color: var(--text-secondary); border: 1px solid var(--border-color); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 500; margin-right: 4px; }
        .mode-selector button.active { background: var(--accent-primary); color: #000; font-weight: 600; border-color: var(--accent-primary); }

        .workspace { display: grid; grid-template-columns: 1fr 480px; flex: 1; overflow: hidden; }

        /* Document Context Panel */
        .page-panel { border-right: 1px solid var(--border-color); display: flex; flex-direction: column; overflow: hidden; background: #0b1120; }
        .panel-header { padding: 12px 20px; background: rgba(30, 41, 59, 0.5); border-bottom: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary); display: flex; justify-content: space-between; }
        .lines-container { flex: 1; overflow-y: auto; padding: 16px 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; }
        .doc-line { padding: 6px 10px; border-radius: 4px; display: flex; gap: 12px; margin-bottom: 2px; }
        .doc-line.target { background: rgba(56, 189, 248, 0.18); border-left: 4px solid var(--accent-primary); color: #fff; font-weight: 600; }
        .doc-line .line-num { color: var(--text-secondary); width: 32px; font-size: 0.8rem; text-align: right; }

        /* Decision Panel */
        .decision-panel { background: var(--bg-card); display: flex; flex-direction: column; padding: 24px; gap: 20px; overflow-y: auto; }
        
        .flag-card { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 14px; color: var(--accent-amber); font-size: 0.85rem; }
        .flag-card.high { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.3); color: var(--accent-red); }
        .flag-card h4 { font-size: 0.9rem; margin-bottom: 6px; display: flex; justify-content: space-between; }

        .meta-card { background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; font-size: 0.85rem; }
        .meta-row { display: flex; justify-content: space-between; margin-bottom: 6px; }

        .action-group { display: flex; flex-direction: column; gap: 12px; }
        .btn-action { background: #334155; color: var(--text-primary); border: 1px solid var(--border-color); padding: 10px 16px; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; text-align: left; transition: all 0.15s; }
        .btn-action:hover { background: #475569; }
        .btn-action.confirm { background: rgba(34, 197, 94, 0.2); border-color: var(--accent-green); color: var(--accent-green); }
        .btn-action.confirm:hover { background: rgba(34, 197, 94, 0.3); }

        .custom-input-group { display: flex; gap: 8px; margin-top: 8px; }
        .custom-input-group input { flex: 1; background: #0f172a; border: 1px solid var(--border-color); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; }

        select { background: #0f172a; border: 1px solid var(--border-color); color: #fff; padding: 8px 12px; border-radius: 6px; width: 100%; font-size: 0.85rem; margin-top: 6px; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>QC Annotation Reviewer</h1>
        </div>
        <div class="mode-selector">
            <button id="btn-suspicious" class="active" onclick="switchMode('suspicious')">Suspicious Queue (<span id="count-suspicious">0</span>)</button>
            <button id="btn-stratified" onclick="switchMode('stratified')">Stratified Sample (<span id="count-stratified">0</span>)</button>
            <button id="btn-all" onclick="switchMode('all')">All Lines</button>
        </div>
        <div class="nav-controls">
            <button class="btn-action" onclick="navigate(-1)">← Prev</button>
            <span id="pos-indicator">1 / 1</span>
            <button class="btn-action" onclick="navigate(1)">Next →</button>
        </div>
    </header>

    <div class="workspace">
        <div class="page-panel">
            <div class="panel-header">
                <span id="doc-id">Resume: -</span>
                <span id="page-num">Page -</span>
            </div>
            <div class="lines-container" id="lines-container"></div>
        </div>

        <div class="decision-panel">
            <div id="flag-card-container"></div>

            <div class="meta-card">
                <div class="meta-row"><span>Target Heading Text:</span><strong id="target-text" style="color: var(--accent-primary)">-</strong></div>
                <div class="meta-row"><span>Original Human Decision:</span><span id="orig-human">-</span></div>
                <div class="meta-row"><span>Machine Suggestion:</span><span id="machine-sug">-</span></div>
                <div class="meta-row" id="qc-status-row" style="display:none"><span>QC Decision:</span><strong id="qc-status-val" style="color:var(--accent-green)">-</strong></div>
            </div>

            <div class="action-group">
                <h3>QC Action</h3>
                <button class="btn-action confirm" onclick="submitDecision('keep_existing')">✓ Keep Existing Human Decision</button>

                <div>
                    <label>Change Section Label:</label>
                    <select id="section-select" onchange="toggleCustomInput()"></select>
                    <div class="custom-input-group" id="custom-group" style="display:none">
                        <input type="text" id="custom-section-input" placeholder="Type custom section name (e.g. conferences)...">
                    </div>
                </div>

                <button class="btn-action" onclick="submitDecision('change_section')">Apply Section Change</button>
                <button class="btn-action" onclick="submitDecision('toggle_heading')">Toggle Heading Status (Heading ↔ Non-Heading)</button>
                <button class="btn-action" onclick="submitDecision('mark_uncertain')">Mark Uncertain / Needs Review</button>
                <button class="btn-action" onclick="navigate(1)">Skip for Now</button>
            </div>
        </div>
    </div>

    <script>
        let currentIndex = 0;
        let currentPayload = null;

        async function fetchPayload(idx) {
            const resp = await fetch(`/api/candidate?index=${idx}`);
            currentPayload = await resp.json();
            render();
        }

        async function switchMode(mode) {
            document.querySelectorAll('.mode-selector button').forEach(b => b.classList.remove('active'));
            document.getElementById(`btn-${mode}`).classList.add('active');
            await fetch(`/api/set_mode?mode=${mode}`);
            currentIndex = 0;
            fetchPayload(0);
        }

        function render() {
            if (!currentPayload || currentPayload.error) return;

            const c = currentPayload.candidate;
            document.getElementById('doc-id').textContent = `Resume: ${c.resume_id}`;
            document.getElementById('page-num').textContent = `Page ${c.page_number}`;
            document.getElementById('pos-indicator').textContent = `${currentPayload.index + 1} / ${currentPayload.total_candidates}`;
            document.getElementById('target-text').textContent = c.text;

            const isH = c.human_is_heading ? "Heading" : "Non-Heading";
            const sec = c.human_section_label || "none";
            document.getElementById('orig-human').textContent = `${isH} (${sec})`;
            document.getElementById('machine-sug').textContent = `${c.machine_suggested_section} (${c.machine_confidence})`;

            // Flag Card
            const flagContainer = document.getElementById('flag-card-container');
            if (c.flag_code) {
                const isHigh = c.flag_severity === 'high';
                flagContainer.innerHTML = `
                    <div class="flag-card ${isHigh ? 'high' : ''}">
                        <h4><span>${c.flag_code}</span> <span>[${c.flag_severity.toUpperCase()}]</span></h4>
                        <p>${c.flag_reason}</p>
                    </div>`;
            } else {
                flagContainer.innerHTML = '';
            }

            // QC Decision Status
            const qcRow = document.getElementById('qc-status-row');
            if (c.qc_decision && c.qc_decision.qc_action) {
                qcRow.style.display = 'flex';
                document.getElementById('qc-status-val').textContent = `${c.qc_decision.qc_action} -> ${c.qc_decision.section_label}`;
            } else {
                qcRow.style.display = 'none';
            }

            // Section Select Options
            const sel = document.getElementById('section-select');
            sel.innerHTML = currentPayload.canonical_sections.map(s => `<option value="${s}" ${s === (c.human_section_label || c.machine_suggested_section) ? 'selected' : ''}>${s}</option>`).join('') +
                `<option value="CUSTOM">-- Custom Section --</option>`;
            
            toggleCustomInput();

            // Render Page Context Lines
            const linesContainer = document.getElementById('lines-container');
            linesContainer.innerHTML = currentPayload.page_lines.map(l => `
                <div class="doc-line ${l.is_target ? 'target' : ''}">
                    <span class="line-num">${l.line_number}</span>
                    <span>${l.text}</span>
                </div>
            `).join('');
        }

        function toggleCustomInput() {
            const selVal = document.getElementById('section-select').value;
            document.getElementById('custom-group').style.display = (selVal === 'CUSTOM') ? 'flex' : 'none';
        }

        function navigate(delta) {
            currentIndex += delta;
            fetchPayload(currentIndex);
        }

        async function submitDecision(action) {
            const c = currentPayload.candidate;
            const selSec = document.getElementById('section-select').value;
            const customVal = document.getElementById('custom-section-input').value.trim();

            let isHeading = c.human_is_heading;
            let sectionLabel = c.human_section_label;
            let customLabel = null;

            if (action === 'keep_existing') {
                sectionLabel = c.human_section_label;
            } else if (action === 'change_section') {
                if (selSec === 'CUSTOM') {
                    sectionLabel = customVal.toLowerCase() || "custom";
                    customLabel = customVal.toLowerCase();
                } else {
                    sectionLabel = selSec;
                }
            } else if (action === 'toggle_heading') {
                isHeading = !isHeading;
            }

            const payload = {
                _key: c._key,
                resume_id: c.resume_id,
                page_number: c.page_number,
                line_number: c.line_number,
                line_index: c.line_index,
                raw_heading: c.text,
                qc_action: action,
                is_heading: isHeading,
                section_label: sectionLabel,
                custom_section_label: customLabel,
                is_custom: selSec === 'CUSTOM' || Boolean(customLabel),
                qc_reason: c.flag_reason || "user_qc_review",
            };

            await fetch('/api/save_decision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            navigate(1);
        }

        fetchPayload(0);
    </script>
</body>
</html>
"""


class QCReviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode("utf-8"))

        elif path == "/api/candidate":
            idx = int(params.get("index", [0])[0])
            payload = get_candidate_payload(idx)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/api/set_mode":
            mode = params.get("mode", ["suspicious"])[0]
            set_queue_mode(mode)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "mode": mode}).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/save_decision":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            decision = json.loads(body.decode("utf-8"))
            save_qc_decision(decision)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "saved"}).encode("utf-8"))


def run_server(port: int = 8000, mode: str = "suspicious"):
    init_state(mode)
    server_address = ("", port)
    httpd = HTTPServer(server_address, QCReviewHandler)
    print(f"QC Reviewer Server started at http://localhost:{port}")
    print(f"Review Mode: '{mode}'")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QC Annotation Web Reviewer")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser.add_argument("--mode", type=str, default="suspicious", choices=["suspicious", "stratified", "all"])
    args = parser.parse_args()

    run_server(port=args.port, mode=args.mode)
