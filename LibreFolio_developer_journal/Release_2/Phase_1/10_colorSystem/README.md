# 10 · Programma colori (dalla review della v1.2 ai token)

> Aperto il 14/10/2026 dal coordinatore colori (sessione «UI color analysis»), dopo la review colori della v1.2 con la
> designer. Fino al 14/10 sera stava in `Phase_0/55_colorSystem` e `Phase_0/56_galleryDeterminism`: il developer l'ha
> portato in `Phase_1` quando è arrivato il primo materiale della designer. I file `plan-phase00…` tengono il nome
> d'origine.
> Piano generale: [`plan-phase00ColorSystemThemeLab.prompt.md`](plan-phase00ColorSystemThemeLab.prompt.md) (decisioni, workstream, corsie).

## 🧭 Ripartire da qui

1. **Stato e decisioni:** testata del [piano generale](plan-phase00ColorSystemThemeLab.prompt.md), sezioni
   «Decisioni del developer» e «Workstream e corsie».
2. **Il materiale della designer**, un giro per cartella in [`designer-feedback/`](designer-feedback/):
   - giro 1 del 14/10, schermate di accesso e palette chiara e scura per tutto il progetto:
     [`2026-10-14-round1-auth/`](designer-feedback/2026-10-14-round1-auth/README.md);
   - giro 2 del 15/10, barra laterale verde, stati, risposte a N1–N6 e Q2–Q13, colori dei grafici GR1–GR5:
     [`2026-10-15-round2-palette/`](designer-feedback/2026-10-15-round2-palette/README.md), con
     [analisi e instradamento](designer-feedback/2026-10-15-round2-palette/analisi.md).
3. **Cosa c'è che non va nei colori, con file e righe:** [`analysis/00_SINTESI.md`](analysis/00_SINTESI.md) (P1–P11),
   poi i report di dettaglio:

   | Report | Argomento |
   |---|---|
   | [01](analysis/01_theme_foundation.md) | token, tema, tema scuro, contrasti, OKLCH contro hex |
   | [02](analysis/02_ui_components.md) | componenti |
   | [03](analysis/03_semantic_dynamic_logic.md) | funzioni che decidono i colori, test che li fissano |
   | [04](analysis/04_charts_dataviz.md) | grafici |
   | [05](analysis/05_history_color_studies.md) | storia delle decisioni sui colori |
   | [inventario](analysis/00_inventory_summary.md) | conteggi esatti |

4. **Il Designer Lab:** [`design-designerLab.md`](design-designerLab.md).
5. **Gli strumenti:** [`scripts/visual_review/README.md`](../../../../scripts/visual_review/README.md):
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
| `designer-feedback/` | Il materiale della designer, un giro per cartella: originali intatti, trascrizione, analisi | coordinatore |
| `designer-package-v1.2/` | Ciò che la designer ha ricevuto il 14/10: pagina d'ingresso, modello delle note, file di lavoro | storico |
| `coordination/` | Registro del coordinatore (corsie, checkpoint, decisioni) e analisi d'implementazione dei workstream, copie del 14/10 | coordinatore |
| `L-designerLab/` | Piano e progressi del workstream L (arriva con i merge di L) | L |
| `R-colorRefactor/` | Piano e progressi del workstream R (arriva con i merge di R) | R |
| `G-galleryDeterminism/` | Workstream G (rumore della gallery): README, evidenze, piano | G |
| `T-tokensTheme/` | Piano e progressi del workstream T, token e tema (arriva con i merge di T) | T |
| `DV-chartColors/` | Piano e progressi del workstream DV, colori dei grafici (arriverà con i merge di DV) | DV |

## Fuori dal repo

- **Cartella di lavoro del toolkit:** `LibreFolio_subRepo/LibreFolio_visual_review/`, accanto al checkout principale
  (predefinito di `scripts/visual_review`). Contiene:
  - snapshot della gallery;
  - diff e maschere del rumore;
  - il pacchetto per la designer;
  - le evidenze di G (`g-workstream/`).
- **Pacchetto inviato alla designer:** `LibreFolio_review_colori_v1.2.zip`, 122 MB. Si rigenera con
  `scripts/visual_review/build_designer_package.py`; in [`designer-package-v1.2/`](designer-package-v1.2/README.md) ci
  sono le sue parti di testo.
- **Inventario completo (CSV):** si rigenera con `scripts/visual_review/color_inventory.py`; i conteggi stanno in
  [`analysis/00_inventory_summary.md`](analysis/00_inventory_summary.md).

## Dati di riferimento

- **Commit dell'analisi:** `6d0b1266c`, con `frontend/src` identico a `27228466c`.
- **Snapshot della gallery** (fuori dal repo, nella cartella di lavoro del toolkit):
  - `baseline-r1` (2.816 PNG) e `baseline-r2` del 14/10, **cancellati il 19/10** per liberare disco; il rumore di allora
    resta misurato in [`G-galleryDeterminism/evidence/stability-2026-10-14.md`](G-galleryDeterminism/evidence/stability-2026-10-14.md);
  - **il riferimento attuale** è il trio del 18/10, `g-r3-prima-ba8e06763-full`, `g-r3-dopo-cd686f445-full` e
    `g-r3-dopo2-cd686f445-full`, con maschere e stabilità da `diffs/g-r3-dopo-cd686f445__vs__g-r3-dopo2-cd686f445`
    (vedi `scripts/visual_review/README.md`, «Known gallery behaviour»).
- **Pacchetto inviato alla designer il 14/10:** `LibreFolio_review_colori_v1.2.zip`, solo italiano, con 177 schermate
  in chiaro e scuro, desktop e mobile.
- **Giro 1 della designer:** ricevuto il 14/10 sera, in
  [`designer-feedback/2026-10-14-round1-auth/`](designer-feedback/2026-10-14-round1-auth/README.md). Alimenta la fase B
  (token per ruolo).
- **Giro 2 della designer:** ricevuto il 15/10 alle 15:03 e approvato dal developer (D-T17), in
  [`designer-feedback/2026-10-15-round2-palette/`](designer-feedback/2026-10-15-round2-palette/README.md). Alimenta
  T-8, DV e le ondate. Il pacchetto completo inviato, con le miniature della gallery, sta fuori dal repo in
  `LibreFolio_visual_review/package/round2-palette-2026-10-15/`.
- **Giro 3 della designer:** ricevuto il 17/10 sera (grafici; toast e banner), applicato nella notte, in
  [`designer-feedback/2026-10-17-round3-grafici/`](designer-feedback/2026-10-17-round3-grafici/README.md), con le
  scelte in `decisioni.md`. Il pacchetto con le domande del 19/10 (39–42), inviato quel giorno dal developer, sta in
  `LibreFolio_visual_review/package/LibreFolio_review_colori_giro3_2026-10-19.zip`.

## Chiusura del programma

- **Sito MkDocs, solo alla fine**, a colori definiti (decisione del developer del 14/10): aggiornare il sito di
  conseguenza.
  - Rigenerare le immagini della documentazione: le produce la gallery.
  - Allineare al nuovo marchio la palette del tema MkDocs Material.
  - Aggiornare le pagine developer sullo stile e sui colori (`styling`, `designer-lab`).
  - Prima di allora, nessun lavoro sul sito per i colori.
