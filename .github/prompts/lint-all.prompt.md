---
description: "Run ruff lint + black format on the entire backend codebase"
---

# Lint & Format All Backend

Use the `lint-format` skill for rules and pitfalls.

## Steps

1. Run ruff statistics to see current state:
   ```
   python -m ruff check backend/ --statistics > /tmp/ruff_stats.txt 2>&1
   ```
2. Read `/tmp/ruff_stats.txt` and report the error breakdown
3. Apply safe auto-fixes:
   ```
   python -m ruff check backend/ --fix
   ```
4. Run black on the whole backend:
   ```
   python -m black backend/
   ```
5. Re-check remaining issues:
   ```
   python -m ruff check backend/ --statistics > /tmp/ruff_remaining.txt 2>&1
   ```
6. Read `/tmp/ruff_remaining.txt`
7. For each remaining error category, fix file by file:
   - **B904**: add `from e` or `from None` to raises in except blocks
   - **F841**: remove or prefix unused variables with `_`
   - **B007**: rename unused loop vars to `_var`
   - **PLC0415**: move imports to top-level or add `# noqa: PLC0415` if circular
   - **B023**: bind loop variables in lambdas with default args
   - Other: follow the skill guide
8. Final verification:
   ```
   python -m ruff check backend/ --statistics > /tmp/ruff_final.txt 2>&1
   ```
9. Report summary: errors before → after, files changed

