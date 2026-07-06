# Modello 3-Pool (K/R/W): comportamento attuale e caso limite del "prelievo anticipato" (bridge financing esterno)

**Data**: 2026-07-03
**Ambito**: `backend/app/services/portfolio_engine.py`, `DailyStateBuilder.build()` — sezione 3-pool event-driven (K, R, W)
**Stato**: comportamento attuale VERIFICATO E CORRETTO sui dati reali; identificato un caso limite NON gestito, da progettare
**Scopo del documento**: fornire a un altro agente/sviluppatore tutto il contesto matematico e i dati reali necessari per proporre una strategia di gestione automatica del caso limite descritto in fondo, senza dover ripercorrere l'indagine.

---

## 1. Executive Summary

Il modello a 3 pool (K = capitale, R = rendimento, W = rendimento prelevato) decompone la cassa
del portafoglio per distinguere capitale proprio da rendimento generato. `K` e `R` sono tracciate
**per broker** (`K_b(t)`, `R_b(t)`), mentre `W(t)` è **intenzionalmente globale**, condivisa tra
tutti i broker: rappresenta concettualmente un "terzo broker non tracciato" — il conto corrente
personale esterno dell'utente (es. banca tradizionale) dove transitano i prelievi prima di essere
eventualmente re-investiti su un broker qualsiasi.

Questa progettazione è stata verificata sui dati reali di produzione ed è **corretta**: su 6 cicli
storici completi di "prelievo da un broker → deposito successivo su un broker qualsiasi", il
sistema ha riconosciuto correttamente il capitale riciclato in **5 casi su 6**.

Il sesto caso ha rivelato un **limite strutturale attuale**: il meccanismo di "ripristino"
(`restore`) funziona **solo se il deposito è cronologicamente successivo al prelievo**. Quando
l'utente anticipa liquidità (deposita prima che il bonifico in arrivo si sia effettivamente
regolato, tipicamente per i classici 2 giorni lavorativi bancari), l'ordine cronologico delle
transazioni registrate può risultare invertito rispetto al reale flusso di cassa, e il sistema
smette di riconoscere il collegamento.

Sono state scartate due soluzioni ovvie (spostare manualmente la data; riusare `CASH_TRANSFER`)
per motivi spiegati alla fine — resta un problema di design aperto.

---

## 2. Il modello attuale — notazione matematica

Riferimento coerente con `portfolio_engine_architecture_v2.md` §11, con l'aggiunta esplicita
dell'indice di broker `b` per `K` e `R` (nel codice: `K: dict[int, Decimal]`,
`R: dict[int, Decimal]`, entrambe chiavate per `broker_id`; `W: Decimal` scalare unico).

### 2.1 Definizioni

```text
K_b(t) = capital_pool del broker b al tempo t       (per-broker)
R_b(t) = returns_pool del broker b al tempo t       (per-broker)
W(t)   = withdrawn_returns_pool, GLOBALE             (condiviso tra tutti i broker)
```

Interpretazione di `W`: rendimento che è uscito dal sistema tracciato (broker) verso un conto
esterno non tracciato, e che resta "ripristinabile" — cioè riconoscibile come capitale riciclato
se in futuro rientra nel sistema tracciato, **su qualsiasi broker**, non necessariamente quello
da cui è uscito.

### 2.2 Evento DEPOSIT sul broker `b`, importo `D > 0`, al tempo `t`

```text
restore   = min(D, W(t⁻))
R_b(t)    = R_b(t⁻) + restore
W(t)      = W(t⁻) − restore
K_b(t)    = K_b(t⁻) + (D − restore)
```

Interpretazione: se `W(t⁻) > 0` (c'è rendimento "in sospeso" nel conto esterno), il nuovo
deposito lo ripristina PRIMA di essere considerato capitale fresco. `W` è globale, quindi
`restore` avviene indipendentemente da quale broker abbia generato il prelievo originale che ha
alimentato `W`.

### 2.3 Evento WITHDRAWAL dal broker `b`, importo `X > 0`, al tempo `t`

```text
from_k    = min(X, max(K_b(t⁻), 0))
K_b(t)    = K_b(t⁻) − from_k
remaining = X − from_k
from_r    = min(remaining, max(R_b(t⁻), 0))
R_b(t)    = R_b(t⁻) − from_r
W(t)      = W(t⁻) + from_r
```

Interpretazione: il prelievo drena prima il capitale proprio del broker, poi il rendimento; la
quota drenata dal rendimento (`from_r`) esce dal sistema tracciato e si accumula in `W`,
**globale**, in attesa di un futuro `DEPOSIT` — su qualunque broker — che la ripristini.

### 2.4 Vincolo implicito nel codice attuale (IL PUNTO CENTRALE DI QUESTO REPORT)

Il codice processa le transazioni **in ordine cronologico stretto** (`current` avanza giorno per
giorno; ad ogni giorno le transazioni multiple sono ordinate per tipo — acquisti, poi vendite,
poi il resto — ma sempre all'interno della sequenza temporale globale). Questo significa che:

```text
restore(t) può utilizzare SOLO W accumulata da eventi con data < t
```

Non esiste alcun meccanismo di "look-ahead": un `DEPOSIT` a `t` non può mai ripristinare un `W`
generato da un `WITHDRAWAL` con data futura rispetto a `t` (`t_withdrawal > t_deposit`), anche se
nella realtà i due movimenti rappresentano lo stesso trasferimento di liquidità (l'utente ha
semplicemente anticipato l'uso dei fondi rispetto alla data di regolamento bancario registrata).

---

## 3. Riproduzione su dati reali (utente `alfy`, broker Directa=1, Recrowd=2, prod DB, oggi 2026-07-03)

Traccia cronologica completa di tutti gli eventi `DEPOSIT`/`WITHDRAWAL` (con contributo di
`INTEREST`/`TAX`/`BUY`/`SELL` a monte per determinare `R_b` disponibile), ottenuta instrumentando
temporaneamente il motore reale (non una riscrittura):

| Data | Broker | Evento | Dettaglio | W dopo |
|---|---|---|---|---|
| 2024-02-27 | Recrowd (2) | WITHDRAWAL 1262.36€ | `from_k`=1005.00 (drena K₂ interamente), `from_r`=257.36 | **257.36€** |
| 2024-07…2025-01 | Recrowd (2) | 7× WITHDRAWAL piccoli (62.36€ cad.) | `from_r`≈0.0005€ cad. (rumore di arrotondamento, ininfluente) | 257.363430€ |
| **2025-02-11** | **Directa (1)** | **DEPOSIT 600€** (primo deposito mai fatto su Directa) | `restore = min(600, 257.36) = 257.36` → riconosciuto correttamente come rendimento riciclato | **0€** ✅ |
| 2025-08-08 | Recrowd (2) | WITHDRAWAL 2322.66€ | `from_k`=2073.26, `from_r`=249.40 | 249.40€ |
| 2025-08-19 | Directa (1) | DEPOSIT 1005€ | `restore`=249.40 | 0€ ✅ |
| 2025-09-17 | Recrowd (2) | WITHDRAWAL 240.58€ | `from_r`=240.58 (K₂ già a 0) | 240.58€ |
| 2025-09-30 | Directa (1) | DEPOSIT 1035€ | `restore`=240.58 | 0€ ✅ |
| 2025-10-06 | Recrowd (2) | WITHDRAWAL 120.29€ | `from_r`=120.29 | 120.29€ |
| 2025-10-28 | Directa (1) | DEPOSIT 1000€ | `restore`=120.29 | 0€ ✅ |
| … (altri cicli analoghi, ~120.29€/mese ricorrenti) | | | | |
| **2026-06-08** | **Recrowd (2)** | **WITHDRAWAL 360.87€** | `from_r`=360.87 (K₂ a 0) | **360.87€ — MAI RIPRISTINATO FINO A OGGI** |

**5 cicli su 6 correttamente riconosciuti.** L'unico caso rimasto "aperto" (`W(oggi) = 360.87€`)
è quello approfondito nella sezione 4.

### 3.1 Verifica indipendente (SQL puro, nessun codice motore coinvolto)

```text
SUM(transactions.amount) WHERE broker_id = 1 (Directa) = 237.61€  (oggi)
SUM(transactions.amount) WHERE broker_id = 2 (Recrowd)  =  0.00€  (oggi)
```

Il motore, filtrando "solo Directa", riporta correttamente `K₁=237.61€, R₁=0€` (100% capitale) —
coerente con l'assenza di prelievi mai avvenuti su Directa. Filtrando "tutti i broker", il motore
riporta `K₁+R₁+K₂+R₂` con una quota di R attribuita a causa del `W` globale non ancora
ripristinato: la "rendita" visibile in dashboard (2.41–2.54€, dopo la formula di riconciliazione
proporzionale che distribuisce la cassa reale secondo il rapporto K:R) discende in parte da questo
meccanismo E in parte da un secondo problema separato (vedi nota a fondo pagina).

> **Nota**: esiste anche un piccolo residuo (~4.78€) nella riconciliazione K+R vs cassa reale del
> solo broker Recrowd, probabilmente legato ad arrotondamenti sui rimborsi parziali di un asset
> obbligazionario (7 vendite frazionarie da 0.031102 unità). È un problema DISTINTO da quello
> descritto in questo report, di importo trascurabile, non ancora isolato nella riga di codice
> esatta — menzionato qui solo per completezza, non è oggetto di questo documento.

---

## 4. Il caso limite: "prelievo anticipato" (bridge financing tramite conto esterno non tracciato)

### 4.1 Cosa è successo realmente (dichiarazione diretta dell'utente)

> "avevo 'anticipato' la cifra perché me la ero bonificata ma ci volevano i canonici 2 gg per
> farla arrivare sul conto, quindi ho fatto il deposito tenendone conto"

Traduzione in termini di flusso di cassa reale:

```text
t0: l'utente AVVIA il bonifico in uscita da Recrowd (360.87€) verso il proprio conto esterno
t0+1gg: l'utente, sapendo che i fondi arriveranno, deposita liquidità su Directa "anticipando"
        l'uso di quei 360.87€ (usando temporaneamente altra liquidità propria come ponte)
t0+2gg: il bonifico da Recrowd si REGOLA effettivamente sul conto esterno
```

Nel sistema, però, sono state registrate solo 2 transazioni con le rispettive **date di
regolamento**:

```text
WITHDRAWAL Recrowd  360.87€  data = 2026-06-08  (data di arrivo fondi sul conto esterno)
DEPOSIT   Directa  1445.00€  data = 2026-06-07  (data in cui l'utente ha versato su Directa,
                                                  UN GIORNO PRIMA della withdrawal)
```

Nota importante sui numeri: il deposito Directa (1445€) è più GRANDE del prelievo Recrowd
(360.87€) — perché quell'unico bonifico/deposito rappresenta **due eventi economici aggregati in
un'unica transazione**: una parte di capitale fresco dell'utente + il "ponte" sui 360.87€ non
ancora arrivati. Non è quindi un semplice trasferimento 1:1 di pari importo tra i due broker.

### 4.2 Perché il motore non lo riconosce

Per la regola in §2.4, `restore(t)` può usare solo `W` accumulata da eventi con data STRETTAMENTE
precedente a `t`. Qui:

```text
t_deposit  = 2026-06-07
t_withdraw = 2026-06-08
t_deposit < t_withdraw   →  W(t_deposit⁻) non include ancora il contributo del withdrawal futuro
                          →  restore = 0
                          →  l'intero deposito (1445€) viene attribuito interamente a K₁
                          →  il prelievo successivo (2026-06-08) genera comunque
                             from_r = 360.87 → W(oggi) = 360.87€, MAI ripristinato
```

Il risultato netto: i 360.87€ restano "intrappolati" in `W` per sempre (finché non arriva un
FUTURO deposito, che però sarebbe un evento economico scorrelato, non la vera "restituzione" di
questi fondi).

### 4.3 Perché le soluzioni ovvie NON vanno bene (secondo l'utente)

**Soluzione "sposta la data" (rendere `t_withdraw ≤ t_deposit`)**: NON generalizzabile. L'utente
ha confermato che l'ordine cronologico reale può variare caso per caso — a volte anticipa
un'uscita e poi bonifica il delta in ritardo, quindi non esiste una convenzione univoca di "quale
data spostare". Richiederebbe correzione manuale continua, error-prone.

**Soluzione "riusa CASH_TRANSFER"** (meccanismo già esistente in
`ScopeAwareTransactionClassifier`/`DailyStateBuilder`, righe ~565 e ~825 di
`portfolio_engine.py`, con gestione nativa di date disallineate tramite `in_transit_intervals`):
NON adatta a questo caso, perché la logica attuale di `CASH_TRANSFER` (gamba di
arrivo: `K[bid] += amt`, commento nel codice: "Approximate: proportional to departure (use K as
default)") assume implicitamente un trasferimento **1:1 di pari importo** tra le due gambe
collegate (`related_transaction_id`). Nel caso reale dell'utente, un singolo bonifico/deposito
aggrega **due voci economiche di importo diverso** (capitale fresco + ponte su rendimento
prelevato) — introdurre uno split esplicito tra le due voci per adattarsi a `CASH_TRANSFER`
significherebbe imporre all'utente una modellazione manuale onerosa ("devastante", nelle sue
parole) ogni volta che effettua un deposito composito.

### 4.4 Vincoli per una soluzione accettabile (raccolti dal confronto con l'utente)

Qualunque strategia proposta deve:

1. **Non richiedere una convenzione fissa sull'ordine cronologico** tra prelievo e deposito
   collegati (a volte precede l'uno, a volte l'altro) — quindi non basarsi solo su "restore da
   eventi passati".
2. **Non richiedere che gli importi coincidano 1:1** tra il prelievo e il deposito che lo
   "copre" — un deposito può aggregare più voci economiche di importo diverso.
3. **Non introdurre ambiguità silenziosa** quando ci sono più prelievi/depositi ravvicinati nello
   stesso periodo (l'utente ha esplicitamente scartato una tolleranza temporale generica di N
   giorni per questo motivo: "in realtà non è male come filosofia, ma è effettivamente
   ambigua...").
4. **Non richiedere collegamento manuale onnipresente** per ogni transazione di questo tipo
   (l'utente ha scartato l'idea di dover collegare esplicitamente ogni coppia prelievo/deposito
   come si fa oggi con `CASH_TRANSFER`, se comporta split manuale degli importi).
5. Il caso è probabilmente **raro ma ricorrente nel tempo** (bridge financing su bonifici bancari
   con 1-2 giorni di regolamento) — una soluzione robusta dovrebbe gestirlo automaticamente senza
   intervento manuale ricorrente, idealmente sfruttando pattern già presenti nei dati (es.
   importo/tempistica) o un meccanismo di riconciliazione differita.

### 4.5 Stato della richiesta

L'utente ha esplicitamente richiesto di **non implementare ancora una soluzione**, ma di produrre
questo report per confrontarsi con un altro agente su una strategia di design. Nessuna modifica al
codice è stata applicata; il file `portfolio_engine.py` risulta al momento invariato rispetto al
repository (verificato con `git status`).

---

## 5. Riferimenti

- Modello matematico completo (§11): `portfolio_engine_architecture_v2.md`
- Implementazione: `backend/app/services/portfolio_engine.py`, classe `DailyStateBuilder`,
  metodo `build()` — blocchi DEPOSIT/WITHDRAWAL (pre-frame righe ~539-550, frame righe ~787-799)
- Wiki: `LibreFolio_devWiki/wiki/concepts/3-pool-cash-model.md`,
  `LibreFolio_devWiki/wiki/entities/portfolio-engine.md`
- Meccanismo di collegamento transazioni esistente (per riferimento, non direttamente
  riutilizzabile per questo caso): `TransactionType.CASH_TRANSFER`,
  `ScopeAwareTransactionClassifier._build_in_transit_interval()`,
  `backend/app/db/models.py` (enum `TransactionType`, campo `related_transaction_id`)
