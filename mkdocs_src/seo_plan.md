# Piano SEO per LibreFolio (GitHub Pages)

Questo documento delinea la strategia per posizionare la documentazione di LibreFolio sui motori di ricerca, ottimizzando l'attuale setup basato su MkDocs e GitHub Pages.

## 1. Analisi e Strategia Teorica

### 1.1 Obiettivi
1.  **Indicizzazione**: Assicurarsi che Google e altri motori di ricerca scansionino correttamente il sito.
2.  **Posizionamento**: Apparire per keyword rilevanti nel settore "Self-hosted Finance".
3.  **Brand Awareness**: Associare "LibreFolio" a concetti di privacy, open-source e controllo finanziario.

### 1.2 Keyword Strategy
Dobbiamo intercettare utenti che cercano alternative a software esistenti o soluzioni specifiche.

*   **Primary Keywords** (Alto volume/Pertinenza):
    *   "Self-hosted personal finance software"
    *   "Open source portfolio tracker"
    *   "Privacy-focused financial analysis"
    *   "Ghostfolio alternative" (molto potente per intercettare traffico comparativo)
    *   "Self-hosted investment tracking"

*   **Secondary Keywords** (Specifiche):
    *   "Track P2P loans self-hosted"
    *   "Docker financial dashboard"
    *   "Multi-currency portfolio manager open source"

### 1.3 Struttura dei Contenuti
I motori di ricerca premiano la struttura gerarchica chiara.
*   **H1**: Deve contenere la keyword principale della pagina (es. "Installation" -> "Install LibreFolio with Docker").
*   **Intro**: Il primo paragrafo deve riassumere il contenuto e contenere keyword.
*   **Internal Linking**: Linkare tra loro le pagine (es. dal tutorial "Track First Stock" linkare alla "Installation Guide").

---

## 2. Implementazione Tecnica (MkDocs)

### 2.1 Ottimizzazione `mkdocs.yml`
Il file di configurazione deve essere arricchito con metadati globali.

```yaml
# Aggiunte necessarie in mkdocs.yml
site_description: "LibreFolio is a self-hosted, open-source personal finance manager focused on privacy. Track stocks, crypto, and P2P loans with full control."
site_author: "Alfystar"
copyright: "Copyright &copy; 2024-2026 Alfystar"

# Configurazione plugin consigliati
plugins:
  - search
  - minify: # Richiede mkdocs-minify-plugin
      minify_html: true
  - git-revision-date-localized: # Mostra freschezza del contenuto
      type: date
```

### 2.2 Meta Tags per Pagina (Overrides)
Per pagine specifiche (es. Home, Features), è utile sovrascrivere la descrizione globale. MkDocs Material supporta il frontmatter YAML all'inizio dei file `.md`.

**Esempio per `index.md`:**
```yaml
---
description: The ultimate self-hosted alternative for financial tracking. Private, flexible, and open-source. Start your journey with LibreFolio.
---

# LibreFolio
...
```

### 2.3 Sitemap e Robots.txt
*   **Sitemap**: MkDocs la genera automaticamente in `/sitemap.xml`. Assicurati che `site_url` in `mkdocs.yml` sia corretto (`https://alfystar.github.io/LibreFolio/`).
*   **Robots.txt**: GitHub Pages ne crea uno di default, ma per un controllo fine si può creare un file `docs/robots.txt` personalizzato (spesso non necessario se non si vogliono bloccare path specifici).

### 2.4 Canonical URLs
Essendo su un sottodominio (`alfystar.github.io`), è cruciale definire i canonical URL per evitare problemi se in futuro sposterai il sito su un dominio custom (`librefolio.com`).
MkDocs Material gestisce i canonical tag automaticamente basandosi su `site_url`.
*   **Azione**: Non cambiare `site_url` finché non sei pronto a migrare il dominio.

### 2.5 Social Cards (Open Graph)
Quando i link vengono condivisi su social/Discord, deve apparire un'anteprima accattivante.
Il tema Material ha un plugin integrato per generare social cards.

```yaml
theme:
  features:
    - navigation.instant
    # ... altri
plugins:
  - social # Genera immagini social automatiche
```

---

## 3. Setup Google Search Console (GSC)

È lo strumento fondamentale per monitorare l'indicizzazione.

1.  **Account**: Accedi a [Google Search Console](https://search.google.com/search-console).
2.  **Proprietà**: Aggiungi una proprietà "URL prefix": `https://alfystar.github.io/LibreFolio/`.
3.  **Verifica**:
    *   Google chiederà di caricare un file HTML (es. `google12345.html`).
    *   Scarica il file.
    *   Mettilo in `mkdocs_src/docs/google12345.html`.
    *   Fai il deploy (`./dev.py mkdocs deploy`).
    *   Clicca "Verifica" su GSC.
4.  **Sitemap**: Invia la sitemap a GSC (`https://alfystar.github.io/LibreFolio/sitemap.xml`).

---

## 4. Roadmap Operativa

### Fase 1: Fondamenta (Subito)
- [x] Aggiungere `site_description` e `site_author` in `mkdocs.yml`.
- [x] Ottimizzare la Home Page (`index.md`) con keyword e struttura chiara.
- [x] Creare pagina "Credits & Legal" per trasparenza e trust.
- [x] Implementare asset grafici (icone PNG) per migliorare l'UX.
- [ ] Verificare il sito su Google Search Console (metodo file HTML).
- [ ] Inviare sitemap a GSC.

### Fase 2: Ottimizzazione Contenuti (Durante la scrittura)
- [ ] Rinominare i titoli H1 per essere più descrittivi (es. "Installation" -> "Docker Installation Guide").
- [ ] Assicurarsi che le immagini abbiano l'attributo `alt` (es. `![Dashboard Screenshot](...)` invece di `![image](...)`).

### Fase 3: Off-Page (Quando il prodotto è stabile)
- [ ] Aggiungere "Topics" al repository GitHub: `personal-finance`, `self-hosted`, `portfolio-tracker`.
- [ ] Linkare la documentazione dal `README.md` principale del repo (in alto).
- [ ] Postare su Reddit (r/selfhosted, r/personalfinance) linkando alla documentazione per casi d'uso specifici.

## 5. Note su Dominio Personalizzato
Se in futuro acquisterai un dominio (es. `librefolio.org`):
1.  Configura il DNS.
2.  Aggiorna `site_url` in `mkdocs.yml`.
3.  Aggiungi il file `CNAME` in `docs/CNAME`.
4.  GitHub Pages gestirà automaticamente i redirect 301 dal vecchio URL `github.io` al nuovo dominio (molto importante per non perdere SEO).
