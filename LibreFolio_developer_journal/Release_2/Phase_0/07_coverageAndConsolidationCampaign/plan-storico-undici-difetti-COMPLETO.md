# Piano — chiusura degli undici difetti aperti + fattorizzazione

## Problema

La corsia «impostazioni, condivisione, logica pura» ha lasciato **undici comportamenti
fissati come caratterizzazione**, non corretti, perché erano decisioni di prodotto. Le
decisioni sono arrivate. Ogni correzione renderà **rosso** il test che oggi fissa il
comportamento vecchio: quel rosso è il segnale che la modifica ha morso, e va convertito
nell'asserzione nuova, non silenziato.

In più l'utente ha chiesto una **fattorizzazione**: il trio *salva / annulla / ripristina*
è duplicato in tre famiglie (4 copie dentro `GlobalSettingsTab`, una per `value_type`; lo
stesso trio dentro i 5 controlli `Setting*`; il trio «di massa» in due header). È la
stessa forma del difetto già fuso in `SyncResultRow`.

## Approccio

**Una fase bloccante, poi sei corsie parallele, poi una validazione.**

La fattorizzazione tocca i componenti che le corsie `B-3` e `B-4` usano, quindi quelle due
aspettano. Ma verificando i file **realmente** toccati è emerso che le altre quattro sono
già disgiunte da essa e possono partire subito:

| corsia | file | sovrapposta alla fase A? |
|---|---|---|
| **A** fattorizzazione | i 5 `Setting*`, `SettingsLayout`, `GlobalSettingsTab`, `PreferencesTab` | — |
| **B-1** broker | `components/brokers/` | no → **parte subito** |
| **B-2** modali | i 3 modali in `settings/`, che la fase A non tocca | no → **parte subito** |
| **B-5** FX | `stores/`, `utils/currency/` | no → **parte subito** |
| **B-6** transazioni | `components/transactions/` | no → **parte subito** |
| **B-3** preferenze | `PreferencesTab` | **sì** → attende |
| **B-4** categoria Altro | `GlobalSettingsTab` | **sì** → attende |


### Due regole di coordinamento, entrambe già collaudate in questa sessione

1. **Nessuna corsia tocca i file i18n.** `en/it/fr/es.json` sono condivisi da quattro
   corsie: scritti in parallelo si corrompono. Ogni corsia **dichiara** le chiavi che le
   servono con i quattro testi; le applico io in un passaggio unico. I test asseriscono
   chiavi, non testo, quindi girano verdi anche prima che le stringhe esistano.
2. **Nessuna corsia tocca il runner.** Registro io i file nuovi in un passaggio solo.

---

## Fase A — fattorizzazione (bloccante, da sola)

**A-01. `SettingActions.svelte`** — il trio per riga, un componente solo.
Sostituisce: le 4 copie interne a `GlobalSettingsTab` (una per `value_type`) e il trio
ripetuto in `SettingCurrency`, `SettingNumber`, `SettingSelect`, `SettingTheme`,
`SettingToggle`.
Prende il meglio delle nove copie: `isSaving` (che oggi hanno solo due), i `data-testid`
già introdotti, `disabled` coerente. Il docblock deve elencare le divergenze trovate,
come fa `SyncResultRow`.

**A-02. `SettingBulkActions.svelte`** — il trio «di massa» per gli header di
`SettingsLayout` e `GlobalSettingsTab`.

**A-03. C7 — `isSaving` ai tre controlli che non ce l'hanno.**
Cade quasi da sé una volta che il trio è unico: `SettingCurrency`, `SettingSelect` e
`SettingTheme` acquistano la prop, e `PreferencesTab` — che lo stato **ce l'ha già** e lo
usa per `isBusy` — lo passa.

> Vincolo: i 289 test delle impostazioni devono restare verdi. Se qualcuno si rompe
> perché interrogava il markup duplicato, è informazione: va aggiornato, non aggirato.

---

## Fase B — sei corsie parallele su file disgiunti

### B-1 · Condivisione broker (A1 + A2)

**A1 — una lettura fallita non deve diventare una revoca.**
Se la `GET` della lista fallisce, il pannello resta modificabile **vuoto**, e siccome il
salvataggio è un rimpiazzo completo il primo *Salva* revoca tutti. Il pannello deve
rifiutare il salvataggio finché non ha letto, con messaggio esplicito e *riprova*.

**A2 — invariante: un broker ha sempre almeno un OWNER.**
Oggi la guardia esiste solo sulla **rimozione** (`BrokerSharingPanel.svelte:262`). Il
percorso di **modifica ruolo** (riga 245) non ha nulla: si retrocede l'ultimo owner a
`VIEWER` e si salva. Stesso stato finale, una sola strada chiusa.
- Estendere la guardia alla retrocessione — nessuna auto-retrocessione se si è l'ultimo.
- Sulla **rimozione**, il messaggio offre le due vie d'uscita volute dall'utente:
  promuovere un altro owner, oppure eliminare il broker con le sue transazioni.
  `DELETE /api/v1/brokers` esiste già e accetta `force`: **niente backend nuovo**.
- Sulla **retrocessione**, l'unica via d'uscita sensata è promuovere qualcun altro prima.

### B-2 · Modali impostazioni (B1 + B2 + B3)

**B1 — `PasswordChangeModal`: niente secondo invio dopo il successo.**
`isSubmitting` torna `false` subito ma la chiusura è a 1500 ms: nella finestra il Salva è
vivo *sotto* il messaggio di successo, e un secondo click manda la vecchia password → il
server risponde «password attuale errata» a chi l'ha appena cambiata, e il timer chiude
il dialogo sopra quell'errore.

**B2 — `SchedulerConfigModal`: il fuso è una lente di lettura, non una ridefinizione.**
Decisione: **(a)**. L'orario assoluto non cambia mai; cambiando fuso i chip vanno
**riconvertiti a schermo**. Oggi il fuso è letto solo all'apertura e al salvataggio, e i
chip non si muovono mai: apri su UTC, vedi `09:00`, passi a Bogotá, salvi → gira alle
14:00 UTC con `09:00` ancora sullo schermo.
*Primo passo della corsia*: confermare come il backend memorizza (UTC o fuso fisso) —
la conversione dipende da quello.

**B3 — `SchedulerLogModal`: un fallimento senza testo non è un successo.**

### B-3 · Preferenze e profilo (C1 + C2 + C3 + C4)

**C1 — applicare tema e lingua solo dopo la conferma del server.**
Oggi `applyTheme` e `currentLanguage.set` girano **prima** della PUT e il `catch` non
ripristina: il server rifiuta, l'utente vede un banner rosso **e l'app resta dipinta nel
tema che il server non ha mai memorizzato**. Al reload torna indietro da sola, senza
spiegazione. Decisione: applicare solo al salvataggio riuscito; in caso di errore, toast.

**C2 — «Ripristina tutto» diventa raggiungibile.** Una riga: i tre flag
`languageNonDefault` / `currencyNonDefault` / `themeNonDefault` esistono già e alimentano
il reset **per riga**; solo l'header riceve `hasNonDefaults={false}` letterale.

**C3 — `saveAll` non si ferma al primo rifiuto**, e riporta cosa è passato e cosa no.

**C4 — allineare `saveAll` a `saveField`** (ripristino dopo errore), che l'utente ha
indicato come comportamento corretto e che è coerente con C1.

### B-4 · Categoria «Altro» (C5)

Una `key` che nessuna categoria rivendica oggi **sparisce da ogni scheda** e sopravvive
solo sotto «Tutte» — regressione silenziosa il giorno in cui il backend aggiunge
un'impostazione e qualcuno dimentica il mapping. Nasce la categoria **Altro**.
Dichiarare le chiavi i18n, non scriverle.

### B-5 · Tasso FX zero (C6)

Il tooltip mostra «Market rate: 0.0000» invece di «non disponibile», e solo dopo essere
passati dalla pagina FX. Causa in `fxStoreRegistry.ts:199`: invertendo la coppia
restituisce `rate: 0` invece di `undefined`. **Zero non è un cambio possibile**: è la
sentinella di «non c'è» che viaggia con la forma di un dato. Senza la visita alla pagina
FX lo store non esiste e il tooltip è corretto; dopo, lo zero arriva a schermo.

Il codice lo sa già a metà: `fxConversionHelper.ts:87` **non** calcola lo spread se il
tasso è 0, mentre la riga 107 lo stampa. Correggere **entrambe** le metà — la sorgente
smette di fabbricarlo, il tooltip lo rifiuta comunque.

### B-6 · Transazioni (C8 + C9)

**C8 — collegare `resolveFormItemsFromOps`.** Non è codice morto: è la funzione giusta
mai chiamata. Fu scritta *per* `TransactionBulkModal` (chiede un adattatore
`(op) => TXReadItem`, e il modale ha già `opToTxLike`), ma alla riga 2280 il modale
costruisce la coppia da sé, saltando `orientPair` (garantisce che `items[0]` sia il
mittente) e `validatePair` (rifiuta tipi diversi o righe che non si referenziano).
L'orientamento oggi è corretto solo perché `collapsePairedOps` a monte tiene già la metà
«from»: un'assunzione, non una garanzia.

> **Trappola**: alle righe 2264-2275 il modale sovrascrive `mainItem.type` per gli split
> in coda, e `validatePair` confronta i tipi. L'ordine fra sovrascrittura e chiamata
> cambia l'esito.

**C9 — eliminare il barrel `transactions/modals/index.ts`**: sette export, zero
importatori.

---

## Fase C — ricomposizione e validazione

- **C-01** Applicare in un passaggio unico tutte le chiavi i18n dichiarate dalle corsie,
  nelle quattro lingue.
- **C-02** Registrare nel runner gli eventuali file di test nuovi; `check-orphans` pulito.
- **C-03** `prettier --check` e `svelte-check --threshold error` a zero.
- **C-04** Suite unit completa verde, due volte.
- **C-05** Corsa completa `--fresh-run --coverage all --workers 8 all`.
- **C-06** Misura prima/dopo e messaggio di commit proposto (mai eseguito).

---

## Note e rischi

- **Ogni correzione rompe il suo test di caratterizzazione.** È il progetto: quei test
  esistono per diventare rossi oggi. Vanno convertiti nell'asserzione nuova.
- **`GlobalSettingsTab` muta le fixture che riceve** (`setting.value = editedValues[key]`
  sugli oggetti di `response.items`): un array a livello di modulo porta il salvataggio di
  un test dentro il successivo. È costato otto rossi la prima volta.
- **`localStorage` è `undefined`** con questo Node/jsdom.
- **Le percentuali di ramo sui `.svelte` piccoli ingannano**: istanbul strumenta il Svelte
  *compilato*, e per un controllo piccolo espone pochissimi arm. Contarli, non citarli.
- **Rischio principale**: la fase A tocca componenti usati ovunque. Se sfora, le corsie
  parallele partono su una base che si muove — per questo è bloccante e da sola.

## Punto di partenza

Linee **78,13 %**, arm di ramo **59,53 %**. `components/settings` a 96,4 % / 73,6 %.
Suite: 15/15 categorie verdi, 3 698 vitest, 929 Playwright.
