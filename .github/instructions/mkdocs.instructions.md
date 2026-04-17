---
applyTo: "mkdocs_src/**"
---

# Documentation Guide (MkDocs)

## Structure

```text
mkdocs_src/
├── mkdocs.yml                  # Main config
├── docs/
│   ├── user/                   # User manual (17 files × 4 languages)
│   ├── admin/                  # Admin manual (6 files × 4 languages)
│   ├── developer/              # Developer manual (EN-only, ~45 files)
│   ├── financial-theory/       # Financial theory (7 files × 4 languages, LaTeX)
│   ├── gallery/                # UI screenshots (desktop + mobile)
│   ├── static/                 # CSS, logo, favicon, icons
│   └── javascripts/            # Custom JS (gallery loader, lang selector, app sync)
├── aphra-pipeline/             # LLM translation pipeline
└── site/                       # Build output (gitignored)
```

## Writing & Translation Rules

### Language Rule
- **All new documentation** is written in **English** (`.en.md` suffix)
- Translations (IT, FR, ES) are handled by the **Aphra pipeline** (see skill `devpy-mkdocs`)

### When to Use What

| Situation | Strategy |
|-----------|----------|
| Few files or small targeted changes | Use the AI agent to update/create translations directly |
| Many files or large-scale changes | Work only in English, then run `./dev.py mkdocs translate` |
| EN-only sections (developer/, POC UX) | No translation needed — **by design**, not an oversight |

### Post-Translation Workflow
After running the Aphra pipeline, check the structural diff report for issues:
```bash
./dev.py mkdocs translate-diff --issues-only
```
Then use the agent to fix reported differences (missing headings, broken links, etc.).

## Style Rules

### Admonition — Mandatory empty line (Prettier-safe)

**CRITICAL**: ALWAYS insert an empty line between the `!!!`/`???` directive and the indented body.

```markdown
<!-- ✅ CORRECT -->
!!! note "Title"

    Content indented 4 spaces.

<!-- ❌ WRONG — Prettier will remove indentation -->
!!! note "Title"
    Content indented 4 spaces.
```

### Tone — Three registers

| Area | Audience | Register |
|------|----------|----------|
| `user/`, `admin/` | End users | 🟢 Friendly & guided |
| `developer/` | Developers | 🟡 Technical but accessible |
| `financial-theory/` | Technical readers | 🔴 Specialized & rigorous (LaTeX) |

### Other Rules
- Write in **English** (translations via pipeline)
- Use **admonitions** for side notes — never for primary content
- **Emoji in headings**: H1-H3 always have 1 emoji
- **Diagrams**: Mermaid inline (no PNG)
- Code blocks with correct language tag

## Gallery Images in Pages

```html
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>
```

Path resolved: `{basePath}/gallery/{viewport}/{lang}/{theme}/{category}/{name}.png`

For gallery generation and translation commands, see skills `devpy-mkdocs`.
