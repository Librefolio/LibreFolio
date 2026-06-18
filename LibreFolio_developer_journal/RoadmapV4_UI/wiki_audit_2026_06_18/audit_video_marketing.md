# Audit Documentazione: Area "Video Marketing"

## 1. Identificazione della Documentazione Esistente
Esplorando le directory del progetto `LibreFolio`, è emerso che non vi è una documentazione ufficiale pubblicata per l'area "Video Marketing" (Remotion, promo clip, AI assets) all'interno della cartella sorgente del sito MkDocs (`mkdocs_src/docs/`). L'unica traccia ufficiale è un commento HTML nella pagina principale (`docs/index.en.md`) che indica una sezione video temporaneamente rimossa (`<!-- Video Section: Temporaneamente rimosso (Work in Progress) -->`).

Tuttavia, esiste una ricca base di documentazione sotto forma di piani di sviluppo (Developer Logs/Plans) posizionata all'esterno della root di MkDocs, in particolare nella directory:
`mkdocs_src/videoClipPrject/01_plan/`

I file identificati includono:
- `master_plan.md`
- `plan_01_home.md`
- `plan_02_video.md`
- `plan_02_video_setup.md`
- `plan_03_openAi.md`
- `ai_assets_prompts.md`

Tali file contengono i dettagli sull'architettura Remotion, sull'inizializzazione del progetto in `video_promo/`, sulla generazione degli asset AI, e sulla strategia multi-lingua (`en`, `it`, `es`, `fr`).

## 2. Valutazione dello Stato della Documentazione

In base ai criteri di valutazione richiesti:

*   **Completa e allineata agli standard estetici**: **Non applicabile**. Non esiste alcuna pagina MkDocs compilata che soddisfi gli standard estetici del sito.
*   **Completa ma da migliorare esteticamente**: I documenti di planning (`plan_02_video_setup.md` e `plan_03_openAi.md`) sono estremamente dettagliati dal punto di vista tecnico. Descrivono i comandi npm, l'architettura `i18n`, i placeholder per la generazione degli asset AI e il montaggio delle scene. Tuttavia, rimangono appunti e piani di lavoro, scritti in formato "checklist/roadmap" per chi ha sviluppato la feature iniziale, ma privi di un'esposizione didattica ottimizzata per il Developer Manual.
*   **Gap da colmare (Analisi del gap)**: Il divario principale è la totale assenza di questi contenuti tecnici all'interno del Developer Manual ufficiale di LibreFolio. Un nuovo sviluppatore che desiderasse aggiornare il video promozionale in seguito a un restyling della UI non saprebbe da dove iniziare senza dover scovare e decifrare le vecchie roadmap del progetto Remotion.
*   **Assente, proposta su dove e cosa scrivere per istruire altri dev**: La documentazione a regime è di fatto assente. È strettamente necessario migrare le nozioni chiave dai file di planning verso il manuale sviluppatori su MkDocs.

## 3. Proposta di Integrazione Documentale (Dove e Cosa Scrivere)

### Dove posizionare la documentazione
Si raccomanda di creare una nuova sezione all'interno del *Developer Manual* dedicata ai media e al marketing.
Una possibile collocazione in `mkdocs.yml` potrebbe essere:
```yaml
- Developer Manual:
    - ...
    - Marketing & Media:
        - Overview: developer/media/index.md
        - Promo Video (Remotion): developer/media/promo-video.md
        - AI Assets Generation: developer/media/ai-assets.md
```

### Cosa Scrivere
La nuova documentazione dovrà essere redatta in lingua inglese (come per policy del *Dev Manual*) per istruire i developer su come mantenere i video:

1.  **Promo Video (Remotion)**:
    *   **Introduzione a Remotion**: Spiegare che i video sono code-driven (React) e che il progetto risiede in `video_promo/`.
    *   **Architettura delle Scene**: Descrivere la pipeline in `MainVideo.tsx` e la struttura parametrica (`<Series>`) delle scene.
    *   **Gestione Multi-lingua (i18n)**: Indicare come vengono iniettati i testi tramite la prop `locale` basandosi sui dizionari presenti in `src/i18n/`.
    *   **Sincronizzazione Asset UI**: Creare una guida operativa su come effettuare gli screenshot della Dashboard (es. via Playwright o script di sync), e come posizionarli in `public/assets/{locale}/`.
    *   **Script di Build**: Spiegare il processo di esportazione finale (`npm run build:en`, `build:all`) che converte il codice in formati video standard (`.mp4`) per YouTube/Social.

2.  **AI Assets Generation**:
    *   **Pipeline Generativa**: Formalizzare i prompt base (attualmente in `ai_assets_prompts.md`) da fornire a strumenti di GenAI (come Gemini Imagen 3) per generare grafiche coerenti col brand (es. `chaos_bg.png`, `opensource_infographic.png`).
    *   **Integrazione**: Mostrare come inserire gli asset AI all'interno della cartella sorgente (`external_src/ai/`) e linkarli nel codice Remotion.

### Conclusione
Completare questa migrazione permetterà di chiudere il gap documentale, convertendo il pregevole lavoro architetturale descritto nei "plan" in vero e proprio capitale di conoscenza (knowledge base) manutenibile per la community open-source e il core team di LibreFolio.
