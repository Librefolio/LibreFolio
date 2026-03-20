# MkDocs Agent Notes — Tricks & Gotchas

This file documents non-obvious behaviors, gotchas, and patterns for agents working on the LibreFolio MkDocs documentation.

---

## 1. Gallery Image Loader — `basePath` detection

**File**: `docs/javascripts/gallery-img-loader.js`

The `gallery-img-loader.js` script auto-resolves screenshot paths for `<img class="gallery-img">` elements on any page. It detects the MkDocs site base path (e.g., `/LibreFolio`) by scanning the current URL for **known top-level doc segments**.

### The Problem

If you add a new top-level section to the docs (e.g., `/user/`, `/admin/`) and forget to add it to the `knownSegments` array in `getBasePath()`, the script will fail to detect the base path correctly. Instead of resolving images at `/LibreFolio/gallery/desktop/...`, it will try `/LibreFolio/user/gallery/desktop/...` → **404**.

### The Fix

When adding a new top-level section to `mkdocs.yml`, **always update the `knownSegments` array** in `gallery-img-loader.js`:

```javascript
var knownSegments = [
    '/gallery/', '/developer/', '/user/', '/admin/',
    '/getting-started/', '/tutorials/', '/financial-theory/',
    '/POC_UX/', '/credits-legal/', '/faq/'
];
```

### How to Test

Open a page in the new section that uses `<img class="gallery-img" ...>` and check the browser console for 404 errors on image paths. If the base path is wrong, the image URL will contain the section path twice (e.g., `/user/gallery/` instead of `/gallery/`).

---

## 2. Gallery Image Usage in Non-Gallery Pages

To embed a gallery screenshot in any documentation page, use:

```html
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>
```

- `data-category`: Maps to the screenshot folder (e.g., `auth`, `dashboard`, `settings`, `files`, `media`, `brokers`, `fx`)
- `data-name`: Maps to the file name without extension (e.g., `01-login`, `main`, `list`)
- The loader resolves the full path as: `{basePath}/gallery/{viewport}/{lang}/{theme}/{category}/{name}.png`
- `viewport` defaults to `desktop` unless `data-gallery="mobile"` is set
- `lang` and `theme` are auto-detected from localStorage and MkDocs theme attributes

Available screenshots can be found in `docs/gallery/desktop.md` by grepping for `data-category` and `data-name`.

---

## 3. Relative Links After Moving Files

MkDocs resolves relative links from the file's directory. When moving files into subdirectories (e.g., `user/files.md` → `user/files/index.md`), **all relative links break**:

- `../admin/settings.md` → `../../admin/settings.md` (one more `..` needed)
- `misc/image-crop.md` → `../misc/image-crop.md`

Always check and fix relative links after moving files. `mkdocs build --strict` will catch broken links.

---

## 4. MkDocs Build Validation

Always run after changes:

```bash
cd mkdocs_src && python -m mkdocs build --strict
```

This catches:
- Broken links (files referenced in nav but not on disk)
- Broken relative links in markdown
- Syntax errors in `mkdocs.yml`

Note: It does NOT catch gallery image 404s — those are runtime JS errors visible only in the browser console.

---

## 5. MkDocs `nav` Section Names vs File Paths

In `mkdocs.yml`, nav entries like:

```yaml
- Brokers:
    - Overview: user/brokers/index.md
    - Broker Sharing: user/brokers/sharing.md
```

The section name ("Brokers") creates a collapsible group in the sidebar. The `index.md` convention makes the overview the landing page for that section.

---

## 6. Dev Server for Preview

```bash
cd mkdocs_src && python -m mkdocs serve --dev-addr 127.0.0.1:8002
```

The `--dev-addr` avoids conflict with the main LibreFolio backend (port 8000) and test backend (port 8001).

