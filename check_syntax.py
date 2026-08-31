import re, sys

with open('backend/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract inline script
m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if not m:
    print("No script found!")
    sys.exit(1)

js = m.group(1)

# Check for the T object - look for mismatched quotes
# Find the T object boundaries
t_start = js.find('const T={')
if t_start == -1:
    print("No T object found")
else:
    # Find closing } of T
    depth = 0
    t_end = t_start
    for i in range(t_start, len(js)):
        if js[i] == '{':
            depth += 1
        elif js[i] == '}':
            depth -= 1
            if depth == 0:
                t_end = i + 1
                break
    
    t_obj = js[t_start:t_end]
    print(f"T object length: {len(t_obj)} chars")
    
    # Check each language section for quote balance
    # Split by language keys
    lang_sections = re.split(r"(?:en|hi|as|bn|mni):{", t_obj)
    for i, sec in enumerate(lang_sections[:6]):
        sq = sec.count("'")
        dq = sec.count('"')
        print(f"  Section {i}: single={sq} double={dq} (single odd={sq%2})")

# Check the full script for obvious syntax issues
# Look for lines with obviously broken strings
lines = js.split('\n')
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    # Check for lines where a single-quoted string might be broken
    # by an unescaped single quote inside
    if stripped.startswith("history_title") or "history_title" in stripped:
        print(f"Line {i}: {stripped[:200]}")

print("\nDone checking.")
