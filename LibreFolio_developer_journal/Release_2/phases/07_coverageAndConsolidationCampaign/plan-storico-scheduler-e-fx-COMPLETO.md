# Piano — scheduler nel fuso configurato, e il tasso FX che può mancare

Due corsie indipendenti, su file completamente disgiunti: possono correre in parallelo.

---

# Corsia 1 · Scheduler — invertire il punto di conversione (D1)

## Il problema, riformulato

La proposta iniziale era passare al modello `(giorno, ora)` per rendere esatta la
conversione di fuso. Ragionando con l'utente è emerso che il difetto non sta nel modello
ma in **dove convertiamo**.

Oggi: giorni e orari sono memorizzati in **UTC**, e la UI converte gli orari a schermo.
I giorni non li converte — non può, perché sono un insieme globale che non sa a quale
orario appartiene. Da qui «lunedì 21:00» per un lavoro che gira di domenica.

Invertendo: giorni e orari memorizzati **nel fuso configurato**, conversione in UTC una
sola volta nel backend, al momento di decidere se eseguire. Allora *«lun-sab alle 06:00 e
23:00, ora di Roma»* torna a essere un concetto rettangolare e ben definito, la UI non ha
niente da convertire, e **il difetto sparisce per costruzione**.

### Il guadagno che non avevamo visto: l'ora legale

Con gli orari in UTC, «le 09:00 di Roma» sono 08:00 UTC d'inverno e 07:00 d'estate: oggi
**il lavoro si sposta di un'ora due volte l'anno** senza che nessuno l'abbia chiesto. Il
codice sa già che è un problema — `_local_times_to_utc` esiste — ma lo applica solo ai
default del primo avvio.

### Il prezzo, accettato dall'utente

Il fuso smette di essere una lente di lettura e diventa **parte della definizione**:
cambiarlo sposta l'istante di esecuzione. È il contrario di quanto deciso per B2, ed è
stato ribaltato consapevolmente perché corrisponde all'aspettativa comune («voglio che
giri alle 6 del mattino, ovunque io sia»).

## Stato di partenza

| dove | cosa c'è oggi |
|---|---|
| `global_settings` | `scheduler_history_sync_times` = CSV `"06:00,23:00"` (UTC), `scheduler_history_sync_days` = CSV `"mon,…"`, `scheduler_timezone` = IANA, default `UTC` |
| `backend/app/services/scheduler/settings.py` | `_parse_times`, `_parse_days`, `_local_times_to_utc` (solo default) |
| `backend/app/services/scheduler/scheduler.py:42` | `due_history_sync`: due controlli indipendenti — giorno, poi orario |
| `backend/app/schemas/settings.py:114-133` | le descrizioni delle chiavi |
| `frontend/…/SchedulerConfigModal.svelte` | chip orari + chip giorni; la riconversione introdotta da B2 |

## Passi

**S-01 · Backend: la decisione converte, non lo storage.**
`due_history_sync` deve valutare ogni slot come istante nel fuso configurato. Attenzione:
il confronto «oggi è un giorno configurato?» va fatto sul **giorno locale**, non su
`now.strftime("%a")` in UTC. Usa `zoneinfo`, già usato altrove nel file.

**S-02 · Le descrizioni delle chiavi sono già sbagliate oggi.**
`scheduler_history_sync_times` dice *«(server local time)»* mentre il codice memorizza UTC,
e `scheduler_timezone` dice *«storage stays UTC»*. Dopo questo lavoro la prima diventa vera
e la seconda falsa: vanno riscritte entrambe, con la semantica nuova detta esplicitamente.

**S-03 · Migrazione dati (Alembic incrementale).**
Gli orari esistenti sono UTC e vanno riletti come locali. La scelta di fondo:

> **La migrazione preserva ciò che l'utente vede oggi nel modale, non l'istante assoluto.**
> L'utente ha configurato guardando quella schermata, quindi quello è il suo intento.

In pratica: convertire gli orari da UTC al fuso configurato, **lasciando i giorni
invariati**. Per le installazioni con `scheduler_timezone = UTC` — il default — la
migrazione è un **no-op**. Per le altre, l'esecuzione si sposterà una volta: è inevitabile,
va scritto nel changelog.

Regola di progetto: **nuova migrazione incrementale**, mai modificare `001_initial`.

**S-04 · Frontend: togliere la conversione, non aggiungerne.**
Rimuovere la riconversione dei chip introdotta da B2 (non serve più: ciò che si vede è ciò
che è memorizzato) e il suo test; al suo posto un **avviso** al cambio fuso, che dica che
gli orari resteranno questi numeri ma l'esecuzione si sposterà. Il test di caratterizzazione
`CHARACTERISATION: weekdays stay UTC…` va convertito: descrive un mondo che non esiste più.

**S-05 · Il ripiego sul browser diventa pericoloso.**
`SchedulerConfigModal.svelte:121`:
```ts
selectedTz = schedulerTimezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
```
Con impostazione vuota il modale adotta il fuso di **chi guarda**. Oggi cambia solo la
lente; domani cambierebbe quando gira il lavoro, e due admin in due continenti fisserebbero
orari diversi a seconda di chi salva per primo. Il ripiego va tolto: se l'impostazione è
vuota, `UTC` — che è già il default dello schema.

**S-06 · Test.**
Backend, con `zoneinfo`, e almeno: un fuso a ovest che sposta il giorno indietro, uno a est
che lo sposta avanti, **e due date a cavallo del cambio d'ora** che dimostrino che l'orario
locale non si muove. Quest'ultimo è il test che oggi fallirebbe.
Frontend: il payload salvato contiene gli orari **come mostrati**, e l'avviso compare al
cambio fuso.

---

# Corsia 2 · FX — un tasso che può mancare (D2)

## Il problema

`apiResultToFxDataPoint` (`frontend/src/lib/stores/fxStoreRegistry.ts:168`) converte un
`rate` null/undefined in **`0`**. È un'assenza travestita da valore, messa al confine con
l'API, quindi a monte di tutto.

E il backend il `null` lo dichiara: `backend/app/schemas/fx.py:157` ha
`rate: Optional[SafeDecimal] = Field(None, …)`, il client generato lo tipizza
`(string | null) | undefined`, lo Zod lo valida come unione con `null`. L'API dice «non ho
un tasso» e **il frontend butta via l'informazione nel punto in cui arriva**.

La correzione precedente ha difeso il tooltip. Gli altri consumatori non si difendono.

## I difetti veri, verificati

| dove | cosa fa oggi |
|---|---|
| `FxCard.svelte:92` | mostra `0.0000` come se fosse un cambio |
| `FxCard.svelte:109,122` | **il grafico disegna un crollo a zero** |
| `FxTable.svelte:103,196` | mostra `0.0000` in cella e **ordina** su quello zero |
| `fx/[pair]/+page.svelte:256,271` | mostra e disegna lo zero |
| `fx/[pair]/+page.svelte:264` | controlla solo `first===0`, non `last===0` → **può dare −100 %** |
| `assets/+page.svelte:947,1017` | gli overlay dei segnali FX calcolano sullo zero |
| `assets/[id]/+page.svelte:653` | idem |
| `FxDataEditorSection.svelte:79-88` | mostra `rate: 0` e al salvataggio lo **rifiuta** (`rate > 0`) |

L'ultimo è il più eloquente: espone un dato che lui stesso considera invalido.

## Passi

**F-01 · Il tipo onesto.** `FxDataPoint.rate: number | null`
(`fxStoreRegistry.ts:36`). Da lì il compilatore fa da guida: `svelte-check` elencherà i
siti da sistemare.

**F-02 · I tre convertitori/caricatori.** `apiResultToFxDataPoint` smette di schiacciare a
zero; `apiResultsToCanonicalFxDataPoints` smette di far entrare in cache il punto non
invertito; `lookupFxRate`/`lookupFxRateSync` si allineano.

**F-03 · I sette consumatori.** Card, tabella, pagina lista, pagina dettaglio, editor, e le
due pagine asset. Ognuno decide **esplicitamente** cosa mostrare in assenza di tasso — la
UI ha già la chiave `transactions.fxInfo.marketNotAvailable` come precedente.

**F-04 · I grafici: un buco, non una congiunzione.**
`LineDataPoint.value` è `number`, quindi un `null` non passa così com'è. **Decisione presa,
reversibile**: la linea deve avere un'**interruzione**, non congiungere i due estremi.
Congiungere disegnerebbe un andamento che non è mai esistito — è la stessa bugia dello
zero, solo più elegante. ECharts rende `null` come interruzione.
Verificare come i grafici trattano oggi i buchi (esiste già `staleDays` per i dati
riempiti all'indietro: c'è un precedente da seguire).

**F-05 · Il delta.** `fx/[pair]/+page.svelte:264` controlla solo l'estremo iniziale. Con
`null` il caso sparisce, ma la guardia va comunque resa simmetrica.

**F-06 · Test.** L'assenza deve essere coperta in ognuno dei tre strati: il convertitore che
non fabbrica più lo zero, i consumatori che mostrano l'assenza, il grafico che si
interrompe. Ogni negativo ha bisogno della sua **barriera di presenza** — «non mostra
0.0000» è vero anche in una pagina che non rende nulla.

---

# Fase finale

- Chiavi i18n dichiarate dalle corsie, applicate in un passaggio unico (le corsie **non**
  toccano `en/it/fr/es.json`).
- Registrazione nel runner dei file di test nuovi; `check-orphans` pulito.
- `prettier --check` e `svelte-check --threshold error` a zero; suite unit verde due volte.
- Corsa completa `--fresh-run --coverage all --workers 8 all`.
- Misura prima/dopo e messaggio di commit proposto (mai eseguito).

# Note e rischi

- **Il rischio maggiore è la migrazione dello scheduler**: tocca dati di installazioni già
  rilasciate. Deve essere un no-op verificabile per `scheduler_timezone = UTC`.
- **Il DST è la parte che si sbaglia in silenzio.** Un test che usa una sola data non lo
  vede. Servono due date, una per lato del cambio d'ora.
- `svelte-check` è la guida della corsia FX: cambiare il tipo per primo trasforma un lavoro
  di ricerca in una lista di errori da chiudere.
- Le due corsie sono disgiunte (`backend/…/scheduler/` + `SchedulerConfigModal` contro
  `stores/`, `utils/currency/`, `components/fx/`, `routes/…/fx/`, `routes/…/assets/`).
  Nessun file in comune.

# Punto di partenza

Suite 15/15 verde in 51m 19s, 3 713 vitest, 934 Playwright.
Linee **78,07 %**, arm di ramo **59,39 %**.
