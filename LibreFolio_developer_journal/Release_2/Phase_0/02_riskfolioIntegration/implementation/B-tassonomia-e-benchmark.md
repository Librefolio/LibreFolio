# Mandato B — Tassonomia degli asset e catalogo dei benchmark

| | |
|---|---|
| **Flusso** | W2 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | DB + backend + frontend — **trasversale, poco profondo** |
| **Taglia** | L |
| **Lane** | porta `6241` · data dir `backend/data/test-risk-b` |
| **Dipende da** | nulla — parte subito |
| **Consegna** | **K2** a G · **K3** a E ed F |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste

L3 — *«sto venendo pagato per questo rischio?»* — è l'unica delle quattro domande che
guarda **fuori** dal portafoglio ([`../01-…`](../01-tesi-e-quattro-domande.md) §3). Per
guardare fuori serve un riferimento, e oggi il benchmark si sceglie al volo a ogni
esecuzione: il beta che ne esce è un numero senza contesto.

Ma il confronto è **plurimo**, ed è qui che il mandato prende la sua forma. Misurare un
portafoglio azionario contro un buono fruttifero postale produce un numero corretto e
privo di significato: è ovvio che l'azionario renda di più e oscilli di più. Perciò non
serve *un* benchmark, serve un **catalogo** con sezioni sensate.

E le sezioni non si possono costruire con i dati di oggi: `AssetType` distingue la
**forma** dello strumento, non il contenuto. Un ETF azionario e uno obbligazionario
sono **entrambi `ETF`**.

> Il mandato è quindi uno solo, in due gesti: dare agli asset una tassonomia che
> distingua il contenuto, e usarla per qualificare i riferimenti.

---

## 2. Cosa leggere prima

1. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **Q1 per intero** — la
   riformulazione, le quattro conferme sul codice, l'avvertimento su `INDEX`, e i
   cinque sotto-punti (a)-(e) tutti chiusi.
2. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **Q9** e **Q10** — i sottotipi e
   il caso monetario, **compresa l'autocorrezione su `LIQUIDITY`**.
3. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **Q12** — i punti che raggruppano
   per tipo, e perché falliscono in silenzio.
4. Decisioni: **D48**-**D53**, **D60**-**D71**.

Poi `wiki-search` su: asset type, classificazione, provider di enrichment.

---

## 3. Il presupposto verificato che rende tutto questo sicuro

Prima di aggiungere valori a un enum usato ovunque, la domanda giusta è *«cosa
pilota?»*. Risposta misurata, branch per branch (**D51**):

`asset_type` fa filtro nelle query (`crud.py:180-181`), raggruppamento ed esposizione,
etichetta, AI export — e **una sola regola di comportamento**: `INDEX` vieta le
transazioni (`transaction_batch_stages.py:501-502`).

> ⚠️ **Il docstring di `AssetType` mente.** A `models.py:160-165` dichiara una
> mappatura verso `valuation_model` (CROWDFUND→SCHEDULED_YIELD, HOLD→MANUAL,
> INDEX→MARKET_PRICE). **`valuation_model` non esiste nel codice**: `grep` su tutto
> `backend/app` lo trova solo lì dentro. È fiction, e va corretta nella stessa
> migrazione — altrimenti il prossimo che legge costruirà un'obiezione su un
> presupposto falso, come è già successo.

Conseguenza: **aggiungere sottotipi non cambia alcun comportamento**. Cambia però ogni
*raggruppamento* (§6).

---

## 4. Gesto 1 — La tassonomia

### 4.1 I nuovi valori di `AssetType`

Regola (**D61**): il secondo livello **non è un elenco nuovo**, è l'insieme dei tipi
base. La specializzazione di un ETF è «quale tipo base contiene».

| Cosa | Valori |
|---|---|
| **Tipi base nuovi** | `COMMODITY`, `REAL_ESTATE` — oggi mancano del tutto |
| **Sottotipi ETF** | azionario, obbligazionario, materie prime, immobiliare, cripto — uno per tipo base |
| **Sottotipo senza base** | il **monetario** — unica eccezione, vedi sotto |
| **Residuo** | `ETF` generico **resta**: è ciò che i provider scrivono, ed è il bilanciato/multi-asset |
| **Non si tocca** | `FUND` non si suddivide: gli ETF sono già fondi, passivi; la distinzione utile è sul contenuto |

⚠️ **L'eccezione monetaria incrina D61, e va scritta, non smussata** (**D67**). Esiste
`ETF_MONETARY` ma **non** un `MONETARY` di primo livello, perché un fondo monetario è
uno strumento che si compra mentre la cassa è il saldo di un conto. La pastiglia riusa
`liquidity.png`, che esiste già.

⚠️ **`LIQUIDITY` NON entra nell'enum** (**D63**). Non è un tipo a metà: è un **secchio
sintetico**. `portfolio_engine.py:1039-1041` inietta la cassa nell'allocazione come
pseudo-tipo. Aggiungerlo creerebbe un doppione **visibile**: gli asset veri entrano in
`by_type` con `asset_type.value` maiuscolo (`:1448`), la cassa entra come `"Liquidity"`
— due chiavi, due fette, stessa icona. Sembrerebbe un bug e lo sarebbe.

**Resta da decidere dentro il mandato**: il naming esatto (`ETF_STOCK` o `ETF_EQUITY`?
il primo è coerente col tipo base che nomina, il secondo con l'uso corrente in
finanza). Sceglierne uno e **usarlo ovunque**.

### 4.2 Le icone

Le due mancanti **esistono già** (**D69**), installate e verificate contro la tavolozza
misurata della famiglia:

```text
frontend/static/icons/asset-types/commodity.png      271×248
frontend/static/icons/asset-types/real-estate.png    296×199
```

Sono **non referenziate** finché l'enum non arriva: questo mandato le collega.

La **pastiglia** è icona grande del contenitore + icona piccola sovrapposta del tipo
base (**D52**), stesso schema che l'altro worktree applica a broker + asset. Va una
costante nuova accanto a `PNG_MAP` in `assetTypes.ts`.

### 4.3 Il selettore a due livelli

Esiste già: `SignalTreeSelect.svelte`, 359 righe (**D62**). Due livelli esatti,
espandibili, ricerca che attraversa entrambi, navigazione da tastiera.

Il costo è la **generalizzazione**, e va messo a preventivo onestamente: spostarlo da
`components/charts/` a `components/ui/select/`, privarlo del nome «Signal», passare il
contenuto dell'opzione come **snippet** invece che via `SignalOptionContent`. E
`SignalTreeItem` ha **un solo campo `icon`**: per la pastiglia serve un secondo slot.

⚠️ Il componente è usato oggi dai segnali: la generalizzazione **non deve cambiarne il
comportamento**. Chi lo usa non deve accorgersi di nulla.

---

## 5. Gesto 2 — Il catalogo dei benchmark

### 5.1 La colonna

Booleana su `assets`, **condivisa fra tutti gli utenti** (**D60**). Non è un
compromesso: non ha senso che lo stesso ETF sia un buon riferimento per un utente e no
per un altro. Ed è coerente col modello — `Asset` (`models.py:464`) **non ha
`user_id`**: è già globale.

Spenta di default ovunque, **accesa di default** quando l'asset viene aggiunto dalla
pagina di rischio.

**`AssetType.INDEX` implica benchmark** (**D53**), come flag **materializzato**, non
come regola ricalcolata: backfill in migrazione per gli `INDEX` esistenti, e accensione
automatica **in sola lettura** alla creazione di un nuovo `INDEX`. Un indice esiste solo
per il confronto.

⚠️ **Il flag è ortogonale al tipo, non lo riusa** (**D49**): un ETF S&P 500 è un ottimo
benchmark **e** un asset che si possiede davvero. Marcarlo `INDEX` gli vieterebbe le
transazioni.

### 5.2 L'ordinamento del selettore — contratto K3

`SignalAssetParamControl.svelte` (64 righe) è raggiunto da `ChartSignalsSection`, che
vive in `/assets/[id]` **e** `/fx/[pair]`, ed è **già usato** da `RiskAnalysisPanel`
alle righe 891 e 1091 (**D50**). Una modifica, quattro benefici.

L'ordinamento oggi è alfabetico puro (`:31`). Diventa **a sezioni**, con i benchmark in
cima. `SelectOption.header` esiste già e ha esattamente la semantica giusta: la voce è
saltata dalla tastiera, ignorata da Invio, e **sparisce quando la ricerca svuota la sua
sezione**.

> È un `sort` più due intestazioni. **Non** un componente nuovo.

### 5.3 ⚠️ Prima dell'ordinamento va riparato cosa il selettore mostra — D73

**Difetto segnalato dal developer**, verificato sul codice: nel segnale **beta** il menù
elenca «**9** / Amundi Core MSCI World UCI…» — l'**id** come riga principale, il nome
come sottotitolo.

**La causa non è nel controllo del segnale**, che passa già `label: asset.display_name`.
È il **rendering di default** di `SearchSelect` (`:496-497`):

```svelte
<div class="font-mono text-sm …">{option.value}</div>
<div class="text-xs text-gray-500 truncate">{option.label}</div>
```

Quel default è **corretto** per i selettori dove il valore *è* un codice leggibile —
valuta, paese, settore — e il `font-mono` lo dichiara apertamente. Diventa un difetto
solo quando il valore è una **chiave primaria di database**.

⚠️ **Non si corregge `SearchSelect`**: si romperebbero i selettori di valuta e paese,
dove mostrare `EUR` in evidenza è giusto. **Si corregge chi lo usa male.**

Chi lo sa e chi no, verificato:

| Selettore | Snippet `item`/`selectedItem` | Esito |
|---|:---:|---|
| `AssetSelect`, `BrokerSearchSelect`, `UserSearchSelect` (in `ui/select/`) | ✅ | corretti |
| `SignalAssetParamControl` (in `charts/`) | ❌ | **mostra l'id** |
| `AssetSetRiskPanel` (in `risk/`) | ❌ | **due volte** — broker `:49` e asset `:55` → mandato **F** |

> Non è un caso isolato: è ciò che succede quando si costruisce un picker ad hoc invece
> di riusare quello che c'è.

**La cura è il riuso, come chiesto dal developer**: `SignalAssetParamControl` si appoggia
ad **`AssetSelect`** (187 righe), che è il picker decente già scritto — icona, ticker,
valuta con bandiera, asset inattivi ordinati in fondo e marcati. Il suo stesso commento
d'intestazione invita a farlo: *«Migrate other asset_id pickers to use this when
convenient»*.

L'esclusione oggi fatta con `excludeAssetIds` si esprime col suo
`filter?: (a: AssetInfo) => boolean`.

**E si guadagna una correzione non richiesta** (**D74**): `SignalAssetParamControl` mette
**valuta e tipo** fra i termini cercabili, mentre `AssetSelect` li esclude
deliberatamente, con la ragione scritta nel codice — `eur`, `bon`, `etf` sono prefissi
condivisi da centinaia di righe, quindi **restituivano l'intero elenco** e la ricerca
sembrava funzionare solo dalla quarta lettera.

**Come si combina con K3**: `AssetSelect` espone già `suggestedIds` — *«prioritized
items shown at the top of the list with a badge»* — che è esattamente il meccanismo per
appuntare i benchmark in cima, **opt-in per punto di chiamata**, quindi senza
trascinarli dentro lo staging delle transazioni. In alternativa restano le intestazioni
di sezione (`SelectOption.header`), che funzionano anche con gli snippet perché si
disegnano in un ramo separato. **Scegliere l'una o l'altra è del mandato**; entrambe
esistono già.

### 5.3 Le tre cose che il catalogo non fa

Vale la pena elencarle, perché sono tre ipotesi scartate che tornerebbero da sole:

| Non fa | Perché | Dove |
|---|---|---|
| Non salva la scelta sul server | La preferenza sta in `localStorage`; il benchmark viaggia nella richiesta, il backend resta senza stato | **D64** |
| Non risolve una lista curata di ISIN | I suggerimenti sono **testi fissi tradotti**, nessuna chiamata ai provider | **D65** |
| Non nomina prodotti | «Un ETF sull'S&P 500», mai un ISIN o un ticker | **D68** |

⚠️ **Regola di degrado obbligatoria** (**D64**): se l'asset in cache viene cancellato o
privato del flag, la zona degrada allo **stato vuoto**, non va in errore. La cache
locale non può assumere che il server sia rimasto d'accordo con lei.

⚠️ **La conversione valutaria è obbligatoria** (**D66**): se il benchmark è in USD e la
valuta base è EUR, il beta misura **anche il cambio**. Si converte con il sistema FX
che esiste già. Senza, il numero è contaminato in silenzio.

---

## 6. Gesto 3 — Allineare i punti che raggruppano

⚠️ **La parte che si dimentica, e l'unica che può fare danno silenzioso.**

`asset_type` non decide cosa il sistema *fa*, ma decide in continuazione come il
sistema **somma**. I punti censiti (Q12):

| Punto | Dove | Se lo dimentichi |
|---|---|---|
| Scenari stress | `scenario_catalog/built_in/hypothetical/*.yml` — 2 file | **Shock silenziosamente a zero** |
| `PNG_MAP` | `assetTypes.ts:19-31` | Icona grigia `other.png`, nessun errore |
| Etichette | `i18n/{en,it,fr,es}.json`, namespace `assets` | Chiave grezza a schermo |
| Filtro tabella | `AssetTable.svelte:181` — elenco **scritto a mano** | I nuovi tipi non sono filtrabili |
| Filtro backend | `crud.py:180-181` | Un filtro `ETF` non trova gli ETF specializzati |
| AI export | `asset_resources.py:110` | ✅ **nulla**: viaggia come `str` libero |

**Il caso peggiore, verificato.** `service.py:446` scrive
`asset_class=asset_type.value`, e gli YAML elencano i secchi per nome:

```yaml
bucket_shocks:
  ETF: -0.25      # ← non troverebbe più ETF_STOCK
```

`_resolve_bucket` (`stress.py:219-226`) **non solleva errore**: ritorna
`UNCONFIGURED_ZERO`, shock `0.0`. In un crollo azionario i tuoi ETF azionari non si
muovono.

Ma i due YAML **sono file nostri** (**D70**): non un vincolo, un **compito**. Si
riscrivono qui, e ne escono migliori — `ETF: -0.25` è già oggi un difetto di modello,
perché colpisce un obbligazionario come un azionario. Con i sottotipi diventa
`ETF_STOCK: -0.35`, `ETF_BOND: -0.05`.

### 6.1 Il cancello G-B è più severo del solito

> Non basta aggiornare le cinque tabelle. Serve **un test che leghi l'enum a tutte**,
> perché tutte ripiegano in silenzio: `other.png` per l'icona, la chiave grezza per
> l'etichetta, `UNCONFIGURED_ZERO` per lo scenario.
>
> Oggi la copertura è affidata alla buona volontà, e un buco non si vede.

Il test deve affermare: per **ogni** valore di `AssetType` esistono una voce in
`PNG_MAP`, un'etichetta in tutte e quattro le lingue, e un secchio in ogni scenario
`asset_class`.

---

## 7. Contratti in uscita

### K2 → mandato G

```typescript
export function primaryAssetType(type: string): string
```

Esportata da `assetTypes.ts`. ⚠️ **Mappa esplicita, mai divisione su `_`**: `REAL_ESTATE`
è un **tipo primario** che contiene un underscore, e spezzarlo produrrebbe un genitore
inesistente (Q12).

`assetTypes.ts` è **di questo mandato** ([`README.md`](./README.md) §2.3): G consuma,
non scrive. Così sparisce l'unico conflitto frontend pericoloso.

### K3 → mandati E ed F

La firma del selettore benchmark ordinato a sezioni, e la regola di degrado a stato
vuoto.

---

## 8. Confini

**Di questo mandato**:

- `backend/app/db/models.py` e **una sola** migrazione Alembic incrementale
- `backend/app/schemas/assets.py`, `backend/app/services/assets/crud.py`
- `backend/app/services/risk/scenario_catalog/built_in/**`
- `frontend/src/lib/utils/assetTypes.ts` — **scrittore unico**
- `frontend/src/lib/components/assets/AssetModal.svelte` (la sezione del tipo e il
  footer) e `AssetTable.svelte` (l'elenco a `:181`)
- `SignalTreeSelect.svelte` → generalizzato in `components/ui/select/`
- `SignalAssetParamControl.svelte`
- i18n: **solo** il namespace `assets` (righe ~70-360)

**Fuori**: tutto ciò che è rischio. Questo mandato **non** tocca
`components/risk/**`, né gli analytic, né `metrics.py`.

⚠️ **Il criterio di ambito, contro l'allargamento**: si estendono **solo i tipi dove la
distinzione ha senso** (**D52**). Se la migrazione Alembic comincia a crescere di
colonne, il mandato sta diventando una riforma del modello asset — ed è il rischio 3 di
[`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §10.

---

## 9. Ordine dei passi

1. Migrazione Alembic **unica**: colonna benchmark + nuovi `AssetType` + backfill
   `INDEX` + correzione del docstring bugiardo.
2. Backend: schemi, filtro e ordinamento in lista.
3. `./dev.py api sync`.
4. `assetTypes.ts`: `PNG_MAP`, pastiglie, `primaryAssetType` → **comunicare K2**.
5. i18n, namespace `assets`, quattro lingue.
6. I due YAML di scenario, riscritti.
7. `AssetTable.svelte:181` e `crud.py:180-181`.
8. Generalizzazione di `SignalTreeSelect` + secondo slot icona.
9. `AssetModal`: albero a due livelli, interruttore nel footer, **readonly se `INDEX`**.
10. `SignalAssetParamControl`: **prima** migrarlo ad `AssetSelect` (§5.3, **D73**),
    **poi** l'ordinamento a sezioni → **comunicare K3**.
11. **Il test enum ↔ tabelle** (§6.1).

---

## 10. Test

| Cosa | Comando |
|---|---|
| Migrazione su DB fresco | `db` (con la data dir assegnata) |
| Schemi | `schemas assets` |
| API asset | `api assets` |
| Scenari | `services risk-all -k scenario` |
| Il test enum ↔ tabelle | dove `test-author` decide, registrato nel catalogo |
| Frontend | lint, type-check, spec toccati |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6241 --data-dir backend/data/test-risk-b \
  services risk-all
```

---

## 11. Definizione di finito

- [ ] Una sola migrazione Alembic, incrementale, che gira su DB fresco **e** su uno
      popolato;
- [ ] backfill `INDEX → benchmark` verificato;
- [ ] docstring `valuation_model` corretto;
- [ ] `api sync` eseguito;
- [ ] **il test enum ↔ tabelle esiste e passa** (cancello G-B);
- [ ] i due YAML riscritti, con gli shock differenziati per sottotipo;
- [ ] `SignalTreeSelect` generalizzato **senza** cambiare il comportamento per i segnali;
- [ ] benchmark in cima al selettore, con degrado a stato vuoto;
- [ ] **il segnale beta mostra i nomi, non gli id** (D73) — `SignalAssetParamControl`
      appoggiato ad `AssetSelect`, esclusione espressa via `filter`;
- [ ] la ricerca non restituisce più l'intero elenco digitando `eur` o `etf` (D74);
- [ ] **K2 e K3 consegnati e comunicati**;
- [ ] nessun processo in ascolto su `6241`.
