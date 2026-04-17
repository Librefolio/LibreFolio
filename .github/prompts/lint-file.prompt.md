---
description: "Run ruff lint + black format on a specific backend Python file"
---

# Lint & Format a Single File

Use the `lint-format` skill for rules and pitfalls.

## Steps

1. Run ruff on the file, saving output to `/tmp/ruff_out.txt`:
   ```
   python -m ruff check <file> > /tmp/ruff_out.txt 2>&1
   ```
2. Read `/tmp/ruff_out.txt` and analyze the errors
3. Apply safe auto-fixes:
   ```
   python -m ruff check <file> --fix
   ```
4. Fix remaining manual issues (B904, B023, F841, PLC0415, etc.) following the skill guide
5. Run black:
   ```
   python -m black <file>
   ```
6. Re-verify ruff (black may reformat lines that re-trigger issues):
   ```
   python -m ruff check <file> > /tmp/ruff_verify.txt 2>&1
   ```
7. Verify Python syntax:
   ```
   python -c "import ast; ast.parse(open('<file>').read()); print('OK')"
   ```
8. Report what was fixed

