# 🎨 Styling & Design System

LibreFolio uses **Tailwind CSS v4** for styling, providing a utility-first approach with a custom design system.

## 🧰 Technology Stack

- **Tailwind CSS v4** (`tailwindcss`, through `@tailwindcss/postcss`): the utility-first CSS framework.
- **CSS-first configuration**: `src/app.css` imports Tailwind and declares the design tokens with
  the `@theme` directive. `tailwind.config.js` only holds an empty `extend` and is not loaded:
  Tailwind v4 reads a JavaScript config only through `@config`, which `app.css` does not use.
- **CSS Variables**: Used for theming (Dark/Light mode) and brand colors.
- **Fonts**: system and locally installed fonts, plus one self-hosted face for flags — see
  [Fonts](#fonts).

## 🎯 Design System

The design system is defined in `src/app.css` using the `@theme` directive.

### 🎨 Brand Colors

| Color Name    | Hex       | Usage                                        |
|:--------------|:----------|:---------------------------------------------|
| `libre-green` | `#1a4031` | Primary brand color, buttons, active states. |
| `libre-beige` | `#f5f4ef` | Backgrounds, cards, warmth.                  |
| `libre-sage`  | `#9caf9c` | Secondary accents, borders.                  |
| `libre-dark`  | `#111111` | Text, dark mode backgrounds.                 |

In dark mode `html.dark` redefines `--color-libre-green` (`#00d681`) and `--color-libre-banner`
(`#00834f`). `@theme` also defines `libre-banner` (`#1a4031`, not used by components today), a
`primary-50…900` (green) and a `surface-50…500` (beige) palette, and the `shadow-card` /
`shadow-card-hover` shadows.

### 💻 Usage

You can use these colors directly in Tailwind classes:

```html
<div class="bg-libre-green text-white p-4 rounded-xl">
  Primary Button
</div>

<div class="bg-libre-beige text-libre-dark">
  Card Content
</div>
```

## 🔤 Fonts {: #fonts }

Every font stack the app sets starts with the **`'LF Flags'`** face:

```css
/* src/app.css — @theme */
--font-sans: 'LF Flags', Inter, system-ui, sans-serif;
--font-mono: 'LF Flags', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
```

The `html` element uses the same sans stack. Inter is not self-hosted: it is used where it is
installed, and `system-ui` takes over elsewhere.

`'LF Flags'` is declared in `static/lf-flags.css`, linked by `src/app.html` and by
`static/offline.html`. Its `unicode-range: U+1F1E6-1F1FF` covers only the regional indicator
symbols that make up a flag, so it draws flags and nothing else: digits, `#`, `*` and every other
emoji keep the fonts after it.

- **Apple devices** draw their own flags: the face resolves to the system Apple Color Emoji
  through its `local()` sources, and nothing is downloaded.
- **Everywhere else — Windows included**, whose Segoe UI Emoji has no flags and prints the two
  letters instead — it uses a locally installed Noto Color Emoji when there is one, and otherwise
  the self-hosted Noto Color Emoji flags subset, `/fonts/noto-color-emoji/noto-color-emoji.0.woff2`,
  fetched only when a flag is on screen.

The subset is not committed (`frontend/static/fonts/` is gitignored): `scripts/update_js_cache.py`
downloads Noto Color Emoji from Google Fonts and keeps only the flags range
(`keep_unicode_ranges`). `./dev.py front build` and `./dev.py docker build` run it first and stop
when the font is missing and cannot be fetched; `./dev.py server` runs it too.

!!! warning "Never name an emoji font in a `font-family`"

    No stack may name Apple Color Emoji, Noto Color Emoji, Segoe UI Emoji or Segoe UI Symbol: an
    emoji font placed before the text font draws digits, `#` and `*` with emoji glyphs. Those names
    appear only as `local()` sources in `static/lf-flags.css`. A component that sets its own stack
    (a monospace cell, an inline style) starts it with `'LF Flags'`, or wraps the flag in
    `.emoji-flag`, which applies the app's sans stack.

    The gate `src/flagFont.gate.test.ts` checks the face, the stacks of `app.css` and
    `offline.html`, and that no source names an emoji font; `e2e/fx/fx-flag-font.spec.ts` reads
    from the browser (Chrome DevTools Protocol) which font actually draws a flag.

## 🌙 Dark Mode

Dark mode is the `dark` class on the `<html>` element. An inline script in `src/app.html` sets
`dark` or `light` before the first paint, from the stored preference (`librefolio-theme` in
`localStorage`) or, when there is none, from `prefers-color-scheme`. `app.css` binds Tailwind's
`dark:` variant to that class:

```css
@custom-variant dark (&:where(.dark, .dark *));
```

Components write explicit `dark:` variants next to the light classes
(`bg-white dark:bg-slate-800`): this is the main mechanism.

### 🔧 Theme Variables

`app.css` also defines semantic variables for both themes (`:root, html.light` and `html.dark`):
`--theme-bg-*`, `--theme-text-*`, `--theme-border-*`, `--theme-accent*` and `--theme-shadow*`.

```css
:root,
html.light {
    --theme-bg-primary: #ffffff;
    --theme-text-primary: #111827;
}

html.dark {
    --theme-bg-primary: #0f172a;
    --theme-text-primary: #f8fafc;
}
```

Components do not read them directly. They feed a set of global `html.dark` overrides in `app.css`
that remap common light utilities — `.bg-white`, `.bg-gray-50`, `.text-gray-800`,
`.border-gray-200`, inputs, `.bg-libre-beige`, … — to the dark palette, a safety net for markup
written without a `dark:` variant.

## 🛠️ Utility Classes {: #utility-classes }

Global classes defined in `src/app.css`:

| Class | Purpose |
|:--|:--|
| `.emoji-flag` | Applies the app's sans stack, so a flag inside an element with its own font (a monospace cell) is still drawn by `'LF Flags'`. |
| `.lf-compact-number-input` | Shared typography of compact numeric inputs: inherited font, `0.75rem`/`1rem`, tabular numerals. Below 768 px the anti-zoom rule still sets inputs to 16 px, and the class only raises the line height. Used by the custom axis bounds of `ChartAestheticsSection.svelte`. |
| `.zoom-guard-exempt` | Opts an input out of the mobile 16 px font size that prevents iOS auto-zoom, for dense toolbars (date fields). |
| `.safe-top`, `.safe-top-offset` | Padding / offset for the iOS safe area (notch, status bar) in standalone mode. |
| `.scrollbar-hidden` | Scrollable without a visible scrollbar. |
| `.lf-price-flash-up`, `.lf-price-flash-down` | One-shot colour flash of a live price — see [Live Prices](components/features/live-ticker.md#price-flash). |

## 🧱 Component Styling

The recurring patterns in the code base:

- **Cards**: `bg-white dark:bg-slate-800 rounded-xl shadow-sm`, often with
  `border border-gray-100 dark:border-slate-700`
- **Inputs**: `rounded-lg` borders with `focus:ring-libre-green` / `focus:border-libre-green`
- **Primary buttons**: `bg-libre-green text-white rounded-lg` (dark mode darkens `bg-libre-green`
  to `#166534` for contrast)
