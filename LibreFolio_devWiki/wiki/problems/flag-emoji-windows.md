---
title: "Flag Emoji Broken on Windows (Segoe UI Emoji)"
category: problem
status: resolved
date: 2026 (Phase 5)
tags: [frontend, emoji, windows, i18n, css]
related_features: [F-008]
---

# Problem: Flag Emoji Not Rendering on Windows

## Symptom
Country/language flag emoji (🇮🇹, 🇫🇷, 🇪🇸, 🇬🇧) displayed as blank boxes or letter pairs on Windows. Linux and macOS showed them correctly.

## Root Cause
Windows' default emoji font (Segoe UI Emoji) **does not support regional indicator flag emoji sequences**. The standard system font stack falls through to a font that doesn't have flags.

## Solution
Load `Noto Color Emoji` from Google Fonts and apply it **only** to containers that display flag emoji:

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');

.emoji-flag {
    font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;
}
```

**Important**: apply `.emoji-flag` only to flag containers (language selector, currency flags), not globally. Other emoji work fine with system fonts — the web font adds significant CSS weight.

## Prevention
When adding any UI element with flag emoji, wrap it in a container with `.emoji-flag` class.

## Source
`LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` — "Emoji Bandiera (Windows Fix)" section

## Source files

| Role | Path |
|------|------|
| Language selector (flag emoji) | `frontend/src/lib/components/layout/LanguageSelector.svelte` |
| App CSS (Noto Color Emoji) | `frontend/src/app.css` |
