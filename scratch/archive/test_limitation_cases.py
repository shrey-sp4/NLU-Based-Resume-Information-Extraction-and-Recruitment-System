import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")
sys.path.insert(0, str(PROJECT_ROOT))

from src.extract_structured_information import extract_institution

case_a = "2013-2021 Doctor of Philosophy (PhD) in Single Crystal Growth and DFT Pandit Deendayal Energy University Gandhinagar, INDIA"
case_b = "Master of Computer Science (Msc cs) appeared From MakhanLal Chaturvedi Rastriya Patrakarita Avam sanchar Vishwavidhyalay (MCURPV) Bhopal with total agg. 70% in year 2014."

out_a = extract_institution(case_a)
out_b = extract_institution(case_b)

print("=== TEST CASE A ===")
print("Input :", case_a)
print("Output:", repr(out_a))

print("\n=== TEST CASE B ===")
print("Input :", case_b)
print("Output:", repr(out_b))
