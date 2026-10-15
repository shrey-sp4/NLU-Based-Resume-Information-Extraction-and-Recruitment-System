import sys

def read_table(path):
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 4 and parts[3].endswith("%"):
                try:
                    rows[parts[0]] = float(parts[3].rstrip("%"))
                except ValueError:
                    pass
    return rows

before = read_table(sys.argv[1])
after = read_table(sys.argv[2])
print(f"{'FIELD':<38} {'BEFORE':>8} {'AFTER':>8} {'CHANGE':>8}")
drops = 0
for field, b in before.items():
    a = after.get(field)
    if a is None:
        continue
    d = a - b
    flag = ""
    if d < -0.05:
        flag = "  <-- DROP"
        drops += 1
    elif d > 0.05:
        flag = "  up"
    print(f"{field:<38} {b:>8.2f} {a:>8.2f} {d:>+8.2f}{flag}")
print(f"\nFields that dropped: {drops}")