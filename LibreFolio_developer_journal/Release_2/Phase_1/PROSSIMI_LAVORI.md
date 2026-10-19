# Prossimi lavori: richieste degli utenti e lotti dopo lo sprint

Il file ha due parti:
1. **Lotti della 1.3 non ancora iniziati**: lavoro pianificato per la 1.3 e mai partito, da confermare dopo lo sprint
   attuale;
2. **Richieste degli utenti**: il registro delle richieste arrivate dagli utenti (il file si chiamava
   `RICHIESTE_UTENTI.md`, rinominato il 19/10).

**La regola** (developer, 19/10): prima finiamo lo sprint attuale, poi si parte con questi lotti. Se si va lunghi, la
prima parte può diventare un `BACKLOG_POST_1.3`.

---

## Lotti della 1.3 non ancora iniziati (dopo lo sprint attuale)

Elenco del 19/10, dal resoconto del coordinatore e dai piani dei workstream. Non ci sono i lotti già dentro lo sprint.
Per ogni lotto: chi lo fa, cos'è, lo stato e il link al punto dove è descritto bene. I link sono relativi a questa
cartella; il testo del link riporta il titolo della sezione da cercare nel file.

### W · Import e transazioni: il riordino mai fatto

Quattro lotti del riordino pianificato in testa alla 1.3 non sono mai partiti. Aspettavano un commit del coordinatore su
`api/v1/brokers.py` e `api/v1/uploads.py` che non è venuto, poi la coda dei difetti li ha superati.

#### W3 · Il router dei broker diviso per risorsa

- **Chi**: W.
- **Cos'è**: `api/v1/brokers.py` (1 254 righe, due router: `/brokers` e `/brokers/import`) diventa il pacchetto
  `api/v1/brokers/`, un modulo per risorsa (`crud.py`, `access.py`, `brim_files.py`, `brim_parse.py`,
  `brim_catalog.py`, forma C2). Riordino puro: stessi URL, stesso ordine delle rotte, stessi `operationId`.
- **Stato**: ❌ non iniziato; `api/v1/brokers.py` è ancora un file solo (verificato il 19/10).
- **Dove**: [piano 04, «7. Lotti e checkpoint» (riga W3) e «5.1 Coordinamento» (Q7–Q10,
  C2)](04_importTransactions/plan-phase01ImportTransactions.prompt.md);
  nel backlog [«T-P2.2 · I file grandi del backend, divisi per cuciture»](../Phase_0/BACKLOG_POST_1.2.md).

#### W4 CP7 · Il taglio di `brim_provider.py` per tema

- **Chi**: W.
- **Cos'è**: la seconda metà di T-PL5. CP6, la rinomina in `services/brim/`, è entrato il 15/10. CP7 taglia
  `services/brim/brim_provider.py` (2 349 righe) per tema: il contratto resta in `brim_provider.py`, così i plugin non
  cambiano; escono `storage.py` (file, lock, sidecar), `combined_files.py`, `parsing.py`, `candidates.py` e
  `duplicates.py`. Lo stato di modulo (`_BROKER_LOCKS`) sta in un modulo solo, con la guardia contro le patch mute dei
  test (C4).
- **Stato**: ❌ non iniziato; il disegno è scritto.
- **Dove**: [piano 04, «W4 — CP6–CP7, PL5: `services/brim/`», nota «Disegno di CP7
  (taglio)»](04_importTransactions/plan-phase01ImportTransactions.prompt.md);
  nel backlog [«T-PL5 · `brim_provider.py` diventa `services/brim/`»](../Phase_0/BACKLOG_POST_1.2.md).

#### W5–W6 · Icone e report d'esempio nella cartella di ogni plugin (U-B3, U-B4)

- **Chi**: W; per la rotta delle icone (`serve_plugin_static` in `uploads.py`) d'accordo con H.
- **Cos'è**: oggi `brim_providers/static/` e `brim_providers/sample_reports/` stanno alla radice della famiglia. U-B3
  porta le icone in `broker_<x>/static/`, con la rotta generica e `generate_static_url` nelle 3 basi. U-B4 porta i
  report d'esempio in `broker_<x>/sample_reports/` (`malformed/` e il README restano alla radice), con i percorsi di
  E2E, fixture, test e doc.
- **Stato**: ❌ non iniziato (verificato il 19/10).
- **Dove**: [piano 04, «2. Voci assegnate: esito della verifica» (righe U-B3 e
  U-B4)](04_importTransactions/plan-phase01ImportTransactions.prompt.md); nel backlog [«U-B3 · Le icone dentro la
  cartella del plugin» e «U-B4 · `sample_reports/` per plugin»](../Phase_0/BACKLOG_POST_1.2.md);
  [piano 45, «9. Backlog post-1.2 (sezione U)»](../Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md).

#### K2b/K2c · Il 400 del parse e l'anteprima illeggibile, a codice

- **Chi**: W in origine; K2b è stato preso da E come **C-70b** (più sotto).
- **Cos'è**: le parti (b) e (c) di C-70: il 400 del parse strutturato a codice e tradotto nel wizard, e il codice
  dell'anteprima di un Excel illeggibile (`preview_unreadable_workbook`). K2c nel piano è solo nominato, senza un
  contenuto suo.
- **Stato**: 🟡 K2a ✅ 15/10; K2b continua come C-70b, a metà e parcheggiato.
- **Dove**: [piano 04, «7. Lotti e checkpoint» (riga K2)](04_importTransactions/plan-phase01ImportTransactions.prompt.md);
  il lavoro vero è nella voce C-70b qui sotto.

### W · Import e transazioni: difetti, richieste ed esplorazioni

#### K3a · La sicurezza dei dati del Bulk e del Form

- **Chi**: W (i rossi dal test-author).
- **Cos'è**: 5 difetti della modifica multipla e del form, da curare prima di ogni funzione nuova di K3:
  - K-4: un cambio di lingua col Bulk aperto rilancia l'apertura e **perde le modifiche non salvate**;
  - B-47: un focus e un blur sulla cassa, senza modifiche, segnano la riga come cambiata («scartare?»);
  - K-2: sul percorso lento, il form o il wizard chiusi dall'utente si riaprono a caricamento finito;
  - K-3: «Reset all» non salta il segnaposto `inaccessible`;
  - B-48: il tetto delle 15 cifre significative, come nel backend, su quantità e cassa.

  In più K-3b, trovata scrivendo i rossi: dopo un reset la coppia può sparire dalla griglia.
- **Stato**: ⏸️ parcheggiato il 19/10. Scritti 26 rossi Vitest e 1 E2E; il secondo giro dei rossi non è mai girato e
  la cura non è mai stata applicata. Patch e cura sono nella cartella di sessione di W (`files/parked/`). Le scelte
  fatte da W (PC5 diviso, valori nel dominio, K-3b nello stesso lotto) tornano come domande alla ripresa.
- **Dove**: [piano 04, «K3a — sicurezza dei dati del Bulk e del
  Form»](04_importTransactions/plan-phase01ImportTransactions.prompt.md); l'analisi è in [piano 04, «K3 — analisi in
  sola lettura»](04_importTransactions/plan-phase01ImportTransactions.prompt.md).

#### V-37b · «⚡ Validate now» come pre-controllo completo

- **Chi**: W (è K3c).
- **Cos'è**: la richiesta del developer del 13/10. Nel form delle transazioni ⚡ resta sempre cliccabile. Al clic
  controlla prima i campi obbligatori, poi il formato; se qualcosa non va, il rosso va su tutte le celle in errore e il
  fuoco sulla prima, senza chiamare il server. Vale per singola, coppia e FX. Il minimo e la data (1b) sono chiusi
  nella 1.2.
- **Stato**: ❌ non iniziato. D-K3-7 (coordinatore, 17/10): nella 1.3, dopo K3b. Circa 1,5–2 giorni, 2–4 chiavi i18n,
  `form.en.md` e galleria.
- **Dove**: [piano 46, «12.15 V-37: analisi del «valid» accanto a un errore del
  form»](../Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md) (il pre-step completo); [piano 04, «K3 —
  analisi in sola lettura», punto 7](04_importTransactions/plan-phase01ImportTransactions.prompt.md) (il punto di
  partenza nel codice di oggi); nel backlog
  [«V-37 · Nel form, «valid» accanto a un errore che blocca Apply»](../Phase_0/BACKLOG_POST_1.2.md).

#### W-B86 e W-B87 · «Noto in silenzio, ignoto con avviso» negli altri plugin di import

- **Chi**: W.
- **Cos'è**: il principio deciso dal developer il 19/10. Una riga che il plugin sa scartare con certezza esce in
  silenzio (al più nel log); una riga che non conosce o non sa leggere esce con un avviso e il link «apri una issue»
  (`report_issue`). Così gli utenti fanno da canarini quando un broker cambia l'export. Danske Bank (W-B85) è dentro
  lo sprint; qui restano gli altri plugin.
  - **W-B86** (medio, chiarezza): 25 plugin saltano righe con un avviso a stringa per riga, che non può portare il
    link. Proposta: un aiuto unico in `_brim_io.py`, con due codici condivisi (`rows_not_recognized`,
    `rows_unreadable`), e un test di contratto su tutti i plugin. DEGIRO, Scalable e Crédit Agricole hanno già note a
    codice: basta `report_issue`. Circa 1,5 giorni.
  - **W-B87 (peso alto, numeri)**: plugin che saltano in silenzio righe con un effetto economico. Revolut (stock
    split), Trading 212 (split, distribuzione di azioni, conversione di valuta), eToro (commissioni overnight, i loro
    rimborsi, la tassa SDRT); con un avviso per riga, Trade Republic (Kosten/Belasting), Swissquote (gambe forex) e
    IBKR (FX senza ISIN). Quantità dopo uno split, costi e tasse escono sbagliati senza che l'utente lo sappia.
    Proposta: almeno l'avviso con `report_issue`; l'import vero, plugin per plugin, dopo.
- **Decisione del 19/10**: il principio va solo sui plugin non in beta; quelli in beta si saltano, perché non abbiamo
  campioni affidabili.
- **Stato**: ❌ non iniziato; analisi e inventario fatti.
- **Dove**: [piano 04, «W-B85 · «Noto in silenzio, ignoto con avviso»: analisi», punti 3 e
  4](04_importTransactions/plan-phase01ImportTransactions.prompt.md);
  nel backlog [«W-B86 · Gli altri plugin BRIM col principio …» e «W-B87 · Plugin che saltano in silenzio righe con un
  effetto economico»](../Phase_0/BACKLOG_POST_1.2.md).

#### Crédit Agricole sui report set: esplorazione, prima l'analisi

- **Chi**: W.
- **Cos'è**: la richiesta del developer del 19/10. Esplorare il passaggio del plugin Crédit Agricole
  (`brim_providers/broker_credit_agricole/`) ai report set nati col pilota Danske Bank: più export dello stesso conto
  uniti in un quadro solo (ruoli conto e titoli, righe in coppia, saldo iniziale come punto di verità). Oggi CA sono
  due import separati, con le gambe `auto_cash`, il taglio a mano della lista titoli e il deposito a mano del saldo
  iniziale. Abbiamo gli export veri: si prova, poi si decide se l'unione regge, con quali limiti, e se il lavoro fatto
  oggi su CA si conserva in parte o si butta.
- **Nodi già noti**: i dati già importati col modello vecchio (le gambe `auto_cash` dei trade ora in coppia), il conto
  esportabile solo per 2 anni e la storia titoli più vecchia, il saldo iniziale nel CSV, i file CA caricati prima dei
  set.
- **Stato**: ❌ non iniziato; era la L3 del backlog della 38 («decisione di prodotto»).
- **Dove**: [design dei report set, «7.2 Crédit Agricole (dopo il
  pilota)»](../phases/26_brimDanskeBank/design-phase00BrimReportSets.md); [piano 26, «2.9 CA (dopo il pilota, fuori da
  questo piano)»](../phases/26_brimDanskeBank/plan-phase00BrimDanskeBank.prompt.md);
  [backlog della 38, «L3 · Crédit Agricole sui report set (§2.9, A10)»](../Phase_0/38_postReleaseBacklog/README.md);
  doc per sviluppatori [`credit_agricole.md`](../../../mkdocs_src/docs/developer/backend/brim/credit_agricole.md) e
  [`danske_bank.md`](../../../mkdocs_src/docs/developer/backend/brim/danske_bank.md).

### X · Plugin, asset e ricerca

Proposta di X (19/10) per tutti e quattro: dopo la 1.3. CP6 (F05) e K-20 sono già nello sprint.

#### CP5 · PL7, il router dei segnali

- **Chi**: X.
- **Cos'è**: un router proprio per i segnali, con gli URL invariati (T-PL7). Oggi `api/v1/signals.py` (63 righe) ha
  solo `/signals/preview`; i pezzi dei segnali stanno in `api/v1/assets/prices.py` e in `api/v1/fx/currencies.py`.
  Riordino puro: stessi URL e `operationId`, nessun effetto per l'utente.
- **Stato**: ❌ non iniziato; la precondizione (PL1 di J) c'è. Tocca i router che l'isolamento dei segnali di X-R16
  cambia.
- **Dove**: [piano 03, «Stato vero di CP5, CP6, CP7, CP8, CP12»](03_pluginsAssets/plan-phase01PluginsAssets.prompt.md);
  nel backlog [«T-PL7 · Un router proprio per i segnali, con gli URL invariati»](../Phase_0/BACKLOG_POST_1.2.md).

#### CP7 · FE4, il frontend dei cambi in `lib/features/fx/`

- **Chi**: X.
- **Cos'è**: spostare `components/fx/*`, `stores/fxStoreRegistry.ts`, `stores/fx/*` e gli helper solo dei cambi in
  `lib/features/fx/`, con X-R9, X-R10 e X-R14. Solo rinomina e import.
- **Stato**: ❌ non iniziato. Aspetta il lotto A dei colori: le due pagine dei cambi sono ancora nella baseline del
  ratchet.
- **Dove**: [piano 03, «4.2 Riordino frontend» e «Stato vero di CP5, CP6, CP7, CP8,
  CP12»](03_pluginsAssets/plan-phase01PluginsAssets.prompt.md).

#### FE5a · Il frontend degli asset in `lib/features/assets/` (il resto di CP8)

- **Chi**: X.
- **Cos'è**: spostare `components/assets/*` e gli helper degli asset (`utils/{assetPriceDerived,assetSimilarity,
  assetGrouping,assetIdentifiers}`) in `lib/features/assets/`. Solo rinomina e import; i tagli FE5b e FE5c sono già
  fatti. Y4a (i segnali di Y) aspetta FE4 e FE5a.
- **Stato**: ❌ non iniziato. Aspetta il lotto A dei colori: 12 file degli asset erano ancora nella baseline (X, su
  `f69f613ab`). Del resto di CP8 sono fatte O-8, O-20, K-16 e O-9; K-20 è nello sprint; K-19 viene dopo la lista di
  Rischio (developer, 06/10).
- **Dove**: [piano 03, «4.2 Riordino frontend» e «Stato vero di CP5, CP6, CP7, CP8,
  CP12»](03_pluginsAssets/plan-phase01PluginsAssets.prompt.md).

#### CP12 · Le impostazioni dei plugin anche per BRIM e Tool

- **Chi**: X (la parte BRIM con W).
- **Cos'è**: oggi `PluginSettingsMixin` (impostazioni per utente o per istanza, con i segreti, migrazione 007) sta solo
  nelle basi dei plugin di asset e cambi. CP12 lo porta nelle basi dei plugin BRIM e dei Tool.
- **Stato**: ❌ non iniziato; le precondizioni ci sono (CP10, PL5). Oggi nessun plugin BRIM o Tool chiede impostazioni.
- **Dove**: [piano 03, «9. Lotti e checkpoint (ordine proposto)», punto 12, e «Stato vero di CP5, CP6, CP7, CP8,
  CP12»](03_pluginsAssets/plan-phase01PluginsAssets.prompt.md).

### E e W · Le traduzioni dei rifiuti dell'import

**Scelta aperta** (resoconto del 19/10): (a) C-70b così com'è, E-21 dopo; (b) C-70b ed E-21 insieme, più grande
(circa 60 messaggi per 4 lingue).

#### C-70b · I rifiuti del parse e dell'anteprima tradotti (K2b di W)

- **Chi**: E; W rivede.
- **Cos'è**: oggi il 400 del parse e gli errori dell'anteprima arrivano in inglese. C-70b li rende oggetti a codice
  `{code, message, context}`, come `BRIMRefusal`: `cannot_parse`, `plugin_not_found` e `parse_failed` per il parse;
  `preview_unreadable`, `preview_unsupported`, `preview_engine_missing` e `preview_sheet_not_found` per l'anteprima. Il
  frontend li traduce (8 chiavi × 4 lingue). Traduce la **cornice**: la frase del plugin resta inglese (E-21).
- **Stato**: 🟡 a metà, parcheggiato il 19/10. Il backend è fatto ma non committato: patch nella cartella di sessione di
  E (`files/parked/c70b-k2b-20261019.patch`). Da fare: il frontend, le chiavi, il runner, la doc e la riga del
  CHANGELOG. Tre domande del test-author restano aperte per la ripresa.
- **Dove**: [piano 08, «C-70b — I rifiuti del parse e dell'anteprima tradotti (K2b di W)», fino a «C-70b.2 —
  Parcheggiato»](08_email/plan-phase01Email.prompt.md); nel backlog [«C-70 · I rifiuti di lettura dei plugin di
  import sono solo in inglese»](../Phase_0/BACKLOG_POST_1.2.md).

#### E-21 · Le frasi dei plugin tradotte

- **Chi**: E (voce aperta dal coordinatore il 17/10); W rivede.
- **Cos'è**: dentro la cornice tradotta di C-70b, il motivo resta la frase inglese del plugin: circa 60 `raise
  BRIMParseError(...)` in più di 30 plugin. La cura, nello stile di K2a: un codice e un contesto per ogni causa che
  l'utente può correggere, tradotti dove lo dice la regola R1 di `gate-plugin-i18n-ownership`, e il risolutore di
  C-70b che li preferisce alla frase.
- **Stato**: ❌ non iniziato; nel backlog era «dopo la 1.3».
- **Dove**: nel backlog [«E-21 · Le frasi `BRIMParseError` dei plugin arrivano in inglese, dentro la cornice
  tradotta»](../Phase_0/BACKLOG_POST_1.2.md); [piano 08, «C-70b.1 — Le risposte, e i rossi al
  `test-author`»](08_email/plan-phase01Email.prompt.md).

---

## Richieste degli utenti

Registro tecnico delle richieste arrivate dagli utenti (issue, discussioni, chat), con lo stato reale nel codice,
la decisione del developer e i task che ne derivano. Una sezione per richiesta, la più recente in alto.

Convenzioni:
- **Stato**: 💬 in discussione con l'utente · 📋 deciso, da pianificare · 🚧 in lavorazione · ✅ fatto · ⛔ non lo faremo.
- Il task, quando entra in un rilascio, prende un codice del backlog (`BACKLOG_POST_1.2.md`) e qui si scrive il link.
- Su GitHub (18/10): etichette `priority: …` / `effort: …` / `blocked`, milestone `1.3.0` e `1.4.0`.
- **Le issue sono degli utenti** (decisione del developer, 19/10): noi non apriamo issue nostre, né ombrelli né task. I
  task che nascono da una richiesta si tengono qui (e nel backlog quando entrano in un rilascio). Le issue #54, #55 e
  #56, aperte da noi il 18/10, sono state cancellate il 19/10; il loro testo è nei file della sessione del
  coordinatore.

---

## Utente @Xgialippo (GitHub, 17/10/2026) — usa Fineco

### #48 · Grafico delle singole posizioni sovrapposte — 💬 (direzione decisa dal developer, 18/10)

**Richiesta.** Un grafico come «Crescita del Portafoglio», ma con una linea per ogni posizione più il portafoglio
intero, «base 100», con la possibilità di escludere una posizione dal grafico (come la legenda del grafico Abs).

**Stato nel codice (18/10).**
- Esiste per i **lotti**: `features/brokers/lots/LotComparisonChart.svelte` (`lotComparisonChartHelpers.ts`),
  sezione «Confronto Valore / Rendimento» (`user/dashboard/positions.*.md` §4). Modo **Rendimento**: un
  «Rendimento aggregato» più una linea per ogni lotto **selezionato** nella tabella dei lotti, in **Abs** o **%**,
  con «Auto / Da 0». Modo **Valore**: aree impilate (valore residuo + incassi + proventi).
- Esiste in parte per gli **asset**: l'indicatore «Confronto Asset» nella pagina dell'asset sovrappone il prezzo di
  **un** altro asset; in modalità % le due curve partono da 0 %.
- Nella Dashboard, scheda «Le tue posizioni» (`PositionsPanel`, sottoschede «Portafoglio» e «Periodo»), il dettaglio
  lotti (`LotsAnalysisPanel`) si apre **sotto** il pannello delle posizioni con `?asset=<id>`
  (`routes/(app)/dashboard/+page.svelte`, `openAssetPanel` / `closeAssetPanel`).

**Decisione del developer (18/10).**
- Si fa la **soluzione 2: il rendimento della posizione**, non l'andamento del prezzo dell'asset. Include acquisti,
  vendite e proventi, come il grafico dei lotti.
- Due viste: **Abs** (P&L in denaro) e **%**, dove **la % è proprio il «base 100»** richiesto dall'utente.
- **Linee, non aree impilate**: un rendimento o un P&L può essere negativo (e una posizione corta ha valore
  negativo), quindi un grafico impilato non regge. Il valore per asset nel tempo c'è già nello storico
  dell'allocazione.
- **Dove**: un grafico sotto «Le tue posizioni» → «Portafoglio».
  - La tabella «Portafoglio» si evolve con i **selettori di riga come la tabella dei lotti**: senza selezione il
    grafico mostra la linea del portafoglio; le righe selezionate aggiungono le loro linee; la legenda le accende e
    le spegne. Così il grafico resta leggibile anche con molti asset.
  - **«Dettaglio lotto» sostituisce il portafoglio**: chiedendo il dettaglio lotti di una posizione, al posto della
    tabella «Portafoglio» (e del suo grafico) compare il dettaglio lotti richiesto, non più sotto.
  - Serve **un modo per tornare al portafoglio** uscendo dal dettaglio lotti (un comando «← Portafoglio» ben
    visibile; anche il «indietro» del browser, visto che il dettaglio è già guidato da `?asset=`).

**Note tecniche per la pianificazione.**
- Riuso: la logica e i gesti di `LotComparisonChart` (selezione → linee, Abs/%, legenda). Va generalizzata a
  «serie per posizione» invece di «serie per lotto», o affiancata da un componente gemello.
- Backend: serve una **serie giornaliera per posizione** (P&L e base per la %) sul periodo. Il motore la conosce già
  (`daily_state`), ma va esposta **solo per le posizioni selezionate**, su richiesta, per non appesantire il report.
- % «base 100»: per una posizione aperta a metà periodo serve la stessa regola del grafico dei lotti
  («Auto / Da 0»: da dove parte la linea). La linea del portafoglio usa il rendimento già calcolato della Dashboard.
- Posizioni corte o con valore negativo: la % va calcolata su una base in valore assoluto, come le altre % del
  periodo (`period_pnl / |start_value|`); da fissare con un test.
- Matematica nella casa (`financial_math/`), regola 10.

**Prossimo passo.** Risposta pubblicata dal developer il 18/10 (in attesa della replica dell'utente); poi analisi
tecnica e codice del backlog quando entra in un rilascio.

### #52 · Portafoglio diviso in sezioni / obiettivi — 💬 chiesto all'utente come raffinare l'idea (18/10)

**Richiesta.** Raggruppare gli asset per obiettivo («i pilastri di Coletti»: fondo emergenze, pensione…), con
sottogruppi o tag, e filtrare la Dashboard per gruppo.

**Stato nel codice.** La Dashboard si filtra solo per broker. Ripiego oggi: più «broker» separati, scomodo con un
solo conto reale.

**Idea già appuntata dal developer** (`TODO_FUTURI.md`, tra le idee sparse): creare dei **«Portafogli»**, cioè
gruppi di broker, di asset o di entrambi, da approfondire. Collegamenti nello stesso file: la distribuzione
proporzionale esplicita per broker del PAC/Rebalancer (futura, «PAC/Rebalancer — Profili Persistenti e Strategie
Estese») e il benchmark persistente per portafoglio/broker (Risk Analysis).

**Domande poste all'utente (18/10)**, per arricchire il task prima di farlo:
- lo stesso asset appartiene sempre a un solo obiettivo, o va diviso fra più obiettivi (a quote o a lotti)?
- gruppi di broker, di asset, o tutti e due?
- cosa si aspetta di vedere per ogni portafoglio: Dashboard filtrata, KPI e allocazione propri, un'allocazione
  obiettivo per il PAC?

### #51 · TER degli ETF e del portafoglio — 📋 nel TODO (18/10), dopo l'ambiente centralizzato degli asset

**Richiesta.** Vedere il TER di ogni ETF e il TER complessivo del portafoglio.

**Stato nel codice.** Il TER arriva solo dal plugin justETF, e solo come testo nella descrizione dell'asset
(`asset_source_providers/justetf/plugin.py`, «TER: x%»); con il potenziamento di Yahoo (#50) arriverà nello stesso
modo anche per gli ETF seguiti con Yahoo. Non è un campo.

**Decisione del developer (18/10).** L'idea è buona ma arriva solo dopo aver ragionato bene e creato un ambiente
centralizzato per le informazioni degli asset. Annotata in `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset»,
sottosezione «Prime idee d'uso dei dati in comune»: il TER medio pesato è il primo esempio di un fatto per asset
aggregato sul portafoglio, da estendere ad altre voci una volta identificate.

### #50 · Investing.com / TradingView e composizione degli ETF — 📋 potenziamento Yahoo deciso (18/10); il resto in `TODO_FUTURI.md`

**Richiesta.** (1) La composizione degli ETF arriva solo da justETF, da Yahoo solo il prezzo; (2) aggiungere
Investing.com o TradingView come provider; (3) esposizione per singola azienda e per emittente del fondo.

**Stato nel codice.** justETF dà paesi e settori (`FAGeographicArea`, `FASectorArea`) e il TER come testo; Yahoo dà
prezzi, dividendi e split.

**Verifiche (18/10).**
- **Yahoo espone i dati dei fondi, LibreFolio non li legge.** `yfinance` 1.7.0, `Ticker(...).funds_data`:
  `top_holdings` (prime 10 con peso), `sector_weightings` (11 settori), `asset_classes`, `bond_holdings`,
  `bond_ratings`, `fund_operations` (TER, «Annual Report Expense Ratio»), `fund_overview` (emittente, tipo legale).
  Prova dal vivo su VOO, SWDA.MI, VWCE.DE, CSPX.L, IWDA.AS, EUNL.DE: tutti con top 10 e settori; TER su 5 su 6
  (manca per VWCE.DE). Manca la ripartizione per **paese**, che dà solo justETF. Nessuna verifica precedente
  trovata (wiki, giornale, sessioni): l'idea «Yahoo non li espone» non era verificata, ed è sbagliata.
- **Anche justETF dà più di quanto usiamo.** `justetf_scraping.get_etf_overview` (`EtfOverview`): `ter`,
  `top_holdings`, `holdings_date`, `fund_provider`, `fund_size_eur`, `replication`, `currency_hedged`,
  `fund_currency`, `fund_domicile`, `index`, `inception_date`, `distribution_frequency`, `countries`, `sectors`.
  Il plugin oggi usa solo `description`, `ter` (come testo), `distribution_policy`, `countries`, `sectors`.
- **Condizioni d'uso delle fonti** (non è un parere legale):
  - justETF, AGB §3.1 (letto nel PDF): l'utente deve astenersi da «Einsatz von Programmen zur automatisierten
    Kursabfrage»;
  - Borsa Italiana / Euronext: dati riservati, il download automatico e il riuso richiedono licenza (dai termini
    pubblicati, non letti clausola per clausola);
  - Yahoo: i termini limitano l'accesso automatico e la ridistribuzione; l'uso personale con yfinance è tollerato
    nei fatti, non autorizzato.
  - In self-hosted (ogni istanza interroga per il suo utente, a basso volume, senza ridistribuire) il rischio è
    basso. **In un servizio ospitato a pagamento diventa uso commerciale** (lo interroghiamo noi per clienti paganti):
    rischio molto più chiaro → servono dati con licenza (fornitore a pagamento, F06) o la chiave dell'utente.
- **Investing.com e TradingView**: niente API ufficiali; i termini vietano la lettura automatica anche agli abbonati
  → niente provider, nemmeno a pagamento.
- **Strada standard a pagamento**: API di data vendor con chiave personale (EODHD Fundamentals, Financial Modeling
  Prep, Finnworlds; Morningstar/LSEG a livello enterprise), con TER e posizioni dei fondi per ISIN. LibreFolio 1.3
  ha già le impostazioni dei plugin con segreti per utente o per istanza (migrazione 007): un plugin a pagamento
  con la chiave dell'utente è la via pulita.

**Decisione del developer (18/10).**
- **Subito: potenziare il plugin Yahoo con i dati che Yahoo dà e che LibreFolio già sa tenere** (per la 1.3.0). Task:
  - per ETF e fondi (`quoteType` `etf` / `mutualfund`), la **distribuzione per settore** da
    `funds_data.sector_weightings` in `classification_params.sector_area` (`FASectorArea`), con la mappatura dei settori
    di Yahoo sui nostri (`validate_sector`), come fa già justETF; oggi Yahoo dà un settore solo per le azioni
    (`info["sector"]`);
  - nella **descrizione** (`short_description`), quando manca `longBusinessSummary`, la descrizione del fondo
    (`funds_data.description`); e, come fa già justETF, **TER ed emittente in coda alla descrizione**
    («TER: x%», da `fund_operations` e `fund_overview.family`);
  - tutto in `fetch_asset_metadata` (`asset_source_providers/yahoo_finance/plugin.py`), con la stessa politica
    d'errore (un dato del fondo che manca non fa fallire i metadati), dentro il thread del core;
  - test: rossi prima, su un `funds_data` finto (settori, TER mancante come per VWCE.DE, fondo senza dati);
    documentazione `user/assets/providers` di Yahoo (cosa offre) e dev `provider_yahoo_finance.md`.
- **Dopo, da studiare bene**: le posizioni dei fondi, le classi di attivo, le obbligazioni, il TER come campo e
  tutto ciò che justETF dà in più → `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset» (priorità medio-alta).
- **Investing.com e TradingView** → `TODO_FUTURI.md`, stessa voce, «Possibili prossime fonti», insieme a extraETF:
  priorità bassa-media, da alzare se portano titoli o classi di titoli che Yahoo, justETF e Borsa Italiana non
  coprono. Il provider CSS Scraper permette già di provare a leggere un prezzo da una loro pagina.
- **Risposta pubblicata dal developer (18/10)**: ha invitato l'utente a scrivere lui i plugin e a proporre una PR
  («il sistema è modulare apposta»).

### #49 (discussione) · «Valore Iniziale» e «Valore Finale» — ✅ risposto (17/10), task aperti

**Risposta data.** Valore della posizione a inizio e a fine periodo, come la colonna «Valore» del Portafoglio; 0 se
la posizione non c'era all'inizio o era chiusa alla fine; il Valore Iniziale è la base delle % del periodo.

**Task promessi all'utente** (per la 1.3.0).
- La frase che spiega le due colonne c'è solo in `user/dashboard/positions.en.md` (riga ~96): portarla in
  `positions.it.md` (e fr/es).
- Un tooltip sulle colonne «Valore Iniziale» e «Valore Finale» (`dashboard.startValue` / `endValue`, oggi senza
  tooltip; le colonne sono nascoste di default).

**Domanda aperta all'utente.** Fineco funziona bene con i suoi report? Se sì, togliere l'etichetta Beta (collegata a
C-91 del backlog: collaudare gli import di Interactive Brokers e Fineco su report veri).

### #47 · Inserire il prezzo unitario invece dell'importo — 📋 risposto (18/10)

**Richiesta.** Nel modulo «Nuova transazione», poter scrivere il prezzo medio unitario invece dell'importo totale.

**Risposta data.** Si aggiunge la scelta «Importo totale / Prezzo unitario», con l'altro valore calcolato; l'importo
risultante resta visibile e modificabile, perché `prezzo × quantità` può differire dall'addebito reale per gli
arrotondamenti. Spiegato anche che il valore di mercato usa il prezzo dell'asset, e solo senza prezzi l'ultimo
acquisto o l'ultima vendita.

**Task.** Il selettore nel modulo (`TransactionFormModal`, sezioni singola e coppia), con la quantità e la regola dei
decimali già in uso (W-B64, N63); valutare lo stesso selettore nella modifica multipla.
