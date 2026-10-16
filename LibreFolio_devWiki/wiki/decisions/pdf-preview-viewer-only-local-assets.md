---
title: "The PDF preview is a viewer only, with its engine and fonts served by the app: the CDN is a fallback, editing and the document menu are off, an empty viewer closes the preview"
category: decision
status: resolved
date: 2026-10-09
tags: [frontend, files, pdf, preview, embedpdf, pdfium, wasm, offline, privacy, gallery, workstream-m, release-1.2]
related:
  - features/F-050
  - decisions/gallery-is-a-release-gate-with-real-data
  - sources/phase00-release-images-and-gallery-2026-10
---

# Decision: read a PDF, never edit it, never need the internet for it

## Context

The file preview ([[features/F-050]]) shows PDFs with EmbedPDF, which runs the PDFium engine compiled to
WebAssembly. Each time it opened, it asked jsDelivr for the engine, its stamps and its fallback fonts, and Google
Fonts for its UI font: offline it never drew a page, and a slow CDN left it loading. The gallery's offline guard made
this visible — a third-party host fails the test ([[decisions/gallery-is-a-release-gate-with-real-data]]).

The viewer also offered what the preview cannot do, since it never saves: the Insert, Form and Redact modes, undo
and redo, and a document menu to open, close, print, protect, capture and export.

## Decision

The developer, through the coordinator, during M's batch 7 (2026-10-09), verbatim:

| Topic | Decision |
|-------|----------|
| Local assets | «si facciamolo subito, ma come fallback lasciamo lo scaricamento remoto, per resilienza» |
| Form, Redact, the «•••» menu | «disattivale, deve essere solo un visualizzatore, se nei 3 puntini ci fosse l'export, disattivalo o nascondilo» |
| The document menu | «togli tutto eccetto fullscreen e copia testo, che senso ha tenere una cosa che non funziona? tienila solo se non riesci a toglierla» |
| The viewer's own «Open Document» path | «lasciamolo ora e per sempre, mi pare un caso troppo limite, apuntiamocelo per evitare di tornarci in futuro, direttametne nel codice» |
| An empty viewer | «Chiudi l'anteprima quando il visore resta vuoto» |

Delivered in `1028a1978` («fix(files): local, viewer-only PDF preview»):

- **Local first.** `pdfViewerAssets.ts` ships the engine (`LOCAL_PDF_ENGINE`) and the Latin, Arabic and Hebrew
  fallback fonts (`LOCAL_FONT_FILES`) as build assets; the CDN is asked only when the local engine does not answer.
  The UI font follows the app; stamps and signature fonts are not loaded.
- **Viewer only.** `PDF_PREVIEW_DISABLED` lists the command categories to remove, from the toolbar and the keyboard
  alike: the editing modes, comments, undo and redo, and the document menu's open, close, print, protect, capture and
  export. Reading, full screen and copying selected text remain.
- **Protected PDFs** still ask for their password, which stays in the browser and goes when the preview closes; once
  the document opens, the preview reports ready instead of staying in error.
- **An empty viewer closes the preview.** After «Cancel» on the password prompt or «Close» on the error card, the
  viewer would show its empty state, whose «Open Document» opens any PDF from the user's disk and which no category
  removes. `onDocumentClosed` now calls `onRequestClose()` when no document is left, with the developer's note in the
  code beside it.

## Options Considered

- **CDN only** (as before): no preview offline, and a request to third parties at every opening.
- **Local only, no CDN:** refused by the developer, who kept the remote download as a fallback «per resilienza».
- **Our own message on the empty viewer** instead of closing: one of the three options put to the developer, who
  chose to close the preview; closing needed no new text.

## Consequences

- The image grows by about 7 MB. The CJK fallback fonts, 30–40 MB each, are still fetched on demand.
- EmbedPDF, PDFium and the Noto fonts are listed in `THIRD_PARTY_LICENSES.md`.
- `pdfPreviewState.ts` (`32d62640f`) publishes when the PDF has finished drawing (`data-state`, `aria-busy`), so the
  gallery and the tests wait for the page itself, not for the preview's fetch.
- **A fallback loop found on the way.** A unit guard found the viewer started 11 times when its start throws: the
  `!host` branch cleared `pdfError` whenever it ran, so the iframe fallback replaced the stage, the effect ran again,
  and the viewer failed again, round after round. It dated from `5b887dd3a` (2026-06-04), so it was in v1.1.0. The fix
  clears the error only when there is no source (`if (!sourceUrl) pdfError = null`); the fallback now starts the
  viewer once and the iframe stays.
- The user guide says the preview is read-only and that a protected PDF's password stays in the browser.

## Source files

| Role | Path |
|------|------|
| Preview modal (`PDF_PREVIEW_DISABLED`, the empty-viewer close, the fallback) | `frontend/src/lib/features/files/FilePreviewModal.svelte` |
| Local engine and fonts, CDN fallback | `frontend/src/lib/utils/files/pdfViewerAssets.ts` |
| Render state | `frontend/src/lib/utils/files/pdfPreviewState.ts` |
| Unit tests | `frontend/src/lib/features/files/FilePreviewModal.test.ts` |
| Asset tests | `frontend/src/lib/utils/files/pdfViewerAssets.test.ts` |
| E2E (the empty viewer closes) | `frontend/e2e/files.spec.ts` |
| Licences | `THIRD_PARTY_LICENSES.md` |
| User guide | `mkdocs_src/docs/user/files/index.en.md` |
| Journal (batch 7, step 20) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` |
