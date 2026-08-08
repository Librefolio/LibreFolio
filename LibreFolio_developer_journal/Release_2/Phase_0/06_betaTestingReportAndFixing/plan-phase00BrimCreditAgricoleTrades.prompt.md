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

## B5 — Suddivisione in più transazioni

Una riga → più transazioni. «+ transazione» aggiunge gambe, con il **residuo da allocare** sempre
visibile.

**Regola di approvazione, come da indicazione del committente:**

> Un blocco di gambe **non è approvabile** finché la somma della loro cassa **non coincide** con
> l'importo della riga dell'estratto conto. Residuo ≠ 0 → non si chiude.

È ciò che rende la funzione sicura: non si può spezzare una riga sbilanciandola. Ed è la stessa
condizione che tiene vera la quadratura col `Saldo Finale`.

> ⚠️ Parte **più nuova e più rischiosa**: tocca l'invariante di cassa. Va **dopo** che il resto
> quadra, come blocco separato. Se serve tagliare, è il candidato al rinvio: senza, il sistema è
> *corretto ma approssimato di ~1.091 €* **e lo dichiara** (B3); con una suddivisione sbagliata
> sarebbe *sbagliato in silenzio*.

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

> ⚠️ **Domanda aperta, da chiarire prima di dichiarare uno scostamento**: le correzioni manuali sono
> state inserite **all'importo di cassa o al controvalore netto**? Cambia il confronto di ~426 €. Va
> verificato, non dedotto.

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
| 🛑 | **Checkpoint: collaudo e consenso UI** | ⏳ **in corso** |

### Fase B — riparazione del plugin ⏳

| Passo | Descrizione | Stato |
|---|---|---|
| B1 | `COMPRAVENDITA` → BUY/SELL | ⏳ |
| B2 | Recupero nominale dalle cedole | ⏳ |
| B3 | ⭐ Rilevatore «non comprato all'emissione» | ⏳ |
| B4 | Ritenute | ⏳ |
| B5 | Suddivisione con quadratura obbligatoria | ⏳ |
| B6 | Fixture + test | ⏳ |
| B7 | Verifica congiunta sul prod locale | ⏳ |

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
