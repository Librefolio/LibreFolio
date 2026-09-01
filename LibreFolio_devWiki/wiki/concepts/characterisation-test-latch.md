---
title: "The characterisation test as a decision latch"
category: concept
date: 2026-08-31
tags: [testing, method, product-decisions, documentation]
related: [concepts/load-only-red-is-a-product-defect, decisions/settings-write-path-contract, decisions/broker-last-owner-guard]
related_problems: [i18n-key-assertion-false-green]
---

# Concept: freeze the behaviour you have not decided about

## Definition

When a test lane finds a behaviour that is **wrong but not yet decided**, the
lane does not fix it and does not skip it. It writes a test that asserts the
behaviour **exactly as it is**, named so that nobody mistakes it for an
endorsement:

```ts
test('CHARACTERISATION: weekdays stay UTC while times convert', …)
```

The test's job is not to defend the behaviour. Its job is to **go red on the day
somebody decides differently**, so that the decision cannot be made silently and
cannot be forgotten.

## Why it beats the alternatives

| alternative | what goes wrong |
|---|---|
| fix it inside the coverage lane | mixes a product decision into a test-writing task; the user never got asked |
| skip the test | the behaviour becomes invisible again the moment the lane closes |
| open an issue only | the issue and the code drift apart; nothing tells you when the drift happens |
| assert the *desired* behaviour and leave it red | a permanently red suite trains everyone to ignore reds |

A characterisation test is the only one of the five that keeps the question
**attached to the code** and **enforced by the runner**.

## How it was used

The 2026-08 settings lane produced **sixteen** of them: eleven defects it
deliberately did not fix, plus five discovered later. Each one shipped with:

- the file and line of the behaviour,
- the decision the user has to make,
- the recommendation, where there was one,
- a test that fails the day the answer changes.

Nine of the sixteen were then decided by the user and closed in the following
lane; the answers are recorded in
[[decisions/settings-write-path-contract]], [[decisions/broker-last-owner-guard]],
[[decisions/scheduler-converts-at-decision]] and
[[concepts/absence-sentinel-vs-nullable-type]].

The scheduler case shows why the mechanism earns its keep. `D1` — weekdays stay
UTC while times convert — was **not a regression introduced by the fix**. It had
always been there, hidden by the fact that times did not convert either.
Correcting half the problem made the other half visible, and the characterisation
test is what held it still long enough to be decided properly.

## Two rules that keep them honest

**Name the decision, not the symptom.** `CHARACTERISATION:` in the title, and a
comment saying what would have to change for this test to be deleted. A frozen
behaviour with no note becomes indistinguishable from a specification within one
quarter.

**Assert on identity, not on prose.** A characterisation test lives longer than
ordinary tests, so it is more exposed to the false-green failure mode described
in [[problems/i18n-key-assertion-false-green]] — a test that asserts an i18n key
is green only until the key gets translated.

## Source files

| Role | Path |
|------|------|
| Scheduler characterisation | `frontend/src/lib/components/settings/SchedulerConfigModal.test.ts` |
| Settings tab characterisations | `frontend/src/lib/components/settings/tabs/PreferencesTab.test.ts`, `GlobalSettingsTab.test.ts` |
| Broker sharing characterisations | `frontend/src/lib/components/brokers/BrokerSharingPanel.test.ts` |
| Test authoring rules | `.github/agents/test-author.agent.md` |
