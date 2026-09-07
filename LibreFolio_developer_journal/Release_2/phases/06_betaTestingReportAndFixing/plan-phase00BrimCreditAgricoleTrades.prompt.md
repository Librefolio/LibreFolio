# P1 — Crédit Agricole: rete di pre-allarme, poi riparazione del plugin

> **Priorità**: 🔴 Bloccante — prerequisito di ogni riconciliazione.
> **Ambito**: `backend/app/services/brim_providers/broker_credit_agricole.py` (solo layout *Movimenti Conto*),
> `backend/app/schemas/brim.py`, wizard di import frontend.
> **Rilievi coperti**: B1, B2, B3, B4, B5, B6, B7, B8
> **Riferimenti**: [`01_tassonomia_findings.md`](01_tassonomia_findings.md) §1 ·
> [`02_riconciliazione_credit_agricole.md`](02_riconciliazione_credit_agricole.md) ·
> [`INDEX.md`](INDEX.md)
>
> **v3 — 06/08/2026.** Sostituisce la stesura precedente, che riparava il plugin senza prima
> costruire una rete di pre-allarme. Motivazione della revisione in §0.

---

## 0. La sequenza (la decisione che struttura tutto)

> **Prima la rete, poi la riparazione.** Nella Fase A i 4 trade **continuano a sbagliare di
> proposito**: sono il banco di prova della rete di pre-allarme. Poi ci si ferma, il committente
> collauda, e solo dopo il consenso sulla UI si ripara il plugin.

Una rete di sicurezza **non si può validare su un sistema che non sbaglia più**. Se riparassimo
prima il plugin, la Fase A resterebbe senza casi reali su cui verificare che l'allarme scatta, che
l'elenco è comprensibile e che il blocco funziona: la collauderemmo su fixture artificiali, cioè
proprio dove i bug non si nascondono.

I 4 BTP sono l'unico caso reale, riproducibile e già capito che abbiamo. **Vanno consumati come
test, non eliminati prima di averli usati.**

```
FASE A — rete di pre-allarme            ██████  i 4 trade sbagliano ANCORA
   └─► STOP · collaudo · consenso UI
FASE B — riparazione del plugin         ██████  i 4 trade diventano corretti
   └─► verifica congiunta sul prod locale
```

---

## 1. Il problema

Il bug dei 50k non è un caso isolato: è il **sintomo di una tassonomia incompleta**.

`_classify_account_row` tipizzava 4 gruppi di causali e mandava **tutto il resto** in un fallback per
segno. Il commento nel codice dichiarava l'assunto sbagliato:

```python
# Everything else (incl. the cash side of trades) -> deposit/withdrawal by sign.
```

Presumeva che la gamba titoli arrivasse sempre dal file *Deposito Titoli*. Quando non arriva, **il
trade sparisce**: nessuna posizione aperta, cassa addebitata come se il titolo fosse stato pagato
altrove.

### Il dato reale — 12 causali, 554 righe

| Causale | Righe | Segno | Prima della fix |
|---|---:|---|---|
| `PAGAMENTO TRAMITE POS` | 218 | tutte − | fallback |
| `PAGAMENTO UTENZE` | 65 | tutte − | fallback |
| `COMMISS./SPESE SU OPERAZ. TITOLI` | 64 | tutte − | ✅ tipizzata |
| `CEDOLE, DIVIDENDI, PREMI ESTRATTI` | 56 | tutte + | ✅ tipizzata |
| `PRELIEVO SPORT. AUTOM. ALTRA BANCA` | 45 | tutte − | fallback |
| `COMMISSIONI/SPESE` | 39 | tutte − | ✅ tipizzata |
| `INTERESSI/COMPETENZE` | 28 | tutte − | ✅ tipizzata |
| `ACCREDITO EMOLUMENTI` | 26 | tutte + | fallback |
| `GIROCONTO/BONIFICO` | 4 | tutte + | fallback |
| **`COMPRAVENDITA TITOLI/FONDI/OPZIONI`** | **4** | tutte − | 🔴 **fallback = il bug** |
| `PRELIEVO NOSTRO SPORTELLO AUTOM.` | 3 | tutte − | fallback |
| `TITOLI SCADUTI O ESTRATTI` | 2 | tutte + | ✅ tipizzata |

> **La lettura chiave**: delle 365 righe che finivano nel fallback, **361 sono legittimamente cassa**
> e 4 sono trade persi. Il fallback non è sbagliato in sé — è sbagliato che fosse
> **indistinguibile** dal "non so cosa farne".

Il codice non sapeva dire la differenza tra *«questa è una spesa al supermercato, prelievo è la
risposta giusta»* e *«questa non l'ho capita, prelievo è una resa»*.

---

## 2. Come è emerso il rateo

**Non è stato calcolato. È stato notato.** È una differenza importante, perché è esattamente ciò che
il plugin può e non può fare.

Sono stati messi affiancati due numeri che **vengono da due file diversi e non si erano mai parlati**:

- la **cassa uscita** dal conto → *Lista Movimenti* (le 4 righe `COMPRAVENDITA`);
- il **`Ctv carico`** della banca → *Andamento Portafoglio*.

Se il carico fosse davvero il denaro uscito, i due numeri sarebbero uguali. Non lo sono:

| Riga file | Data | Descrizione | Cassa uscita | `Ctv carico` banca | Δ |
|---|---|---|---:|---:|---:|
| r392 | 25/02/2025 | `NOTA INF. ACQ. TIT:BTP PIU 25-2-33 CU` | 15.000,00 | 15.000,00 | **0,00** |
| r282 | 28/07/2025 | `NOTA INF. ACQ. TIT:BTP 1/3/32 1,65%` | 46.603,73 | 46.177,79 | 425,94 |
| r283 | 28/07/2025 | `NOTA INF. ACQ. TIT:BTP 01/03/35 3,35%` | 50.683,13 | 50.018,11 | 665,02 |
| r211 | 05/11/2025 | `SOTTOSC SICAV … AMUNDI PIO GLOB EQ G` | 20.129,44 | 20.129,41 | 0,03 |
| | | | | | **1.090,99** |

Tre cose saltano fuori da sole:

1. **Il BTP PIU ha Δ esattamente 0.** Comprato il **25/02/2025**, cioè **il giorno di emissione**
   («25-2-33»), a 100. Nessun rateo, nessuna commissione: cassa = nominale = carico.
2. **La SICAV ha Δ 0,03** — puro arrotondamento. I fondi non hanno rateo.
3. **Solo i due BTP comprati sul secondario hanno Δ ≠ 0.** Ed è lì il rateo.

👉 L'intuizione del committente («se non è stato comprato all'emissione, forse serve una rettifica»)
è **confermata dai dati su 4 casi su 4**.

### 2.1 Cos'è il rateo

Comprando un'obbligazione **a metà periodo cedolare**, si pagano al venditore gli interessi già
maturati. Non è costo del titolo: **torna con la prima cedola**. La banca lo tiene separato, il file
*Movimenti Conto* no — riporta **solo il totale**.

### 2.2 La scoperta che cambia il piano: **lo scorporo NON è deducibile**

Il calcolo è stato tentato. Non torna:

| Bond | Cedola semestrale | Giorni maturati (1/3 → 28/7) | Rateo teorico | Δ osservato | Residuo |
|---|---:|---:|---:|---:|---:|
| BTP 1/3/32 1,65% | 412,50 | 149 / 184 | 334,06 | 425,94 | **+91,88** |
| BTP 01/03/35 3,35% | 837,50 | 149 / 184 | 678,17 | 665,02 | **−13,15** |

Il residuo del secondo è **negativo**. Se fosse commissione sarebbe impossibile. Quindi il modello di
maturazione è sbagliato da qualche parte — convenzione, data di regolamento, o il modo in cui la
banca compone il prezzo medio. **Con i dati disponibili non è determinabile.**

Verificato anche che **non esiste una riga di commissione di negoziazione**: le 64
`COMMISS./SPESE SU OPERAZ. TITOLI` sono tutte `SPESE STACCO CEDOLA` da −1,50 € o
`ADDEBITO CAPITAL GAIN`. Nessuna vicina al 28/07/2025.

> **Conclusione, ed è il cuore del piano**: il plugin deve **accorgersi** che manca qualcosa e
> **dirlo**, non calcolarlo. Un rateo inventato è peggio di un rateo mancante: il primo è un errore
> silenzioso, il secondo è uno scarto noto e dichiarato.

### 2.3 Il rilevatore che ne deriva

Una volta recuperato il nominale dalle cedole (B2), il test è **una sottrazione**:

```
|cassa|  ==  nominale   →  comprato all'emissione alla pari: pulito, nessun avviso
|cassa|  !=  nominale   →  il totale mescola prezzo + rateo + commissioni,
                           che il file NON separa  →  ⚠ «forse serve una rettifica»
```

Verificato su tutti e 4: BTP PIU pulito, gli altri due segnalati, la SICAV segnalata per un motivo
diverso (quantità non ricavabile — non ha cedole).

> ⚠️ È un'**euristica**, quindi `warning` e mai `blocker`. Sfugge solo il caso in cui uno sconto sul
> prezzo compensi al centesimo il rateo: praticamente impossibile, e comunque innocuo.

---

## 3. Architettura: registro causale-first

Il fallback implicito è sostituito da un **registro esplicito**: ogni causale ricade in uno e un solo
livello, e nessuna può più passare inosservata.

```
riga
 │
 ├─ 1. TIPIZZATA ────────────► handler dedicato → transazione completa, silenziosa
 │
 ├─ 2. NOTA, MA NON RISOLTA ─► ripiego di cassa + TODO «da verificare» + EVIDENZA   ◄── il cuore
 │
 ├─ 3. CASSA DICHIARATA ─────► deposito/prelievo per segno, silenzioso
 │      (POS, utenze, prelievi, emolumenti, giroconto)
 │
 └─ 4. SCONOSCIUTA ──────────► deposito/prelievo per segno + notice INFO
```

Il livello 3 è il contributo concettuale: **dichiarare che deposito/prelievo è la risposta giusta**
trasforma il silenzio da "non gestito" in "gestito, ed è cassa". Il livello 2 è ciò che mancava del
tutto.

> **Invariante**: la classificazione usa **solo** `causale` + `descrizione` (+ il file stesso per gli
> indici). Nessun DB, nessuna rete, nessuno stato — coerente col contratto BRIM.

**Verifica di completezza**: tier 1 tipizzate (5) + tier 3 cassa dichiarata (6) + tier 2 irrisolta
(1) = **12** = l'intero istogramma delle causali reali. Nessuna causale reale cade nel tier 4.

### 3.1 I due gradi di dubbio

Coincidono con le severità **già esistenti** in `brim.py` — nessun enum nuovo:

| Severità | Semantica | Auto-approvabile |
|---|---|---|
| `blocker` | **Deve** essere aperta e corretta | ❌ No |
| `warning` | Da guardare, ma utilizzabile così com'è | ✅ Sì |

**Fase A**: `COMPRAVENDITA` sta interamente al livello 2 → **4 righe `blocker`**. Massimo carico
sulla rete, che è ciò che si vuole collaudare.
**Fase B**: sale al livello 1; restano `blocker` solo i casi irrisolvibili (la SICAV) e `warning`
quelli dedotti. **Stesso meccanismo, che si restringe progressivamente.**

### 3.2 Come si spiega un dubbio: **tabella navigabile + commento umano**

> Indicazione del committente, e diventa il modello per **tutti** i messaggi del plugin — non solo
> per le righe di origine.

Un avviso era una stringa. Diventa una coppia **dati + interpretazione**:

```python
class BRIMEvidence(BaseModel):
    title: str                       # "Riga di origine", "Cedola corrispondente", "Confronto"
    headers: List[str]
    rows: List[List[str]]
    row_numbers: List[int]           # numero di riga nel file sorgente
    comment: Optional[str] = None    # il commento "umano" su cosa non torna
```

Esempio, il trade non risolto in Fase A:

| # | Data | Causale | Descrizione | Importo |
|---|---|---|---|---:|
| **283** | 28/07/2025 | COMPRAVENDITA TITOLI/FONDI/OPZIONI | NOTA INF. ACQ. TIT:BTP 01/03/35 3,35% | −50.683,13 |

> 💬 *Questa riga è un'operazione su titoli, ma dalla descrizione non ricavo quantità e strumento.
> L'ho registrata come prelievo: **l'importo è giusto, il titolo manca**.*

E in Fase B, quando il nominale è noto ma il totale non torna, l'evidenza diventa **due tabelle**
(la riga di acquisto e la cedola che le ha dato il nominale) più:

> 💬 *Cassa uscita 50.683,13 € contro un nominale di 50.000. La differenza è rateo cedolare e
> commissioni, che il file non separa. Se ti serve il costo di carico esatto, spezza la riga.*

**Perché è meglio del solo testo**: il numero che non torna resta **verificabile accanto alla frase
che lo spiega**. Chi legge non deve fidarsi — può guardare.

---

# FASE A — Rete di pre-allarme ✅ *(consegnata 06/08/2026)*

> Obiettivo: il sistema **riconosce di non aver capito** e lo dice bene.
> **I 4 trade restano sbagliati.** La loro classificazione non è stata toccata.

## A1 — Registro causali a 4 livelli ✅

`_classify_account_row` riscritta come dispatch esplicito, ora restituisce una **tripla**
`(tipo, cassa, livello)`. Livello 3 popolato con la whitelist ricavata dai dati (POS, utenze,
prelievi ATM ×2, emolumenti, giroconto). `COMPRAVENDITA` inserita al **livello 2**: resta
deposito/prelievo per segno, ma **segnalata `blocker` con evidenza**.

> **Nota implementazione**: passo che **non cambia una sola transazione prodotta** — cambia solo ciò
> che il sistema *dichiara* di sapere. I livelli 2, 3 e 4 condividono lo stesso ripiego per segno.

## A2 — `BRIMNotice`, livello INFO, `BRIMEvidence` ✅

`warnings: List[str]` → `List[BRIMNotice]`, con `severity` (`info` | `warning`), `code` stabile per
i18n, `message`, `evidence` e `context`.

> **Nota implementazione — la scelta che ha evitato una migrazione di massa**: un
> `field_validator(mode="before")` converte una stringa in
> `BRIMNotice(severity="warning", code="generic", message=…)`. Le **198 chiamate
> `warnings.append("…")` sparse su 30 provider continuano a funzionare immutate**. Prova sperimentale:
> dei 457 test preesistenti **455 sono passati senza modifiche**; gli unici 2 rossi erano test che
> iteravano i warning come stringhe.
>
> Frontend: `./dev.py api sync` eseguito, `BRIMNotice`/`BRIMEvidence` presenti in `generated.ts`;
> nuovi tipi esportati in `types/files.ts`. Resa: **`info` azzurro, `warning` ambra**, sia nel
> pannello di dettaglio parse sia nella modale di conferma su **Avanti** — che compare per entrambe le
> severità, perché un `info` è una decisione presa dal plugin, non rumore da saltare.

## A3 — Evidenza sui todo + riga di origine ✅

`BRIMFieldTodo` guadagna `evidence: List[BRIMEvidence] = []`. In Fase A il plugin ci mette la **riga
del file con le intestazioni** e il commento. Campo **opzionale**: additivo, gli altri 29 provider
restano invariati.

> **Nota implementazione**: il todo usa `field="asset_id"`, che nella transazione prodotta è vuoto.
> Questo aggancia gratuitamente l'auto-clear già presente in `TransactionBulkModal` — appena
> l'utente sceglie il titolo, il blocker sparisce da solo.
>
> Alternativa scartata: rileggere `GET /files/{id}/preview` e indicizzare la riga → seconda fetch e
> soprattutto **disallineamento degli indici** se la preview tronca o pagina. Il dato ce l'ha già il
> plugin nel momento in cui segnala.

## A4 — Visibilità del blocco in `TransactionBulkModal` ✅ *(ambito ridotto — vedi nota)*

Il **gate di salvataggio richiesto esisteva già**: `hasTodoBlockers` → `commitDisabled`, più la
classe riga `row-todo-blocker`. I nuovi todo `blocker` ci si innestano senza modifiche.

> **⚠️ Fuori pista — un buco trovato strada facendo**: il gate funzionava, ma **il messaggio del todo
> blocker non veniva mostrato da nessuna parte**. L'utente vedeva una riga rossa e un Salva
> disabilitato, senza mai leggere il perché. Aggiunto un banner rosso che elenca le righe bloccate con
> numero, messaggio e **tabelle di evidenza**. `ImportTodo` ora trasporta `evidence`.

> **Nota implementazione — deviazione dichiarata**: il piano prevedeva un **pannello di revisione
> dedicato nello Step 3** (elenco righe, apertura in `TransactionFormModal`, conferma rapida,
> «conferma tutte», gate su `step3CanContinue`). **Non è stato costruito**, per due motivi:
>
> 1. la richiesta originale del committente — *«arrivati in bulk transaction modal, non si possa
>    fare salva finché non le ha visionate»* — è **già soddisfatta** dal gate esistente, ora reso
>    visibile;
> 2. la motivazione tecnica del pannello (il rilevamento duplicati confronta una riga tipizzata
>    `WITHDRAWAL` invece che `BUY`) **sparisce con B1**, che corregge il tipo all'origine. Costruire
>    ora una UI di correzione manuale per un difetto che la Fase B elimina rischia di essere lavoro
>    da buttare.
>
> Decisione rinviata al checkpoint: se al collaudo la correzione nel bulk modal risulta scomoda, il
> pannello si costruisce; altrimenti decade.

## A5 — Messaggio delle rettifiche ✅

I «36 movimenti iniziali» sono **33 `GIRO ALTRO DOSSIER` + 3 `VERS.TITOLI`** — confermato dai file.

Testo precedente: due frasi lunghe, gergo interno («gamba»), nessun riferimento alle righe. Ora è un
notice **INFO** con evidenza (l'elenco delle 36 righe in tabella):

> **Titoli trasferiti da un altro dossier (36 righe)**
> Registrati come rettifiche, senza movimento di cassa: erano già tuoi, non li hai comprati ora.
> Ogni riga mantiene il prezzo di carico della banca, quindi lo stesso titolo può comparire più
> volte a prezzi diversi.

> **⚠️ Fuori pista — bug preso in revisione**: la prima stesura interpolava `tx_type.value.lower()`,
> facendo comparire l'inglese `withdrawal` dentro una frase italiana. Sostituito con
> `"prelievo"/"versamento"` espliciti.

## Verifica sui dati reali ✅

Eseguita end-to-end sui 3 file veri del beta tester:

| Metrica | Atteso | Osservato |
|---|---|---|
| Todo `blocker` | 4 (le righe `COMPRAVENDITA`) | **4** — r211, r282, r283, r392 |
| Notice tier 4 (causale sconosciuta) | 0 | **0** |
| Righe di cassa segnalate a torto | 0 su 361 | **0** |

> **Zero falsi allarmi.** È il criterio più importante del checkpoint, e la whitelist del livello 3
> copre l'intero istogramma reale.

**Test**: 463 passati (`./dev.py test external brim-providers`), di cui **6 nuovi**:
disgiunzione dei livelli del registro, *cassa dichiarata non genera allarme*, *il trade è bloccato e
non silenziosamente incassato*, *il todo porta con sé la riga di origine*, *causale sconosciuta come
INFO*, *coercizione stringa → `BRIMNotice` su un provider non toccato*.
**E2E**: 8 passati (`./dev.py test front-transaction tx-brim-import`). **svelte-check**: 0 errori.

---

## 🛑 CHECKPOINT — collaudo e consenso UI ⏳ *(in corso)*

Si consegna e **ci si ferma**. Import dei 3 file reali e verifica:

| # | Cosa deve succedere | Stato |
|---|---|---|
| 1 | Le **4 righe `COMPRAVENDITA` compaiono come da verificare** (`blocker`) | ✅ verificato lato backend |
| 2 | Le 361 righe di cassa **non** compaiono: nessun falso allarme | ✅ verificato lato backend |
| 3 | L'evidenza (tabella + commento) è leggibile e utile | ⏳ **giudizio del committente** |
| 4 | Il Salva resta bloccato finché i `blocker` non sono risolti | ✅ gate preesistente + banner |
| 5 | Pannello di revisione nello Step 3: serve davvero? | ⏳ **decisione al collaudo** |
| 6 | Il notice INFO delle 36 rettifiche è azzurro e comprensibile | ⏳ |
| 7 | Correggendole a mano, i totali tornano | ⏳ |

> Il **punto 2 è il più importante e il meno ovvio**: una rete che segnala troppo viene ignorata, e
> allora tanto vale non averla. 4 allarmi su 554 righe è il bersaglio, ed è stato centrato.
>
> Il **punto 3 è quello su cui serve il giudizio del committente**: è il modello di come il plugin
> parlerà da qui in avanti, in tutti i messaggi.

**La Fase B non parte prima del consenso sulla UI.**

---

# FASE B — Riparazione del plugin ⏳

> Solo dopo il checkpoint.

**Ordine di esecuzione approvato (08/08/2026)**: `B1 → B2 → B4 → B3 + B5-lite → B6 → B7`.
>
> B4 precede B3 perché il rilevatore del rateo confronta la cassa con il nominale, e le ritenute
> cambiano gli importi di cassa delle cedole da cui il nominale viene ricavato: misurare uno scarto
> su numeri che stanno per cambiare significa doverlo rimisurare. B5-lite nasce attaccata a B3,
> come azione della stessa evidenza.

## B1 — `COMPRAVENDITA` → BUY/SELL

Sale al livello 1. Sotto-dispatch sulla descrizione — verificato sui dati reali: `NOTA INF. ACQ.` e
`SOTTOSC` sono acquisti; per le vendite ci si aspetta `VEND`/`RIMBORSO`/`DISINVEST`. **Il segno
dell'importo fa da conferma.** Disaccordo tra parola chiave e segno → `blocker`, mai una scelta
arbitraria.

> ⚠️ **Doppia contropartita — il rischio più insidioso.** `_parse_securities` aggiunge un `DEPOSIT`
> prima del BUY perché quel file non ha cassa. Nei *Movimenti Conto* **la cassa è la riga stessa**:
> aggiungere una contropartita raddoppierebbe il movimento. Test dedicato.

> ⚠️ Nei dati reali **non esistono vendite**: il ramo SELL nascerà testato solo su fixture. Va
> dichiarato come tale, non spacciato per verificato.

## B2 — Recupero della quantità dalle cedole

Le cedole portano **ISIN + `NOMINALE`**, e i nomi combaciano **per prefisso**:

| Acquisto (troncato) | Cedola (troncata) | ISIN | Nominale |
|---|---|---|---:|
| `BTP 1/3/32 1,65%` | `BTP 1/3/32 1,65%` | IT0005094088 | 50.000 |
| `BTP 01/03/35 3,35%` | `BTP 01/03/35 3,35%` | IT0005358806 | 50.000 |
| `BTP PIU 25-2-33 CU` | `BTP PIU 25-2-33 CUM` | IT0005634792 | 15.000 |

Indice **nome → (ISIN, nominale)** su tutto il file, interrogato per prefisso.

> ⚠️ I due campi sono **troncati a larghezze diverse**: confronto per **prefisso normalizzato e
> bidirezionale**, mai per uguaglianza.
>
> ⚠️ **Ambiguità ⇒ `blocker`, mai un'ipotesi.** Un nominale sbagliato crea una posizione sbagliata
> che poi inquina il FIFO a valle: molto peggio del chiedere.

Precedente già in produzione: `income_identity_by_date` fa lo stesso per le scadenze, chiavato per
data. **Si generalizza un meccanismo esistente.**

Esito atteso: **3 bond risolti**, **la SICAV resta `blocker`** — non ha cedole, quindi le sue
1.843,575 quote non sono ricavabili da nessuna parte.

## B3 — Rilevatore «non comprato all'emissione» ⭐

Confronto `|cassa|` vs nominale (§2.3). Se differiscono → `warning` con **due tabelle di evidenza**
(riga di acquisto + cedola che ha fornito il nominale) e il commento che spiega la differenza e
propone la rettifica.

> Non calcola nulla: **misura uno scarto e lo mostra**. È la forma più onesta di intelligenza che il
> plugin può avere su questo dato.

## B4 — Ritenute sulle cedole

Tutte le 56 cedole portano `RITENUTA`: **2.203,42 €** mai registrati. Cedola **lorda** + gamba `TAX`
separata. Verificato: `15.000 × 2,85% ÷ 4 = 106,88` lordo − `13,36` = **93,52** = ciò che si importa
oggi.

> Mantiene la cassa fedele al `Saldo Finale` della banca — la prova di quadratura più severa
> disponibile.

> ⚠️ **Rompe la deduplica verso il passato**: una cedola già importata **netta** (93,52) non
> corrisponde più alla stessa cedola letta **lorda** (106,88), quindi al re-import non risulta
> duplicata e verrebbe contata due volte.
>
> ✅ **Deciso (08/08/2026, committente)**: rischio accettato, **nessun avviso e nessuna migrazione**.
> Un solo utente usa Crédit Agricole: gli verrà chiesto di **cancellare e reimportare da zero**
> quando la Fase B è completa. Da non trasformare in codice di compatibilità.

## B5 — Suddivisione in più transazioni ➡️ **ridotta a B5-lite** *(deciso 08/08/2026)*

L'idea originale: una riga → più transazioni, «+ transazione» aggiunge gambe, **residuo da
allocare** sempre visibile, e

> un blocco di gambe **non è approvabile** finché la somma della loro cassa **non coincide** con
> l'importo della riga dell'estratto conto. Residuo ≠ 0 → non si chiude.

Perché serve, in una riga: l'estratto conto porta **un solo importo netto che impacchetta eventi
diversi**. Nel BTP del beta test quell'unico numero contiene *acquisto a corso secco + rateo +
commissione*; registrato come un solo BUY, gonfia il **costo di carico di ~1.091 €**, e quel numero
sbagliato entra nel FIFO e inquina ogni plusvalenza futura. Il committente lo ha già dovuto fare a
mano (acquisto al controvalore netto, commissioni a parte).

### Cosa manca oggi

Il plugin **sa già** emettere più transazioni da una riga (gambe FEE/TAX, contropartite fittizie del
*Deposito Titoli*). Manca il pezzo **guidato dall'utente**:

- `FixPatch` (`FixFlaggedStep.svelte`) è `{type, asset_id, quantity}` → **una riga = una
  transazione**: nessun campo cassa, nessun «+ gamba», nessun residuo;
- il wizard non ha un modello «una riga di origine → N transazioni in anteprima»;
- manca il collegamento riga→gambe per evidenza e deduplica.

### La decisione: B5-lite

> ✅ **Deciso (08/08/2026, committente)**: l'editor di gambe generico **non si fa**. Chi deve
> aggiungere altro lo fa dalla **bulk transaction**, che esiste già ed è il posto giusto per
> l'editing libero.
>
> Si fa invece **B5-lite**: B3 misura già lo scarto fra cassa e nominale. Invece di limitarsi a
> dichiararlo, offre un bottone **«applica la rettifica»** che spezza *quel* caso in **due gambe
> precalcolate** — BUY a corso secco + rateo — e nient'altro.
>
> Nessun editor generico, nessun residuo da gestire a mano: **il residuo è zero per costruzione**,
> perché le due gambe sono derivate dallo stesso importo di riga. È l'unica forma di suddivisione
> che non può sbilanciare la cassa.

Copre il caso reale (~1.091 €, 2 titoli) a una frazione del costo e del rischio dell'editor libero.

## B6 — Fixture e test

`credit_agricole-conti.csv` ha già **una riga per causale** e la cedola `BTP SAMPLE` che combacia con
l'acquisto: il recupero del nominale è testabile **senza toccare dati reali**. Da aggiungere: una
vendita, un fondo senza cedole, un acquisto alla pari (cassa = nominale) e uno sopra la pari.

Test:

- Un test di livello per ogni causale del registro → una causale nuova non può più entrare in
  silenzio nel fallback. *(già presente da A1)*
- `COMPRAVENDITA` → BUY, **nessun deposito/prelievo spurio**.
- Recupero nominale per prefisso con troncamenti diversi; prefisso ambiguo ⇒ `blocker`.
- Trade senza quantità ricavabile ⇒ `blocker`, non prelievo. *(già presente da A1)*
- **B3**: cassa = nominale ⇒ nessun avviso; cassa ≠ nominale ⇒ `warning` con 2 evidenze.
- Vendita (solo fixture).
- Ritenuta: lordo − ritenuta = netto della banca.
- Coercizione stringa → `BRIMNotice` su un provider **non toccato**. *(già presente da A2)*
- Suddivisione che non chiude con residuo ≠ 0.

⚠️ **Nessun dato del beta tester nelle fixture** — sono dati bancari personali.

```bash
./dev.py test external brim-providers
./dev.py api sync        # dopo modifiche a brim.py
./dev.py lint && ./dev.py format
```

## B7 — Verifica congiunta

Broker nuovo sul **prod locale**, import dei 3 file insieme, confronto con
`Andamento Portafoglio_CAI_20260805174957.xlsx`.

| # | Controllo | Atteso |
|---|---|---|
| 1 | **Cassa vs `Saldo Finale`** | **quadratura esatta** ← per primo |
| 2 | 4 righe `COMPRAVENDITA` | 4 trade, 0 movimenti di cassa spuri |
| 3 | BTP 01/03/35 in posizione | ✅ presente |
| 4 | Ctv carico | 529.887,94 € **+ 1.090,96** se il rateo non è stato scorporato |
| 5 | Avvisi «forse serve rettifica» | 2 (BTP 1/3/32, BTP 01/03/35) — **non** BTP PIU |
| 6 | Righe da verificare | 1 `blocker` (SICAV) |
| 7 | Ritenute | 2.203,42 € |

> Il controllo 1 è il più rapido **e** il più severo: un solo numero che, se torna, valida in blocco
> segni, contropartite e assenza di doppi conteggi.

**Confronto col server Linux**: là 3 righe sono state corrette a mano, quindi i totali devono
coincidere **salvo il BTP 01/03/35** (mai inserito) e salvo il rateo.

> ✅ **Risolta (08/08/2026, committente)**: le correzioni manuali sono state inserite **al
> controvalore netto**, con le **commissioni aggiunte a parte**. Oltre a queste, l'unico movimento
> inserito a mano è un **saldo iniziale fittizio**, che compensa il fatto che il conto titoli non
> porta liquidità propria. Nient'altro.
>
> Due conseguenze dirette:
> 1. il confronto col server Linux si fa **sul controvalore netto**, non sull'importo di cassa —
>    lo scarto di ~426 € citato sopra non si applica;
> 2. quella correzione manuale **è già una suddivisione B5 fatta a mano** (netto + commissione):
>    B5 non introduce un concetto nuovo, automatizza ciò che il committente ha già dovuto fare.

---

## 4. Rischi

| # | Rischio | Perché | Contromisura |
|---|---|---|---|
| 1 | **Doppia contropartita di cassa** | I due layout hanno regole opposte | Mai contropartite in `_parse_account_movements`. Test dedicato |
| 2 | Nominale errato da prefisso ambiguo | Posizione sbagliata → inquina il FIFO | Ambiguità ⇒ `blocker` |
| 3 | Regressione sugli altri 29 provider | `warnings` cambia forma | ✅ Validator di coercizione + test su provider non toccato — 455/457 test verdi senza modifiche |
| 4 | **Troppi allarmi** | Una rete rumorosa viene ignorata | ✅ Livello 3 esplicito; 4 allarmi su 554 righe, verificato sui dati reali |
| 5 | Ramo SELL non verificato sul campo | Zero vendite nei dati reali | Test su fixture; dichiarare il limite |
| 6 | Suddivisione che sbilancia la cassa | Tocca l'invariante | Non approvabile con residuo ≠ 0; blocco separato |
| 7 | Δ rateo scambiato per bug | ~1.091 € di scarto atteso | **B3 lo dichiara** all'import, non lo si scopre dopo |
| 8 | **Tentazione di calcolare il rateo** | I conti **non tornano** (§2.2) | Vietato dedurlo: si misura lo scarto e si chiede |

---

## 5. Vincoli

- **Due layout CA distinti**: *Deposito Titoli* (contropartite artificiali) e *Movimenti Conto*
  (cassa reale). **Non vanno mai unificati.**
- Segni: `BUY → cash < 0`, `SELL → cash > 0`; `FEE`/`TAX`/`WITHDRAWAL` < 0;
  `INTEREST`/`DIVIDEND`/`DEPOSIT` > 0.
- Nessun accesso a DB o rete durante il parse.
- Dopo modifiche a schemi/API: `./dev.py api sync`.
- **Nessun commit da parte dell'agente**: li esegue il committente.

---

## 6. Stato

### Fase A — rete di pre-allarme ✅

| Passo | Descrizione | Stato |
|---|---|---|
| A1 | Registro causali a 4 livelli (`COMPRAVENDITA` → livello 2, resta sbagliata) | ✅ 06/08/2026 |
| A2 | `BRIMNotice` + INFO + `BRIMEvidence` + coercizione + `api sync` + resa frontend | ✅ 06/08/2026 |
| A3 | Evidenza sui todo (riga di origine + commento) | ✅ 06/08/2026 |
| A4 | Visibilità del blocco nel bulk modal (banner + evidenza) | ✅ 06/08/2026 — *pannello Step 3 rinviato al checkpoint* |
| A5 | Messaggio rettifiche come INFO con evidenza | ✅ 06/08/2026 |
| 🛑 | **Checkpoint: collaudo e consenso UI** | ✅ 12/08/2026 — UI approvata dal committente |

### Fase B — riparazione del plugin ✅

| Passo | Descrizione | Stato |
|---|---|---|
| B1 | `COMPRAVENDITA` → BUY/SELL | ✅ 08/08/2026 |
| B2 | Recupero nominale dalle cedole | ✅ 08/08/2026 |
| B3 | ⭐ Rilevatore «non comprato all'emissione» | ✅ 08/08/2026 |
| B4 | Ritenute | ✅ 08/08/2026 |
| B5-lite | Scorporo in due gambe guidato dal netto | ✅ 08/08/2026 |
| B5-full | ⭐ Scorporo a **N voci tipizzate** + rilevatore indipendente dalle cedole | ✅ 10/08/2026 |
| B6 | Fixture + test | ✅ 08/08/2026 |
| B7 | Verifica congiunta sul prod locale | ✅ 12/08/2026 — riconciliato al centesimo |
| B10 | ➕ Disinvestimento fondi che arriva come bonifico | ✅ 12/08/2026 |
| B11 | ➕ Segno sulle righe corrette + riga che spariva alla riapertura | ✅ 12/08/2026 |
| B12 | ➕ Riconciliazione finale | ✅ 12/08/2026 |

### Note implementazione B7 — primo giro di verifica sul prod locale (12/08/2026)

Confronto fra il DB di prod (utente `marco`, broker 4) e `Andamento Portafoglio_CAI_20260805174957.xlsx`.

**Carico totale: 540.674,69 € contro 529.887,94 € attesi.** Delta 10.786,75 €, scomposto per intero:

| Voce | € | Verdetto |
|---|---|---|
| AMUNDI PRIMO INV LC ancora in posizione | +9.648,19 | file non importato — vedi sotto |
| BTP 01/03/35: rateo + commissioni non scorporati | +665,02 | scelta dell'utente («tieni com'è») |
| BTP 1/3/32: idem | +425,94 | idem |
| prezzi a 2 decimali nel file sorgente | +47,60 | irriducibile |

Il motore di carico è **corretto**: sulle posizioni arrivate per successione il costo
coincide al centesimo con l'atteso della banca (BTP 17-11-28 → 81.659,20 vs 81.659,19;
BTP FUT 16-11-33 e BTP FUT 27-04-37 esatti). Le tre tranche per titolo non sono una
duplicazione: sono tre righe reali del file, con prezzi diversi, una per quota ereditaria.

**Il caso AMUNDI PRIMO INV LC.** Il rimborso del fondo (−1.867,178 quote, 9.984,47 €) esiste
come `SELL` corretta e già agganciata al titolo, ma solo in
`Lista Movimenti Deposito Titoli_CAI_20260725173815.xlsx`, che **non è stato importato**: il
DB contiene esattamente i 36 `ADJUSTMENT` prodotti da
`Lista Movimenti Deposito Titoli_CAI_20240605-20240801.xlsx`, che di righe ne produce 36 e
nient'altro. Nessuna riga `auto_cash` in DB conferma che il file recente non è mai passato.

Nel file di conto lo stesso evento c'è, ma sotto causale `GIROCONTO/BONIFICO`
(`ORD:AMUNDI PRIMO INVESTIMENTO … SCT::RIMBORSI`), e lì il plugin lo registra come `DEPOSIT`
di sola cassa **senza alcun todo**. È l'asimmetria con la sottoscrizione della SICAV, che
invece arriva come `COMPRAVENDITA TITOLI/FONDI/OPZIONI` e infatti produce il blocker
`ca_account_trade_unresolved` che l'utente ha corretto a mano.

> **⚠️ Fuori pista**: euristica proposta e **non** implementata. Riconoscere il rimborso di un
> fondo da un bonifico in entrata è ambiguo: nello stesso file c'è un
> `SCT:RIMBORSO IRPEF - 730` che qualunque match su «rimbors» prenderebbe per buono. Decisione
> rimandata all'utente; l'alternativa più onesta è un avviso a livello di file quando si importa
> un export di solo conto («questo export non contiene i movimenti del dossier titoli»).

#### B10 — Il disinvestimento di un fondo arriva come bonifico ✅ 12/08/2026

Approvata l'euristica e implementata. Il fondo non passa dal dossier: la casa di gestione
**bonifica** il denaro, quindi la riga cade sotto `GIROCONTO/BONIFICO` ed è indistinguibile,
*per sola causale*, da una pensione o da un rimborso fiscale.

La parola chiave da sola **non basta**: su 4 righe reali `GIROCONTO/BONIFICO` ne prende 3.
Il discriminante che regge è un altro — **chi paga è anche il soggetto del pagamento**:

| # | Riga reale | Marcatore rimborso | Ordinante ricompare | Esito |
|---|---|:---:|:---:|---|
| 1 | `ORD:AMUNDI PRIMO INVESTIMENTO … RIMBORSI … SU AMUNDI PRIMO INVES TIMENTO CL B` | ✅ | ✅ | 🔴 **blocker** |
| 2 | `ORD:DIVISIONE SERVIZI … RIMBORSO IRPEF - 730` | ✅ | ❌ | cassa silenziosa |
| 3 | `ORD:NUOVE VIE … SALDO RIMB COSTO ENERGIA` | ✅ | ❌ | cassa silenziosa |
| 4 | `ORD:AKLAMIO GMBH … RICOMPENSE AKLAMIO-SCT` | ❌ | ❌ | cassa silenziosa |

Un fondo rimborsa **sé stesso**; un rimborso fiscale riguarda qualcos'altro. Il confronto
**ignora gli spazi** (`_squash`) perché l'export spezza il nome a metà parola sulla larghezza
di colonna — `AMUNDI PRIMO INVES TIMENTO` — ed è proprio la riga che ci interessa.

Implementazione: `_sct_fund_redemption_name` + promozione da tier 3 a **tier 2** dentro
`_classify_account_row`. Nessuna UI nuova: riusa il blocker `ca_account_trade_unresolved`
già collaudato, con un `reason` dedicato (`fund_redemption`) e un messaggio proprio. La riga
resta `DEPOSIT` con la cassa giusta — **le quote non si inventano**: un fondo dichiara il
controvalore, non il numero di quote, e questo layout non ha cedole da cui ricavarlo.

Verifica sul campo: **12 file reali dell'utente, ~2.100 righe → 1 solo allarme**, sulla riga
giusta, zero falsi positivi. Test: `./dev.py test external brim-providers` → **484 passed**
(+3 nuovi: la riga che scatta, il decoy che tace, il detector sul nome spezzato).

#### B11 — Due bug trovati riprovando l'import da zero ✅ 12/08/2026

**1. La correzione non applicava le regole di segno.** `applyFixToRow` scriveva tipo e quantità
grezzi. Ritipizzare un deposito in vendita cambia ciò che i numeri hanno il diritto di
significare, e il payload usciva con `quantity > 0`: il ricontrollo duplicati falliva in blocco
(`transactions: SELL requires quantity < 0`) e ripiegava sul verdetto vecchio.

`applySignRules` — l'helper già usato dal modale bulk — imponeva **solo** il verso negativo;
`positive` era trattato come «libero». Reso simmetrico (una regola `positive` vincola quanto una
`negative`, il backend rifiuta allo stesso modo) e i versi liberi (`free`/`any`, dove il segno
*è* l'informazione: ADJUSTMENT, TRANSFER) restano intoccati. Poi agganciato al fix step: l'utente
dichiara la **grandezza**, il segno è affare del tipo, esattamente come nel form transazioni.

**2. Riaprendo una riga già decisa, la riga spariva.** `fixStepRows` tiene una riga se *ha todo
di fix* **oppure** *porta una decisione*. Applicare una correzione ritira i todo, quindi da quel
momento la riga viveva solo grazie alla decisione — e `reopenFixRow` la decisione la toglieva
**senza restituire i todo**: la riga non soddisfaceva più nessuna delle due metà e svaniva sotto
le mani dell'utente, recuperabile solo con un F5. Ora la riapertura rimette i todo dallo snapshot
(la transazione resta com'è: la bozza in editing è stata letta da lì).

Test: `vitest` → **598 passed** (+3 su `applySignRules`), `svelte-check` 0 errori, build OK.

#### B12 — Riconciliazione finale: chiusa al centesimo ✅ 12/08/2026

Reimportato da zero, l'AMUNDI è stato intercettato e completato. Carico **531.026,50 €** contro
**529.887,94 €** attesi: delta **1.138,56 €**, che è *esattamente* la somma dei residui già noti e
già accettati dall'utente:

| Voce | € |
|---|---:|
| BTP 01/03/35 — rateo + commissioni non scorporati | 665,02 |
| BTP 1/3/32 — idem | 425,94 |
| Prezzi a 2 decimali nel file d'origine | 47,60 |
| **Totale** | **1.138,56** |

Nessuno scostamento macroscopico residuo. Il delta si azzera scorporando i due bond nello step
di correzione; i 47,60 € sono irriducibili (il file non porta più decimali).

**Bug trovato e corretto**: `/assets/all` filtra `active=True`, quindi un titolo scaduto
archiviato come inattivo — l'esito verso cui spinge l'avviso di scadenza — non si apriva né
dall'ispeziona del wizard né dalla propria pagina di dettaglio. Passati i tre lookup per id a
`/assets/query` con `active` omesso.

| B8 | Asserzione sulla riga `COMPRAVENDITA` già nel fixture (buco di copertura) | ✅ 08/08/2026 — coperto da B6 |
| B9 | Avviso «titolo scaduto» anche dal layout *Movimenti Conto* | ✅ 12/08/2026 |

> **Note implementazione (08/08/2026)**
>
> - **B1** — `_classify_trade_direction` (parola chiave + segno concorde, disaccordo ⇒ `blocker`),
>   `_trade_asset_name` (dopo `TIT:` o dopo il riferimento d'ordine). `try_account_trade` crea il
>   trade **senza contropartita di cassa** (rischio n.1: qui la riga *è* la cassa) con test dedicato.
> - **B2** — indice `nominal_by_isin` costruito nella stessa pre-pass di `income_identity_by_date`,
>   confronto per **prefisso normalizzato bidirezionale** (min 6 caratteri). Nome ambiguo o nominali
>   discordi ⇒ `blocker`, mai un'ipotesi. Il trade riusa la stessa chiave `isin:` delle cedole, così
>   acquisto e reddito finiscono sullo stesso strumento.
> - **B3** — confronto `|cassa|` vs nominale nel ramo BUY: uguali ⇒ silenzio, diversi ⇒ `warning`
>   `ca_account_trade_not_at_issuance` con **due tabelle** (riga d'acquisto + cedola che ha fornito
>   il nominale). Verificato che l'acquisto alla pari **non** genera avvisi (bersaglio: pochi allarmi).
> - **B4** — `_ACCOUNT_RITENUTA_RE`; cedola **lorda** + gamba `TAX` separata sullo stesso asset e
>   sulla stessa data. Somma invariata ⇒ la cassa continua a quadrare col `Saldo Finale`. Lo storno
>   di cedola (importo negativo) **non** viene lordizzato: inventerebbe un rimborso d'imposta.
> - **Test**: `./dev.py test external brim-providers` → **478 passed**. Fixture estesa con acquisto
>   alla pari, acquisto sopra la pari, vendita, fondo senza cedole, ritenuta.
>
> **⚠️ Fuori pista — la prima lettura di B5-lite era sbagliata.** Avevo concluso che lo scorporo
> non fosse fattibile perché lo scarto misurato da B3 (`|cassa| − nominale`) **non è il rateo**:
>
> | Bond | Nominale | Cassa | `Ctv carico` banca | Rateo+comm. veri | Scarto B3 |
> |---|---:|---:|---:|---:|---:|
> | BTP 1/3/32 1,65% | 50.000 | 46.603,73 | 46.177,79 | **+425,94** | **−3.396,27** |
> | BTP 01/03/35 3,35% | 50.000 | 50.683,13 | 50.018,11 | **+665,02** | **+683,13** |
>
> I numeri restano veri — il primo bond è stato comprato **sotto la pari**, quindi lo scarto B3 è
> negativo e non ha niente a che vedere col rateo — ma la conclusione no. Correzione del committente:
>
> > *«lo split se viene fatto è valido solo se la somma degli importi delle transazioni è pari al
> > valore della transazione; il fatto che sia sotto o sopra la pari non c'entra».*
>
> L'unico invariante è **somma delle gambe = importo della riga**. Un numero lo dà l'utente (il
> controvalore netto, che è sulla nota informativa), **l'altra gamba è il resto**: il residuo è zero
> per costruzione e non serve dedurre né il rateo né le commissioni. Lo scarto B3 non è un ingrediente
> del calcolo — è solo ciò che **fa comparire la domanda**.

> **Note implementazione B5-lite (08/08/2026)**
>
> - **B3 cambia canale**: da `BRIMNotice` a **field todo `warning` sul BUY** (`field="cash"`,
>   `reason_code` invariato, `context` con cassa/nominale/delta/valuta). Motivo: un avviso che
>   l'utente **può risolvere** deve stare dove si risolve. Un test verifica che lo stesso rilievo
>   **non** compaia anche fra i notice: mostrarlo due volte insegna a saltarlo.
> - **Terzo gruppo** nello step di correzione — «Importi che comprendono più cose» — separato dai
>   trade (`blocker`) e dalle spese senza strumento: sono tre domande diverse.
> - **Una gamba, non un editor**: l'utente digita il controvalore netto, la seconda gamba è il resto.
>   Cassa in uscita ⇒ `FEE` (resta **fuori dal costo di carico FIFO** ma conta sul rendimento della
>   posizione: è esattamente ciò che serve); cassa in entrata ⇒ `INTEREST`.
> - **`splitRowAmount`** (`frontend/src/lib/utils/transactions/splitRowAmount.ts`, 8 test vitest):
>   sottrazione a virgola fissa perché `50683.13 - 50018.11` in float dà `665.0199999999968`, e una
>   gamba che non ricompone l'estratto conto è proprio ciò che la funzione deve impedire.
> - **La gamba è una transazione vera** in anteprima, inserita subito dopo la riga madre, con indice
>   in uno spazio dedicato (`1.000.000 + indice`): ri-applicare la sostituisce invece di duplicarla,
>   **Ripristina** la elimina.
> - Il ramo `INTEREST` (vendita con rateo incassato) è **implementato ma non provato sui dati reali**:
>   nei 3 file del beta test non ci sono vendite. *(Superato da B5-full: le gambe di onere sono
>   sempre in uscita, quindi `INTEREST` — che pretende cassa positiva — non serve più.)*

> **Note implementazione B5-full (10/08/2026) — due correzioni di rotta chieste dal committente**
>
> **① Il messaggio spiegava troppo, e nel posto sbagliato.** La riga chiusa dell'elenco è ciò che
> l'utente legge mentre scorre venti righe: ora dice solo *«Riga 282: acquisto di BTP 1/3/32 1,65% —
> l'importo di questa riga potrebbe raggruppare più voci insieme.»*. Tutto il ragionamento (cosa è
> stato cercato nel resto del file, cosa è stato trovato e dove) è passato al commento dell'evidenza,
> che si legge solo aprendo la riga.
>
> **② Il rilevatore dipendeva da cosa altro c'era nell'export.** Domanda del committente:
>
> > *«se io avessi importato solo l'acquisto, senza ancora la cedola, tu come avresti capito le cose?»*
>
> Risposta: **non l'avrei capito.** B3 misurava uno scarto contro il nominale, e il nominale arriva
> dalle cedole (B2). Senza cedole nello stesso file la riga finiva in `_TIER_UNRESOLVED` — bloccata
> per quantità mancante — e la zona di scorporo **non compariva affatto**. Importando per periodi
> successivi (prima l'acquisto, poi le cedole) l'avviso non sarebbe mai apparso, perché l'acquisto
> è già stato importato quando la cedola arriva.
>
> Il trigger giusto non è *«ho colto una contraddizione»* ma **«questo è un trade, e questo tracciato
> non separa mai il prezzo dagli oneri»**. Quindi:
>
> - `ca_account_trade_not_at_issuance` → **`ca_account_trade_bundled_amount`**, emesso su **ogni**
>   compravendita risolta, acquisto o vendita, con o senza scarto. Il testo dell'evidenza ha tre
>   varianti: scarto misurato, alla pari («sembra un acquisto all'emissione: se è così non c'è nulla
>   da correggere»), vendita («l'accredito è già netto»).
> - Anche le righe **bloccate** (`ca_account_trade_unresolved`) portano ora `split_hint`: sono trade
>   anche loro, solo più incompleti. La zona compare appena l'utente sceglie acquisto o vendita.
> - **Solo acquisti e vendite**: dividendi e cedole sono l'importo intero per definizione, non hanno
>   nulla da scorporare (decisione del committente, `splitApplies`).
> - **Rumore misurato prima di accettare la scelta**: sui 3 file veri passa da 2 a **3 avvisi su 507
>   transazioni**. Il timore registrato in B3 («4 allarmi su 554, non 554») non si materializza perché
>   le compravendite sul conto sono pochissime. Il test che proteggeva il caso alla pari è stato
>   riscritto — non cancellato — per documentare l'inversione e il perché.
>
> **③ Suggerimenti letti dal file** (`split_suggestions`, mostrati come elenco nel pannello). Il più
> importante **previene un errore vero**: se il file registra già una riga di spese a ±3 giorni,
> scorporarla di nuovo dal totale del trade la **conta due volte**. Gli altri restringono il campo:
> fondo ⇒ niente rateo; obbligazione ⇒ probabile rateo; totale = nominale al centesimo ⇒ forse
> all'emissione. Nessuno è dedotto da dati di mercato: tutti si leggono nell'export.
>
> **④ Da due gambe fisse a N voci tipizzate.** `splitRowAmount` → **`splitRowCharges`** (9 test
> vitest). L'utente elenca gli oneri che sa nominare — *Commissioni* (`FEE`), *Imposte e bolli*
> (`TAX`), *Rateo cedolare* (`FEE`) — e **la gamba del trade è il resto**. Invariante identico e
> più forte di prima: l'utente può solo spostare denaro **fra** le gambe, mai dentro o fuori
> dall'import.
>
> Il **rateo** non può essere un `INTEREST`: `schemas/transactions.py` regola 11 impone `cash > 0`
> per `INTEREST`, e un rateo pagato è cassa in uscita. `FEE` non è un ripiego: il rateo **non è
> costo del titolo** (torna con la prima cedola lorda, cfr. B4), quindi deve stare fuori dal costo
> di carico FIFO — che è esattamente dove `FEE` lo mette.
>
> Sulle **vendite** il segno si inverte: l'accredito è già netto, quindi la gamba del trade è
> *maggiore* della riga (`totale + oneri`), mentre su un acquisto è minore. Una sola formula,
> `main = totale ∓ Σ oneri`, con il tetto («gli oneri non possono mangiarsi tutto l'acquisto»)
> applicato solo in uscita, dove ha senso.

> **⑤ Rifinitura della UI (stessa giornata, secondo giro di riscontri).**
>
> - **Selettore del tipo di onere**: era un `<select>` nativo, ora è il `SearchSelect` di casa con
>   l'**icona della transazione che verrà creata**. Il rateo porta l'icona di `FEE` ma il proprio
>   nome: l'icona dice al sistema cosa sarà, l'etichetta dice all'utente cos'è. Le voci già usate
>   **spariscono** dalle altre righe (`kindOptions`): due righe dello stesso tipo sarebbero due
>   risposte alla stessa domanda, e la seconda si sommerebbe invece di correggere la prima.
> - Le stesse icone compaiono nella **tabellina di riepilogo**, così la riga letta e la transazione
>   che nascerà si riconoscono a colpo d'occhio.
> - **Pannelli richiudibili, un colore per gruppo** (trade → rosa, scorporo → ambra, oneri →
>   azzurro). Tingere tutto d'ambra equivaleva a non raggruppare: l'occhio legge la tinta prima del
>   titolo, e una tinta uniforme dice «un mucchio solo» per quanti titoli ci siano dentro. I
>   pannelli nascono **aperti**: una piega che nasconde lavoro in sospeso è una trappola.
> - **«Tieni tutte» / «Ripristina tutte» anche nell'intestazione di ogni pannello**, oltre che
>   nella barra globale. Con tre domande diverse sullo schermo, «tieni tutte» senza soggetto è una
>   decisione che l'utente non può verificare prima di prenderla. `acceptAllPluginFallbacks` e
>   `resetAllFixRows` accettano ora un elenco facoltativo di indici.
>
> **⑥ Bug vero trovato durante il collaudo: il ricontrollo duplicati falliva con 422.** Segnalato
> dal committente come banner rosso *«Non è stato possibile ricontrollare i duplicati (transactions:
> ADJUSTMENT requires asset_id · … +10 more)»* dopo «tieni tutte».
>
> Non era un passo saltato dall'utente. `refreshDuplicateReport` rimappava gli id fittizi degli
> asset e, per quelli **non ancora risolti**, mandava `asset_id: null` — con l'intento di far
> confrontare la riga sugli altri campi. Ma `POST /brokers/import/duplicates` valida il payload
> come `TXCreateItem` veri, e la regola 5 pretende un asset per `ADJUSTMENT/BUY/SELL/DIVIDEND/
> TRANSFER`: **una riga senza asset fa fallire l'intera chiamata**, non solo sé stessa. Le 15
> violazioni del committente = 5 asset non risolti × 3 righe (il file di deposito titoli ne genera
> 36 di `ADJUSTMENT`, da successione e `VERS.TITOLI`). Il verdetto mostrato restava quello vecchio,
> cioè calcolato prima delle correzioni: **il caso peggiore**, perché sembrava aggiornato.
>
> Correzione: le righe il cui asset è ancora irrisolto vengono **escluse dalla domanda** (array
> parallelo `asked`), invece di essere spedite monche. Non si può chiedere «questa è già nel
> database?» di una transazione che non si sa a cosa si riferisca.
>
> ✅ **Sospetto secondo difetto — verificato e SMENTITO (12/08/2026).** Avevo segnalato che
> `buildFinalTxList()` mantiene l'id **fittizio** quando l'asset resta irrisolto, quindi l'import
> finale avrebbe spedito `asset_id: 2147483647`. Rilettura del codice: **non è raggiungibile**. Il
> pulsante Importa è disabilitato da `step4CanImport = step4SelectedCount > 0 &&
> !step4HasUnresolvedSelected`, e `step4HasUnresolvedSelected` usa **esattamente lo stesso filtro**
> del payload (`t.selected && !beforeOpeningIndices.has(t.index)`). L'id fittizio sopravvive solo
> nelle righe che non partono mai. Anche le gambe di scorporo sono coperte: stanno in
> `mergedTransactions`, ereditano l'`asset_id` della madre, e sono `FEE`/`TAX` — che un asset non
> lo pretendono. Nessuna correzione può creare un `BUY` senza asset: `draftIsValid` blocca
> `rule.assetField === 'required' && d.asset_id == null`.
>
> Il ricontrollo duplicati era diverso proprio perché avviene **prima** di quel cancello: lì le
> righe irrisolte esistono per costruzione, ed è per questo che vanno escluse dalla domanda.

> **Note implementazione B9 (12/08/2026) — l'avviso di scadenza mancava metà dei casi**
>
> Segnalazione dal collaudo: `BTP 20-25 1.40FOICUM`, scaduto nel 2025, non mostrava il banner
> «titolo probabilmente scaduto» alla creazione dell'asset. Non erano gli asset aggregati: la
> fusione nel wizard **concatena** le notice (`leadRes.notices = [...leadRes.notices,
> ...folded.notices]`) e `AssetModal` le deduplica per `reason`.
>
> Causa vera: `detect_maturity_hits` era cablato **solo** in `_parse_securities`. Il layout
> *Movimenti Conto* creava correttamente la `SELL` da `TITOLI SCADUTI O ESTRATTI` ma **non** la
> `BRIMAssetNotice`. È il caso più comune, non quello raro: il file di conto è quello che copre
> anni, quindi è quasi sempre lì che si vede il rimborso.
>
> Estratto `_attach_maturity_notices(...)` a livello di modulo e chiamato da **entrambi** i rami.
> Misura sui file veri: da **0** a **3** notice (`BTP 20-25 1.40FOICUM` e `BTP 05/26 0.55FOICUM`
> nel file da 507 righe, `BTP 05/26` in quello da 79). Nessun falso positivo sul `SCT:RIMBORSO`
> IRPEF: quella riga non ha asset, e `detect_maturity_hits` salta gli `asset_id` nulli — fatto
> asserito da un test apposta, perché l'euristica cerca la parola «rimborso» che il file usa anche
> per i rimborsi di cassa.
>
> Test: 2 nuovi → **481 passed**.

### File toccati in Fase A

| File | Natura |
|---|---|
| `backend/app/schemas/brim.py` | `BRIMEvidence`, `BRIMNotice`, coercizione, `evidence` su `BRIMFieldTodo` |
| `backend/app/services/brim_providers/broker_credit_agricole.py` | registro a 4 livelli, evidenze, notice INFO |
| `backend/test_scripts/test_external/test_brim_providers.py` | 6 test nuovi, 2 corretti |
| `frontend/src/lib/api/generated.ts` | rigenerato (`./dev.py api sync`) |
| `frontend/src/lib/types/files.ts` | `BrimNotice`, `BrimEvidence` |
| `frontend/src/lib/components/transactions/import/BrimEvidenceTable.svelte` | **nuovo** — tabella evidenza |
| `frontend/src/lib/components/transactions/import/BrimNoticeList.svelte` | **nuovo** — lista notice info/warning |
| `frontend/src/lib/components/transactions/modals/ParseDetailModal.svelte` | notice strutturati |
| `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` | modale conferma azzurra/ambra, `evidence` nei todo |
| `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` | banner blocker con evidenza |
| `frontend/src/lib/utils/transactions/txPayloadHelpers.ts` | `ImportTodo.evidence` |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | 3 chiavi nuove |

### Correzioni emerse durante il checkpoint (06/08/2026)

| # | Segnalazione | Esito | Stato |
|---|---|---|---|
| C1 | «Errore» sul parse di *Lista Movimenti Deposito Titoli* | **Non è una regressione.** Log server: `200` due volte, 36 tx / 12 mapping, nessuna eccezione. Il browser stava eseguendo il bundle **precedente** alla ricompilazione: lo schema Zod vecchio era `z.array(z.string())` e rifiutava i notice strutturati. Discriminante: dei 4 file, **solo questo ha `warnings` non vuoto** — gli altri tre passano con entrambi gli schemi. **Rimedio: ricarica forzata del browser.** | ✅ diagnosticato |
| C2 | La UI dice solo «errore», mai il motivo | **Bug vero, corretto.** Banner rosso sopra la tabella Step 3 con nome file + messaggio; il badge di stato «errore» diventa una cella HTML con il messaggio nel tooltip. | ✅ 06/08/2026 |
| C3 | Risolutore duplicati: sfondo giallo, sovrapposizione totale in arancione | **Corretto.** Il pannello passa a cromia neutra (grigio/slate): il colore resta **solo** dove porta significato. Il badge di tier inverte la semantica da *gravità* a **sicurezza**: `sure` (sovrapposizione **totale**) → **verde**, è la scelta sicura; `probable` (**parziale**) → **arancione**, è quella che va guardata. | ✅ 06/08/2026 |
| C4 | Risolutore: raggruppare per grado di sovrapposizione, pannelli chiusi, badge di stato | **Fatto.** Due sotto-pannelli («Sovrapposizione parziale» per primo, poi «totale»), entrambi chiusi all'apertura. Il risolutore stesso si apre **solo** se esiste almeno un gruppo parziale; altrimenti resta ripiegato con badge verde *Tutto auto-risolto*. Con parziali presenti il badge è arancione *N da verificare*. | ✅ 07/08/2026 |
| C5 | `(asset_id)` grezzo nell'elenco «Campi da completare» | **Corretto.** Passa da `translateFieldName` → *(Asset)*, *(Quantità)*… con ripiego sul nome pulito se manca la chiave. | ✅ 07/08/2026 |
| C6 | Il titolo «Campi da completare manualmente (N)» non spiega cosa sono | **Fatto.** Icona info con tooltip: le transazioni elencate potrebbero essere sbagliate e verrà chiesto di correggerle prima di salvare. | ✅ 07/08/2026 |
| C7 | Modale «Note dall'importazione»: cosa succede con i warning? | **Ristrutturata.** Il raggruppamento passa da *file* a **gravità prima, file poi**: due sezioni distinte, *Da verificare* (ambra) sopra e *Note informative* (azzurro) sotto, ciascuna con le sue fisarmoniche per file. Prima un singolo warning sepolto fra note informative era indistinguibile da esse. Modale allargata da `lg` (32rem) a `4xl` (56rem). | ✅ 07/08/2026 |
| C8 | Testo delle rettifiche lungo e poco chiaro, da tradurre | **Riscritto** su 4 righe (identificazione → perché «Rettifica» → cosa succederà importando l'altra metà → dettaglio righe). **Ora è localizzato**: nuovo `resolveBrimNotice.ts` risolve `importWizard.brimNotice.<code>` interpolando `context`, con ripiego sul messaggio del plugin. Un plugin gira backend-side e non conosce la lingua del lettore: il `code` sì. EN/IT/FR/ES. | ✅ 07/08/2026 |
| C9 | Le righe di dettaglio dovrebbero essere ripiegabili | **Fatto.** `BrimEvidenceTable` ha ora `collapsible`: intestazione cliccabile con conteggio righe, chiusa all'apertura. Usata nella modale note e nel banner del bulk modal. | ✅ 07/08/2026 |
| C10 | «4 riga/righe» — plurale finto | **Corretto** con plurale ICU vero (`{n, plural, one {…} other {…}}`, verificato funzionante con svelte-i18n 4) su `todoBlockerVerifyHint`, `todoWarningVerifyHint`, `noticeConfirmMessage`, in tutte e 4 le lingue. | ✅ 07/08/2026 |
| C11 | Il banner blocker spinge il resto del bulk modal fuori schermo | **Corretto.** Banner ripiegato all'apertura (intestazione + conteggio), elenco con altezza massima `max-h-72` e scorrimento proprio, evidenze ripiegabili. La griglia da correggere resta visibile. | ✅ 07/08/2026 |
| C12 | La correzione arriva troppo tardi: allo step 4 non si può più cercare nel DB | ⚠️ **Confermato e peggiore del previsto** — il confronto duplicati non avviene allo step 4 ma dentro `POST …/parse` (step 3), quindi sulle righe *prima* di qualunque correzione, e non viene mai rifatto. Piano dedicato: [`plan-phase00ImportFlowStepRestructure.prompt.md`](./plan-phase00ImportFlowStepRestructure.prompt.md). | 📋 piano |

> C3 è più di un ritocco: prima *tutto* era ambra e il caso più sicuro era colorato **più** allarmante
> del caso dubbio — il segnale era invertito. Ora la scala di colore dice cosa fare, non quanto è
> grave.

**File toccati dalle correzioni**: `ImportWizardModal.svelte` (banner, tooltip, cromia risolutore),
`frontend/src/lib/i18n/{en,it,fr,es}.json` (`importWizard.parseErrorsTitle`).
Verifiche: `./dev.py front check` → 0 errori / 0 warning; `tx-import-resolution` → **10 passed**.

---

# 🏁 Riepilogo finale di P1 — consegna e passaggio di consegne

> **Documento di handoff.** Gemello del [riepilogo di P3](./plan-phase00AssetIdentityAndIdentifiers.prompt.md#-riepilogo-finale-di-p3--consegna-e-passaggio-di-consegne),
> scritto per chi coordinerà la chiusura congiunta dei due piani.
> Contiene: cosa è stato consegnato, i fuori pista (la parte più istruttiva),
> e i **task residui — tutti e soli di test**.
> Ultimo aggiornamento: **12/08/2026**.

---

## 1. Stato in una riga

**Il codice di P1 è completo e validato sui dati reali del committente.** Fase A e Fase B sono
chiuse, il checkpoint UI è approvato, e la riconciliazione con l'estratto della banca **torna al
centesimo**. Ciò che resta è **esclusivamente la formalizzazione degli E2E**, rinviata per la
stessa regola che governava P3: niente test UI finché l'interfaccia non è approvata. Ora lo è.

---

## 2. Il problema che P1 doveva risolvere

Crédit Agricole è **banca e broker insieme**: lo stesso estratto conto porta la liquidità e i
titoli. Il plugin classificava per causale, e tutto ciò che non riconosceva finiva in
**deposito/prelievo per segno**.

> Un acquisto da 50.000 € diventava un prelievo anonimo. La cassa restava giusta — ed è proprio
> questo che rendeva il guasto invisibile: **la posizione spariva**, e la perdita riaffiorava
> mesi dopo come un buco inspiegabile nel carico.

L'invariante che ne discende governa tutto il resto:

> **Meglio bloccare che indovinare.** Una riga che il plugin non sa leggere fino in fondo va
> dichiarata e passata all'utente; una riga *indovinata male* apre una posizione fantasma che
> avvelena in silenzio ogni match FIFO a valle.

---

## 3. Cosa è stato consegnato

### 3.1 Il registro a 4 livelli (`broker_credit_agricole.py`)

Ogni riga del conto finisce in uno di quattro livelli. **Tutti e quattro producono la cassa
giusta**: differiscono solo in *quanto* dichiarano.

| Livello | Cosa contiene | Voce dell'utente |
|---|---|---|
| 1 — tipizzato | Commissioni, imposte, cedole, dividendi, interessi | nessuna, è certo |
| 2 — irrisolto | `COMPRAVENDITA` e i disinvestimenti fondi | 🔴 **blocker** da correggere |
| 3 — cassa dichiarata | Stipendio, POS, utenze, bonifici | nessuna, è cassa vera |
| 4 — sconosciuto | Tutto il resto | ℹ️ notice informativa |

### 3.2 Fase A — la rete di pre-allarme

| Passo | Cosa risolve |
|---|---|
| **A1** | Il registro stesso: prima non esisteva una tassonomia, solo un `if` gigante |
| **A2** | `BRIMNotice` strutturata (codice + contesto + evidenza) al posto di stringhe, livello `INFO`, resa frontend |
| **A3** | Ogni todo porta **la riga d'origine del file** e un commento che spiega perché è lì |
| **A4** | Il blocco è visibile nel bulk modal, non solo nel wizard |
| **A5** | Il messaggio delle rettifiche diventa INFO con evidenza |

### 3.3 Fase B — la riparazione vera

| Passo | Cosa risolve |
|---|---|
| **B1** | `COMPRAVENDITA` → BUY/SELL. Parola chiave **e** segno devono concordare: se litigano la riga **non** viene tipizzata |
| **B2** | La quantità si recupera dalle **cedole dello stesso titolo** (confronto per prefisso normalizzato bidirezionale, min 6 caratteri). Nome ambiguo o nominali discordi ⇒ blocker |
| **B3** | ⭐ Rilevatore «non comprato all'emissione»: `\|cassa\| ≠ nominale` ⇒ warning con **due tabelle** (riga d'acquisto + cedola che ha dato il nominale) |
| **B4** | Le cedole arrivano nette ma il file scrive la ritenuta: import **lordo** + gamba `TAX` separata. La somma resta invariata ⇒ la cassa continua a quadrare col `Saldo Finale` |
| **B5-full** | ⭐ Scorporo a **N voci tipizzate** (commissione / imposta / rateo). L'utente dà il netto, **l'ultima gamba è il resto**: il residuo è zero per costruzione |
| **B9** | L'avviso «titolo scaduto» scatta anche dal layout *Movimenti Conto*, non solo dal dossier |
| **B10** | ⭐ Il disinvestimento di un fondo che arriva **come bonifico** |
| **B11** | Segno delle righe corrette + riga che spariva alla riapertura |

### 3.4 Fuori pista che hanno prodotto lavoro reale

Nessuno era nel piano iniziale; ognuno è nato da una prova del committente.

| # | Fuori pista | Esito |
|---|---|---|
| **1** | **La prima lettura di B5-lite era sbagliata** | Avevo concluso che lo scorporo non fosse fattibile perché lo scarto di B3 non è il rateo. Vero, ma irrilevante: correzione del committente — *«lo split è valido solo se la somma delle gambe è pari al valore della transazione»*. L'unico invariante è quello. Lo scarto B3 non è un ingrediente del calcolo: è ciò che **fa comparire la domanda** |
| **2** | **B3 cambia canale** | Da `BRIMNotice` a **field todo `warning` sul BUY**. Un avviso che l'utente **può risolvere** deve stare dove si risolve |
| **3** | **Il ricontrollo duplicati andava in 422** | Una sola riga con asset irrisolto faceva fallire l'intera chiamata, che ripiegava in silenzio sul verdetto pre-correzione. Ora le righe senza strumento sono **escluse dalla domanda**: senza strumento non potrebbero comunque collidere con niente |
| **4** | **Il disinvestimento di un fondo non passa dal dossier** | La casa di gestione **bonifica** il denaro: la riga cade sotto `GIROCONTO/BONIFICO` e per sola causale è identica a una pensione. La parola «rimborso» da sola prende **3 righe reali su 4** — il discriminante che regge è che **chi paga sia anche il soggetto del pagamento**. Un fondo rimborsa sé stesso; l'IRPEF no |
| **5** | **`/assets/all` filtra `active=True`** | Un titolo scaduto archiviato come inattivo — l'esito verso cui spinge l'avviso di scadenza — non si apriva né dall'ispeziona del wizard né dalla propria pagina. Tre lookup per id passati a `/assets/query`. Stessa cecità trovata su `fx/[pair]`, **non** corretta: è un percorso di valute, fuori ambito |
| **6** | **`applySignRules` era asimmetrico** | Imponeva solo il verso negativo, `positive` era trattato come libero. Ritipizzare un deposito in vendita mandava `quantity > 0` e il ricontrollo duplicati falliva in blocco. Reso simmetrico; i versi liberi (ADJUSTMENT, TRANSFER — dove il segno **è** l'informazione) restano intoccati |
| **7** | **Riaprire una riga decisa la faceva sparire** | Una riga vive nel fix step se *ha todo* **o** *porta una decisione*; correggere ritira i todo, e riaprire ritirava la decisione **senza restituirli**. La riga svaniva sotto le mani, recuperabile solo con F5 |
| **8** | **`duckduckgo#N` → `WebSearch#N`** | L'etichetta era vera al primo giorno; da quando la ricerca gira su 10 browser via `ddgs` era una firma falsa nei dati |

---

## 4. La prova che conta: riconciliazione col prod locale

Confronto fra il DB di prod (utente `marco`, broker 4) e l'estratto della banca
`Andamento Portafoglio_CAI_20260805174957.xlsx`, **dopo** import rifatto da zero.

| Grandezza | Valore |
|---|---:|
| Carico calcolato da LibreFolio | **531.026,50 €** |
| Carico atteso dalla banca | **529.887,94 €** |
| **Delta** | **1.138,56 €** |

Il delta è **interamente spiegato**, e sono tutte voci che il committente ha scelto di lasciare
così:

| Voce | € |
|---|---:|
| BTP 01/03/35 — rateo + commissioni non scorporati | 665,02 |
| BTP 1/3/32 — idem | 425,94 |
| Prezzi a 2 decimali nel file d'origine | 47,60 |
| **Totale** | **1.138,56** |

**Nessuno scostamento macroscopico residuo.** Le posizioni trasferite tornano al centesimo con la
banca (BTP 17-11-28 → 81.659,20 contro 81.659,19; BTP FUT 16-11-33 e 27-04-37 **esatti**).

> **Nota su un falso allarme.** Le «3 tranche per titolo» non sono un bug: sono **tre righe vere
> nel file**, una successione divisa fra eredi, ciascuna col suo prezzo. Il piano ha rischiato di
> inseguire un fantasma qui.

---

## 5. Verifiche già eseguite (tutte verdi)

| Comando | Esito |
|---|---|
| `./dev.py test external brim-providers` | **484** passati |
| `vitest` (frontend) | **598** passati su 54 file |
| `./dev.py front check` | **0 errori / 0 warning** |
| `./dev.py front build` | ok |
| `./dev.py mkdocs build` | 0 warning, 0 link rotti, i18n it/fr/es |
| `black` + `ruff` sui file toccati | puliti |
| Rilevatore B10 su **12 file reali** (~2.100 righe) | **1 solo allarme**, riga giusta, 0 falsi positivi |

---

## 6. ⏳ Task residui — sono **tutti** di test

> **Nessun task di produzione è aperto.** Come per P3, quanto segue è la formalizzazione
> rinviata per decisione del committente: niente test UI durante lo sviluppo.

### ⚠️ Vincolo di coordinamento — la suite va **una sola**

Vale integralmente quanto scritto nel riepilogo di P3: gli E2E dei due piani condividono la
porta backend **6041**, la **5173** del frontend e **lo stesso database di test**, quindi non
possono girare in parallelo.

Ma c'è di più, ed è la ragione per cui i due piani vanno chiusi insieme: **P1 e P3 attraversano
lo stesso wizard, nello stesso ordine**. Un import Crédit Agricole passa *necessariamente* per lo
step di unificazione asset di P3; e lo step di correzione di P1 **deriva il proprio picker dalle
risoluzioni di P3**. Non sono due suite che si sovrappongono: è **un solo percorso** che i due
piani hanno costruito da capi opposti.

### G‑01 — Il percorso end-to-end Crédit Agricole

1. Import del file *Lista Movimenti Conto*: gli step condizionali `assets`, `fix` e `duplicates`
   compaiono tutti e tre.
2. Una riga `COMPRAVENDITA` con quantità ricavabile dalle cedole diventa **BUY** da sola.
3. Una riga `COMPRAVENDITA` su un fondo (niente cedole) resta **blocker**: si sceglie il titolo e
   si scrive la quantità.
4. Il **disinvestimento via bonifico** compare come blocker; i tre decoy (IRPEF, rimborso energia,
   ricompense) **non** compaiono.
5. Si ritipizza in **SELL**: la quantità esce **negativa** senza che l'utente scriva il segno.
6. Lo **scorporo a N voci** produce gambe la cui somma è esattamente l'importo della riga.
7. Il ricontrollo duplicati **non** va in errore con righe ancora irrisolte in lista.
8. Il validatore finale intercetta una quantità sbagliata (posizione in negativo).

### G‑02 — Regressioni che sono già state sbagliate una volta

Non sono ipotesi: ognuna corrisponde a un difetto realmente trovato in beta.

1. **Riaprire una riga decisa non la fa sparire** (fuori pista 7).
2. **«Tieni com'è» azzera prima di accettare** — altrimenti la riga resta corretta sotto
   un'etichetta che lo nega.
3. **Un asset inattivo si apre dall'ispeziona del wizard** (fuori pista 5).
4. **L'avviso «titolo scaduto» compare anche dal layout conto** (B9).
5. **Le cedole lorde + gamba TAX sommano al netto della banca** (B4).
6. **Un acquisto alla pari non genera avvisi** — il bersaglio è *pochi allarmi*, non *molti*.

### G‑03 — Copertura E2E mancante, misurata

Come per P3, nessuno dei `data-testid` introdotti da P1 compare negli spec esistenti:

| `data-testid` | Spec che lo usano |
|---|---|
| `import-wizard-step-fix` | **0** |
| `fix-step-split-kind` | **0** |
| `asset-import-notice` | **0** |
| `import-wizard-recheck-openings` | **0** |

Gli spec da estendere sono gli stessi di P3 — `tx-brim-import.spec.ts` e
`tx-import-resolution.spec.ts` — e **quest'ultimo descrive il flusso a 5 step, ormai superato**.
Va riallineato ai 7 step condizionali *prima* di aggiungerci casi, o si costruisce sopra un
modello che non esiste più.

### G‑04 — Validazione finale congiunta

`./dev.py front check` · backend `--filter brim` e `--filter asset` · frontend `--filter import` ·
`i18n audit` · **`./dev.py api sync` una volta sola**, concordata fra i due piani (le modifiche
API sono di entrambi).

---

## 7. Punti lasciati aperti di proposito

| Punto | Stato |
|---|---|
| `fx/[pair]/+page.svelte:686` usa ancora `/assets/all` | Fuori ambito: è un percorso di coppie valutarie, non di strumenti |
| Il `reason` dell'avviso di scadenza è **italiano hard-coded** nel plugin (`broker_credit_agricole.py:377`) | Debito i18n dichiarato. Titolo e piè di pagina sono già localizzati sul `kind`; solo il bullet no |
| Asset 50 `Btpi Tf 0,15% Mg51` porta le cedole di `BTP 05/26 0.55FOICUM` | Sollevato una volta; il committente ha confermato che gli ISIN in prod sono corretti (quelli del file sono i codici d'emissione). **Non richiuso** |
| `AssetModal.svelte:668/788` usa `toLowerCase()` grezzo invece di `normalizeAssetName` | Deriva nota, segnalata dal riepilogo di P3 come «nel percorso di P1». Non corretta |
| I due BTP col rateo non scorporato | **Scelta del committente** («tieni com'è»). Sono 1.090,96 € dei 1.138,56 € di delta: scorporandoli il conto va a zero |

---

## 8. Chiusura — blindatura a test (08/08/2026) ✅

> Il codice era già in produzione e collaudato a mano dal committente; la formalizzazione dei
> test era stata **rinviata di proposito** finché la UI non fosse approvata. Approvata la UI,
> questo capitolo chiude il piano.

### Cosa si è deciso di provare

Non il broker: il **contratto**. Parole del committente:

> «i test su CA non dovrebbero servire tanto per testare CA, quanto per testare i molti nuovi
> flag che abbiamo inventato per far comunicare il pars system con il frontend»

Quindi ogni test punta a un canale plugin→frontend, non a un importo di Crédit Agricole.

### Test scritti

| Livello | File | Test | Cosa fissa |
|---|---|---|---|
| Backend | `test_brim_providers.py` → `TestPluginFrontendContract` | **13** | La *forma* che il frontend legge: `split_hint` ⇒ `split_suggestions` non vuoto · `nominale_row` punta a una riga reale · la scadenza arriva come `BRIMAssetNotice(kind="maturity_suspected")` · la causale ignota è `info`, mai `warning` · i 5 `reason_code` sono distinti e ognuno porta almeno una `evidence` con `comment` |
| Backend | `test_api/test_asset_merge_api.py` | **7** | Il livello HTTP della fusione, che aveva solo test di servizio |
| Backend | contratto endpoint duplicati | **3** | `BUY` senza `asset_id` ⇒ 422, cioè *perché* il frontend deve filtrare |
| Vitest | `fixRowLifecycle.test.ts` | **13** | Il ciclo di vita della riga nel fix step, estratto puro dal wizard |
| Vitest | `duplicateRecheckPayload.test.ts` | **8** | Chi entra e chi resta fuori dal ricontrollo duplicati |
| Vitest | `splitRowCharges.test.ts` | **17** | Scorporo a N gambe, resto sull'ultima, somma discordante |
| E2E | `tx-import-ca-contract.spec.ts` *(nuovo)* | **12** | CAC‑001…012 sui `data-testid` dei canali |

Totale della superficie CA/provider a valle: **502 test** verdi.

### Difetti trovati **dai test** (la parte interessante)

1. **Evidenza muta** — `ca_succession_transfer_in` produceva una tabella di evidenza **senza
   `comment=`**: nel frontend appariva una tabella senza spiegazione. Trovato dal test di
   contratto n. 12, corretto nel plugin.
2. **Riga riaperta che spariva** — il difetto già noto è ora **inchiodato** da CAC‑005 e dai
   test di `rowSurvivesFixStep`: non può tornare senza rompere quattro test.

### Fuori pista incontrati scrivendo gli E2E

> **⚠️ Fuori pista** — Le `BRIMNotice` **non** sono visibili nello step di analisi: vivono nella
> modale di conferma che si apre *uscendo* da quello step (`import-wizard-warning-confirm`,
> `ImportWizardModal.svelte` ~4990‑5030). Ogni E2E che prosegue oltre il terzo step su un file
> con warning **deve** chiuderla, o tutti gli step successivi semplicemente non compaiono. È il
> singolo fatto che è costato più tempo di diagnosi: annotato qui perché il prossimo non lo
> ripaghi.

> **⚠️ Fuori pista** — `fix-step-reset` sta **dentro** il corpo espanso della riga
> (`FixFlaggedStep.svelte:876`): la riga va aperta con `fix-step-row-toggle` prima di poterla
> ripristinare.

### Cosa resta da collaudare a mano

Nulla di bloccante. I due punti del §7 restano aperti per scelta (rateo non scorporato, `reason`
italiano hard-coded nel plugin).
