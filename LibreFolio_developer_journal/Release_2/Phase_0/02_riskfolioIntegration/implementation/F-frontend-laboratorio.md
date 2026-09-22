# Mandato F — Asset Global, il laboratorio

| | |
|---|---|
| **Flusso** | W6 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | frontend |
| **Taglia** | L |
| **Lane** | porta `6245` · data dir `backend/data/test-risk-f` |
| **Dipende da** | **D** (bloccante) |
| **Riceve** | **K5** da D · **K3** da B · **K7** da I |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste

Asset Global è **l'unica pagina dove si possono analizzare asset che non si
possiedono**. Quello è il suo valore, e oggi non è dichiarato da nessuna parte: è
presentata come «un'altra vista del tuo portafoglio», e quindi confonde.

Lo split F15 round-2 ha già reso il concetto di prima classe nel modello dati — tre
pannelli discriminati da `txScope` (`+page.svelte:98` e `:1585-1615`):

| pannello | contenuto |
|---|---|
| `own` | asset posseduti dall'utente |
| `others` | asset di altri utenti di cui si ha visibilità |
| `analysis` | **asset osservati e non posseduti** ← il laboratorio vero e proprio |

Le domande vere del laboratorio sono altre da quelle della dashboard:

- *«questi due ETF che sto per comprare sono la stessa cosa?»*
- *«se aggiungo questo, la mia diversificazione migliora davvero?»*
- *«come si sono comportati davvero, questi tre, nel 2008?»*

**Nessuna richiede pesi. Tutte richiedono pochi asset, non cento.**

---

## 2. Cosa leggere prima

1. [`../05-grammatica-visiva-e-rappresentazioni.md`](../05-grammatica-visiva-e-rappresentazioni.md)
   **§8 per intero** — il dossier heatmap, che è metà di questo mandato.
2. Lo stesso documento **§9.2** — perché è una pagina di tabelle.
3. [`../01-tesi-e-quattro-domande.md`](../01-tesi-e-quattro-domande.md) **§4** e **§5**.
4. [`../03-mappa-livelli-pagine.md`](../03-mappa-livelli-pagine.md) **§4** — le quattro
   correzioni.
5. Decisioni: **D3**, **D11**, **D19**, **D54**.

---

## 3. ⚠️ La regola dei pesi — il vincolo che governa tutto

> ## 🔑 Con pesi → euro → «io». Senza pesi → percentuali → «questi».
>
> **In questa pagina non compare mai un euro.** In nessun pannello, compreso `others`.

Non è una regola estetica, è il rimedio a una trappola cognitiva **reale e presente**:
oggi il filtro broker di Asset Global produce *il set di asset* di un broker **senza
pesi**, mentre Broker Detail produce un'analisi **con** pesi. Stessa parola, semantica
opposta, nessun segnale visivo che le distingua. Un utente che confronta i due numeri
conclude che uno dei due è rotto.

Se Asset Global non mostra mai un euro, **la confusione diventa impossibile per
costruzione**, senza bisogno di alcun disclaimer.

È verificabile con una ricerca. Quindi va verificata.

**Conseguenza immediata**: il filtro broker va rinominato in senso esplicito —
*«precarica gli asset di…»* — perché costruisce un **insieme**, non un portafoglio.

---

## 4. Il difetto che rende la pagina inutilizzabile all'apertura

```js
selectedAssetIds = assets.filter(a => a.active !== false).slice(0, 100)
```

All'apertura la pagina seleziona **fino a cento asset**. Una matrice 100×100 sono
**diecimila celle**, e sopra i 12 asset i numeri spariscono
(`label.show: length <= 12`). **La vista nasce illeggibile per costruzione.**

Per tornare a sei asset servono **novantaquattro click** sulla X: non esiste
«deseleziona tutto» né «inverti». L'unico strumento di massa è il filtro broker —
proprio quello semanticamente ambiguo.

> Non è che scegliere sia difficile: **il sistema sceglie male al posto dell'utente e
> non gli dà modo di disfare.**

**E costa anche in prestazioni.** La matrice di correlazione è O(N²·T) in Python puro:
su dieci asset 37 ms, su cento **3 682 ms** — contro 0,2 ms della versione NumPy. **Il
default della pagina è il caso peggiore della curva.** L'event loop non si blocca
(`risk/base.py:242` usa `asyncio.to_thread`), ma il Python puro trattiene la GIL dove
NumPy la rilascia: quasi quattro secondi in cui ogni altra richiesta rallenta, senza
una richiesta colpevole evidente.

Il mandato **A** corregge il lato calcolo (M3); questo mandato corregge il lato
selezione (**D19**): **ultima selezione dell'utente da `localStorage`, con fallback
agli asset posseduti**. Il 100 resta un limite, non un punto di partenza.

---

## 5. La heatmap — sei difetti verificati

⚠️ **Correzione preliminare, per non rifare lavoro già fatto**: la heatmap **è già**
ECharts nativa e la scala **è già** divergente (`#b91c1c → #f8fafc → #1d4ed8`, min −1
max +1). Una precedente proposta di «migrare a ECharts con scala divergente» era
sbagliata: entrambe le cose esistono.

| # | Difetto | Cura |
|---|---|---|
| 1 | **Il tooltip non mostra i nomi** — gli indici sono in `value[0]`/`value[1]` e `labels` è nello scope, ma nessuno li ha scritti nel template. Senza i due nomi, un numero di correlazione non ha significato utilizzabile | Nomi + banda qualitativa (§5.1) |
| 2 | **Nomi troncati due volte** — `grid` con margini fissi in px **e** `axisLabel` con `width: 100`. Lo spazio riservato è una costante, non una misura | `truncateName` da `$lib/utils/text`, già usata da `LineChart` |
| 3 | **La rotazione è neutralizzata** — `rotate: 35` e poi taglio a 100px si annullano a vicenda | Rotazione a 45° **con il margine calcolato** (`larghezza · sin(angolo)`) |
| 4 | **La diagonale è rumore puro** — sempre ρ = 1, quindi sempre il colore più saturo: la riga più appariscente dice che un asset è correlato con sé stesso | Spegnerla |
| 5 | **Il triangolo superiore è un riflesso** — la correlazione è simmetrica: metà dell'inchiostro, zero informazione | Solo triangolo inferiore |
| 6 | **Deriva tecnica** — `ResizeObserver`/`MutationObserver` a mano invece di `createResizeWatcher`; `animation: false` invece di `CHART_ANIMATION_CONFIG`; nessun `tooltipPositionAboveFinger` né `scheduleFirstRenderStabilityFix` | Adottare ciò che ogni altro grafico del progetto usa |

> Diagonale spenta + solo triangolo inferiore: su 10 asset da 100 celle a **45**, senza
> perdere nulla.

### 5.1 Il tooltip che serve

```text
┌──────────────────────────────────────────┐
│  NVIDIA Corp.   ×   Bitcoin              │
│                                          │
│  ρ = +0,62        correlazione alta       │
│  ▸ si muovono quasi sempre insieme        │
│                                          │
│  748 osservazioni · copertura 98,3%       │
└──────────────────────────────────────────┘
```

Con banda qualitativa, perché `0,62` non dice nulla a chi comincia:

| \|ρ\| | Banda | Frase |
|---|---|---|
| > 0,7 | alta | si muovono quasi sempre insieme |
| 0,3 – 0,7 | moderata | si muovono spesso nella stessa direzione |
| < 0,3 | bassa | si muovono in modo largamente indipendente |
| negativa | inversa | tendono a compensarsi |

### 5.2 Riordino per similarità

Clustering su `1−|ρ|`: i blocchi di asset che si muovono insieme diventano **quadrati
adiacenti**. Si *vede* la mancata diversificazione invece di doverla cercare cella per
cella. Solo frontend, dati già presenti.

### 5.3 Filtri e azioni di massa

```text
Tipo    [ETF ✓] [Azioni ✓] [Crypto] [Bond]
Settore [ Tech ▾ ]   Area [ ▾ ]   Valuta [ ▾ ]
                                        12 asset selezionati
[ Tutti ]  [ Nessuno ]  [ Inverti ]  [ ↺ I miei ]
```

`asset_type` è già su `AssetOption`; `sectorStore` e `countryStore` esistono e sono già
popolati. **Si seleziona per criterio, non per elenco.**

### 5.4 Oltre ~20 asset, cambiare domanda

Nessuno legge 400 celle, ma la domanda dietro resta valida e ha una risposta migliore
in forma di **lista**:

```text
Coppie più correlate                          ρ
  MSCI World  ×  S&P 500                   +0,97   ⚠ quasi identici
  VWCE        ×  MSCI World                +0,94   ⚠
Coppie che si compensano
  Oro         ×  S&P 500                   −0,23
```

Le coppie quasi-identiche sono **il** risultato che si cerca: due prodotti pagati per
una sola esposizione. **La matrice lo nasconde, la lista lo dichiara.**

---

### 5.5 ⚠️ Anche qui i selettori mostrano l'id — D73

Stesso difetto che il developer ha segnalato sul segnale beta, e **`AssetSetRiskPanel`
lo commette due volte**: sul broker (`:49`) e sull'asset (`:55`).

La causa è il **rendering di default** di `SearchSelect` (`:496-497`), che stampa
`option.value` in **`font-mono`** come riga principale e `option.label` come
sottotitolo. È corretto dove il valore *è* un codice leggibile — valuta, paese — e il
`font-mono` lo dichiara; è un difetto quando il valore è una **chiave primaria**.

⚠️ **Non si corregge `SearchSelect`**: si romperebbero i selettori di valuta e paese.
Si corregge chi lo usa male.

| Selettore | Cura |
|---|---|
| asset (`:55`) | **`AssetSelect`** — 187 righe già scritte: icona, ticker, valuta con bandiera, inattivi in fondo e marcati |
| broker (`:49`) | **`BrokerSearchSelect`** — già corretto, già con i suoi snippet |

> Tutti i selettori dedicati in `ui/select/` sovrascrivono il default. I due che
> sbagliano sono entrambi costruiti **fuori** da quella cartella. È ciò che succede
> quando si costruisce un picker ad hoc invece di riusare quello che c'è.

Il mandato **B** applica la stessa cura a `SignalAssetParamControl` (§5.3 del suo file).
Qui vale in più una nota di coerenza: il filtro broker va **rinominato** come filtro
d'insieme (§3), quindi il componente lo si tocca comunque.

---

## 6. Le colonne di rischio nelle tabelle

**D54**: entrano **tutti** i segnali utili, ma **nascosti per default** e attivabili
dall'utente. Visibile di default il solo **max drawdown**, perché è facile da capire e
ad alto impatto.

> Non serve alcun meccanismo nuovo. `DataTable` espone già `hiddenByDefault` per
> colonna e persiste in `localStorage` **solo gli override espliciti**
> (`DataTable.svelte:193-199`), con una nota nel codice che spiega perché: così un
> default che cambia resta la verità viva, e un valore vecchio non può tenere nascosta
> una colonna che dovrebbe vedersi.

Le tre tabelle hanno già la sincronizzazione delle colonne fra pannelli
(`mirrorColumnResize`, `additionalTableRefs`): le colonne di rischio trasformano la
tabella in uno strumento di confronto **senza introdurre un solo grafico nuovo** e
senza uscire dal linguaggio percentuale.

Candidati: volatilità annua, max drawdown, correlazione media col resto del set, e
`RG` — l'escursione fra il giorno migliore e il peggiore, che dice a colpo d'occhio chi
è nervoso (**D45**).

---

## 7. Cosa NON va in questa pagina

| Fuori | Perché |
|---|---|
| **Shock ipotetico** | Senza pesi è quasi **tautologico**: riscrive l'input in forma diversa |
| **Contributo al rischio** | Richiede pesi, che qui non esistono |
| **Qualunque euro** | Regola dei pesi, §3 |

**Dentro invece sì**: il **replay storico in percentuale** — *«come si sono comportati
davvero questi tre ETF nel 2008»* — è un confronto genuino, ed è **l'unico strumento di
L4 ammesso qui**.

E il titolo: la pagina è intitolata «Correlation» ma renderizza anche lo stress. Il
titolo deve corrispondere al contenuto, o il contenuto al titolo.

---

## 8. Confini

**Di questo mandato**:

- `frontend/src/routes/(app)/assets/+page.svelte`
- `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte`
- `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` — ⚠️ **eccezione
  concordata**: sta dentro `risk/`, che è del mandato **E**, ma appartiene a questo
- le colonne di rischio nelle tre tabelle
- i18n: **solo** il sotto-blocco `risk.lab.*`, che E apre

**Fuori**: tutto il resto di `components/risk/**` (mandato E), i grafici di allocazione
(G), `components/ui/**` (D), il backend.

---

## 9. Test

| Cosa | Come |
|---|---|
| Unitari | Vitest sugli helper di selezione e sul clustering |
| E2E | `portfolio/risk-lab.spec.ts` (tuo, nasce dalla divisione di D) e `assets/asset-list.spec.ts` (**condiviso con B**) |
| **La regola dei pesi** | una ricerca che prova che **nessun simbolo di valuta** compare nella pagina |
| Statici | lint + `svelte-check` |

> ## ⚠️ Il tuo test E2E non è dove ti aspetti
>
> Oggi il test che ti riguarda — *«asset global maps broker holdings and supports
> remove/add»* — vive dentro `portfolio/risk-analysis.spec.ts`, 817 righe **condivise
> con E**. Il mandato **D** lo divide prima che tu cominci (K5):
>
> | File | Chi |
> |---|---|
> | `portfolio/risk-lab.spec.ts` | **tuo** |
> | `portfolio/risk-mocks.ts` | di **E** — tu lo **consumi**, non lo scrivi: se ti serve un cambiamento, lo **chiedi** |
> | `portfolio/risk-analysis.spec.ts` | di **E** — non toccare |
> | `portfolio/risk-asset-detail.spec.ts` | 🚫 **di nessuno**, è la rete su Asset Detail |
>
> E `assets/asset-list.spec.ts` (692 righe, 24 test) lo tocchi **anche tu** per le
> colonne di rischio, mentre **B** lo tocca per il filtro dei tipi: coordinarsi tramite
> il coordinatore, non scoprirselo al merge.

⚠️ Selettori `data-testid`, mai testo tradotto. Ogni test condivide DB e backend con i
vicini: niente posizioni fisse, niente conteggi globali.

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6245 --data-dir backend/data/test-risk-f \
  <categoria> <azione>
```

---

## 10. Definizione di finito

- [ ] **Nessun euro in nessun pannello**, verificato con una ricerca;
- [ ] filtro broker rinominato come filtro d'**insieme**;
- [ ] **i due selettori mostrano i nomi, non gli id** (D73): asset su `AssetSelect`,
      broker su `BrokerSearchSelect`;
- [ ] selezione iniziale da `localStorage` con fallback agli asset posseduti — **mai
      cento**;
- [ ] azioni di massa: tutti / nessuno / inverti / i miei;
- [ ] heatmap: tooltip con i nomi e la banda qualitativa, etichette non troncate due
      volte, diagonale spenta, solo triangolo inferiore, primitive del progetto adottate;
- [ ] riordino per similarità;
- [ ] lista delle coppie oltre ~20 asset;
- [ ] colonne di rischio nascoste per default, max drawdown visibile;
- [ ] titolo coerente col contenuto;
- [ ] lint, `svelte-check`, Vitest ed E2E verdi;
- [ ] nessun processo in ascolto su `6245`.
