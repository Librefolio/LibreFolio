# P3 — Ciclo di vita degli asset e identificativi

> ## ⚠️ PIANO SUPERATO — non eseguire
>
> Questo documento è stato **sostituito** da
> [`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](plan-phase00AssetIdentityAndIdentifiers.prompt.md)
> (05/08/2026), che ne assorbe integralmente l'ambito (A1–A5) e lo allarga a
> **l'identità dell'asset** nel suo complesso: doppio ISIN dei BTP «CUM», ricerca sugli
> identificativi alternativi (**A6** ➕), unificazione degli asset tra file diversi (**W2**,
> arrivata da P2) e fusione dei duplicati già presenti in DB.
>
> Resta qui solo come traccia dell'analisi originale.

> **Priorità**: 🔴 Alta — **A1 provoca danno permanente ai dati mentre restiamo fermi**
> **Ambito**: `frontend/src/lib/components/ui/select/AssetSelect.svelte`, `SearchSelect.svelte`,
> `ImportWizardModal.svelte`, `AssetModal.svelte`
> **Rilievi coperti**: A1–A5 (+ X1, X2 sospesi)
> **Riferimenti**: [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §2, §3, §5

---

## 0. Perché questo piano viene subito dopo P1

A1 non è solo un fastidio: **costringe l'utente a creare asset duplicati**. Ogni giorno che passa
con questo difetto attivo, il database accumula titoli doppi che poi andranno riconciliati e
fusi a mano. È l'unico rilievo dell'intera sessione che **peggiora nel tempo** invece di restare
stabile.

Il tester lo ha marcato da sé come grave:

> *"non facendo selezionare un disattivato, una transazione finita non si può altrimenti importare!
> **grave** perché costringe a creare un secondo asset uguale"*

---

## 🔴 A1 — Impossibile selezionare un asset disattivato durante l'import

### Evidenza

```js
// frontend/src/lib/components/ui/select/AssetSelect.svelte:64-68  — ordinamento
filtered.sort((a, b) => { if (a.active !== b.active) return a.active ? -1 : 1; ... });

// frontend/src/lib/components/ui/select/AssetSelect.svelte:73     — la riga incriminata
disabled: a.active === false,
```

```js
// frontend/src/lib/components/ui/select/SearchSelect.svelte:240
if (option.disabled) return;      // il click è un no-op silenzioso
```

Il campo è `Asset.active` (`backend/app/db/models.py:508`).

> ⚠️ **Nota di naming**: sul modello `Asset` il campo è **`active`**, non `is_active`.
> `is_active` è riservato a `User` e `Broker`. Cercare la stringa sbagliata fa concludere
> erroneamente che il campo non esista.

Lo store carica correttamente **tutti** gli asset, inattivi inclusi (`assetStore.ts:107`,
*"the FULL set... no filter"*): l'asset è quindi **visibile ma non cliccabile** — l'utente lo vede
e non capisce perché non può sceglierlo.

### Perché è la scelta sbagliata proprio nell'import

Disabilitare gli inattivi ha senso quando si **crea** una nuova operazione: non si compra un
titolo dismesso. Ma l'import è **retroattivo per natura**: importa la storia. Un BTP scaduto e
disattivato è *esattamente* l'asset a cui vanno agganciate le sue cedole e il suo rimborso.

Il vincolo è applicato in un contesto in cui la sua motivazione non vale.

### Fix

1. Aggiungere una prop `allowInactive` a `AssetSelect` / `SearchSelect` (default `false`, così
   nessun altro punto d'uso cambia comportamento).
2. Passarla `true` dal wizard di import (`ImportWizardModal.svelte:~3393`).
3. Marcare visivamente l'opzione come inattiva — **selezionabile ma riconoscibile**.
4. **Decisione di prodotto**: selezionando un asset inattivo, riattivarlo automaticamente
   (`active: true`) o lasciarlo inattivo con le transazioni collegate?
   → *Proposta*: **lasciarlo inattivo** e mostrare un avviso. Importare la storia di un titolo
   scaduto non deve farlo riapparire tra le posizioni correnti. La riattivazione resta un gesto
   esplicito dell'utente.

Il backend supporta già il cambio di stato (`FAAssetPatchItem.active`): **nessun cambio di schema**.

**Complessità**: Piccola · Solo frontend

---

## 🟠 A2 — Modale ISIN spuria quando l'ISIN è già tra gli identificativi alternativi

### Evidenza

`checkAndPromptIdentifier` (`ImportWizardModal.svelte:905-934`) legge **solo**:
- `info.identifier_isin` (`:916`)
- `info.identifier_ticker` (`:921`)

Non legge mai `info.identifier_other`, che **esiste** (`backend/app/db/models.py:519`,
`Optional[List[str]]`) ed è esposto al frontend (`assetStore.ts:58`).

Tester: *"se poi ho un isin che è dentro gli altri identificatori, non deve comparire la modale
per sostituire l'isin, perché è già consumato da un altro identificatore"* — la formulazione è
esatta: l'identificativo è **già riconosciuto**, quindi non c'è nulla da risolvere.

### Fix

Corto circuito prima di aprire la modale:

```js
if (info.identifier_other?.includes(res.extractedIsin)) return;   // già noto
```

Stesso trattamento per il ticker.

**Complessità**: Piccola · Nessun cambio di schema (il campo esiste già)

---

## 🟡 A3 — Messaggio/condizione dell'identificativo

**Verdetto: ⚠️ PARZIALE — il rilievo come formulato non si riproduce.**

Il tester riferiva: *"l'errore dell'isin non era dovuto al fatto che l'asset già esisteva, ma che
l'isin dell'import è diverso dall'isin del provider"*.

Verifica: la condizione (`:916`) è **corretta** — scatta proprio quando l'ISIN importato differisce
da quello memorizzato. E il testo, in tutte e 4 le lingue, dice:

> *"{asset} **ha già** {existing} come {type}, ma il file importato usa {value}. Vuoi sostituirlo?"*

Non esiste in codice alcuna stringa "l'asset esiste già" legata al conflitto ISIN. Il rilievo è
plausibilmente una parafrasi del *"ha già…"* iniziale.

### Difetto reale trovato nelle vicinanze

```js
// ImportWizardModal.svelte:929
identifierPromptIsConflict = existingValue !== null;
```

Se `info.identifier_isin` è la **stringa vuota** `""` invece di `null`, allora `"" !== null` è
`true` → l'interfaccia mostra il testo di *conflitto* ("sostituire?") pur non essendoci alcun
valore preesistente. L'utente legge di un conflitto inesistente.

**Fix**: normalizzare il valore vuoto (`info.identifier_isin || null`).

**Bonus di chiarezza**: valutare di arricchire il messaggio distinguendo i due casi —
*"il provider usa un ISIN diverso"* vs *"nessun ISIN memorizzato"* — perché sono situazioni
diverse che oggi condividono lo stesso testo.

**Complessità**: Banale

---

## ✨ A4 — Salvare l'identificativo del report come identificativo alternativo

### Il caso d'uso reale

> *"essendo poi che l'asset era uno dei btp cum, quindi all'emissione, quello del provider è quello
> liberamente scambiabile, io in generale aggiungerei un'opzione che dice di mettere come altro
> identificativo l'identificativo del report"*

È un caso **strutturale**, non un'eccezione: i BTP *CUM* (in collocamento) hanno un codice diverso
da quello del titolo liberamente scambiabile che il provider espone. Entrambi sono corretti,
riferiti allo stesso strumento in due fasi della sua vita. Oggi l'utente può solo **sostituire**
— cioè perdere un'informazione vera.

Nei file del beta test: `BTP PIU 25-2-33 **CUM**`, ISIN `IT0005634792`.

### Fix

Aggiungere una **terza opzione** alla modale dell'identificativo:

| Opzione | Effetto |
|---|---|
| Assegna soltanto | *(esistente)* ignora l'identificativo del file |
| Sostituisci e assegna | *(esistente)* l'ISIN del file rimpiazza quello memorizzato |
| **Aggiungi come alternativo** | **(nuova)** l'ISIN del file va in `identifier_other`, quello primario resta |
| Annulla | *(esistente + fix W6)* |

**Sinergia con A2**: una volta salvato in `identifier_other`, il successivo import **non
ripresenterà la modale** — le due fix si chiudono a vicenda e il flusso converge.

**Complessità**: Piccola/Media · `identifier_other` esiste già → nessuna migrazione

---

## ✨ A5 — Modifica asset dalle card dello step 4

> *"sarebbe utile avere l'edit asset in ogni card dello stato 4 dell'import dopo averlo assegnato"*

Oggi, per correggere un asset appena assegnato (nome, ISIN, provider), occorre uscire dal wizard —
perdendo il contesto di import.

**Fix**: pulsante "modifica" sulla card, che apre `AssetModal` in sovrapposizione e, alla chiusura,
aggiorna la card.

**Attenzione**: al ritorno vanno rivalutate le risoluzioni (se l'utente corregge l'ISIN, la
segnalazione di conflitto potrebbe non avere più senso) → coordinare con **W7** di P2, che
introduce proprio la rivalutazione dello stato di risoluzione.

**Complessità**: Media · Solo frontend

---

## ⏸️ X1, X2 — Sospesi: da riprodurre insieme al tester

> **Non pianificati.** Il codice attuale contraddice il sintomo descritto. Implementare una fix
> alla cieca rischierebbe di "correggere" codice funzionante e di lasciare intatta la causa vera.

### X1 — *"non posso riportare attivo un asset disattivato dal modifica"*

Il toggle **esiste ed è sempre renderizzato**:

```svelte
<!-- AssetModal.svelte:1860-1873 -->
data-testid="asset-active-toggle"  role="switch"  onclick={() => (active = !active)}
```

Non è condizionato a `editMode`, ed è incluso sia in `saveCreate()` (`:1142`) sia in `saveEdit()`
(`:1236`). Il backend accetta l'aggiornamento (`FAAssetPatchItem.active`, con `"active": false`
citato come esempio nella docstring di `patch_assets_bulk`).

**Da chiarire**: il toggle era *invisibile* (problema di layout/scroll nel footer della modale),
*disabilitato*, oppure *presente ma senza effetto al salvataggio*? Serve l'asset specifico.

> Ipotesi da verificare per prima: il toggle sta nel **footer** della modale e potrebbe essere
> fuori dall'area visibile su viewport ridotti — sarebbe un difetto reale, ma di layout, non di logica.

### X2 — *"anche export AI è disattivo"*

Nessun filtro su `Asset.active` esiste nell'AI export:
- `runtime_service.py:586` → `select(Asset).where(Asset.id.in_(sorted(asset_ids)))`, senza condizioni;
- `asset_core.py:138` e `asset_resources.py:112` propagano `active` come **semplice metadato di output**.

**Ipotesi alternativa**: l'asset non compariva perché a **posizione zero** (l'universo dell'export
è guidato dalle posizioni), non perché disattivato. Meccanismo diverso → fix diversa.
Serve l'export specifico e l'asset coinvolto.

---

## Ordine di esecuzione

```
A1 🔴  [subito: ogni giorno di attesa = altri asset duplicati nel DB]
  │
A3 ──▶ A2 ──▶ A4      [catena identificativi: si chiudono a vicenda]
  │
A5                     [dipende da W7 di P2]
  │
X1, X2                 [bloccati: servono i passi di riproduzione]
```

---

## Verifica

```bash
./dev.py front check
./dev.py test frontend --filter asset
```

**Test E2E da aggiungere:**

| # | Scenario | Asserzione |
|---|---|---|
| 1 | Import con asset disattivato in elenco | è **selezionabile**, e resta inattivo dopo l'assegnazione |
| 2 | ISIN già in `identifier_other` | la modale **non** compare |
| 3 | `identifier_isin === ""` | mostra il testo "nuovo identificativo", non "conflitto" |
| 4 | "Aggiungi come alternativo" | l'ISIN finisce in `identifier_other`, il primario resta invariato |
| 5 | Reimport dopo il #4 | nessuna modale — *chiusura del ciclo A2 ↔ A4* |

---

## Stato

| ID | Rilievo | Complessità | Stato |
|---|---|---|---|
| A1 🔴 | Asset disattivato non selezionabile | Piccola | ⏳ Da iniziare |
| A2 | ISIN già in `identifier_other` | Piccola | ⏳ Da iniziare |
| A3 | Condizione conflitto su stringa vuota | Banale | ⏳ Da iniziare |
| A4 | Opzione "aggiungi come alternativo" | Piccola/Media | ⏳ Da iniziare |
| A5 | Modifica asset dalle card step 4 | Media | ⏳ Da iniziare |
| X1 | Riattivazione da modifica | — | ⏸️ Da riprodurre |
| X2 | AI export su asset inattivo | — | ⏸️ Da riprodurre |
