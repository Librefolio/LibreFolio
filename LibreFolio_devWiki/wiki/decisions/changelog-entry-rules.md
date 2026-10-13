---
title: "What a CHANGELOG line may claim: a 🐛 fixes a defect of the last release, a ✨ is new since it, «Present since» names the release the defect was born in, UI names come from the English catalogue, an upgrade break also goes in ⚠️"
category: decision
status: accepted
date: 2026-10-13
tags: [changelog, release, documentation, review, release-1.2]
related:
  - decisions/changelog-translated-by-chapter
  - problems/portfolio-wac-endpoint-answered-anyone
---

# Decision: rules for the lines of the CHANGELOG

## Context

Before the 1.2 tag, workstreams T and I checked the 227 lines of the CHANGELOG's [1.2.0] chapter one by one against
the code and against `v1.1.0` (T 139 lines, I 88). More than 40 claims were false or partly false — six of them in
the version they named; 15 lines described defects born and cured after 1.1.0, so they were no news to a 1.1 user;
lines sat in the wrong section; the four-level risk panel, new in 1.2, was not announced at all. The chapter was
rewritten in `60f734e08` (+132 −141).

## Decision

- A 🐛 line fixes a defect that existed in the last release.
- A ✨ line describes something that did not exist in the last release.
- «Present since» names the release in which the defect was born — «since v1.0.0» now stands on 11 lines, where it
  stood on one.
- The names of the interface are those of the English catalogue.
- A change that breaks something on upgrade also goes in ⚠️ — seven notes now, where there was one.
- CVaR and Sharpe stay in 🔄 on purpose: their figures change.

## Consequences

- The review also found a security fix that had shipped silently: [[problems/portfolio-wac-endpoint-answered-anyone]].
- Two small defects went to the backlog: C-70 (the import plugins' refusals only in English, with their code) and C-71
  (two «Rolling Return» indicators with the same name).
- The reviewers' reports are working files outside the repository; the result is the chapter itself.
- The release page built on the verified chapter, in draft until the tag: [[sources/release-1.2.0]].

## Source files

| Role | Path |
|------|------|
| The chapter [1.2.0] | `CHANGELOG.md` |
| Backlog (C-70, C-71) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
