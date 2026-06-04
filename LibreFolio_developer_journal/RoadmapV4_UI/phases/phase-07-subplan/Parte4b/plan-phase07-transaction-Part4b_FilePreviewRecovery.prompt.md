# Plan — Phase 7 Part 4b: File Preview System Recovery

← Previous: [`plan-phase7b-filePreview.md`](./plan-phase7b-filePreview.md)

**Date**: 2026-06-04
**Status**: ✅ COMPLETATO (delivery iniziale + recovery + polish finale)
**Priority**: P1 UX / mobile usability
**Estimated effort**: ~1 giorno pianificato, effettivo multi-sessione con rounds di stabilizzazione
**Predecessors**:
- ✅ Parte 4 — `/transactions` frontend shell completata
- ✅ Piano storico preview — [`./plan-phase7b-filePreview.md`](./plan-phase7b-filePreview.md)

**Successors**:
- ⏳ Parte 5 — Staging Modal unificata (indipendente dal preview shell)
- ⏳ Futuro opzionale: estendere stessa preview al Broker Detail se tornerà utile

**Macro plan parent**: [`../phase-07-transactions.md`](../phase-07-transactions.md) §"Parte 4b"

---

## 🎯 Obiettivo

Consegnare un sistema di **preview inline** per i file accessibili da `/files`, utile su desktop ma soprattutto su mobile, evitando download + apertura in app esterne.

Scope finale effettivamente consegnato:

1. **Static Resources tab** — preview inline da lista + grid.
2. **BRIM tab** — preview inline dei file import broker.
3. **Tipi supportati**: image, text, markdown, CSV, XLSX, XLS, PDF.
4. **Esperienza preview-first**: modale unica, metadata coerenti, scroll interno stabile, dark mode, dettagli errore leggibili.

---

## ✅ Scope finale vs piano storico

| Tema | Piano storico `plan-phase7b-filePreview.md` | Decisione finale Part 4b | Esito |
|------|---------------------------------------------|---------------------------|-------|
| Posizione feature | Files page + Broker Detail | **Files page (Static + BRIM)** subito; Broker Detail rinviato | ✅ Ridotto intenzionalmente |
| Immagini | Slider qualità manuale | **Niente slider**: preview ottimizzata a zoom 1x, originale oltre 1x | ✅ Più semplice / più utile |
| Markdown | Raw/rendered | **Confermato**, con render più curato + KaTeX | ✅ |
| Testo | Viewer raw | **Confermato**, restyling document-like | ✅ |
| CSV/XLSX/XLS | DataTable generica | **CheetahGrid** spreadsheet-style, più vicina a Excel | ✅ Migliore fit |
| PDF | Solo download nel piano storico | **Reader embedded** con UI viewer-only | ✅ Esteso |
| Codice syntax-highlight | Previsto | **Non prioritario** in questo slice | ⏸️ Rinviato |
| Annotazioni PDF | Non definite | **Disabilitate**: niente persistenza lato LibreFolio | ✅ Decisione prodotto |

---

## 🧩 Deliverable implementati

### Backend

- `backend/app/services/file_preview.py`
  - detection unificata preview type
  - lettura preview per text / markdown / table / image / pdf
  - mapping engine Excel esplicito:
    - `.xlsx` → `openpyxl`
    - `.xls` → `xlrd`
- endpoint preview riusati per Static + BRIM con payload coerente
- error messages più onesti quando manca reader engine

### Frontend

- `frontend/src/lib/components/files/FilePreviewModal.svelte`
  - modale preview unica multi-tipo
  - image viewer con zoom + switch automatico a source originale + drag-pan
  - text viewer con line numbers e superficie neutra
  - markdown raw/rendered con typography migliorata + KaTeX
  - table viewer via `cheetah-grid`
  - PDF embedded viewer con annotation/comment UI disabilitata
- `frontend/src/routes/(app)/files/+page.svelte`
  - state machine preview
  - surfacing di `detail` backend via helper condiviso
- `frontend/src/lib/components/files/FilesTable.svelte`
  - doppio click → preview immediata
- `frontend/src/lib/components/files/FileGrid.svelte`
  - doppio click → preview immediata
- `frontend/src/lib/components/ui/ModalBase.svelte`
  - body/html scroll lock stabile, senza leak sullo sfondo

### Seed data / manual test support

- `backend/test_scripts/test_db/populate_mock_data.py`
  - static resources demo per preview:
    - markdown sample
    - txt sample
    - PDF/XLS/XLSX sample da `backend/staticResources/FilePreviewSamples/`
    - avatar immagini già presenti

### Coverage

- `backend/test_scripts/test_api/test_uploads_api.py`
  - test reale preview `.xls`
- `frontend/e2e/files.spec.ts`
  - preview markdown
  - preview image
  - detail backend surfacing
  - vertical scroll interno immagine
  - comment button PDF nascosto
  - preview tabellare BRIM

---

## 🔧 Recovery / stabilization rounds completati

### 1. Refinement UX dopo primo walktest

- size file resa human-readable via helper già esistente
- doppio click per aprire preview in entrambi i tab
- immagini: quality perceived migliorata usando `source_url` originale quando si supera 1x
- drag-pan aggiunto al viewer immagini

### 2. Seed di file realistici

- utente ha aggiunto sample PDF/XLS/XLSX
- populate DB esteso per mostrare sample previewabili in Static Resources
- nessun CSV statico extra: restano validi quelli broker già presenti

### 3. Fix root-cause di scroll / layout

- problema reale non era solo image pan
- root cause: catena `height: 100%` senza parent con altezza definita + ownership scroll confusa
- fix:
  - altezza esplicita shell preview
  - `preview-body` come vero contenitore flex
  - renderer interni con `flex: 1; min-height: 0; overflow`
  - scroll lock globale della pagina sotto la modale

### 4. Error handling onesto

- prima il FE mostrava solo `e.message`
- ora il modal mostra `response.data.detail` quando FastAPI lo fornisce
- esempio pratico: errore `.xls` con engine mancante

### 5. Restore legacy `.xls`

- `.xls` è rimasto **in scope**
- fix applicato su due livelli:
  1. backend con engine selection deterministica
  2. runtime con `xlrd`
- nota ambiente:
  - `Pipfile` dichiarava già `xlrd`
  - refresh lock via `pipenv install/lock` è stato bloccato da problema SSL locale
  - runtime corrente sbloccato con install diretta nel virtualenv

### 6. PDF viewer-only cleanup

- annotazioni/commenti non persistono in LibreFolio
- UI comment/annotation nascosta via config viewer, non via hack CSS sul DOM
- risultato: preview pulita, coerente con feature realmente supportate

### 7. Polish text + markdown

- text viewer:
  - niente più toolbar encoding invasiva
  - sfondo meno terminal-style
  - spacing gutter migliorato
- markdown viewer:
  - headings / lists / tables / blockquotes / code blocks sistemati
  - formule LaTeX renderizzate via KaTeX
  - scroll interno corretto

### 8. Polish finale visuale

- preview Excel ora realmente dark in dark mode, non solo container esterno
- bordo PDF ritoccato con tono grigio/slate più leggibile

---

## 🗂️ File chiave toccati

| Area | File | Ruolo |
|------|------|-------|
| Backend | `backend/app/services/file_preview.py` | core preview service + engine Excel |
| Backend | `backend/test_scripts/test_db/populate_mock_data.py` | sample preview seed |
| Backend | `backend/test_scripts/test_api/test_uploads_api.py` | regression `.xls` |
| Frontend | `frontend/src/lib/components/files/FilePreviewModal.svelte` | renderer unico preview |
| Frontend | `frontend/src/routes/(app)/files/+page.svelte` | orchestrazione preview + error surfacing |
| Frontend | `frontend/src/lib/components/ui/ModalBase.svelte` | scroll lock |
| Frontend | `frontend/src/lib/components/files/FilesTable.svelte` | preview on double-click |
| Frontend | `frontend/src/lib/components/files/FileGrid.svelte` | preview on double-click |
| Frontend | `frontend/e2e/files.spec.ts` | regression coverage |

---

## 📋 Outcome finale

Parte 4b è stata **consegnata** con focus pragmatico:

- preview inline utile su `/files`
- supporto reale per image / text / markdown / csv / xlsx / xls / pdf
- errori leggibili
- scroll stabile
- mobile value alto perché non richiede app esterne

L'idea storica è stata quindi **attualizzata**: si è conservato ciò che dava valore reale, scartando invece complessità non necessarie (slider qualità manuale, code preview, integrazione Broker Detail immediata).

---

## ✅ Verifica finale eseguita

- `cd frontend && npm run check`
- `./dev.py test api uploads`
- `./dev.py test front-utility files`

---

## Note finali

- Questo file funge da **piano di recupero + recap implementativo** della Parte 4b.
- Il piano storico resta come riferimento di partenza, ma la fonte aggiornata dello stato finale è questo documento.
