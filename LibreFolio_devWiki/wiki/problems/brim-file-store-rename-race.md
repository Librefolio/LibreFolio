---
title: "BRIM file store: the path is derived from the sidecar while the file is being renamed"
category: problem
status: resolved
date: 2026-08-29
tags: [backend, brim, filesystem, races, atomicity, parallelism]
related: [concepts/load-only-red-is-a-product-defect]
---

# Problem: `[Errno 2] No such file or directory` on a file that exists

## Symptom

Under a parallel run, BRIM file operations intermittently failed with
`[Errno 2] No such file or directory` on a path that was correct a moment
earlier and correct again a moment later.

## Root cause

Two writers, one derived value.

`get_file_path()` computes the folder from the **content** of the sidecar
metadata (`file_info.status`). `_move_file()` renames the **data file first** and
rewrites the sidecar **afterwards**. Between those two steps the sidecar still
describes the old status, so any concurrent `get_file_path()` computes a path
that no longer holds a file.

The window is small and entirely invisible at one worker.

## A second, independent atomicity hole in the same store

BRIM metadata writes were a plain read-modify-write over `last_parse_result`.
Two concurrent parses could interleave and the later write would silently drop
the earlier one — no error, no log.

**Fix**: `_write_metadata_atomic()` — serialise to a temp file in the same
directory, then `Path.replace()`, which is atomic on POSIX and on Windows.

## Fix for the rename race

The path is no longer derived from mutable sidecar content at read time; the move
and the sidecar update are ordered so that no reader can observe the intermediate
state.

## Why it belongs in the record

It is the counter-example to the reflex that a red under load is test noise. See
[[concepts/load-only-red-is-a-product-defect]]: this one is a real data-loss path
for any user running two imports at once, and it existed for as long as the store
did. Four workers did not cause it; they made it reproducible.

## Source files

| Role | Path |
|------|------|
| File store | `backend/app/services/brim_provider.py` — `get_file_path`, `_move_file` |
| Atomic metadata write | `backend/app/services/brim_provider.py` — `_write_metadata_atomic` |
| BRIM developer guide | `mkdocs_src/docs/developer/backend/brim/` |
