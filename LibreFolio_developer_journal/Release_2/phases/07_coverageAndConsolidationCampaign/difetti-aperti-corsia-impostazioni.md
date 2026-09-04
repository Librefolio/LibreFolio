# Difetti aperti dopo la corsia «impostazioni, condivisione, logica pura»

Undici comportamenti che i test hanno **fissato così come sono**, senza correggerli.
Ognuno ha un test che diventa rosso il giorno in cui decidi diversamente.

Sono ordinati per gravità: quelli in **A** sono perdite di dati o di accesso,
quelli in **B** sono errori mostrati all'utente su operazioni riuscite,
quelli in **C** sono affordance morte o incoerenze.

---

## A — perdita silenziosa di accesso o di stato

### A1. `BrokerSharingPanel`: una lettura fallita diventa una revoca

**Dove**: `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte`

La lista delle condivisioni viene caricata all'apertura. Se quella `GET` fallisce, il
pannello **non si blocca**: resta modificabile con una lista vuota. Il salvataggio è un
rimpiazzo completo, quindi il primo `Salva` **revoca tutti** i condivisi esistenti.

L'utente non vede nulla di anomalo: vede un pannello vuoto, che è indistinguibile da
«questo broker non è condiviso con nessuno».

**Decisione richiesta**: il pannello deve rifiutarsi di salvare finché la lettura non è
riuscita? (La mia raccomandazione è sì, con un messaggio esplicito e un pulsante
«riprova».)


utente favorevole

### A2. Guardia asimmetrica sull'ultimo proprietario

**Dove**: stesso file.

Rimuovere l'ultimo proprietario è **vietato**. Retrocederlo a `VIEWER` è **permesso**.
Il risultato è identico — un broker senza nessuno che possa amministrarlo — ma solo una
delle due strade è chiusa.

**Decisione richiesta**: estendere la guardia al cambio di ruolo, o è un caso che l'admin
di sistema può sempre recuperare?

No l'ultimo utente owner non si può eliminare, se ci prova il sistema dovrebbe chiedergli se vuole eliminare il broker, e conseguentemente le transazioni associate, o promuovere un nuovo owner al suo posto.

> **Nota tecnica (verificata)**: il ramo «elimina il broker» è già servito —
> `DELETE /api/v1/brokers` esiste e accetta `force` per procedere anche con transazioni
> associate. Non serve backend nuovo per quella metà.
>
> La guardia asimmetrica sta in `BrokerSharingPanel.svelte:262`, dentro la funzione di
> **rimozione**. Il percorso di **modifica ruolo** (riga 245) non ha nulla di equivalente:
> si può selezionare `VIEWER` sull'ultimo owner e salvare, ottenendo lo stesso stato che
> la rimozione vieta.
>
> ⇒ vedi domanda residua in fondo al file.

---

## B — errore mostrato su un'operazione riuscita

### B1. `PasswordChangeModal` accetta un secondo invio dopo il successo

**Dove**: `frontend/src/lib/components/settings/PasswordChangeModal.svelte`, `handleSubmit`

`isSubmitting` torna a `false` subito, ma la chiusura è programmata a 1500 ms. In quella
finestra i campi contengono ancora i valori e `Salva` è vivo **sotto** il messaggio di
successo. Un secondo click manda la vecchia password, che non esiste più → il server
risponde «password attuale errata» a chi l'ha appena cambiata, e il timer chiude il
dialogo sopra quell'errore.

**Verificato**: `changePassword` chiamata due volte.

**Decisione richiesta**: nessuna, secondo me — è un difetto puro. Basta non riabilitare
il pulsante dopo il successo. Confermi che lo correggo?

si sono d'accordo

### B2. Cambiare fuso orario rischedula il lavoro senza dirlo

**Dove**: `frontend/src/lib/components/settings/SchedulerConfigModal.svelte`

Il suggerimento dice «gli orari qui sotto sono mostrati in questo fuso», ma il fuso viene
letto solo all'apertura e al salvataggio: i chip **non vengono mai riconvertiti**.
Apri su UTC, vedi `09:00`, cambi fuso su Bogotá, salvi → il lavoro gira alle **14:00 UTC**
con `09:00` ancora sullo schermo.

**Verificato nel payload.**

**Decisione richiesta**: quale delle due è l'intenzione?
- (a) il fuso è solo una lente di lettura → gli orari vanno riconvertiti a schermo, l'orario assoluto non cambia
- (b) il fuso ridefinisce l'orario → l'orario assoluto cambia, e va detto esplicitamente

direi che l'opzione a è quella corretta, tanto lo scheduler sul backend per evitare dubbi lo fa in UTC mi pare, o comunque in un fuso fisso, è nella ui che per comodità facciamo scegliere il fuso in base alle impostazioni correnti.

### B3. `SchedulerLogModal` marca ✓ un fallimento senza messaggio

**Dove**: `frontend/src/lib/components/settings/SchedulerLogModal.svelte`

Una esecuzione fallita ma priva di testo d'errore viene resa con il segno di successo.

**Decisione richiesta**: nessuna. Difetto puro, correggo se dai il via.

si correggi

---

## C — affordance morte, incoerenze, rollback mancanti

### C1. `PreferencesTab` applica tema e lingua **prima** della PUT e non torna indietro

**Dove**: `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte`, `saveField`

`applyTheme(...)` e `currentLanguage.set(...)` girano prima di `await ...put(...)`, e il
`catch` mostra l'errore ma non ripristina. Il server rifiuta, l'utente vede un banner
rosso, **e l'app resta dipinta nel tema che il server non ha mai memorizzato**. Al reload
successivo torna indietro da sola, senza spiegazione.

**Decisione richiesta**: rollback nel `catch`, oppure applicare solo dopo la conferma?
(Il secondo è più lento ma non mente mai.)

direi di applicare solo al salvataggio e in caso di fallimento far comparire un toast che spiega l'errore.

### C2. `PreferencesTab`: «Ripristina tutto» è irraggiungibile

`resetAll()` esiste ed è corretta, ma `SettingsLayout` riceve `hasNonDefaults={false}`
**letterale**, quindi il pulsante non si rende mai. Dal punto di vista dell'utente è
codice morto.

**Decisione richiesta**: calcolare `hasNonDefaults` davvero, o rimuovere `resetAll()`?

mi pare strano, dopo aver modificato i settings ho il reset button, sicuro che sia irragiungibile?

> **Risposta (verificata)**: quello che vedi è il reset **per riga**, non quello di massa —
> sono due pulsanti diversi. `SettingsLayout` li governa con due flag distinti:
> `hasChanges` accende *salva tutto* + *annulla tutto*, `hasNonDefaults` accende
> *ripristina tutto*. Le tre righe di `PreferencesTab` ricevono ciascuna il proprio
> `isNonDefault` calcolato bene (`languageNonDefault`, `currencyNonDefault`,
> `themeNonDefault`), quindi il reset per riga compare. Solo l'header riceve
> `hasNonDefaults={false}` **letterale**, e quindi *ripristina tutto* non compare mai.
>
> I tre flag esistono già: la correzione è una riga,
> `hasNonDefaults={languageNonDefault || currencyNonDefault || themeNonDefault}`.
> `resetAll()` resta e diventa raggiungibile.

### C3. `PreferencesTab.saveAll` si arresta al primo rifiuto

Il ciclo non è protetto: se il tema fallisce, valuta e lingua **non vengono nemmeno
tentati**, e l'unico messaggio non dice quali campi sono atterrati. L'utente vede tre
campi ancora «modificati» e non sa quali riprovare.

risolvi mostrando cosa è stato salvato e cosa no

### C4. `ProfileTab`: `saveField` ripristina dopo un errore, `saveAll` no

Fallito il salvataggio singolo, il campo torna al valore originale. Fallito quello di
massa, i campi restano sui valori rifiutati e l'header continua a offrire «salva tutto»
sugli stessi dati che il server ha appena respinto.

**Decisione richiesta**: quale dei due comportamenti è quello giusto? Vanno allineati.

credo che il comportamento di saveField sia corretto e in linea anche con la scelta c1

### C5. `GlobalSettingsTab`: una chiave che nessuna categoria rivendica è visibile solo sotto «Tutte»

Se il backend introduce una `key` non elencata in nessuna categoria, quell'impostazione
**scompare da ogni scheda di categoria**. Si presenta come una regressione silenziosa il
giorno in cui qualcuno aggiunge un'impostazione lato server e dimentica il mapping.

**Decisione richiesta**: le chiavi non rivendicate vanno in una categoria «Altro»?

si come idea è buona, creiamo la categoria altro

### C6. Tooltip FX: «Market rate: 0.0000» invece di «non disponibile»

Si presenta **solo** se si è passati prima dalla pagina FX — cioè dipende dalla
navigazione precedente, il che lo rende difficile da riprodurre a mano.

non sono sicuro di aver capito il perchè, ma se sai quale sia il valore corretto risolvilo

> **Risposta (trovato il meccanismo)**: il valore corretto è **«non disponibile»**, e il
> codice lo sa già a metà. `fxStoreRegistry.ts:199`, quando la coppia va invertita:
>
> ```ts
> return {...point, rate: point.rate !== 0 ? 1 / point.rate : 0};
> ```
>
> Quando il tasso non è invertibile restituisce un punto con `rate: 0` invece di
> `undefined`. Ma **zero non è un cambio possibile**: è la sentinella di «non c'è», che
> però viaggia con la forma di un dato.
>
> Ecco anche il «solo se si è passati dalla pagina FX»: senza quella visita lo store
> della coppia non esiste, `lookupFxRateSync` esce a `undefined` e il tooltip dice
> correttamente «non disponibile». Dopo la visita lo store esiste, il punto c'è, e lo
> zero arriva fino a schermo come `0.0000`.
>
> La conferma che è una guardia lasciata a metà è in `fxConversionHelper.ts`: la riga 87
> **non** calcola lo spread se `marketRate === 0` — quindi tratta lo zero da sentinella —
> mentre la riga 107 lo stampa come se fosse un tasso.
>
> Correggo entrambe le metà: la sorgente smette di fabbricare lo zero, e il tooltip lo
> rifiuta comunque (difesa in profondità).

### C7. Tre controlli `Setting*` su cinque non hanno `isSaving`

`SettingCurrency`, `SettingSelect` e `SettingTheme` non ricevono affatto la prop: il loro
`Salva` non si disabilita mai e due click mandano due salvataggi. I loro stessi commenti
in testa dichiarano che «seguono la stessa API di `SettingSelect` per coerenza».

non sono sicuro è un bug che non lo hanno o è perchè non gli serve?

> **Risposta (verificata)**: è un bug. `PreferencesTab` **ha** `isSaving` (riga 50), lo
> alza in `saveField` e in `saveAll`, e lo usa già per `isBusy` sul contenitore — quindi
> lo stato esiste ed è calcolato bene. Ma i tre controlli che quel tab monta
> (`SettingSelect` per la lingua, `SettingCurrency`, `SettingTheme`) **non dichiarano
> affatto la prop**: non c'è la porta per riceverlo.
>
> `SettingNumber` e `SettingToggle` ce l'hanno e la usano (`disabled={isSaving}` sul
> Salva). Sono gli stessi tre a mancare che dichiarano nel proprio commento di intestazione
> di «seguire la stessa API per coerenza».
>
> Esito concreto: sui tre senza prop il Salva resta vivo durante la PUT, e un secondo
> click manda un secondo salvataggio.

### C8. `resolveFormItemsFromOps` non ha chiamanti

`TransactionBulkModal` costruisce la coppia a mano, **saltando `orientPair` e
`validatePair`**. O la funzione va usata, o va rimossa: oggi è una seconda
implementazione non esercitata della stessa decisione.

mi pare che avessimo creato degli helper globali per fattorizzare, se ne esiste già uno simile a questo, come per altre parti del progetto, fai un merge del meglio di entrambe, mentre se è codice morto, eliminalo.

> **Risposta (verificata)**: non è codice morto — è **la funzione giusta mai collegata**.
> `resolveFormItemsFromOps` è stata scritta *per* `TransactionBulkModal`: la sua firma
> chiede un adattatore `(op) => TXReadItem`, e il modale ha già `opToTxLike` che è
> esattamente quello. Poi però, alla riga 2280, costruisce la coppia da sé:
>
> ```ts
> formItems = partnerItem ? [mainItem, partnerItem] : [mainItem];
> ```
>
> Saltando due controlli che la funzione condivisa fa:
> - **`orientPair`** — garantisce che `items[0]` sia il *mittente*. Qui l'orientamento è
>   corretto solo perché `collapsePairedOps` a monte tiene già la metà «from» come
>   visibile: è un'assunzione non verificata, non una garanzia.
> - **`validatePair`** — rifiuta due righe con tipi diversi o che non si referenziano a
>   vicenda. Oggi una coppia mal formata verrebbe aperta nel form senza un fiato.
>
> Quindi: collegare, non eliminare. **Attenzione in fase di esecuzione**: alle righe
> 2264-2275 il modale sovrascrive `mainItem.type` per gli split in coda; `validatePair`
> confronta i tipi, quindi l'ordine fra la sovrascrittura e la chiamata cambia l'esito.

### C9. Barrel `transactions/modals/index.ts`: sette export, nessun importatore

se sono codice morto, eliminalo.

> **Risposta (verificata)**: nessun file nel progetto importa da
> `transactions/modals/index.ts`. Codice morto, lo elimino.

---

## D — emerso durante le correzioni, decisione ancora da prendere

### D1. Lo scheduler ragiona in giorni UTC, ma mostra gli orari nel fuso locale

**Dove**: `frontend/src/lib/components/settings/SchedulerConfigModal.svelte`

Corretto B2, gli **orari** ora si riconvertono al cambio fuso e l'istante assoluto non si
muove più. Ma i **giorni della settimana** restano quelli UTC, e non sono riconvertibili
uno per uno: sono un insieme globale, non un attributo di ciascun orario.

Conseguenza concreta, verificata: se il lavoro gira **lunedì alle 02:00 UTC** e l'utente
guarda con il fuso di Bogotá (UTC−5), il modale mostra **il chip «lunedì» acceso e
l'orario `21:00`**. Ma le 21:00 locali di quel momento sono **domenica**. La combinazione
che l'utente legge non esiste.

Non è una regressione introdotta da B2: c'era già, ed era nascosta dal fatto che prima
nemmeno gli orari si convertivano. Correggendo metà del problema, l'altra metà è diventata
visibile.

**Coperto** dal test di caratterizzazione `CHARACTERISATION: weekdays stay UTC…`, che
asserisce `21:00` + `mon=true` + `sun=false` e payload `times=02:00`, `days=mon`. Diventerà
rosso il giorno in cui si decide.

**Decisione richiesta**: tre strade, in ordine di costo.
- (a) **Avviso**: lasciare il modello com'è e dire a schermo che i giorni sono in UTC.
  Costo minimo, ma chiede all'utente di fare la conversione in testa.
- (b) **Giorni riconvertiti in blocco**: applicare lo scarto del fuso all'insieme dei
  giorni. Funziona solo se tutti gli orari cadono dallo stesso lato della mezzanotte;
  altrimenti mente comunque.
- (c) **Il modello diventa (giorno, ora)**: ogni slot porta il proprio giorno, e la
  conversione è esatta. È corretto, ma tocca il backend.
la soluzione c mi pare la migliore
### D2. Lo zero-sentinella FX si vede anche nei grafici, nelle tabelle e negli overlay

**Dove**: `frontend/src/lib/stores/fxStoreRegistry.ts:168` (`apiResultToFxDataPoint`)

Correggendo C6 è emerso che la riga segnalata **non era la sorgente**, solo una delle due.
Quella vera sta al confine con l'API: `apiResultToFxDataPoint` converte un `rate`
null/undefined in **`0`**. È la stessa scrittura — un'assenza travestita da valore — ma
messa all'ingresso, quindi **a monte di tutto**.

E il backend il `null` lo dichiara esplicitamente: `backend/app/schemas/fx.py:157` ha
`rate: Optional[SafeDecimal] = Field(None, ...)`, il client generato lo tipizza
`(string | null) | undefined`, e lo Zod lo valida come unione con `null`. Cioè: l'API dice
«non ho un tasso», e il frontend **butta via quell'informazione al confine**.

C6 ha chiuso il tooltip, che ora si difende. Ma il tooltip non è l'unico consumatore, e gli
altri non si difendono. **Difetti veri, verificati con file e riga**:

| dove | cosa fa oggi |
| --- | --- |
| `FxCard.svelte:92` | mostra `0.0000` come se fosse un cambio |
| `FxCard.svelte:109,122` | **il grafico disegna un crollo a zero** |
| `FxTable.svelte:103,196` | mostra `0.0000` in cella, e ordina su quello zero |
| `fx/[pair]/+page.svelte:256,271` | mostra e disegna lo zero |
| `fx/[pair]/+page.svelte:264` | il delta controlla solo `first===0`, non `last===0` → **può produrre −100 %** |
| `assets/+page.svelte:947,1017` | gli overlay dei segnali FX calcolano sullo zero |
| `assets/[id]/+page.svelte:653` | idem |
| `FxDataEditorSection.svelte:79-88` | mostra `rate: 0` nella griglia — e al salvataggio lo rifiuta (`rate > 0`), quindi **espone un dato che lui stesso considera invalido** |

**Il tipo onesto è `FxDataPoint.rate: number | null`.** Stima misurata, non a impressione:
1 tipo, 3 converter/loader, 7 consumatori di produzione, più la pressione su
`LineDataPoint.value` (che è `number`, quindi davanti ai grafici serve un filtro, non un
`null` che passa). Circa 20-30 siti `.rate` reali, molti dei quali diventano un filtro
`rate != null && rate !== 0`. **Media, non enorme.**

**Decisione richiesta**: è un lavoro a sé, da pianificare. Lo apriamo come corsia
successiva?

1. **`GlobalSettingsTab` muta le fixture che riceve.** `saveSetting` fa
   `setting.value = editedValues[key]` sugli oggetti arrivati da `response.items`. Un
   array di fixture a livello di modulo porta quindi il salvataggio di un test dentro il
   successivo. È costato otto rossi prima di essere capito.

2. **`localStorage` è `undefined`** con questo Node/jsdom. `AboutTab` lo legge in tre
   punti, quindi il file installa uno stub a mano su `globalThis` **e** su `window`.

3. **Le percentuali di ramo sui `.svelte` piccoli ingannano.** Un `SettingSelect` al 50 %
   è 1 arm su 2: istanbul strumenta il Svelte *compilato*, e per controlli piccoli
   quell'output espone pochissimi arm. La matrice vera va contata a mano.

4. **`GlobalSettingsTab` contiene quattro copie identiche** del trio salva/annulla/
   ripristina, una per `value_type`. È la stessa forma del difetto già fuso in
   `SyncResultRow`.

dopo aver letto il punto 4 direi che siamo davanti a un area di codice che può beneficiare di una rifattorizzazzione, prendi le varie istanze e fattorizza prendendo il meglio di tutte e riusale.
