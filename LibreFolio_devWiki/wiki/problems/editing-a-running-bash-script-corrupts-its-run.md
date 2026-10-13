---
title: "A bash script edited while it ran went on from an old offset in the new file: a command lost, then a fragment and a syntax error"
category: problem
status: resolved
date: 2026-10-12
tags: [bash, scripting, tooling, agents, parallel-calls, workstream-u, release-1.2]
related:
  - decisions/plugin-folders-and-split-i18n
---

# Problem: changing the script under bash's feet

## Symptom

Workstream U added a new part to its gate script in the same batch of parallel calls that was running it (2026-10-12,
19:25). The new part was reported as «command not found»; the run then went on through the parts it already knew, and
at the end of the loop failed on a fragment of a line («ead_code: command not found») and a syntax error, with EXIT 2
and nothing more executed. The worktree and the port were untouched.

## Root Cause

Bash reads a script as it goes, not all at once. It had parsed the old version of the function list, so the new part
did not exist for it; when it came back to the file for the next lines, it read from its old byte offset in a file
whose bytes had moved, and found half a line.

## Solution

The new part was run again on its own, in a new process.

## Prevention

- Never change a script in the batch that runs it, nor while it runs (U's rule after this).
- To change a long-running script, write a new file and start a new process.

## Source files

| Role | Path |
|------|------|
| Plan 45 (§10, U-2, the detour of 19:25) | `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` |
