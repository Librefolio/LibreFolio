---
paths:
  - "mkdocs_src/**"
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
| EN-only section (developer/) | No translation needed — **by design**, not an oversight |

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

### Content Tabs — Mandatory 4-space indentation

**CRITICAL**: Content under `=== "Tab Title"` must ALWAYS be indented by exactly **4 spaces** (including inner code blocks and lists). The translation pipeline can sometimes alter this to 1 space in local translations, which breaks the tab container rendering and displays tabs sequentially (one below the other). Ensure all languages maintain the 4-space base indentation.

```markdown
=== "Linux"

    Content indented 4 spaces.

    ```bash
    curl -fsSL https://tailscale.com/install.sh | sh
    ```

=== "macOS"

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
- **Diagrams**: Mermaid inline (no PNG). 
  - Standard engine (Dagre) is the default, best for simple graphs.
  - The site serves Mermaid and its **ELK layout** from its own pinned copies (`./dev.py cache js`: Mermaid 11.17.2 and
    `@mermaid-js/layout-elk` 0.2.3, each checked against a pinned hash, nothing asked of a CDN when a page opens).
    A diagram says `layout: elk` in its frontmatter when ELK reads better than Dagre (many nodes, nested subgraphs);
    `javascripts/mermaid-early.js` registers the layout before Material draws. Keep a diagram small either way: few nodes,
    short labels, `flowchart LR` or `TD`, or several small diagrams instead of one big one.
  - **Colours**: a node that sets its own `fill` (`style X fill:#…` or a `classDef`) must also set `color:` — dark text
    (`#1b1b1b`) on a light fill, white on a dark one. Without it the text takes the theme's colour, which is light in the
    dark theme, and a pale box shows white text on white.
  - Clicking a diagram opens it full screen with zoom and pan (`javascripts/diagram-zoom.js`). A script that must see
    the diagram's SVG goes in the head of `overrides/main.html`, before Material's bundle, never in
    `extra_javascript`: Material draws into a closed shadow root and the script must open it first.
- **Tables** need no markup for their widths: `javascripts/table-balance.js` gives a table with a long cell next to a short one
  columns in proportion to the square root of their text (wide screens only). Put a long log line in a table freely; do not
  force widths by hand.
- Code blocks with correct language tag

## Gallery Images in Pages

### Single Image
```html
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>
```

### Image Carousel
For displaying multiple related images, use the custom `lf-screenshot-carousel` component:
```html
<div class="lf-screenshot-carousel" data-carousel="my-carousel-id" data-carousel-interval="3000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="settings" data-name="user-preferences" data-title="User Preferences">
    <img class="gallery-img lf-screenshot-carousel-item" data-category="settings" data-name="global-settings" data-title="Global Settings (Admin)">
</div>
```

Path resolved: `{basePath}/gallery/{viewport}/{lang}/{theme}/{category}/{name}.webp`, then the same `.png`, then the public site's (the gallery writes PNG, `dev.py mkdocs gallery` converts it to WebP at the end; the site keeps both)

For gallery generation and translation commands, see skills `devpy-mkdocs`.
