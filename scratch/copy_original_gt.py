import shutil
from pathlib import Path

src_dir = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser\ground_truth")
dst_dir = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser\data\ground_truth\original_10")

dst_dir.mkdir(parents=True, exist_ok=True)

for p in src_dir.glob("*.json"):
    shutil.copy2(p, dst_dir / p.name)
    print(f"Copied {p.name} to {dst_dir}")

print("Done copying original 10 ground-truth files.")
