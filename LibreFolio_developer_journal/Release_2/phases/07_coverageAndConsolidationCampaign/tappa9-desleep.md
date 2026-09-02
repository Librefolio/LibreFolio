# Tappa 9 — le 159 sleep: 159 → 8

Chiuso il punto 1 di «Da fare ancora». **Delle 159 in gioco ne restano 8**, e tutte e 8 sono
deliberate e annotate sul posto (77,5 s → 15,7 s di attesa a orologio). Le 221 di
`gallery.spec.ts` restano fuori perimetro per scelta dell'utente.

**La regola che ha fatto la differenza, e che non era ovvia all'inizio:** togliere una sleep
davanti a qualcosa che **non ritenta** non rende il test più veloce, lo rende **muto** — e
continua a riportare verde. `count()`, `textContent()`, `getAttribute()`, `inputValue()`,
`evaluate()` e soprattutto `isVisible()` (il cui `timeout` è **ignorato**) non ritentano. Lì la
sleep va **trasformata**, non cancellata. Da qui `e2e/fixtures/probe.ts`: `appears`, `exists`,
`optionsClosed`.

## Le quattro forme incontrate, in ordine di frequenza

| forma | quante | rimedio |
|---|---|---|
| sleep prima di un matcher che ritenta già | ~70 | cancellata |
| sleep in fondo a un helper | ~50 | l'helper asserisce la **post-condizione che promette** |
| sleep davanti a una lettura one-shot | 29 | `appears()`/`exists()`, o matcher che ritenta |
| sleep fra due dropdown | 12 | `optionsClosed(page)` |

## Segnali di prodotto aggiunti perché mancavano

Ognuno serve prima all'utente e poi al test.

- **`DataTableToolbar` non diceva quante righe teneva**: `data-testid="selection-toolbar"` +
  `data-selected-count`. Ha sbloccato barriere in quattro spec diverse.
- **Lo stepper del wizard di import non diceva su quale passo era**: il passo corrente era
  distinguibile solo da classi CSS. Aggiunto `aria-current="step"`, che è il valore ARIA previsto
  esattamente per gli stepper. Il test di back-navigation usava un filtro di **testo**
  (`hasText: /Back/i`) su un pulsante che aveva già `data-testid="import-wizard-back"` — cioè una
  mina i18n messa lì per aggirare un'informazione mancante.
- **`<html>` non pubblicava lo stato di idratazione.** Il `+layout.svelte` scrive
  `data-i18n-ready`, quindi l'attributo **non esiste** finché il client non ha idratato:
  `waitForSelector('html[data-i18n-ready="true"]')` è insieme la barriera d'idratazione e quella
  delle traduzioni. Sostituisce la sleep in `navigateTo`, chiamata **112 volte**.

## Difetti trovati inseguendo le sleep

La sleep era il sintomo, non il problema.

1. `tx-brim-import:245` asseriva `expect(count).toBeGreaterThanOrEqual(0)` — **vero per qualsiasi
   conteggio mai esistito**. Terzo test della famiglia «passa senza testare».
2. `tx-broker-access:69` verificava che i broker del VIEWER fossero **assenti** da una tendina,
   senza alcuna barriera che provasse che la tendina avesse renderizzato: una tendina lenta era
   indistinguibile da un filtro corretto.
3. `TransactionBulkModal` indicizza le righe per **UUID dell'operazione pendente**, non per id di
   transazione, e **fonde una coppia in una riga sola**. Incrociare i due id è impossibile per
   costruzione; l'unica invariante onesta è `1 ≤ righe in stage ≤ righe selezionate`.

## Trappola da ricordare

`expect.poll()` su un **Locator** non applica il matcher che credi: `expect()` è sovraccaricato su
`Locator`, quindi `expect.poll(() => findRow(…)).toBeNull()` brucia tutto il timeout e fallisce su
una pagina dove la riga è dimostrabilmente sparita. Si polla un **numero**, o meglio si asserisce
`toHaveCount(0)` su un `data-row-id` catturato prima dell'azione.

## Ricadute

Regole **3**, **18** e **19** di `.github/agents/test-author.agent.md` aggiornate con la tabella
ritenta/non-ritenta, la trappola di `expect.poll`, la post-condizione degli helper e il prefisso di
testid condiviso.

## Verifica

`front-transaction` **219/219**, uscita 0 (`--workers 4`, load average 10–12).

---

## Coda — tre rossi che la corsa completa ha scoperto, e nessuno era una sleep

La corsa `all-frontend --workers 4` ha chiuso **619/620**, poi **618/620** al giro dopo. I rossi
non erano nei file de-sleepati: erano **la stessa famiglia dell'8.2**, «`.first()` non è mai
un'identità», in file che non avevo toccato. Con quattro worker che scrivono nello stesso
database, «il primo elemento» è l'oggetto che un vicino ha creato un secondo fa.

| test | prendeva | conseguenza |
|---|---|---|
| `asset-detail` (26 test, un helper solo) | la **prima card** della lista | un asset appena creato senza storia prezzi → ECharts non monta il canvas → sembra una regressione del grafico |
| `data-quality-banners` FX_PAIR_MISSING / FX_PAIR_NO_DATA | il **primo asset attivo** da `/assets/query` | un asset senza eventi → nessun evento a cui agganciare il problema FX → il banner non compare mai |
| `asset-event-delete` (×3) | — | cliccava una card **mentre la lista si ristampava** con i prezzi appena arrivati: il nodo veniva sostituito e la navigazione andava persa |

Correzioni: i primi due scelgono ora un asset **seminato per nome** (`Apple`, `Microsoft`,
`NVIDIA` — la convenzione già usata da `tx-wac-bulk`, `tx-wac-formmodal`,
`tx-commit-all-types`); il terzo aspetta `waitForSettled(assets-page)` prima di cliccare, che è
ciò che `goToAssetsPage()` faceva già e che quel file si era riscritto a mano senza.

`goToFirstAssetDetail` è stato rinominato `goToSeededAssetDetail`: il vecchio nome era diventato
una bugia.

## Rossi da carico, non chiusi

Su una macchina a load average 8–29 due test sono caduti una volta e sono tornati verdi al giro
successivo senza modifiche:

- `risk-analysis` «asset Risk runs typed scenarios» — `data-catalog` fermo su `pending` oltre i
  20 s. È il catalogo **globale** delle capacità, non dipende dall'asset scelto: latenza pura.
- `tx-wac-formmodal` FM3 — la seconda gamba del form doppio non risulta compilata al commit.
  Stessa famiglia di WB1/WB2/WB8/FM6, non indagata.

## Coda 2 — `toHaveCount(0)` non guarda la visibilità

Il quarto rosso, `files` «pdf preview hides comment button», **non** era carico: era
deterministico. Ed è la lezione dell'8.8 applicata male da me stesso.

La barriera di presenza che avevo aggiunto (`[data-epdf-i]` visibile prima di asserire
un'assenza) era giusta e ha funzionato: ha smesso di far passare il test *grazie* alla lentezza.
Ma ha smascherato che **anche l'assert era sbagliata**.

`toHaveCount(0)` conta i **nodi nel DOM**, la visibilità non la guarda. `@embedpdf` disabilita
una categoria **nascondendo** il controllo, non smontandolo. Quindi il pulsante c'era, e c'era
per progetto: la configurazione funzionava già.

La prova sta nello `error-context.md`, ed è il motivo per cui va letto *prima* di rilanciare:
lo snapshot di accessibilità **non elencava** il pulsante commenti — gli snapshot ARIA
escludono ciò che è nascosto — pur elencando il `search-button` che gli sta accanto nello
stesso gruppo. Due controlli fratelli, uno visibile e uno no: l'unica differenza è
`panel-comment` nella lista disabilitata.

Correzioni:

- l'assert diventa `toBeHidden()`, e **acquista i denti** con l'assert gemella
  `search-button` → `toBeVisible()`: se domani sparisse l'intera barra, «il pulsante commenti
  non si vede» tornerebbe vero per il motivo sbagliato;
- la lista in `FilePreviewModal` copre ora tutte e tre le definizioni di `comment-button` che il
  visualizzatore spedisce (`annotation`, `annotation-comment`, `panel-comment`), estratta in una
  costante con il *perché* accanto invece che in linea nella chiamata.

Va anche corretto a posteriori il racconto dell'8.8: la doppia lista **era** un difetto — con
`ui.disabledCategories` che sovrascrive la globale, la categoria `annotation` veniva persa e gli
strumenti di annotazione comparivano in un'anteprima di sola lettura. Ma non era *quel* pulsante:
il pulsante commenti era già nascosto. Il rosso di stanotte era il test, non il prodotto.
