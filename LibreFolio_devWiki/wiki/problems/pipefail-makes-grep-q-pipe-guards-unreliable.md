---
title: "Under `set -o pipefail`, `if ! producer | grep -q X` can fire although X is there: grep -q exits early and the producer dies of SIGPIPE"
category: problem
status: accepted
date: 2026-11-07
tags: [shell, bash, ci, scripts, pipefail, sigpipe]
related:
  - concepts/ci-release-pipeline
---

# Problem: `pipefail` makes `if ! … | grep -q` guards unreliable

## Symptom

A shell guard of the form

```bash
set -euo pipefail
if ! producer | grep -q "$expected"; then echo "missing $expected"; exit 1; fi
```

reports `missing` and stops a script **even though the producer's output contains the text**, and only sometimes:
with a short output it passes, with a long one it fails. Listed by the coordinator among the problems of the 1.3
closing (07/11/2026); no incident is recorded in the repository, and the release workflow already uses the safe form.

## Root cause

`grep -q` exits with 0 at the **first** match and closes the pipe. If the producer is still writing, its next write
gets `SIGPIPE` and it exits with 141. Without `pipefail` the pipeline's status is grep's (0, found). With `pipefail` the
status is the last non-zero one, 141, so the pipeline «fails», and `!` turns that failure into «not found». Whether it
happens depends on timing and on how much the producer still had to write: a race, not a logic error.

It is the same family as the rule in `CLAUDE.md` about `tee` followed by `head` or `grep -m`: a consumer that stops
reading early kills the writer, silently.

## Solution

Never put an early-exiting reader (`grep -q`, `grep -m`, `head`) after a producer in a guard under `pipefail`. Capture
first, then test:

```bash
manifest="$(docker buildx imagetools inspect "$tag")"
if ! grep -q "$platform" <<<"$manifest"; then …; fi
```

The release workflow's manifest check (`linux/amd64` and `linux/arm64` in every tag) is written this way since it was
introduced (`dd05157bf`, 23/10/2026).

## Prevention

- In a `pipefail` script, a pipeline used as a condition ends with a reader that reads to the end, or the producer's
  output is captured into a variable or a file first.
- Alternatively `grep -c … >/dev/null` or `grep … >/dev/null` (no `-q`) reads everything, at the cost of reading it.

## Impact

It would produce false alarms in guard scripts; no product impact.

## Source files

| Role | Path |
|------|------|
| Safe form: capture, then here-string | `.github/workflows/release.yml` |
| Scripts that run under `pipefail` | `scripts/visual_review/gallery_snapshot.sh`, `scripts/visual_review/designer_live.sh` |
