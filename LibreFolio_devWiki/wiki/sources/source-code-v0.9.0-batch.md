---
title: "Source Code v0.9.0 Batch"
category: "source"
tags: ["source-code", "v0.9.0", "remotion", "ui", "gallery"]
---

# Source Code v0.9.0 Batch

## Summary
Ingest of the newly created and modified source files up to commit `6d89b44` (v0.9.0). This includes the newly bootstrapped Remotion project for the Video Promo, an interactive pros/cons slider in the MkDocs homepage, and the overhaul of the E2E gallery generation script to support Phase 7 and 8 features.

## Key Takeaways
- **Remotion Video Promo**: A new React-based project within `mkdocs_src/videoClipPrject/video_promo` designed to programmatically generate promotional videos with i18n support and AI-generated audio/assets.
- **Interactive Pros/Cons Slider**: A new interactive UI component added to the MkDocs homepage for better user guidance.
- **Gallery Overhaul**: E2E tests expanded to generate 72 screenshots for all new features (Transactions, Import Wizard, Scheduler, etc.), automatically handling empty states.

## Pages Created / Updated
- [[entities/video-promo-remotion]]
- [[concepts/interactive-pros-cons-slider]]

## Source files
| File | Git Hash | Date |
|------|----------|------|
| `mkdocs_src/videoClipPrject/video_promo/*` | `6d89b44` | 2026-06-17 |
| `mkdocs_src/docs/index.en.md` | `6d89b44` | 2026-06-17 |
| `frontend/e2e/gallery.spec.ts` | `6d89b44` | 2026-06-17 |
