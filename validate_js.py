"""Basic JS syntax validator - checks balanced brackets, braces, parens, quotes"""
import re

with open('script_0.js', encoding='utf-8') as f:
    js = f.read()

# Remove strings and comments to avoid false positives
# Simple approach: track line numbers with issues

errors = []
lines = js.split('\n')
paren = 0
brace = 0
bracket = 0

# Track string state
in_single = False
in_double = False
in_backtick = False
prev_char = ''

for i, line in enumerate(lines, 1):
    for j, ch in enumerate(line):
        if in_single:
            if ch == "'" and prev_char != '\\':
                in_single = False
        elif in_double:
            if ch == '"' and prev_char != '\\':
                in_double = False
        elif in_backtick:
            if ch == '`' and prev_char != '\\':
                in_backtick = False
        else:
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == '`':
                in_backtick = True
            elif ch == '(':
                paren += 1
            elif ch == ')':
                paren -= 1
            elif ch == '{':
                brace += 1
            elif ch == '}':
                brace -= 1
            elif ch == '[':
                bracket += 1
            elif ch == ']':
                bracket -= 1
        
        if paren < 0:
            errors.append(f"Line {i}: Extra closing paren ')' ")
            paren = 0
        if brace < 0:
            errors.append(f"Line {i}: Extra closing brace '}}' ")
            brace = 0
        if bracket < 0:
            errors.append(f"Line {i}: Extra closing bracket ']' ")
            bracket = 0
        
        prev_char = ch

if paren != 0:
    errors.append(f"Unbalanced parens: {paren} unclosed")
if brace != 0:
    errors.append(f"Unbalanced braces: {brace} unclosed")
if bracket != 0:
    errors.append(f"Unbalanced brackets: {bracket} unclosed")
if in_single:
    errors.append("Unclosed single quote string")
if in_double:
    errors.append("Unclosed double quote string")
if in_backtick:
    errors.append("Unclosed backtick template")

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print(f"  {e}")
else:
    print("All balanced - no syntax errors detected")
