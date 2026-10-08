---
title: Tools
description: What a Tool is, the tools available today, and how to open one.
---

# 🧰 Tools

A **Tool** is a standalone calculation: you supply the data for one operation, and it returns a result or a structured error. It is not an instruction to modify your portfolio.

The Tool platform is **experimental**. The catalogue currently offers exactly
**one** tool:

| Tool | What it does |
|---|---|
| [PAC allocator](pac-allocator/index.md) | Plans which purchases bring an allocation as close as possible to its target, using the cash and contributions available now. |

Its card opens a guided planner. Its own page explains how to use it and what
the calculation engine behind it does.

!!! note "A second tool was withdrawn"

    The catalogue previously offered a Portfolio Rebalancer next to the PAC
    allocator. Both were prototypes and both were removed. Only the PAC
    allocator has been rebuilt so far, so a bookmark to the Rebalancer's
    documentation page no longer resolves.

## 🖱️ Opening a tool

Open **Tools** from the sidebar to see the catalogue as a grid of cards. For a ready tool, the **entire card** is clickable, not just its title or an icon; an arrow indicator marks it as open-able. A tool whose interface is missing has neither, and states its situation on the card instead.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="hub" alt="Tools catalogue with the PAC allocator card, its version pair, and the Documentation and Reload actions">
</div>

Both the catalogue and an open tool show:

- a **Documentation** action linking to that tool's page, with a label that appears next to the icon on wider screens and collapses to an icon-only control on narrow screens;
- a **Reload** action that reloads the catalogue (from the hub) or the current tool's interface (from an open tool), with the same responsive icon-only behavior; reloading an open tool first asks for confirmation (**Reload tool?**), because it replaces the interface and discards its current draft;
- the tool's compatibility pair, `Backend/API <contract_version> · UI <ui.version>`, with no separate build or implementation number shown alongside it.

When some catalogue entries or interfaces are unavailable, the hub says how many and points to **Settings → About → Plugin diagnostics**.

## ℹ️ Good to know

- **A tool never changes your portfolio.** It records no transactions, places no orders, and
  saves nothing to your portfolio: acting on its result is up to you.
- **Server busy, or a time limit reached?** You get no result, and that says nothing about your
  figures: wait a moment, then try again.
- **A tool is missing or cannot be opened?** Look in **Settings → About → Plugin diagnostics**:
  its **Tools** panel says, tool by tool, whether it is available and, if not, why. See
  [About](../settings/about.md).
