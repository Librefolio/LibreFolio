# 55 · Sistema colori (programma colori dopo la 1.2)

> Aperta il 14/10/2026 dal coordinatore, dopo la review colori della v1.2 con la designer.
> Piano generale: [`plan-phase00ColorSystemThemeLab.prompt.md`](plan-phase00ColorSystemThemeLab.prompt.md) (decisioni, workstream, corsie).

## 🧭 Ripartire da qui

1. **Stato e decisioni:** testata del [piano generale](plan-phase00ColorSystemThemeLab.prompt.md), sezioni
   «Decisioni del developer» e «Workstream e corsie».
2. **Cosa c'è che non va nei colori, con file e righe:** [`analysis/00_SINTESI.md`](analysis/00_SINTESI.md) (P1–P11),
   poi i report di dettaglio:

   | Report | Argomento |
   |---|---|
   | [01](analysis/01_theme_foundation.md) | token, tema, tema scuro, contrasti, OKLCH contro hex |
   | [02](analysis/02_ui_components.md) | componenti |
   | [03](analysis/03_semantic_dynamic_logic.md) | funzioni che decidono i colori, test che li fissano |
   | [04](analysis/04_charts_dataviz.md) | grafici |
   | [05](analysis/05_history_color_studies.md) | storia delle decisioni sui colori |
   | [inventario](analysis/00_inventory_summary.md) | conteggi esatti |

3. **Il Designer Lab:** [`design-designerLab.md`](design-designerLab.md).
4. **Gli strumenti:** [`scripts/visual_review/README.md`](../../../../scripts/visual_review/README.md):
   - snapshot della gallery, da confrontare solo con snapshot dello stesso giorno;
   - diff con classi di stabilità;
   - pacchetto per la designer;
   - server per la designer;
   - inventario.

## Contenuto

| Percorso | Cosa | Di chi |
|---|---|---|
| `plan-phase00ColorSystemThemeLab.prompt.md` | Piano generale: architettura a token, fasi, workstream, corsie, decisioni | coordinatore |
| `design-designerLab.md` | Progetto del Designer Lab | coordinatore (base del piano di L) |
| `analysis/` | Analisi colori v1.2 (14/10/2026): sintesi in italiano, report in inglese, inventario | storico: non si aggiorna |
| `L-designerLab/` | Piano e progressi del workstream L | L |
| `R-colorRefactor/` | Piano e progressi del workstream R | R |
| `../56_galleryDeterminism/` | Workstream G (rumore della gallery) | G |

## Dati di riferimento

- **Commit dell'analisi:** `6d0b1266c`, con `frontend/src` identico a `27228466c`.
- **Snapshot della gallery** (fuori dal repo, nella cartella di lavoro della sessione del coordinatore):
  - `baseline-r1` (2.816 PNG) e `baseline-r2` del 14/10;
  - rumore misurato in [`../56_galleryDeterminism/evidence/stability-2026-10-14.md`](../56_galleryDeterminism/evidence/stability-2026-10-14.md).
- **Pacchetto inviato alla designer il 14/10:** `LibreFolio_review_colori_v1.2.zip`, solo italiano, con 177 schermate
  in chiaro e scuro, desktop e mobile.
- **Il suo report è atteso:** quando arriva, va in `designer-feedback/` e alimenta la fase B (token per ruolo).
