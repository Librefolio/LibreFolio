# 🎨 Styling & Design System

LibreFolio uses **Tailwind CSS v4** for styling, providing a utility-first approach with a custom design system.

## Technology Stack

- **Tailwind CSS v4**: The latest version of the utility-first CSS framework.
- **CSS Variables**: Used for theming (Dark/Light mode) and brand colors.
- **Inter Font**: The primary typeface for the application.

## Design System

The design system is defined in `src/app.css` using the `@theme` directive.

### Brand Colors

| Color Name    | Hex       | Usage                                        |
|:--------------|:----------|:---------------------------------------------|
| `libre-green` | `#1a4031` | Primary brand color, buttons, active states. |
| `libre-beige` | `#f5f4ef` | Backgrounds, cards, warmth.                  |
| `libre-sage`  | `#9caf9c` | Secondary accents, borders.                  |
| `libre-dark`  | `#111111` | Text, dark mode backgrounds.                 |

### Usage

You can use these colors directly in Tailwind classes:

```html
<div class="bg-libre-green text-white p-4 rounded-xl">
  Primary Button
</div>

<div class="bg-libre-beige text-libre-dark">
  Card Content
</div>
```

## Dark Mode

Dark mode is implemented using the `dark` class on the `<html>` element. We use CSS variables to handle color switching automatically.

### Theme Variables

Instead of hardcoding colors for dark mode (e.g., `dark:bg-slate-900`), we prefer using semantic CSS variables defined in `app.css`:

```css
:root {
    --theme-bg-primary: #ffffff;
    --theme-text-primary: #111827;
}

html.dark {
    --theme-bg-primary: #0f172a;
    --theme-text-primary: #f8fafc;
}
```

This allows components to adapt automatically without cluttering the markup with `dark:` modifiers.

## Component Styling

We aim for consistency by reusing common patterns:

- **Cards**: `bg-white dark:bg-gray-800 rounded-2xl shadow-card p-6`
- **Inputs**: `rounded-lg border-gray-200 focus:ring-libre-green`
- **Buttons**: `rounded-xl font-medium transition-all active:scale-95`
