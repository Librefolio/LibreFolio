---
title: "The test runner refuses test names an action cannot apply: exit 2, before anything runs"
category: decision
status: resolved
date: 2026-10-17
tags: [testing, test-runner, cli, workstream-h, release-1.3]
related:
  - concepts/derived-test-inventory
  - concepts/test-isolation-classes
  - decisions/test-runner-package-split
---

# Decision: names given to a whole-only action stop the command

## Context

Every registry category's parser takes test names after the action (`nargs="*"`). The live registry had **36** actions
registered with `test_names=False`: every category's `all`, `db create`, `db populate` and 18 Vitest units. For them
`run_test_from_registry()` dropped the names **in silence** and ran the whole action:

- `dev.py test services all test_foo` ran all of `services`, and recreated the lane's database;
- `dev.py test external all yfinance` looked like a provider filter and ran every provider;
- `dev.py test db populate --force --clean extra` repopulated without a word;
- `dev.py test front-portfolio risk-unit name` ran the whole unit.

Found by the test-author of lot H-25 (16/10), which gave the parallel pre-pass the consolidated passes' rule: no
parallel pass with test names. That rule only stepped aside, it did not make names work after `all`.

## Options Considered

1. **Refuse**: exit 2, with a message that says to name the action. Loud, cheap and honest.
2. **Apply the names to the whole category**, as `-k` on every unit: more useful, but wider, and every runner path
   would have to learn it.
3. Refuse only after `all`, leaving the other 20 actions to a later lot.

## Decision

Option 1, the single rule for all 36 actions (the coordinator, 17/10, lot H-26). `_refused_test_names(args)`
(`scripts/test_runner/_cli.py`) is a pure function. It returns `None` when there are no names, when the category or
the action is not in the registry (argparse answers those), or when the action takes names; otherwise it returns the
message. Both entries call it first:

- `_dispatch_test_command()` for `dev.py test`;
- `main()` for `python -m scripts.test_runner`.

Each prints the message with `print_error()` and returns 2, **before** anything else runs: `tee_output()`
(`--log-file`), `_activate_log_dir()` (which archives the previous `.testLog`), `_timed_run()` (the campaign record)
and `_snapshot_log_dir_db()`. `--list` is refused too. After `all` the message says «name the action — dev.py test
<category> <action> <names>»; after another action it says the action «takes no test names: it runs whole».

## Consequences

- Real check: six refused commands exited 2, and the `.testLog` archive, the run cache, the campaign and the lane
  database stayed byte-identical (inode, time, size).
- Flags are not names: `external all --exclude-providers yfinance broker_coinbase` still works.
- The suite commands (`all`, `all-backend`, `all-frontend`) never took names: argparse already refused them.
- `--help` marks the actions that take names `[TEST_NAME]`. Three `front-utility` Vitest actions take names (Vitest
  `-t`), the other units do not.
- Applying names to a whole category stays possible later, if someone asks. The parallel pre-pass already steps aside
  when names are given.
- Same file, lot H-30: `main()`'s `--log-file` branch now takes the database snapshot in a `finally`, as
  `_dispatch_test_command()` always did, so a crashed run keeps its evidence.

## Links

- [[concepts/derived-test-inventory]]: the registry is the source the rule reads.
- [[concepts/test-isolation-classes]].

## Source files

| Role | Path |
|------|------|
| `_refused_test_names()`, both entries, the `--log-file` branch of `main()` | `scripts/test_runner/_cli.py` |
| The rule over every action of the live registry, the entries, `dev.main()`, the H-30 snapshot | `backend/test_scripts/test_utilities/test_test_runner_cli.py` |
| How names are given, and when they are refused | `mkdocs_src/docs/developer/test-walkthrough/index.md` |
| `test_names=False` when adding an action | `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md` |
| The lots H-25, H-26 and H-30 | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
