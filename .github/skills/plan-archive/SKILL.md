---
name: plan-archive
description: "Use this skill when the user needs to verify, cross-link, or archive development plans. Covers plan naming conventions, cross-linking between plans, archiving completed plan chains into phases/, and updating README indexes."
---

# Plan Archive Skill

> Verification and archiving of development plans in `LibreFolio_developer_journal/`.

## Workflow Overview

```
Plan → Execute → [Repeat: BugfixPlan + Execute] → Debug → Archive
```

## File Naming Convention

Plans follow an ordered naming scheme encoding phase, step, iteration, and bugfix round:

| Pattern | Example | Use |
|---------|---------|-----|
| `plan-phase{NN}{Description}.prompt.md` | `plan-phase06Assets.prompt.md` | Main phase plan |
| `plan-phase{NN}Step{N}{Description}.prompt.md` | `plan-phase06Step3AssetModal.prompt.md` | Step-level plan |
| `plan-phase{NN}BugfixMigration.prompt.md` | `plan-phase06BugfixMigration.prompt.md` | Bugfix iteration |
| `plan-phase{NN}Step{N}Round{N}-{Description}.prompt.md` | `plan-phase06Step3Round6-LayoutPolish.prompt.md` | Bugfix round N |
| `plan-phase{NN}Step{N}Round{N}{Suffix}.prompt.md` | `plan-phase06BugfixMigration-part3b.prompt.md` | Sub-iteration |
| `plan-phase{NN}Step{N}Round{N}-checklist-{Description}.md` | `checklist-F9-MergeSplitTest.md` | Verification checklist |

## Cross-Linking Rules

When a plan spawns a follow-up:
1. **Original plan**: add a forward link at the bottom → `→ Follow-up: [filename](path)`
2. **New plan**: add a back link at the top → `← Previous: [filename](path)`

## Verification Checklist (before archiving)

1. ✅ All plans in the chain have status ✅ (completed)
2. ✅ Cross-links are present and correct (forward + backward)
3. ✅ File naming follows the convention above
4. ✅ No orphan plans (every bugfix plan links back to its parent)

## Archiving Procedure

When a phase is complete:

1. **Create phase summary** (if not exists):
   ```
   phases/phase-{NN}-{name}.md
   ```

2. **Create subplan directory**:
   ```
   phases/phase-{NN}-subplan/
   ```

3. **Move all plan files** from `RoadmapV4_UI/` into `phases/phase-{NN}-subplan/`, grouped by step:
   ```
   phases/phase-{NN}-subplan/
   ├── README.md                    # Index table with all sub-plans
   ├── Bugfix-Step{N}/              # Plans grouped by step
   │   ├── plan-phase{NN}...md
   │   └── checklist-...md
   └── ...
   ```

   **ALWAYS use `git mv` (never plain `mv` or `cp`+`rm`)** so git follows the
   rename and `git log --follow` keeps tracking the file across the archive.
   Move-and-fix should always be a single atomic preparation:

   ```bash
   # 1. Move with git so history is preserved
   git mv plan-phaseNN-Foo.prompt.md \
          phases/phase-NN-subplan/StepX/plan-phaseNN-Foo.prompt.md
   ```

   For multi-file moves write the operations to a temporary script under
   `/tmp/libreFolio_archive_phaseNN.sh` (per the global "long commands"
   rule) — easier to review, replay, and keeps the terminal log readable.

4. **Fix relative cross-links after move**. The path delta is mechanical:
   the file gains 2 extra `../` levels (`RoadmapV4_UI/` → `RoadmapV4_UI/phases/phase-NN-subplan/StepX/`).
   Targets that need rewriting:

   | Old (from `RoadmapV4_UI/`) | New (from `phase-NN-subplan/StepX/`) |
   |----------------------------|--------------------------------------|
   | `./other-plan.md` (sibling now in same StepX) | `./other-plan.md` (unchanged) |
   | `./other-plan.md` (sibling now in different StepY) | `../StepY/other-plan.md` |
   | `./phases/phase-NN-…md` | `../../phase-NN-…md` |
   | `../phase-NN-…md` (already under `phases/`) | `../../phase-NN-…md` |
   | `../../TODO_FUTURI.md` (project root) | `../../../../../TODO_FUTURI.md` |
   | `../../../backend/…` (project source) | add 2 more `../` |

   Use a `/tmp/libreFolio_fix_phaseNN_links.sh` helper with `sed -i ''` (BSD
   sed on macOS). Validate at the end with a Python one-liner that walks the
   archived folder and `os.path.normpath()`-resolves every `](./…)` and
   `](../…)` link, printing the broken ones. Code references (`backend/…`)
   that were *already broken before the move* are noise — leave them.

5. **Create/update README.md** in the subplan directory with a table:
   ```markdown
   | File | Step | Description | Status |
   |------|------|-------------|--------|
   | `plan-phase06Step3Round12...md` | Step 3 | Round 12 — ... | ✅ |
   ```

6. **Update master index** at `phases/00-index.md` with the new phase entry.

7. **Update phase summary** at `phases/phase-{NN}-{name}.md` to mark the
   archived parts/steps as ✅ and add a `**Sub-plans archiviati**` link to
   the new `phase-{NN}-subplan/README.md`.

## Directory Structure

```
LibreFolio_developer_journal/
├── RoadmapV4_UI/
│   ├── phases/                    # Archived completed phases
│   │   ├── 00-index.md            # Master index
│   │   ├── phase-{NN}-{name}.md   # Phase summary
│   │   └── phase-{NN}-subplan/    # All sub-plans for the phase
│   └── plan-*.md                  # Active (in-progress) plans
└── knowledge_base/                # Project reference docs
```

## Common Commands

```bash
# List all active plans (not yet archived)
ls LibreFolio_developer_journal/RoadmapV4_UI/plan-*.md

# List archived phases
ls LibreFolio_developer_journal/RoadmapV4_UI/phases/

# Check a phase's sub-plans
cat LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/README.md
```

