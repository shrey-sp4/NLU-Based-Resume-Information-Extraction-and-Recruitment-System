import json
import csv
import re
from pathlib import Path

GT_DIR = Path("ground_truth")
PRED_DIR = Path("output/predictions")
EVAL_DIR = Path("output/evaluation")

def tokenize(text):
    return set(re.findall(r'\b\w+\b', str(text).lower()))

def calc_f1(gt_text, pred_text):
    gt_tokens = tokenize(gt_text)
    pred_tokens = tokenize(pred_text)
    
    if not gt_tokens and not pred_tokens:
        return 1.0, 1.0, 1.0 # Both empty and correctly predicted empty
    if not gt_tokens or not pred_tokens:
        return 0.0, 0.0, 0.0
        
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
    
    # 1. Exact Match on Personal Details
    for field in ["name", "email", "phone"]:
        gt_val = gt.get("personal_details", {}).get(field, "")
        pred_val = pred.get("personal_details", {}).get(field, "")
        exact_match = 1 if str(gt_val).strip() == str(pred_val).strip() else 0
        metrics.append({"section": f"personal_{field}", "exact_match": exact_match, "p": exact_match, "r": exact_match, "f1": exact_match})
        
    # 2. Token Overlap on Standard List Sections
    list_sections = ["summary", "education", "experience", "research_interests", "skills", "projects", "certifications", "responsibilities", "references"]
    for sec in list_sections:
        gt_list = gt.get(sec, [])
        pred_list = pred.get(sec, [])
        
        # Safely convert to string in case GT contains dicts instead of flat strings
        gt_text = " ".join(str(item) for item in (gt_list if isinstance(gt_list, list) else [gt_list]))
        pred_text = " ".join(str(item) for item in (pred_list if isinstance(pred_list, list) else [pred_list]))
        
        p, r, f1 = calc_f1(gt_text, pred_text)
        metrics.append({"section": sec, "exact_match": "", "p": p, "r": r, "f1": f1})
        
    # 3. Token Overlap on Publications (Nested Dictionary)
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

def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    gt_files = sorted(GT_DIR.glob("*.json"))
    
    all_section_metrics = []
    resume_aggregates = []
    
    for gt_path in gt_files:
        pred_path = PRED_DIR / gt_path.name
        
        # Fallback to catch potential filename mismatches between GT and Predictions
        if not pred_path.exists():
            possible_names = [
                gt_path.name.replace(".json", "_sections.json"),
                gt_path.name.replace("_sections.json", ".json"),
                gt_path.stem + "_sections.json",
                gt_path.stem.replace("_sections", "") + ".json"
            ]
            for pname in possible_names:
                if (PRED_DIR / pname).exists():
                    pred_path = PRED_DIR / pname
                    break
                    
        if not pred_path.exists():
            print(f"Missing prediction for {gt_path.name}. Skipping.")
            continue
            
        res_metrics = evaluate_resume(gt_path, pred_path)
        
        f1_scores = [m['f1'] for m in res_metrics]
        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0
        
        resume_aggregates.append({
            "resume": gt_path.name,
            "average_f1": round(avg_f1, 4)
        })
        
        for m in res_metrics:
            all_section_metrics.append({
                "resume": gt_path.name,
                "section": m["section"],
                "exact_match": m["exact_match"],
                "precision": round(m["p"], 4),
                "recall": round(m["r"], 4),
                "f1_score": round(m["f1"], 4)
            })

    if not resume_aggregates:
        print("No evaluation metrics could be calculated. Check your prediction files.")
        return

    # Save section_metrics.csv
    with open(EVAL_DIR / "section_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume", "section", "exact_match", "precision", "recall", "f1_score"])
        writer.writeheader()
        writer.writerows(all_section_metrics)

    # Save resume_metrics.csv
    with open(EVAL_DIR / "resume_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["resume", "average_f1"])
        writer.writeheader()
        writer.writerows(resume_aggregates)
        
    # Calculate and save overall_metrics.csv
    overall_f1 = sum(r["average_f1"] for r in resume_aggregates) / len(resume_aggregates) if resume_aggregates else 0
    with open(EVAL_DIR / "overall_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Score"])
        writer.writerow(["System Average F1", round(overall_f1, 4)])

    print(f"Evaluation finished! CSVs saved to {EVAL_DIR}")

if __name__ == "__main__":
    main()