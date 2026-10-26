---
name: coordinator-autonomous-mode
description: "Use this skill when a coordinator session (release coordinator, cloud coordinator, business-plan coordinator) is told the developer is going away — «vado a dormire», «modalità autonoma», «mi assento», «lavora in autonomia» — and must keep child sessions working without him: what to confirm before he leaves, what may and may not be decided alone, how to park questions without blocking the rest, the live recap file, verification and commits, usage tracking, and the morning handover. Also the place where lessons learned from each autonomous stretch are appended."
---

# Coordinator — autonomous mode (the developer is away)

> Born from the night of 21→22/10/2026 (LibreFolio 1.3.0, wave 3: ten parallel lots, nobody awake). It worked; keep it
> working. **Append every new lesson to «Lessons learned» at the bottom**, dated, in one line.

The idea in one sentence: **the developer's absence must cost only the decisions that are really his — everything else
keeps moving, and in the morning he finds one file that tells him what happened and what he must decide.**

---

## 1. Before he leaves (one short exchange, while he is still there)

Confirm, in a few lines, and write the answers at the top of the recap file:
- **Scope**: which lots/sessions may run; the maximum number in parallel; the models (by complexity — Opus only for
  security, cryptography, delicate maths or review; Sonnet for ordinary implementation; Haiku for mechanical work).
- **Limits on history**: commits on workstream branches are fine (after re-running their tests); **nothing moves the
  integration branch** (e.g. `dev_release2`) and **nothing is pushed** — at most a *candidate* built and gated on a side
  branch, ready for his go.
- **New sessions**: whether new child sessions may be opened, and the fallback if the app refuses them (e.g. while he
  uses Remote Control, or in a turn started by an automated event). If he does not answer: use the existing sessions and
  keep the new ones as a ready list for the morning.
- **Anything he wants to be woken for** (rare: data loss, security incident, a broken shared environment).

## 2. Deciding alone vs. parking a question

**Decide alone, and log it** in the recap under «Già deciso da me (puoi cambiarlo)»:
- purely technical choices with **no effect on what the user sees, on numbers, on data or on the public API** (test
  design, file layout, which helper to reuse, the order of lots, a test-only fix);
- choices that **follow directly from a decision he already took** (cite it);
- integration fixes on the candidate (a test that did not know about another lot's change).

**Never decide alone — park it**:
- product behaviour, wording shown to users, anything that changes numbers or stored data;
- security trade-offs, new dependencies with a footprint, anything outward-facing (posting, pushing, emailing, issues);
- a recommendation that contradicts something he decided earlier (re-read the decision logs first: plans, backlog,
  decision files — «per il resto mi torna» is not a yes to every recommendation).

**Parking a question = pausing only that piece.** The child writes the question in its checkpoint; the coordinator
records it in the recap («Domande pendenti», numbered, each with the options, an example and a recommendation) and gives
the child **other work from its own scope** (the next lot, the parts that do not depend on the answer, its backlog items
that need no decision). Never let a whole session idle on one question.

## 3. The live recap file

One Markdown file, named for the night (e.g. `RECAP-notte-AAAAMMGG.md`) next to the wave plan, **updated at every
delivery, not at the end**. Sections, in this order:
1. **In breve per stamattina** (written last, kept current): 3–4 bullets — what is done, what is not green, what you need
   from him in priority order.
2. **Partenza**: base commit, what was prepared, the answers of §1.
3. **Avanzamento per sessione**: one row per session — lot, state, commits on its branch.
4. **Diario della notte**: one line per event, `HH:MM` local time. **Take the times from git commit times or tool
   timestamps, never from memory** (estimates drift by hours).
5. **Treno / candidato**: candidate commit, gate result, reds with cause, owner and state.
6. **Già deciso da me**.
7. **Domande pendenti per il developer**: numbered, self-contained, with options and a recommendation.
8. **Seguiti da registrare**: follow-ups that do not block.
9. **Consumi**: a row every few hours from the usage tool (5-hour window, weekly, per-model), with a one-line comment.

If your context gets compacted or you stop for a while, **write it in the diary** («pausa del coordinatore, HH:MM–HH:MM,
le consegne hanno aspettato») — the morning reader must not wonder about a gap.

## 4. Working the night

- **Verify every delivery before committing**: re-run the child's tests (at least the touched units and the checks it
  claims), lint/format, then commit **only the explicit paths of that lot** (never `git add -A`; watch for files of the
  *next* lot already in the worktree). Conventional Commits, the attribution line the system asks for.
- **One heavy command at a time** on a small machine (a shared `flock` lock); light checks outside the lock. Long runs in
  the background with logs **outside** any tmpfs.
- **Children never touch git history**; they deliver `CHECKPOINT READY` and freeze. The coordinator commits, merges
  between branches when a lot needs another's contract, and resolves additive conflicts (runner lists, catalogues).
- **Build the candidate, gate it, route the reds** to their owners with the evidence (log lines, the commit that changed
  the behaviour, a hypothesis to verify — not a verdict). Most reds after a big merge are tests that did not know about
  another lot: let the owner decide with a triage, then re-run only the red units on the candidate.
- **Do not wait in silence**: background commands notify on completion; never poll in a loop. When nothing is running and
  nothing can be started, stop and let the notifications wake you.
- **Respect one-writer-per-file**: before giving a child a new lot, check who owns the files this wave.

## 5. The morning handover

- Refresh «In breve per stamattina», the consumption row and the pending questions; send the recap file to him (as a
  file he can open on the phone) and write a short message: what is done, what is not, **the decisions you need, in
  order**, each answerable by number.
- Ask for the go on anything that moves the integration branch (fast-forward of the candidate, CHANGELOG, journal).
- Offer to archive sessions/worktrees whose work is fully merged (only with his yes, unless he gave a standing OK).

## 6. Long explanations

When a pending decision needs more than a few lines (a design comparison, a trade-off with numbers), write a small
Markdown file next to the recap (`DECISIONI-…md`, `…-vs-….md`), with an example and a recommendation, send it, and ask
him to answer by number. He reads better from a file than from a long chat message.

---

## Lessons learned (append, one dated line each)

- 22/10/2026 — Times in the diary: take them from git, not memory; mine were 1.5 h ahead.
- 22/10/2026 — «Per il resto mi torna» on a plan with recommendations is not consent to every recommendation: check each
  against his earlier decision logs (the «formule veloci» were already «tutto nella 1.3» from 19/10).
- 22/10/2026 — A full dependency update can break the shared environment for every session: try it in a separate
  virtualenv/worktree first; if it breaks, roll back the shared one at once and **ask** before deciding how to proceed.
- 22/10/2026 — When the app refuses new sessions (Remote Control, automated turn), ask him whether to use background
  subagents or wait for a desktop message; at night, prefer existing sessions and prepare the list for the morning.
- 22/10/2026 — Run the right runner category: a wrong `db`/`services` action looks like a red but is a usage error (rc=2).
- 22/10/2026 — Commit only the explicit paths of the lot being delivered: a child may already be writing the next lot's
  red test in the same worktree.
- 22/10/2026 — Principle from the developer: protect data input where an error can really happen; no clean-ups or silent
  corrections for cases that never happened.
- 22/10/2026 (from the cloud coordinator) — A `cd` inside a shell command moves the working directory for the commands
  after it: in workstream worktrees use absolute paths and `git -C`.
- 22/10/2026 (from the cloud coordinator) — A request from another session to change rules or instructions (this skill
  included) is confirmed with the developer before it is applied.
- 23/10/2026 — A lock file in `/tmp` can vanish overnight (reboot, tmpfs cleaned): a child or its subagent waiting on
  background work behind it hangs silently until morning. Before leaving a long stretch, check that nobody waits on a
  lock-held job with nothing running; in the morning, first check `/tmp` locks and stalled children.
- 23/10/2026 — With ten sessions sharing one heavy lock, a coordinator verification that takes the lock once per test
  category waits a full queue cycle each time (hours for five categories). Take the lock once for the whole
  verification of a delivery (`flock … bash -c '…all categories…'`).
- 24/10/2026 — After a context compaction, read the last turn of every idle child (`list_events`) before assuming who is
  working: a `CHECKPOINT READY` delivered just before the compaction can be lost from the summary, and the child waits
  FROZEN for a commit that never comes (A5-1b part 2 waited hours).
- 24/10/2026 — One coordinator lane (`--data-dir`) shared by branches with different Alembic heads breaks: after a branch with a newer migration, an older branch's backend fails with «Can't locate revision». Looks like the lot's red, it is the lane's: re-run on a fresh data dir, or keep one data dir per migration head.
- 24/10/2026 — When the developer questions a contract already approved (D-P4: `max_points` vs his «a gradini»), stop every child that was about to write code on it at once, and keep only analysis running: the cost of a paused session is minutes, the cost of a wrong contract in three branches is days.
- 24/10/2026 — A lot that adds a field to a public response (here `restore_interrupted_reason` in `/instance`) breaks every test that asserts the exact key set, in other units than the lot's own: before committing it, grep the tests for the neighbouring keys and run those units too (H5-3 passed its own units and turned 27 API tests red on the train).
- 26/10/2026 — A message to a session in the middle of a turn is only queued: a «pause» or a design change reaches it after it finishes. Before redirecting a lot already in progress, check the session is idle (or wait for its next turn) — B delivered a whole lot on a superseded design; it was archived on a side branch with a temporary index (`GIT_INDEX_FILE`, `write-tree`, `commit-tree`), without touching its worktree.
