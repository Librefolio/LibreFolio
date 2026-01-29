# Guida Rapida - Modificare Colori Dark Mode

**File da modificare**: `frontend/src/app.css`

---

## 🎨 Variabili Dark Mode Principali (linee 82-105)

```css
/* Dark theme - MODIFICA QUESTE */
html.dark {
    /* SFONDI */
    --theme-bg-primary: #0f172a;     /* Sfondo principale (più scuro) */
    --theme-bg-secondary: #1e293b;   /* Sfondo secondario (card, input) */
    --theme-bg-tertiary: #334155;    /* Sfondo terziario (hover, selected) */
    --theme-bg-card: #1e293b;        /* Sfondo card */
    --theme-bg-hover: #334155;       /* Sfondo hover */

    /* TESTI */
    --theme-text-primary: #f8fafc;   /* Testo principale (bianco) */
    --theme-text-secondary: #cbd5e1; /* Testo secondario */
    --theme-text-tertiary: #64748b;  /* Testo terziario (placeholder) */
    --theme-text-muted: #94a3b8;     /* Testo muted */

    /* BORDI */
    --theme-border-primary: #334155;   /* Bordo principale */
    --theme-border-secondary: #1e293b; /* Bordo secondario */

    /* ACCENT (verde) */
    --theme-accent: #22c55e;         /* Verde accent */
    --theme-accent-hover: #16a34a;   /* Verde hover */
    --theme-accent-bg: rgba(34, 197, 94, 0.15); /* Sfondo accent */
}
```

---

## 🔧 Come Fare Prove

### Metodo 1: DevTools (Temporaneo)

1. Apri DevTools (F12)
2. Vai su `<html class="dark">`
3. Aggiungi/modifica stili inline

### Metodo 2: Modifica CSS (Permanente)

1. Apri `frontend/src/app.css`
2. Modifica le variabili nella sezione `html.dark { ... }`
3. Salva - Hot reload applica subito

---

## 📋 Parametri Comuni da Modificare

### Se sfondi troppo uniformi:

```css
/* Aumenta contrasto tra livelli */
--theme-bg-primary: #0a0f1a;    /* Più scuro */
--theme-bg-secondary: #1a2332;  /* Leggermente più chiaro */
--theme-bg-tertiary: #2a3342;   /* Ancora più chiaro */
```

### Se input troppo scuri:

```css
/* Linea 157-162: Input specifici */
html.dark input,
html.dark select,
html.dark textarea {
    border-color: #546175;  /* Bordo più chiaro */
    background-color: #2a3342; /* Sfondo più chiaro */
}
```

### Se testi poco leggibili:

```css
--theme-text-secondary: #e2e8f0; /* Più chiaro */
--theme-text-muted: #a8b4c4;     /* Più chiaro */
```

---

## 🎯 Scala Colori Consigliata (Slate Tailwind)

| Nome      | Colore    | Uso                 |
|-----------|-----------|---------------------|
| slate-950 | `#020617` | Sfondo più scuro    |
| slate-900 | `#0f172a` | Sfondo principale   |
| slate-800 | `#1e293b` | Card, input         |
| slate-700 | `#334155` | Hover, bordi        |
| slate-600 | `#475569` | Bordi chiari        |
| slate-500 | `#64748b` | Testo muted         |
| slate-400 | `#94a3b8` | Testo terziario     |
| slate-300 | `#cbd5e1` | Testo secondario    |
| slate-200 | `#e2e8f0` | Testo più leggibile |
| slate-100 | `#f1f5f9` | Testo chiaro        |
| slate-50  | `#f8fafc` | Testo bianco        |

---

## 💡 Suggerimenti

1. **Aumenta contrasto input**: Usa `--theme-bg-tertiary` per input invece di `--theme-bg-secondary`

2. **Differenzia livelli**:
    - Page background: `slate-900` (#0f172a)
    - Card background: `slate-800` (#1e293b)
    - Input background: `slate-700` (#334155)

3. **Test rapido in DevTools**:
   ```javascript
   document.documentElement.style.setProperty('--theme-bg-secondary', '#2a3342');
   ```

---

## 📁 Dove Sono i Componenti Specifici

| Componente     | File                                            |
|----------------|-------------------------------------------------|
| Login page     | `AnimatedBackground.svelte`                     |
| Modali         | `BrokerModal.svelte`, etc.                      |
| Input generici | `app.css` linee 157-166                         |
| Sidebar        | `Sidebar.svelte` (usa Tailwind)                 |
| Card           | Usa classe `bg-white` → overridden in `app.css` |

---

**Prova a modificare le variabili e dimmi cosa funziona/non funziona!**
