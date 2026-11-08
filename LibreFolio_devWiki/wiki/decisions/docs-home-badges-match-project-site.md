---
title: "The docs home shows the three project badges of the public project site, in the site's colour roles"
category: decision
status: resolved
date: 2026-11-07
tags: [docs, mkdocs, home, design-system, branding, release-1.3]
related:
  - problems/derived-css-properties-resolve-where-declared
  - decisions/colour-factorisation-at-pixel-parity
---

# Decision: the docs home badges match the project site

## Context

The documentation home had three uppercase pill badges of its own («100% OPEN SOURCE», «HIGHLY EXPANDABLE»,
«SELF-HOSTED»). The public project site (librefolio.eu) presents the project with three different badges. Two sets of
claims for one project read as two projects.

## Decision

- The home shows **the same three badges as the project site**, same words, icons, colours and band: *Private, by
  design* (a lock), *100% Open, open source* (code brackets), *Multi-broker, one portfolio* (a grid). They stay
  together: one row, or one column where the row does not fit — never two and one (the developer, 06/11/2026).
- The markup is a list (`<ul class="project-badges">` with an `aria-label`), the icons inline SVG, `aria-hidden`.
- **Icon colours come from the roles**, not from hand-written hex: the lock in the text role (the brand green would
  vanish on the dark card), the code in amber, the brokers in the link role (`--lf-link`).
- Translated in it, fr, es (`be77ff9e8`).

## Consequences

- The brokers icon first used `--lf-focus` as a workaround, because `--lf-link` kept its light value under the docs'
  dark scheme; once the theme hook was fixed it went back to `--lf-link` (`b6215da03`). See
  [[problems/derived-css-properties-resolve-where-declared]].

## Links

- Commits: `ba544c36c`, `be77ff9e8`, `7666f3421`, `b6215da03`. Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]

## Source files

| Role | Path |
|------|------|
| Home page (en) | `mkdocs_src/docs/index.en.md` |
| Badge styles | `mkdocs_src/docs/stylesheets/home-custom.css` |
| Colour roles read by the docs | `mkdocs_src/hooks/lf_theme_tokens.py` |
