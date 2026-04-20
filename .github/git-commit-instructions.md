# Git Commit Message Format

## Language

- **Always write commit messages in English**, including subject and body.
  This applies to every commit regardless of the language used in the
  conversation, the plan files, or the codebase comments.

## Structure

```
<type>(<scope>): <subject>
```

- **type**: required — what kind of change
- **scope**: optional — area of codebase affected
- **subject**: required — imperative mood, lowercase start, no period at end

## Types

| Type | When to use |
|------|-------------|
| `feat` | New feature, new functionality, new endpoint |
| `fix` | Bug fix, correction |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation only (mkdocs, plans, README) |
| `chore` | Maintenance, config, CI, dependencies |

## Scope (optional)

Use parentheses to narrow down the area. Common scopes:

| Scope | Area |
|-------|------|
| `backend` | Backend-only changes |
| `ui` / `frontend` | Frontend-only changes |
| `ui+backend` | Cross-stack changes |
| `docs` | Documentation |
| `docker` | Docker / deployment |
| `tests` | Test infrastructure |
| `phase06` / `phase07` | Roadmap phase reference |
| `phase06-step3` | Step within a phase |
| `fx` / `assets` / `schedule` | Feature domain |
| `plan` | Development plans |

Multiple scopes can be combined: `feat(docker,docs): ...`

## Subject Line Rules

- **Imperative mood**: "add feature" not "added feature"
- **Lowercase** first word (after type/scope prefix)
- **No period** at end
- **Max ~72 chars** for the first line
- Can list multiple changes with ` + ` separator: `fix A + refactor B + update C`
- Can reference specific items with codes: `F1-F8`, `D1-D5`, `H7 H9 H10`
- Can reference plan rounds: `Round 5`, `Round 12`

## Examples

```
feat: complete Phase 6 — Asset Management + Buy Me a Coffee integration
feat(tests): complete coverage debt plan B1-B12 + eliminate all 0% functions
fix(phase06-step4-part0): round 3 — FxCard layout, scoped settings, cross-domain preview
refactor: rename endpoint sync, fix FX bulk invert, reactive provider icons
docs(en): rewrite developer backend docs for Phase 06 asset system
chore: gallery headless default + fix missing nav translations (IT/FR)
feat(ui+backend): UX polish C.5/C.6 + sync modals + ghost signals + logging fix
fix(scheduled-investment): UX polish and bug fixes for asset editor
```

## Multi-line Body (optional)

For complex commits, add a blank line after the subject and a body with details:

```
feat(phase6-step3): Round 5 complete — testing feedback plan ready

- Unified metadata fetch pipeline
- Provider UI improvements
- Icon removal from asset cards
- Distribution editor fixes (9 points addressed)
```

## What NOT to Do

- ❌ Don't start subject with uppercase: `Fix something` → `fix: something`
- ❌ Don't end with period: `fix: something.` → `fix: something`
- ❌ Don't use past tense: `fixed bug` → `fix bug`
- ❌ Don't write generic messages: `update files` → describe what changed
- ❌ Don't write in Italian or any non-English language: `fix: correggi bug` → `fix: correct bug`

