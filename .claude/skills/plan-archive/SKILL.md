---
name: plan-archive
description: "Use this skill when the user needs to verify, cross-link, or archive development plans in the developer journal (a separate local repository beside the code), or tidy the working notes a release left outside it. Covers where the journal lives, the Release_N layout, moving loose notes in, verifying plans against the code before archiving, the move with git mv and the link fixer, the indexes to update, and where the residues go."
---

# Plan Archive Skill

> Verification and archiving of development plans in the developer journal.

## Where the journal is

The journal is its **own local Git repository**, beside the main checkout: `../LibreFolio_developer_journal/`. It has no
remote and is not part of the public repository. From a worktree, reach it with:

```bash
J="$(git rev-parse --path-format=absolute --git-common-dir)/../../LibreFolio_developer_journal"
```

- Every `git mv`, `git add` and `git commit` of an archive runs **inside the journal** (`git -C "$J" …`), on `main`,
  by explicit path. Never in the code repository.
- In coordinated work only the coordinator commits there; a workstream writes its own files and never runs Git in it.
- Record `git rev-parse --short HEAD` and `git status --porcelain` before; verify both after, and report the SHAs.
- Links from the journal to the code no longer resolve (the journal used to live inside the code repo): about a
  thousand old relative links are broken and stay so. Cite code as `path:line` and a commit hash, not as a link.

## Layout (Release_2 onwards)

```
Release_N/
├── Phase_K/                       # ACTIVE: the release in progress (Phase_1 = 1.3, Phase_2 = 1.4, …)
│   ├── README.md                  # live state of the release
│   ├── plan-phaseKK<Release>.prompt.md
│   ├── 00_coordination/           # coordinator papers: kickoff, briefs, plans, recaps, testlists
│   │   └── ondataN/               # one folder per wave
│   └── NN_<theme>/                # one folder per theme / workstream
│       ├── plan-phaseKK<Theme>.prompt.md
│       └── notes/                 # kickoffs (ondataN-kickoff-X.md), checkpoints, analyses
├── Phase_0/BACKLOG_POST_x.y.md    # single backlog index, one line per item, dated sign lines
├── Phase_{K+1}/ATTIVITA_INIZIO_<next>.md   # what the next release starts with
├── Phase_{K+1}/RESIDUO_CLOUD.md   # what only the managed service needs
└── phases/                        # ARCHIVE: original folder names, never renamed
    ├── 00-index.md                # master index: one table row per archived folder
    ├── NN_<stream>/               # archived Phase_0 streams (flat)
    └── Phase_K/NN_<theme>/        # archived folders of a release phase
```

`RoadmapV4_UI/` and older roadmaps are history: same idea, with `phases/phase-NN-subplan/` and plan files grouped by
step. Do not reorganise them.

## Plans: naming and cross-links

| Pattern | Use |
|---|---|
| `plan-phase{NN}{Description}.prompt.md` | main plan |
| `plan-phase{NN}Step{N}{Description}.prompt.md` | step plan |
| `plan-phase{NN}Step{N}Round{N}-{Description}.prompt.md` | bugfix round N |
| `plan-phase{NN}Step{N}Round{N}{Suffix}.prompt.md` | sub-iteration |

A follow-up plan links back at the top (`← Previous: [file](path)`), the original links forward at the bottom
(`→ Follow-up: [file](path)`).

## 1. Bring loose notes in

A release leaves working files outside the journal: in `LibreFolio_prj/` and in `salvataggi-worktrees-*/<wave>/`.

- **Only ours.** Other coordinators (managed service, business plan) leave notes in the same places. A file wholly about
  them stays out. In a mixed file, remove the lines about the managed service: fleet, storage, the founder, customers,
  plans and prices. Replace a removed block with one placeholder line. A plain pointer like "the cloud coordinator is
  told" may stay. Scan with `grep -i -E 'librefolio-cloud|\bfly\b|\bR2\b|\blfc\b|fondatore|clienti|flotta|polar|brevo'`.
- **Destination.** Coordinator files go to `00_coordination/ondataN/`. Workstream kickoffs go to
  `<theme>/notes/ondataN-kickoff-<X>.md`, and checkpoints and analyses go to `<theme>/notes/`. The workstream letter
  decides the theme. When the destination already holds a file with that name, compare the two first: the journal copy
  may be an edited (sanitised) version.
- **Only Markdown.** Logs, test data, `.diff`/`.tar` salvage bundles and helper scripts never go into the journal.
  Report them to the developer with their size; they decide whether to keep, compress or delete them.
- **Live files stay** where the work uses them until the release is tagged: the release closing list, the open
  testlist, issue reply drafts, anything a running gate writes into.
- Add the new files to the coordination README index, then commit in the journal.

## 2. Verify before archiving

A plan's own ✅ is not proof. For every folder, list what its plan or README leaves open, then check the code at the
release head. Give each item one verdict:

| Verdict | Proof |
|---|---|
| **FATTO** | `file:line`, or a commit that is an ancestor of HEAD (`git merge-base --is-ancestor`) |
| **OBSOLETO** | superseded, removed, or decided otherwise: cite where |
| **GIÀ TRACCIATO** | the line in `ATTIVITA_INIZIO_*.md`, `RESIDUO_CLOUD.md` or `TODO_FUTURI.md` |
| **APERTO** | what is missing, in one line |

- Read the backlog index too: each item has dated sign lines under it (✅ closed, ⏭️ next release, ✖️ discarded,
  ⏳ waiting, 🌊 to do, 🌐 translation debt). The **last** line is the item's state.
- Many folders: fan out read-only `Explore` subagents, one per group of folders, with the paths and the verdict table
  above. Subagents write nothing; the coordinator collects. Keep `/tmp` in mind: it is a RAM disk, and a full one
  silently kills every shell, the agents' too.
- Sign every closure found in the backlog: one line under the item, at its end, in the section's format:
  `  ✅ DD/MM (verifica per l'archivio): in dev con \`<hash>\``. The same id can exist in two sections (`B6` of Risk,
  `B6` of I): match the item, not the string, and check each line lands under the right one.

## 3. Archive

A folder moves only when nothing is APERTO. A whole phase moves as `phases/Phase_K/` once every folder of it has.

1. Stamp each plan of the folder under its title:
   `> ✅ **Verificato sul codice e archiviato il DD/MM/YYYY** (\`<branch>\` = \`<hash>\`): …`.
2. Move with Git, inside the journal, so history follows:
   ```bash
   git -C "$J" mv Release_2/Phase_0/41_brokerPnlFlows Release_2/phases/41_brokerPnlFlows
   git -C "$J" mv Release_2/Phase_1/08_email Release_2/phases/Phase_1/08_email
   ```
   For many moves, write a script in the scratchpad (or `/tmp/libreFolio_archive_<x>.sh`) and run it.
3. Fix the relative links of the whole journal with the helper next to this file. It resolves each link from where the
   file was, maps it through the moves, and rewrites it from where the file is now. Links that were already broken
   are listed and left alone: their count must not grow.
   ```bash
   python3 .claude/skills/plan-archive/fix_links.py --journal "$J" \
       --moved Release_2/Phase_1/08_email=Release_2/phases/Phase_1/08_email [--moved …] [--dry-run]
   ```
   Paths written in backticks are text, not links: the helper does not touch them. Grep for the old path afterwards.
4. Update `phases/00-index.md`: one table row per archived folder (what it was, the outcome with a commit, the date),
   and remove its bullet from «Not archived».
5. Commit in the journal by explicit path, one commit per step (notes in, backlog signs, the move).

## 4. Residues

What stays APERTO is not decided by the archiver. Write it into one file in the next phase
(`Phase_{K+1}/DA-DECIDERE-residui-<release>.md`): folder, item, what is missing, a proposal. Proposals are `1.4`
(a line in `ATTIVITA_INIZIO_*`), `cloud` (`RESIDUO_CLOUD.md`), `futuro` (`TODO_FUTURI.md`) or `scarta`. Once the
developer has answered, move each item to its home, sign it in the backlog, and archive the folders that are now
clean.
