import re, sys

with open('backend/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if not m:
    print('NO SCRIPT FOUND')
    sys.exit(1)

js = m.group(1)

# Check for </script> inside script
if '</script>' in js.lower():
    print('FATAL: </script> found inside script block!')

# Track string state to ignore parens/braces inside strings
balance = {'(': 0, '{': 0, '[': 0}
in_str = None  # None, "'", '"', '`'
escape = False
line_num = 1

for i, ch in enumerate(js):
    if ch == '\n':
        line_num += 1

    if escape:
        escape = False
        continue

    if ch == '\\' and in_str:
        escape = True
        continue

    if in_str:
        if ch == in_str:
            in_str = None
        continue

    if ch in ("'", '"', '`'):
        in_str = ch
        continue

    if ch in balance:
        balance[ch] += 1
    elif ch in (')', '}', ']'):
        close_to_open = {')': '(', '}': '{', ']': '['}
        key = close_to_open[ch]
        balance[key] -= 1
        if balance[key] < 0:
            print(f'EXTRA {ch} at line {line_num}, char {i}')
            context = js[max(0, i-60):i+30]
            # Show the line
            print(f'Context: ...{repr(context)}...')

print(f'Final balances: {balance}')
print(f'Paren: {balance["("]}, Brace: {balance["{"]}, Bracket: {balance["["]}')

if all(v == 0 for v in balance.values()):
    print('ALL BALANCED - JS should parse OK')
else:
    print('IMBALANCED - JS will have parse errors!')
