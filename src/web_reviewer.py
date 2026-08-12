import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure src is on pythonpath if run directly
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from annotation_reviewer import (
    load_machine_records,
    load_human_annotations,
    save_human_annotations,
    create_annotation_from_machine,
    make_key,
    CANONICAL_SECTIONS,
    summarize,
)

DEFAULT_MACHINE_PATH = Path("data/section_annotations/section_line_annotations.jsonl")
DEFAULT_HUMAN_PATH = Path("data/section_annotations/human_annotations.jsonl")

# Global state
STATE = {
    "machine_path": DEFAULT_MACHINE_PATH,
    "human_path": DEFAULT_HUMAN_PATH,
    "machine_records": [],
    "human_annotations": {},
    "all_candidates": [],
    "resume_page_map": {}, # (resume_id, page_number) -> list of line records
    "key_to_candidate_index": {},
}


def init_state(machine_path: Path = DEFAULT_MACHINE_PATH, human_path: Path = DEFAULT_HUMAN_PATH):
    machine_path = Path(machine_path)
    human_path = Path(human_path)
    STATE["machine_path"] = machine_path
    STATE["human_path"] = human_path
    STATE["machine_records"] = load_machine_records(machine_path)
    STATE["human_annotations"] = load_human_annotations(human_path)

    # Build page map for complete page context lookups
    page_map = {}
    for r in STATE["machine_records"]:
        key = (r.get("resume_id"), r.get("page_number", 1))
        page_map.setdefault(key, []).append(r)
    STATE["resume_page_map"] = page_map

    # Collect all machine-suggested candidates (preserving document order)
    all_candidates = []
    for r in STATE["machine_records"]:
        if r.get("machine_suggested_heading") is not None:
            all_candidates.append(r)
    
    all_candidates.sort(key=lambda r: (r.get("resume_id"), r.get("page_number", 0), r.get("line_index", 0)))
    STATE["all_candidates"] = all_candidates

    key_map = {}
    for idx, cand in enumerate(all_candidates):
        key_map[make_key(cand)] = idx
    STATE["key_to_candidate_index"] = key_map


def get_first_unannotated_index() -> int:
    all_cands = STATE["all_candidates"]
    human_ann = STATE["human_annotations"]
    for idx, cand in enumerate(all_cands):
        if make_key(cand) not in human_ann:
            return idx
    return 0


def get_candidate_payload(candidate_idx: int) -> dict:
    all_cands = STATE["all_candidates"]
    if not all_cands:
        return {"error": "No candidate records loaded"}
    
    # Clamp index
    candidate_idx = max(0, min(candidate_idx, len(all_cands) - 1))
    target_rec = all_cands[candidate_idx]
    target_key = make_key(target_rec)

    # Fetch page context
    resume_id = target_rec.get("resume_id")
    page_num = target_rec.get("page_number", 1)
    page_lines = STATE["resume_page_map"].get((resume_id, page_num), [])

    # Format lines for UI
    formatted_page_lines = []
    for r in page_lines:
        r_key = make_key(r)
        is_target = (r_key == target_key)
        is_cand = (r.get("machine_suggested_heading") is not None)
        ann = STATE["human_annotations"].get(r_key)
        formatted_page_lines.append({
            "_key": r_key,
            "line_number": r.get("line_number"),
            "line_index": r.get("line_index"),
            "text": r.get("text"),
            "is_target": is_target,
            "is_candidate": is_cand,
            "machine_suggested_heading": r.get("machine_suggested_heading"),
            "machine_suggested_section": r.get("machine_suggested_section"),
            "human_annotation": ann,
        })

    human_ann = STATE["human_annotations"].get(target_key)

    total_candidates = len(all_cands)
    annotated_count = len(STATE["human_annotations"])
    
    return {
        "index": candidate_idx,
        "total_candidates": total_candidates,
        "annotated_count": annotated_count,
        "remaining_count": max(0, total_candidates - annotated_count),
        "percentage_annotated": round((annotated_count / total_candidates * 100) if total_candidates else 0, 1),
        "first_unannotated_index": get_first_unannotated_index(),
        "canonical_sections": CANONICAL_SECTIONS,
        "candidate": {
            "_key": target_key,
            "resume_id": resume_id,
            "page_number": page_num,
            "line_number": target_rec.get("line_number"),
            "line_index": target_rec.get("line_index"),
            "text": target_rec.get("text"),
            "machine_suggested_heading": target_rec.get("machine_suggested_heading"),
            "machine_suggested_section": target_rec.get("machine_suggested_section") or "other",
            "machine_confidence": target_rec.get("machine_confidence"),
            "machine_suggestion_method": target_rec.get("machine_suggestion_method"),
            "machine_review_required": target_rec.get("machine_review_required"),
            "human_annotation": human_ann,
        },
        "page_lines": formatted_page_lines,
    }


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Section Annotation Reviewer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border-color: #334155;
            --accent-primary: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Top Header */
        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title h1 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .badge {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-primary);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .progress-container {
            flex: 1;
            max-width: 450px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .progress-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .progress-bar-bg {
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            height: 8px;
            overflow: hidden;
        }

        .progress-bar-fill {
            background: linear-gradient(90deg, #38bdf8, #22c55e);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
        }

        .nav-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-nav {
            background: #334155;
            color: var(--text-primary);
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-nav:hover {
            background: #475569;
        }

        .jump-input {
            width: 60px;
            background: var(--bg-dark);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 5px 8px;
            border-radius: 6px;
            text-align: center;
            font-size: 0.85rem;
        }

        /* Main Workspace Layout */
        .workspace {
            display: grid;
            grid-template-columns: 1fr 440px;
            flex: 1;
            overflow: hidden;
        }

        /* Page Context Panel */
        .page-panel {
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: #0b1120;
        }

        .panel-header {
            padding: 12px 20px;
            background: rgba(30, 41, 59, 0.5);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .page-content {
            flex: 1;
            overflow-y: auto;
            padding: 24px 32px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .line-row {
            display: flex;
            gap: 16px;
            padding: 4px 12px;
            border-radius: 4px;
            margin-bottom: 2px;
            transition: background 0.1s ease;
        }

        .line-num {
            color: var(--text-muted);
            width: 32px;
            text-align: right;
            user-select: none;
            font-size: 0.8rem;
        }

        .line-text {
            flex: 1;
            white-space: pre-wrap;
            word-break: break-word;
            color: #cbd5e1;
        }

        .line-row.target-candidate {
            background: rgba(245, 158, 11, 0.18);
            border: 1px solid rgba(245, 158, 11, 0.6);
            box-shadow: 0 0 12px rgba(245, 158, 11, 0.15);
        }

        .line-row.target-candidate .line-text {
            color: #fbbf24;
            font-weight: 600;
        }

        .line-row.other-candidate {
            background: rgba(56, 189, 248, 0.06);
            border-left: 3px solid rgba(56, 189, 248, 0.4);
        }

        .line-tag {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 8px;
            font-family: 'Inter', sans-serif;
        }

        .tag-heading {
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.4);
        }

        .tag-rejected {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        /* Control Panel */
        .control-panel {
            background: var(--bg-card);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 20px;
            gap: 20px;
        }

        .card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .card-title {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        .candidate-preview {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.05rem;
            color: #fbbf24;
            background: rgba(245, 158, 11, 0.1);
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #f59e0b;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 0.85rem;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .meta-label {
            color: var(--text-muted);
            font-size: 0.75rem;
        }

        .meta-val {
            color: var(--text-primary);
            font-weight: 500;
        }

        /* Action Buttons */
        .action-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .btn-action {
            padding: 12px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: transform 0.1s ease, filter 0.15s ease;
        }

        .btn-action:active {
            transform: scale(0.98);
        }

        .btn-confirm {
            background: #16a34a;
            color: white;
        }

        .btn-confirm:hover {
            filter: brightness(1.15);
        }

        .btn-reject {
            background: #dc2626;
            color: white;
        }

        .btn-reject:hover {
            filter: brightness(1.15);
        }

        .btn-skip {
            background: #334155;
            color: var(--text-primary);
            grid-column: span 2;
        }

        .btn-skip:hover {
            background: #475569;
        }

        /* Section Selection Grid */
        .section-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }

        .btn-section {
            background: #0f172a;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            text-align: left;
            transition: all 0.15s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .btn-section:hover {
            background: #334155;
            color: var(--text-primary);
            border-color: var(--accent-primary);
        }

        .btn-section.active {
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-primary);
            border-color: var(--accent-primary);
            font-weight: 600;
        }

        .btn-section.suggested {
            box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.6);
        }

        .sec-num {
            font-size: 0.7rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 1px 5px;
            border-radius: 3px;
        }

        /* Keyboard Hints */
        .keyboard-hints {
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            gap: 4px;
            border-top: 1px solid var(--border-color);
            padding-top: 12px;
        }

        .hint-row {
            display: flex;
            justify-content: space-between;
        }

        kbd {
            background: #334155;
            color: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.7rem;
        }

        .status-toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #16a34a;
            color: white;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.2s ease;
            pointer-events: none;
        }

        .status-toast.show {
            opacity: 1;
            transform: translateY(0);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>Section Heading Annotator</h1>
            <span class="badge">NLU Pipeline</span>
        </div>

        <div class="progress-container">
            <div class="progress-labels">
                <span>Progress: <strong id="annotated-text">0 / 0</strong></span>
                <span id="percentage-text">0%</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progress-fill"></div>
            </div>
        </div>

        <div class="nav-controls">
            <button class="btn-nav" id="btn-prev" onclick="navigate(-1)">&larr; Prev</button>
            <input type="number" classjump-input" id="input-index" value="0" min="0" onchange="jumpToIndex(this.value)">
            <span style="font-size: 0.85rem; color: var(--text-muted);" id="max-index-label">/ 0</span>
            <button class="btn-nav" id="btn-next" onclick="navigate(1)">Next &rarr;</button>
        </div>
    </header>

    <div class="workspace">
        <!-- Page View Panel -->
        <div class="page-panel">
            <div class="panel-header">
                <div>
                    <strong id="resume-id-label" style="color: var(--text-primary);">Resume ID</strong>
                    <span id="page-num-label" style="margin-left: 8px;">Page 1</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">
                    Scroll to view complete resume page context
                </div>
            </div>
            <div class="page-content" id="page-lines-container">
                <!-- Lines injected dynamically -->
            </div>
        </div>

        <!-- Annotation Control Panel -->
        <div class="control-panel">
            <div class="card">
                <div class="card-title">Machine Candidate Line</div>
                <div class="candidate-preview" id="cand-text">Loading candidate...</div>
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="meta-label">Suggested Section</span>
                        <span class="meta-val" id="cand-suggested-sec" style="color: var(--accent-primary);">--</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Confidence</span>
                        <span class="meta-val" id="cand-confidence">--</span>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">1. Heading Verdict</div>
                <div class="action-buttons">
                    <button class="btn-action btn-confirm" onclick="submitVerdict(true)">
                        &check; YES, Heading [Y]
                    </button>
                    <button class="btn-action btn-reject" onclick="submitVerdict(false)">
                        &cross; NO, Content [N]
                    </button>
                    <button class="btn-action btn-skip" onclick="skipCandidate()">
                        &rarr; Skip Candidate [S]
                    </button>
                </div>
            </div>

            <div class="card">
                <div class="card-title">2. Select Section Label (if YES)</div>
                <div class="section-grid" id="section-buttons-grid">
                    <!-- Buttons injected dynamically -->
                </div>
            </div>

            <div class="card">
                <div class="card-title">3. Optional Annotator Notes</div>
                <input type="text" id="notes-input" placeholder="e.g. Ambiguous header format" 
                       style="background: #0f172a; border: 1px solid var(--border-color); color: white; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem;">
            </div>

            <div class="keyboard-hints">
                <div class="hint-row"><span>Confirm machine suggestion:</span> <kbd>Y</kbd> or <kbd>Space</kbd></div>
                <div class="hint-row"><span>Reject (not a heading):</span> <kbd>N</kbd> or <kbd>Backspace</kbd></div>
                <div class="hint-row"><span>Skip candidate:</span> <kbd>S</kbd> or <kbd>&rarr;</kbd></div>
                <div class="hint-row"><span>Previous candidate:</span> <kbd>&larr;</kbd></div>
                <div class="hint-row"><span>Quick Section Select:</span> <kbd>1-9</kbd></div>
            </div>
        </div>
    </div>

    <div class="status-toast" id="toast">Annotation Saved</div>

    <script>
        let currentPayload = null;
        let selectedSection = "education";

        async function fetchCandidate(index) {
            try {
                const res = await fetch('/api/candidate?index=' + index);
                const data = await res.json();
                if (data.error) {
                    alert(data.error);
                    return;
                }
                currentPayload = data;
                render();
            } catch (err) {
                console.error("Failed to load candidate", err);
            }
        }

        function render() {
            if (!currentPayload) return;
            const c = currentPayload.candidate;

            // Header progress
            document.getElementById('annotated-text').innerText = `${currentPayload.annotated_count} / ${currentPayload.total_candidates}`;
            document.getElementById('percentage-text').innerText = `${currentPayload.percentage_annotated}%`;
            document.getElementById('progress-fill').style.width = `${currentPayload.percentage_annotated}%`;

            document.getElementById('input-index').value = currentPayload.index;
            document.getElementById('max-index-label').innerText = `/ ${currentPayload.total_candidates - 1}`;

            // Page header
            document.getElementById('resume-id-label').innerText = c.resume_id;
            document.getElementById('page-num-label').innerText = `Page ${c.page_number}`;

            // Render Page Lines
            const linesContainer = document.getElementById('page-lines-container');
            linesContainer.innerHTML = '';
            let targetElem = null;

            currentPayload.page_lines.forEach(line => {
                const row = document.createElement('div');
                let classes = ['line-row'];
                if (line.is_target) classes.push('target-candidate');
                else if (line.is_candidate) classes.push('other-candidate');
                row.className = classes.join(' ');

                let tagHtml = '';
                if (line.human_annotation) {
                    if (line.human_annotation.is_heading) {
                        tagHtml = `<span class="line-tag tag-heading">Heading: ${line.human_annotation.section_label}</span>`;
                    } else {
                        tagHtml = `<span class="line-tag tag-rejected">Not Heading</span>`;
                    }
                } else if (line.is_candidate) {
                    tagHtml = `<span class="line-tag" style="background: rgba(255,255,255,0.06); color: #94a3b8;">Suggested: ${line.machine_suggested_section || 'other'}</span>`;
                }

                row.innerHTML = `
                    <span class="line-num">${line.line_number}</span>
                    <span class="line-text">${escapeHtml(line.text || '(blank)')}</span>
                    ${tagHtml}
                `;
                linesContainer.appendChild(row);

                if (line.is_target) {
                    targetElem = row;
                }
            });

            if (targetElem) {
                targetElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // Candidate Details Card
            document.getElementById('cand-text').innerText = c.text || '(empty line)';
            document.getElementById('cand-suggested-sec').innerText = c.machine_suggested_heading || c.machine_suggested_section;
            document.getElementById('cand-confidence').innerText = c.machine_confidence ? (c.machine_confidence * 100).toFixed(1) + '%' : 'N/A';

            // Pre-select section: human selection if already annotated, else machine suggestion
            if (c.human_annotation && c.human_annotation.section_label) {
                selectedSection = c.human_annotation.section_label;
            } else {
                selectedSection = c.machine_suggested_section || "other";
            }

            if (c.human_annotation && c.human_annotation.annotator_notes) {
                document.getElementById('notes-input').value = c.human_annotation.annotator_notes;
            } else {
                document.getElementById('notes-input').value = '';
            }

            renderSectionGrid();
        }

        function renderSectionGrid() {
            const grid = document.getElementById('section-buttons-grid');
            grid.innerHTML = '';
            const sections = currentPayload.canonical_sections || [];
            const suggested = currentPayload.candidate.machine_suggested_section;

            // Map 1-9 to first 9 sections
            const quickHotkeys = ['1','2','3','4','5','6','7','8','9'];

            sections.forEach((sec, idx) => {
                const btn = document.createElement('button');
                let classes = ['btn-section'];
                if (sec === selectedSection) classes.push('active');
                if (sec === suggested) classes.push('suggested');
                btn.className = classes.join(' ');

                const hk = idx < 9 ? quickHotkeys[idx] : '';
                btn.innerHTML = `
                    <span>${sec}</span>
                    ${hk ? `<span class="sec-num">${hk}</span>` : ''}
                `;
                btn.onclick = () => {
                    selectedSection = sec;
                    renderSectionGrid();
                    // Quick-submit heading with this section
                    submitVerdict(true, sec);
                };
                grid.appendChild(btn);
            });
        }

        async function submitVerdict(isHeading, customSection = null) {
            if (!currentPayload) return;
            const c = currentPayload.candidate;
            const sec = isHeading ? (customSection || selectedSection) : "other";
            const notes = document.getElementById('notes-input').value.strip ? document.getElementById('notes-input').value.strip() : document.getElementById('notes-input').value;

            const payload = {
                key: c._key,
                resume_id: c.resume_id,
                page_number: c.page_number,
                line_number: c.line_number,
                line_index: c.line_index,
                is_heading: isHeading,
                section_label: sec,
                annotator_notes: notes,
            };

            try {
                const res = await fetch('/api/annotate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast(isHeading ? `Saved: Heading (${sec})` : `Saved: Not Heading`);
                    // Advance to next index automatically
                    navigate(1);
                } else {
                    alert("Error saving: " + data.error);
                }
            } catch (err) {
                console.error("Save error", err);
            }
        }

        function skipCandidate() {
            navigate(1);
        }

        function navigate(delta) {
            if (!currentPayload) return;
            let targetIdx = currentPayload.index + delta;
            if (targetIdx >= 0 && targetIdx < currentPayload.total_candidates) {
                fetchCandidate(targetIdx);
            }
        }

        function jumpToIndex(val) {
            let idx = parseInt(val, 10);
            if (!isNaN(idx)) {
                fetchCandidate(idx);
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 1500);
        }

        function escapeHtml(str) {
            return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        // Global Keyboard Event Handling
        document.addEventListener('keydown', (e) => {
            // Ignore if typing in notes input
            if (document.activeElement && document.activeElement.tagName === 'INPUT') {
                return;
            }

            const key = e.key.toLowerCase();
            if (key === 'y' || e.code === 'Space') {
                e.preventDefault();
                submitVerdict(true);
            } else if (key === 'n' || e.code === 'Backspace') {
                e.preventDefault();
                submitVerdict(false);
            } else if (key === 's' || e.code === 'ArrowRight') {
                e.preventDefault();
                skipCandidate();
            } else if (e.code === 'ArrowLeft') {
                e.preventDefault();
                navigate(-1);
            } else if (['1','2','3','4','5','6','7','8','9'].includes(key)) {
                const idx = parseInt(key, 10) - 1;
                const sections = currentPayload ? currentPayload.canonical_sections : [];
                if (sections[idx]) {
                    e.preventDefault();
                    selectedSection = sections[idx];
                    renderSectionGrid();
                    submitVerdict(true, sections[idx]);
                }
            }
        });

        // Initial load: start at first unannotated candidate
        fetch('/api/candidates')
            .then(res => res.json())
            .then(data => {
                const startIndex = data.first_unannotated_index || 0;
                fetchCandidate(startIndex);
            });
    </script>
</body>
</html>
"""


class SectionReviewerHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging in terminal stdout unless error
        pass

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_str: str):
        body = html_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("", "/", "/index.html"):
            self.send_html(INDEX_HTML)
            return

        if path == "/api/candidates":
            total = len(STATE["all_candidates"])
            annotated = len(STATE["human_annotations"])
            self.send_json({
                "total_candidates": total,
                "annotated_count": annotated,
                "first_unannotated_index": get_first_unannotated_index(),
                "canonical_sections": CANONICAL_SECTIONS,
            })
            return

        if path == "/api/candidate":
            idx_str = query.get("index", ["0"])[0]
            try:
                idx = int(idx_str)
            except ValueError:
                idx = 0
            payload = get_candidate_payload(idx)
            self.send_json(payload)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/annotate":
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                self.send_json({"success": False, "error": f"Invalid JSON: {e}"}, 400)
                return

            key = data.get("key")
            if not key or key not in STATE["key_to_candidate_index"]:
                self.send_json({"success": False, "error": "Invalid candidate key"}, 400)
                return

            cand_idx = STATE["key_to_candidate_index"][key]
            rec = STATE["all_candidates"][cand_idx]

            is_heading = bool(data.get("is_heading", False))
            section_label = str(data.get("section_label") or "other")
            notes = str(data.get("annotator_notes") or "")

            try:
                ann = create_annotation_from_machine(
                    rec,
                    is_heading=is_heading,
                    section_label=section_label,
                    annotator_notes=notes,
                    review_state="annotated"
                )
            except Exception as e:
                self.send_json({"success": False, "error": f"Validation failed: {e}"}, 400)
                return

            # Update memory state
            STATE["human_annotations"][ann["_key"]] = ann

            # Persist to disk immediately (NEVER touching machine JSONL file)
            save_human_annotations(STATE["human_path"], STATE["human_annotations"])

            self.send_json({
                "success": True,
                "key": ann["_key"],
                "annotated_count": len(STATE["human_annotations"]),
                "total_candidates": len(STATE["all_candidates"]),
            })
            return

        self.send_response(404)
        self.end_headers()


def run_server(port: int = 8000, host: str = "127.0.0.1", machine_path: Path = DEFAULT_MACHINE_PATH, human_path: Path = DEFAULT_HUMAN_PATH):
    init_state(machine_path, human_path)
    server_address = (host, port)
    httpd = HTTPServer(server_address, SectionReviewerHTTPHandler)
    print("=" * 65)
    print(f"  Resume Section Heading Annotation Dashboard")
    print("=" * 65)
    print(f"  * Machine file: {STATE['machine_path']}")
    print(f"  * Human file:   {STATE['human_path']} ({len(STATE['human_annotations'])} annotations loaded)")
    print(f"  * Candidates:   {len(STATE['all_candidates'])} heading candidates to review")
    print(f"  * Next queue:   Index {get_first_unannotated_index()}")
    print("-" * 65)
    print(f"  Open dashboard in your browser at:")
    print(f"  ==> http://{host}:{port}/")
    print("=" * 65)
    print("Press Ctrl+C to stop the server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server. Annotations safely saved.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=port)
