import glob, json, os, subprocess

for path in sorted(glob.glob("output/predictions/*.json")):
    rel = path.replace("\\", "/")
    r = subprocess.run(["git", "show", "HEAD:" + rel], capture_output=True, encoding="utf-8")
    if r.returncode:
        continue
    old = json.loads(r.stdout)["personal_details"]["name"]
    with open(path, encoding="utf-8") as f:
        new = json.load(f)["personal_details"]["name"]
    if old != new:
        print(f"{os.path.basename(path)[:34]:<34} {old!r} -> {new!r}")