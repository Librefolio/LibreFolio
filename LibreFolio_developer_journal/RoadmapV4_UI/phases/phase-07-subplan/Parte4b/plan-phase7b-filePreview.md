# Plan: File Preview System

**Data**: 18 Febbraio 2026
**Status**: 🔀 **ASSORBITO in Phase 7 — Parte 4b**
**Priorità**: Media
**Dipende da**: Phase 7 (Transactions) completata, Image Crop Modal completato ✅

> **📌 Aggiornamento 18 Aprile 2026**: questo piano autonomo è stato **incorporato** come
> **Parte 4b** del macro-plan di Phase 7. Vedere:
> - [`phase-07-transactions.md` §Parte 4b](../../phase-07-transactions.md)
>
> Il contenuto qui sotto resta come riferimento storico per il dettaglio tecnico (step
> backend/frontend, librerie, tipi, test E2E). Quando si implementerà la Parte 4b, usare
> questo documento come base per il **piano di dettaglio** `plan-phase07Part4b-FilePreviewSystem.prompt.md`,
> aggiornando:
> - Svelte 5 runes (`$state`, `$derived`, `$effect`) al posto di store
> - `ModalBase` esistente per la modale
> - `DataTable` esistente per preview tabellari
> - `data-testid` per selettori E2E
> - Integrazione in `BrokerImportFilesModal` (oltre a Files page)

> **📌 Riferimento aggiornato**: [`plan-phase05-to-08-upgrade.md` §7](../../../plan-phase05-to-08-upgrade.md)
> Questo piano è stato **spostato** da Phase 4.9 a Phase 7.5 perché ha più senso dopo che tutte
> le entità (brokers, assets, transactions, FX) sono disponibili per dare contesto ai file BRIM.
> Quando si arriva a implementare, aggiornare questo piano per:
> - Usare `PriceChartShared` per preview serie storiche CSV
> - Usare `DataTable` per preview tabellari
> - Usare `ModalBase` per la modale di preview
> - Integrare in Files page (entrambi i tab) e Broker Detail

---

## 🎯 Obiettivo

Implementare un sistema di preview dei file direttamente nell'interfaccia, senza necessità di scaricare l'intero file. La preview deve essere contestuale al tipo di file e
accessibile sia dalla pagina Files che dal broker detail (BRIM files).

---

## 📋 Requisiti Funzionali

### Tipi di File Supportati

| Categoria          | Estensioni                     | Comportamento Preview                          |
|--------------------|--------------------------------|------------------------------------------------|
| **Immagini**       | jpg, jpeg, png, gif, webp, svg | Mostra immagine con selector qualità           |
| **Testo**          | txt, log, json, xml, yaml, yml | Mostra contenuto con range righe selezionabile |
| **Markdown**       | md, markdown                   | Rendering markdown nel browser                 |
| **Tabellari**      | csv, xlsx, xls                 | Tabella interattiva con range righe            |
| **Codice**         | py, js, ts, html, css, sql     | Syntax highlighting + range righe              |
| **Binari/Archivi** | zip, tar, gz, pdf, etc.        | Solo download (no preview)                     |

### Comportamento UI

1. **Icona/Button Preview**: Visibile solo per file con preview supportata
2. **Modal Preview**: Si apre al click, con controlli specifici per tipo
3. **Controlli per Immagini**:
    - Slider qualità (25%, 50%, 75%, 100%)
    - Dimensioni originali mostrate
4. **Controlli per Testo/Tabelle**:
    - Input "Da riga" e "A riga"
    - Paginazione o scroll infinito
    - Conteggio righe totali (se disponibile)
5. **Markdown**: Toggle raw/rendered

### Posizioni

- Pagina `/files` - Tab Static: colonna azioni per ogni file
- Pagina `/files` - Tab BRIM: colonna azioni per ogni file
- Pagina `/brokers/[id]` - Sezione Import Files: colonna azioni

---

## 🔧 Step di Implementazione

### Step 1: Backend - Librerie & Setup (30 min)

#### 1.1 Dipendenze Python

```bash
cd backend
pipenv install python-magic  # File type detection
pipenv install openpyxl      # Excel reading (già presente?)
pipenv install markdown      # Markdown to HTML
```

**Verifica dipendenze esistenti**:

- `pandas` per CSV/Excel parsing
- `Pillow` per image preview (già usato)

#### 1.2 Configurazione

```python
# backend/app/config.py
# Aggiungere costanti per preview
PREVIEW_MAX_LINES = 100  # Max righe per default
PREVIEW_MAX_FILE_SIZE_MB = 50  # Max size per preview testuale
```

---

### Step 2: Backend - API Endpoints (2h)

#### 2.1 Nuovo modulo: `backend/app/services/file_preview.py`

```python
"""
File Preview Service

Handles preview generation for different file types.
"""
from enum import Enum
from pathlib import Path
from typing import Optional
import mimetypes

class PreviewType(str, Enum):
    IMAGE = "image"
    TEXT = "text"
    MARKDOWN = "markdown"
    TABLE = "table"
    CODE = "code"
    UNSUPPORTED = "unsupported"

def detect_preview_type(filename: str, mime_type: Optional[str] = None) -> PreviewType:
    """Detect preview type from filename/mime."""
    ext = Path(filename).suffix.lower()
    
    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}:
        return PreviewType.IMAGE
    elif ext in {'.md', '.markdown'}:
        return PreviewType.MARKDOWN
    elif ext in {'.csv', '.xlsx', '.xls'}:
        return PreviewType.TABLE
    elif ext in {'.txt', '.log', '.json', '.xml', '.yaml', '.yml'}:
        return PreviewType.TEXT
    elif ext in {'.py', '.js', '.ts', '.html', '.css', '.sql'}:
        return PreviewType.CODE
    else:
        return PreviewType.UNSUPPORTED

def get_text_preview(filepath: Path, start_line: int = 1, end_line: int = 100) -> dict:
    """Get text file preview with line range."""
    ...

def get_table_preview(filepath: Path, start_row: int = 1, end_row: int = 50) -> dict:
    """Get CSV/Excel preview as JSON rows."""
    ...

def get_markdown_preview(filepath: Path, render: bool = True) -> dict:
    """Get markdown preview, optionally rendered to HTML."""
    ...
```

#### 2.2 Nuovi Endpoint API

**File**: `backend/app/api/v1/uploads.py`

```python
@router.get("/files/{file_id}/preview")
async def preview_file(
    file_id: int,
    start_line: int = Query(1, ge=1),
    end_line: int = Query(100, ge=1),
    render_md: bool = Query(True),
    img_quality: int = Query(100, ge=25, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> FilePreviewResponse:
    """
    Get file preview based on type.
    
    Returns:
    - preview_type: image|text|markdown|table|code|unsupported
    - content: preview content (varies by type)
    - metadata: file info, total_lines, etc.
    """
    ...
```

**File**: `backend/app/api/v1/brokers_import.py`

```python
@router.get("/files/{file_id}/preview")
async def preview_brim_file(
    file_id: int,
    start_line: int = Query(1, ge=1),
    end_line: int = Query(100, ge=1),
    # ... same params
) -> FilePreviewResponse:
    """Preview BRIM file (typically CSV/Excel)."""
    ...
```

#### 2.3 Schema Response

**File**: `backend/app/schemas/uploads.py`

```python
class FilePreviewResponse(BaseModel):
    preview_type: str  # "image" | "text" | "markdown" | "table" | "code" | "unsupported"
    content: Optional[str | list[dict]]  # Text/HTML string or JSON rows for tables
    metadata: FilePreviewMetadata

class FilePreviewMetadata(BaseModel):
    filename: str
    mime_type: str
    total_lines: Optional[int]
    total_rows: Optional[int]
    file_size_bytes: int
    preview_start: int
    preview_end: int
    # For images
    original_width: Optional[int]
    original_height: Optional[int]
    preview_quality: Optional[int]
```

---

### Step 3: Frontend - Librerie & Setup (15 min)

#### 3.1 Dipendenze npm

```bash
cd frontend
npm install marked            # Markdown parser
npm install dompurify         # HTML sanitizer for markdown
npm install highlight.js      # Syntax highlighting (optional)
```

#### 3.2 Tipi TypeScript

```typescript
// frontend/src/lib/types/preview.ts
export type PreviewType = 'image' | 'text' | 'markdown' | 'table' | 'code' | 'unsupported';

export interface FilePreviewResponse {
    preview_type: PreviewType;
    content: string | Record<string, unknown>[];
    metadata: FilePreviewMetadata;
}

export interface FilePreviewMetadata {
    filename: string;
    mime_type: string;
    total_lines?: number;
    total_rows?: number;
    file_size_bytes: number;
    preview_start: number;
    preview_end: number;
    original_width?: number;
    original_height?: number;
    preview_quality?: number;
}
```

---

### Step 4: Frontend - Componenti UI (3h)

#### 4.1 FilePreviewModal

**File**: `frontend/src/lib/components/ui/media/FilePreviewModal.svelte`

```svelte
<!--
  FilePreviewModal - Modal for previewing files inline

  Props:
  - open: boolean
  - fileId: number
  - filename: string
  - fileType: 'static' | 'brim'
  
  Features:
  - Auto-detects preview type from backend
  - Image: quality slider
  - Text/Code: line range selector
  - Table: row range selector + DataTable rendering
  - Markdown: toggle raw/rendered
-->
```

#### 4.2 Preview Type Components

| Componente               | Scopo                                   |
|--------------------------|-----------------------------------------|
| `ImagePreview.svelte`    | Mostra immagine con zoom/quality slider |
| `TextPreview.svelte`     | Mostra testo con line numbers           |
| `MarkdownPreview.svelte` | Render markdown con toggle raw          |
| `TablePreview.svelte`    | Usa DataTable per JSON rows             |
| `CodePreview.svelte`     | Syntax highlighting                     |

#### 4.3 Integrazione FilesTable

**File**: `frontend/src/lib/components/files/FilesTable.svelte`

```svelte
<!-- Nella colonna actions, aggiungere: -->
{#if canPreview(file)}
    <button
        class="action-btn"
        on:click={() => openPreview(file)}
        title={$t('files.preview')}
        data-testid="file-preview-btn"
    >
        <Eye size={16} />
    </button>
{/if}
```

#### 4.4 Utility Function

```typescript
// frontend/src/lib/utils/filePreview.ts
export function canPreview(filename: string): boolean {
    const ext = filename.split('.').pop()?.toLowerCase();
    const previewable = [
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
        'txt', 'log', 'json', 'xml', 'yaml', 'yml',
        'md', 'markdown',
        'csv', 'xlsx', 'xls',
        'py', 'js', 'ts', 'html', 'css', 'sql'
    ];
    return previewable.includes(ext || '');
}
```

---

### Step 5: Integrazione Broker Detail (1h)

#### 5.1 BrokerImportFiles.svelte

Aggiungere stessa logica preview alla tabella file BRIM nel broker detail.

#### 5.2 API Routing

I file BRIM usano endpoint diverso (`/api/v1/brokers/import/files/{id}/preview`) ma stesso schema response.

---

### Step 6: Traduzioni i18n (15 min)

```bash
./dev.py i18n add "files.preview" --en "Preview" --it "Anteprima" --fr "Aperçu" --es "Vista previa"
./dev.py i18n add "files.previewTitle" --en "File Preview" --it "Anteprima File" --fr "Aperçu du fichier" --es "Vista previa del archivo"
./dev.py i18n add "files.quality" --en "Quality" --it "Qualità" --fr "Qualité" --es "Calidad"
./dev.py i18n add "files.lineRange" --en "Lines" --it "Righe" --fr "Lignes" --es "Líneas"
./dev.py i18n add "files.fromLine" --en "From line" --it "Da riga" --fr "De la ligne" --es "Desde línea"
./dev.py i18n add "files.toLine" --en "To line" --it "A riga" --fr "À la ligne" --es "Hasta línea"
./dev.py i18n add "files.totalLines" --en "Total lines" --it "Righe totali" --fr "Lignes totales" --es "Líneas totales"
./dev.py i18n add "files.totalRows" --en "Total rows" --it "Righe totali" --fr "Lignes totales" --es "Filas totales"
./dev.py i18n add "files.showRaw" --en "Show raw" --it "Mostra raw" --fr "Afficher brut" --es "Mostrar raw"
./dev.py i18n add "files.showRendered" --en "Show rendered" --it "Mostra renderizzato" --fr "Afficher rendu" --es "Mostrar renderizado"
./dev.py i18n add "files.previewUnsupported" --en "Preview not available for this file type" --it "Anteprima non disponibile per questo tipo di file" --fr "Aperçu non disponible pour ce type de fichier" --es "Vista previa no disponible para este tipo de archivo"
```

---

### Step 7: Test E2E (1h)

#### `frontend/e2e/file-preview.spec.ts`

```typescript
// Test image preview with quality selector
test('image preview shows quality slider', async ({ page }) => {...});

// Test text preview with line range
test('text preview shows line range controls', async ({ page }) => {...});

// Test table preview renders in DataTable
test('csv preview renders as table', async ({ page }) => {...});

// Test markdown toggle
test('markdown preview toggles raw/rendered', async ({ page }) => {...});

// Test preview not shown for binary files
test('binary file shows download only, no preview', async ({ page }) => {...});

// Test preview in broker detail
test('brim file preview works in broker detail', async ({ page }) => {...});
```

---

## 📊 Stima Tempo

| Step                        | Tempo   | Note                       |
|-----------------------------|---------|----------------------------|
| Step 1: Backend Setup       | 30 min  | Librerie, config           |
| Step 2: Backend API         | 2h      | Endpoints, service, schema |
| Step 3: Frontend Setup      | 15 min  | Librerie, tipi             |
| Step 4: Frontend Components | 3h      | Modal + tipo-specifici     |
| Step 5: Broker Detail       | 1h      | Integrazione               |
| Step 6: Traduzioni          | 15 min  | CLI i18n                   |
| Step 7: Test E2E            | 1h      | Playwright                 |
| **Totale**                  | **~8h** | 1 giorno lavorativo        |

---

## 📁 File da Creare/Modificare

### Backend

| File                       | Azione    | Descrizione                                  |
|----------------------------|-----------|----------------------------------------------|
| `services/file_preview.py` | **Nuovo** | Logica preview per tipo                      |
| `schemas/uploads.py`       | Modifica  | `FilePreviewResponse`, `FilePreviewMetadata` |
| `api/v1/uploads.py`        | Modifica  | Endpoint `/files/{id}/preview`               |
| `api/v1/brokers_import.py` | Modifica  | Endpoint `/files/{id}/preview`               |
| `config.py`                | Modifica  | Costanti preview                             |

### Frontend

| File                               | Azione    | Descrizione                |
|------------------------------------|-----------|----------------------------|
| `types/preview.ts`                 | **Nuovo** | Tipi TypeScript            |
| `utils/filePreview.ts`             | **Nuovo** | Utility `canPreview()`     |
| `ui/media/FilePreviewModal.svelte` | **Nuovo** | Modal principale           |
| `ui/media/ImagePreview.svelte`     | **Nuovo** | Preview immagini           |
| `ui/media/TextPreview.svelte`      | **Nuovo** | Preview testo              |
| `ui/media/MarkdownPreview.svelte`  | **Nuovo** | Preview markdown           |
| `ui/media/TablePreview.svelte`     | **Nuovo** | Preview tabelle            |
| `ui/media/CodePreview.svelte`      | **Nuovo** | Preview codice             |
| `files/FilesTable.svelte`          | Modifica  | Aggiungere bottone preview |
| `brokers/BrokerImportFiles.svelte` | Modifica  | Aggiungere bottone preview |
| `e2e/file-preview.spec.ts`         | **Nuovo** | Test E2E                   |

---

## ✅ Success Criteria

- [ ] Bottone preview visibile solo per file supportati
- [ ] Click apre modal con preview appropriata al tipo
- [ ] Immagini: slider qualità funzionante
- [ ] Testo: range righe selezionabile, contenuto aggiornato
- [ ] Tabelle: DataTable con JSON rows, paginazione
- [ ] Markdown: toggle raw/rendered
- [ ] Codice: syntax highlighting
- [ ] Binari: NO bottone preview
- [ ] Funziona in Files Page (Static + BRIM)
- [ ] Funziona in Broker Detail
- [ ] Dark mode styling corretto
- [ ] Mobile responsive

---

## 🔗 Dipendenze

- **Backend esistente**: Endpoint `img_preview` per immagini (già funzionante)
- **Frontend esistente**: `DataTable` component per tabelle
- **Librerie nuove**: marked, dompurify, highlight.js (frontend), markdown (backend)

---

## 📝 Note

- La preview backend deve essere efficiente (streaming per file grandi)
- Considerare cache per preview frequenti
- Security: sanitizzare HTML markdown prima del rendering
- Accessibilità: alt text per immagini, focus management nel modal

---

→ Follow-up: [`plan-phase07-transaction-Part4b_FilePreviewRecovery.prompt.md`](./plan-phase07-transaction-Part4b_FilePreviewRecovery.prompt.md)
