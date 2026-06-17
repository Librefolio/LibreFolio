# Prompt AI per asset video — LibreFolio Promo

> Dove mettere i file generati:
> **`mkdocs_src/videoClipPrject/external_src/ai/`**
>
> Il sync script li rileva automaticamente e li copia in `public/assets/ai/`
> prima di ogni build (`npm run sync`).

---

## Asset da generare

### 1. `chaos_bg.png` — Scena 1 (Hook)

**Usato in:** sfondo full-screen con overlay scuro + testo headline

**Formato:** 3840×2160 (4K) o 1920×1080 minimo  
**Stile:** dark, cinematico, distopico

#### Prompt (Imagen 3 / Midjourney / DALL-E):

```
Abstract digital chaos: dozens of overlapping financial charts (line charts,
candlesticks, bar graphs) in neon colors, scattered spreadsheet grids,
floating stock tickers (AAPL, BTC, ETF labels), crypto logos, multiple
app interface fragments exploding outward. Dark background (#0a0a1a),
neon purple and cyan accent glows. Overwhelming, fragmented, dystopian
tech aesthetic. High detail, 4K cinematic, wide angle, no text readable.
```

**Variante più astratta:**
```
Exploding financial data visualization: stock charts disintegrating into
particles, spreadsheet cells floating in void, crypto logos scattered
chaotically. Deep space dark background with purple and blue neon glow.
Photorealistic digital art, 8K, ultra wide.
```

---

### 2. `opensource_infographic.png` — Scena 5 (Open Source)

**Usato in:** sfondo con overlay a bassa opacità (25%) — può essere "rumoroso"  
**Formato:** 3840×2160 o 1920×1080  
**Stile:** flat/geometric, dark background, accenti teal e viola

#### Prompt:

```
Clean flat design infographic icons on dark background (#0f2027):
center - an open padlock with glowing teal outline (open-source symbol).
Left - a server rack icon with purple glow (self-hosted).
Right - a cloud icon split between server and cloud (hybrid deployment).
Below - a puzzle piece icon for extensibility/plugins.
Dark teal and purple accent colors (#34d399, #818cf8). Minimal geometric
style, subtle grid background, no text, 4K resolution.
```

**Variante con GitHub:**
```
Geometric tech illustration: GitHub Octocat logo stylized in wireframe
teal glow, flanked by a server icon (purple) and cloud icon (blue-teal),
connected by flowing data lines. Dark (#0f2027) background with subtle
circuit board texture. Flat vector aesthetic, 4K, no readable text.
```

---

## Note tecniche

| Aspetto | Dettaglio |
|---------|-----------|
| **Formato file** | PNG (preferito) o JPG alta qualità (>90%) |
| **Risoluzione minima** | 1920×1080 (il video è 1920×1080 @2x = 3840×2160) |
| **Dimensione max consigliata** | < 10 MB per file |
| **Cartella destinazione** | `mkdocs_src/videoClipPrject/external_src/ai/` |
| **Nome file ESATTO** | `chaos_bg.png` e `opensource_infographic.png` |
| **Dopo aver messo i file** | Eseguire `npm run sync` nella cartella `video_promo/` |

---

## Come testare dopo aver aggiunto i file

```bash
cd mkdocs_src/videoClipPrject/video_promo
npm run sync     # copia i nuovi file in public/assets/ai/
npm run start    # apre Remotion Studio — navigare su Scena 1 e Scena 5
```

---

## Stato asset gallery (auto-sincronizzati)

| Scena | Asset | Fonte | Stato |
|-------|-------|-------|-------|
| 1 Hook | `chaos_bg.png` | AI generato | ⏳ **da generare** |
| 2 Hero | `dashboard_main.png` dark+light | Gallery desktop | ✅ |
| 3 MultiAsset | `echarts_view.png` + `datatable_view.png` dark+light | Gallery desktop | ✅ |
| 4 Mobile | `dashboard_main.png` dark+light mobile | Gallery mobile | ✅ |
| 5 OpenSource | `opensource_infographic.png` | AI generato | ⏳ **da generare** |
| 6 CTA | `logo.png` | Static docs | ✅ |
