import json
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

GT_DIR = Path("ground_truth")
PRED_DIR = Path("output/predictions")
EVAL_DIR = Path("output/evaluation")

NAME_MATCH_FLOOR = 0.5

def tokenize(text):
    return set(re.findall(r'\b\w+\b', str(text).lower()))

def normalize_email(email):
    return str(email).strip().lower()

def normalize_phone(phone):
    digits = re.sub(r'\D', '', str(phone))
    return digits[-10:] if len(digits) >= 10 else digits

def score_name(gt_name, pred_name):
    gt_norm = str(gt_name).strip().lower()
    pred_norm = str(pred_name).strip().lower()
    if not gt_norm and not pred_norm: return 1.0
    if not gt_norm or not pred_norm: return 0.0
    ratio = SequenceMatcher(None, gt_norm, pred_norm).ratio()
    return ratio if ratio >= NAME_MATCH_FLOOR else 0.0

def score_exact_normalized(gt_val, pred_val, normalizer):
    gt_norm = normalizer(gt_val)
    pred_norm = normalizer(pred_val)
    if not gt_norm and not pred_norm: return 1.0
    if not gt_norm or not pred_norm: return 0.0
    return 1.0 if gt_norm == pred_norm else 0.0

def calc_f1(gt_text, pred_text):
    gt_tokens = tokenize(gt_text)
    pred_tokens = tokenize(pred_text)
    if not gt_tokens and not pred_tokens: return 1.0, 1.0, 1.0
    if not gt_tokens or not pred_tokens: return 0.0, 0.0, 0.0
    tp = len(gt_tokens.intersection(pred_tokens))
    fp = len(pred_tokens - gt_tokens)
    fn = len(gt_tokens - pred_tokens)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return precision, recall, f1

def evaluate_resume(gt_file, pred_file):
    with open(gt_file, 'r', encoding='utf-8') as f: gt = json.load(f)
    with open(pred_file, 'r', encoding='utf-8') as f: pred = json.load(f)
    metrics = []
    
    personal_scorers = {
        "name": lambda g, p: score_name(g, p),
        "email": lambda g, p: score_exact_normalized(g, p, normalize_email),
        "phone": lambda g, p: score_exact_normalized(g, p, normalize_phone),
    }
    for field, scorer in personal_scorers.items():
        gt_val = gt.get("personal_details", {}).get(field, "")
        pred_val = pred.get("personal_details", {}).get(field, "")
        exact_match = 1 if str(gt_val).strip() == str(pred_val).strip() else 0
        score = scorer(gt_val, pred_val)
        metrics.append({"section": f"personal_{field}", "exact_match": exact_match, "p": score, "r": score, "f1": score})
        
    list_sections = ["summary", "education", "experience", "research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
    for sec in list_sections:
        gt_list = gt.get(sec, [])
        pred_list = pred.get(sec, [])
        gt_text = " ".join(str(item) for item in (gt_list if isinstance(gt_list, list) else [gt_list]))
        pred_text = " ".join(str(item) for item in (pred_list if isinstance(pred_list, list) else [pred_list]))
        p, r, f1 = calc_f1(gt_text, pred_text)
        metrics.append({"section": sec, "exact_match": "", "p": p, "r": r, "f1": f1})
        
    gt_pubs = gt.get("publications", {})
    pred_pubs = pred.get("publications", {})
    for pub_type in ["journal_articles", "conference_papers", "conference_proceedings", "communications", "book_chapters", "books", "technical_reports", "preprints"]:
        gt_pub_list = gt_pubs.get(pub_type, []) if isinstance(gt_pubs, dict) else []
        pred_pub_list = pred_pubs.get(pub_type, []) if isinstance(pred_pubs, dict) else []
        gt_text = " ".join(str(item) for item in (gt_pub_list if isinstance(gt_pub_list, list) else [gt_pub_list]))
        pred_text = " ".join(str(item) for item in (pred_pub_list if isinstance(pred_pub_list, list) else [pred_pub_list]))
        p, r, f1 = calc_f1(gt_text, pred_text)
        metrics.append({"section": f"publications_{pub_type}", "exact_match": "", "p": p, "r": r, "f1": f1})
        
    return metrics

def normalize_filename(filename):
    name = filename.lower().replace(".json", "").replace("_sections", "")
    return re.sub(r'[^a-z0-9]', '', name)

def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    gt_files = sorted(GT_DIR.glob("*.json"))
    
    all_section_metrics = []
    resume_aggregates = []
    available_preds = {normalize_filename(p.name): p for p in PRED_DIR.glob("*.json")}
    
    for gt_path in gt_files:
        norm_gt_name = normalize_filename(gt_path.name)
        if norm_gt_name in available_preds:
            pred_path = available_preds[norm_gt_name]
        else:
            continue
            
        res_metrics = evaluate_resume(gt_path, pred_path)
        f1_scores = [m['f1'] for m in res_metrics]
        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0
        
        resume_aggregates.append({"resume": gt_path.name, "average_f1": round(avg_f1, 4)})
        for m in res_metrics:
            all_section_metrics.append({"resume": gt_path.name, "section": m["section"], "exact_match": m["exact_match"], "precision": round(m["p"], 4), "recall": round(m["r"], 4), "f1_score": round(m["f1"], 4)})

    with open(EVAL_DIR / "section_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume", "section", "exact_match", "precision", "recall", "f1_score"])
        writer.writeheader()
        writer.writerows(all_section_metrics)
    with open(EVAL_DIR / "resume_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume", "average_f1"])
        writer.writeheader()
        writer.writerows(resume_aggregates)
        
    overall_f1 = sum(r["average_f1"] for r in resume_aggregates) / len(resume_aggregates) if resume_aggregates else 0
    with open(EVAL_DIR / "overall_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Score"])
        writer.writerow(["System Average F1", round(overall_f1, 4)])
    print(f"Evaluation finished! CSVs successfully updated and saved to {EVAL_DIR}")

if __name__ == "__main__":
    main()