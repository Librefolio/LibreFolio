# ⚛️ UI Atoms

Small, standalone UI primitives and input helpers.

---

## ThemeToggle

A **light/dark/auto theme toggle** with animated icons.

- Three states: ☀️ Light, 🌙 Dark, 💻 Auto (follow system)
- Smooth icon transition animation
- Persists choice in user settings

**Used by**: [Settings PreferencesTab](../settings.md), header.

---

## DocsLink

A **link to the MkDocs documentation** with book icon.

- Opens documentation in a new tab
- Configurable target path (defaults to docs root)

**Used by**: Header help menu.

---

## AnimatedBackground

**Animated SVG waves** for the login page background.

- Multiple layered wave paths with parallax animation
- Theme-aware colors (adapts to light/dark mode)
- Low CPU usage (CSS animations, no JS)

**Used by**: Login page (behind `LoginCard`/`RegisterCard`).

---

## OrderableList

A **drag-and-drop reorderable list**.

- Drag handles on each item
- Visual feedback during drag (elevated shadow, placeholder)
- Emits reordered array on drop

**Used by**: DataTable column reorder (in `DataTableToolbar`).

---

## PasswordInput

*Located in `lib/components/ui/input/`*

A **password field with visibility toggle** (eye icon).

- Toggle between `type="password"` and `type="text"`
- Eye / EyeOff icon from lucide-svelte

**Used by**: [LoginCard, RegisterCard](../auth.md), `PasswordChangeModal`.

---

## PasswordStrength

*Located in `lib/components/ui/input/`*

A **password strength indicator** powered by `zxcvbn`.

- Color-coded strength bar (red → orange → yellow → green)
- Textual feedback and suggestions
- Score: 0 (very weak) to 4 (very strong)

**Used by**: [RegisterCard](../auth.md) (below password field).

