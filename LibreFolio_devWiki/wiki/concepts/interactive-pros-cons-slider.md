---
title: "Interactive Pros/Cons Slider"
category: "concept"
tags: ["ui", "mkdocs", "user-guidance"]
related: ["sources/source-code-v0.9.0-batch"]
---

# Interactive Pros/Cons Slider

## Context
An interactive component added to the LibreFolio documentation homepage to help users decide if the tool is right for them.

## Details
- Implemented purely in HTML/CSS within MkDocs (`mkdocs_src/docs/index.en.md` and `home-custom.css`).
- Enhances user guidance by providing a clear, interactive visual representation of the software's strengths and target audience compared to its limitations.

> *2026-11-07 lint:* the section is now titled «Is LibreFolio right for you?» and is a static comparison — grouped
> cards on mobile, `.lf-fit-*` classes, no script or range input — since `34e201bfe` (2026-06-17, «refine fit comparison
> styling and copy»); the original slider came with `f2f2227b6` (2026-06-16).

## Source files
| File |
|------|
| `mkdocs_src/docs/index.en.md` |
| `mkdocs_src/docs/stylesheets/home-custom.css` |
