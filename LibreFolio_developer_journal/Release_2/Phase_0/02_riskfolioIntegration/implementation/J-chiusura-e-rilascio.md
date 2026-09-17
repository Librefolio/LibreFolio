# Mandato J — Chiusura e rilascio

| | |
|---|---|
| **Flusso** | W10 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | trasversale |
| **Taglia** | S |
| **Lane** | porta `6249` · data dir `backend/data/test-risk-j` |
| **Dipende da** | **tutti** |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste come mandato separato

Perché **D46** lo richiede: si rilascia **solo a catena completa**, dal worktree
separato. Niente stati intermedi su `dev_release2`.

E perché la chiusura ha un contenuto proprio che nessun altro mandato può fare: il
banner si toglie **una volta sola**, il CHANGELOG si scrive **una volta sola**, e
qualcuno deve verificare che gli undici mandati abbiano davvero consegnato ciò che hanno
dichiarato.

> ⚠️ È anche il mandato in cui è più facile barare, perché arriva quando tutti sono
> stanchi e tutto sembra fatto. **Un cancello che si apre per stanchezza non è un
> cancello.**

---

## 2. Il banner beta — dove va e dove resta

Il banner (`RiskBetaBanner.svelte`, 11 righe) è montato oggi in **3 dei 4** punti
d'ingresso.

> Non è mai stato un giudizio sulla qualità dei calcoli: è **il segnaposto di una
> catena di piano interrotta** ([`../00-…`](../00-analisi-stato-attuale.md) §3).

**La regola** (**D46**, che raffina Q4):

| Livello | Banner | Perché |
|---|:---:|---|
| **L1** Quanto può fare male | ❌ via | Fatti osservati sul campione. Nulla è stimato |
| **L2** Sono diversificato | ❌ via | Struttura calcolata sui dati reali |
| **L3** Sono pagato per il rischio | ❌ via | Confronto con un benchmark reale |
| **L4** — replay storico | ❌ via | Rendimenti reali di un periodo reale |
| **L4** — shock ipotetico | ❌ via | Deterministico, ipotesi dichiarata dall'utente |
| **L4** — **simulazione** | ✅ **resta** | **È un modello.** È lì, e solo lì, che un avvertimento è onesto |

⚠️ **Asset Detail** resta com'è e **conserva il suo banner**: è parcheggiato (**D8**,
**D47**) e si riapre **dopo** questo rilascio, così eredita una grammatica già decisa.

---

## 3. Il CHANGELOG — scrittore unico

`CHANGELOG.md` è **di questo mandato e di nessun altro**, mai.

**Dove**: capitolo `## [Unreleased]`, che oggi esiste e dichiara *«Preparing v1.1.1»*.

⚠️ La sezione `### 🔄 Changed` in quel capitolo **non esiste ancora** — ci sono solo
`### ✨ Added` e `### 🐛 Fixed`. Va creata, con l'emoji, nell'ordine canonico del
formato.

### 3.1 La voce su M2 — quella che non si può omettere

M2 cambia **un numero già mostrato agli utenti**. Tre fatti, e nessuna scusa:

1. il CVaR mostrato **cambia leggermente**;
2. cambia perché la stima precedente era **sistematicamente più bassa** del valore
   corretto — **non** perché si sia cambiata convenzione;
3. l'entità: circa lo **0,27%** in valore relativo della misura.

> La frase che rende la voce onesta senza spaventare: lo stimatore coerente
> (Acerbi-Tasche) **è** «la media delle giornate peggiori», con l'ultima contata in
> proporzione a quanto rientra nel 5%. La definizione non cambia. Cambia che ora la
> calcoliamo bene.

Si coordina con la pagina CVaR del mandato **I**.

### 3.2 Il resto del capitolo

Le altre voci arrivano dai mandati, **user-facing soltanto**: i quattro livelli, il
laboratorio, il catalogo dei benchmark, i sottotipi di asset, il Monte Carlo rifondato,
l'affettamento del portafoglio.

**Non** entrano: M1, M3, M5, M6 (velocità e possesso, nessun effetto osservabile), la
promozione delle primitive, l'oracolo di test.

---

## 4. La verifica finale — cancello G-C

L'unico cancello del piano che blocca **tutti**.

### 4.1 Verifica per mandato

Per ciascuno degli **undici**: la definizione di finito è soddisfatta, l'evidenza è nel
suo piano vivo (`implementation/progress/<LETTERA>-esecuzione.md`), e il piano è
aggiornato fino all'ultimo passo.

⚠️ Non si accetta «verde» come risposta. Si accetta **il comando eseguito e il suo
esito**.

### 4.2 Verifica trasversale — le cose che nessun singolo mandato poteva vedere

| # | Verifica | Come |
|---|---|---|
| 1 | **La regola dei pesi** regge | Nessun simbolo di valuta in Asset Global, in nessun pannello |
| 2 | **Dashboard e Broker Detail sono lo stesso componente** | Ispezione: se sono diventati due, E ha fallito anche con i test verdi |
| 3 | **Un pannello, un livello** | Nessun file del rischio oltre le 600 righe |
| 4 | **Enum ↔ tabelle** | Il test di B passa: ogni `AssetType` ha icona, etichetta ×4 e secchio di scenario |
| 5 | **`undefined_windows` intatto** | L'avviso utente sui segnali rolling esiste ancora |
| 6 | **TE, IR e `sobol_start_index` spariti dalla UI** | Ricerca nel frontend |
| 7 | **`check-links` verde** | Nessun `DocsLink` appeso |
| 8 | **Nessuna porta della banda 6240 in ascolto** | `lsof` su ciascuna, `6240`-`6250` |
| 9 | **La convenzione di segno regge** | I campi acquisiti da N (`WR`, `DaR`, `CDaR`, `UCI`) hanno **la stessa convenzione** di `max_drawdown` dentro lo stesso oggetto. Riskfolio restituisce magnitudini positive: due convenzioni nello stesso output passerebbero ogni test |
| 10 | **NEA coincide con AI Export** | `NEA == 10000 / herfindahl_index_points` sullo stesso portafoglio. Se divergono, l'applicazione dice due numeri sulla concentrazione |
| 11 | **NEA non è mai mostrato da solo** | Ispezione della UI di L2: NEA senza diversification ratio dice «diversificato» a un portafoglio correlato 0,95 |
| 12 | **I due test di Asset Detail sono verdi e non riscritti** | `portfolio/risk-asset-detail.spec.ts` — sono la **rete** che prova che E ed F non hanno toccato la pagina parcheggiata (**D8**, **D47**). Verdi perché intatti, non perché adattati: `git log` su quel file deve mostrare **solo** lo spostamento di D |
| 13 | **La galleria è rigenerata** | **G** ha cambiato i colori dei grafici di allocazione, quindi `gallery.spec.ts:605` produce immagini diverse. La rigenerazione è **di questo mandato**, dopo l'integrazione: farla prima avrebbe fotografato uno stato intermedio |

> ### ⚠️ Una nota che evita un falso allarme in §4.1
>
> Le definizioni di finito di **C** e **G** dichiarano `git diff` vuoto su
> `risk_plugins/` e sul backend. Sono corrette **nel loro worktree**.
>
> Sulla revisione combinata, però, `risk_plugins/` **avrà** modifiche: sono di **N**,
> che aggiunge campi additivi a `historical_kpi.py` e `risk_contribution.py`. È lavoro
> previsto, non una violazione.

### 4.3 Gate di integrazione

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6249 --data-dir backend/data/test-risk-j \
  services risk-all
```

Più: `api risk`, `schemas risk`, lint e `svelte-check` sul frontend, gli spec E2E dei
mandati E, F, G, e `mkdocs build` in modalità stretta.

⚠️ **Sulla revisione combinata**: gli undici mandati hanno lavorato in worktree separati.
Due file possono fondersi senza conflitto testuale e **contraddirsi semanticamente** —
è esattamente ciò che [`README.md`](./README.md) §2.2 e §2.4 esistono per prevenire, ma
prevenire non è verificare. Le superfici condivise (`schemas/risk.py`, le quattro
lingue, il catalogo dei test) vanno **rilette a mano** sulla revisione combinata, non
solo testate.

---

## 5. Cosa si riapre dopo, e va lasciato scritto

Chiudere bene significa anche **non far sparire** ciò che è stato rimandato.

| Cosa | Dove | Stato atteso |
|---|---|---|
| **Asset Detail** | **D47** | Riaperto subito dopo, con le sue due lacune note: `risk_contribution` è `PORTFOLIO`-only, e la card rolling mostra un valore puntuale invece della forma nel tempo |
| Tracking error / information ratio | `TODO_FUTURI.md` | Ancora registrato, priorità bassa |
| Portfolio optimization | `TODO_FUTURI.md` | Ancora registrato, priorità molto bassa |
| Monte Carlo livelli 4-5 | `TODO_FUTURI.md` | Ancora registrato |
| Stimatori robusti di covarianza | `TODO_FUTURI.md` | Ancora registrato |
| Contributi al rischio su misure non-MV | [`../04-…`](../04-decisioni-e-questioni-aperte.md) Q7 | Deciso quando si ridisegna la card, col blocco dei contributi negativi |
| `SignalDomain.PORTFOLIO` | **D18** | Non serviva per la v1; se la sparkline di portafoglio diventasse desiderabile, il costo è la piattaforma segnali intera |

---

## 6. Archiviazione

A rilascio avvenuto, la catena di piani va archiviata secondo la skill `plan-archive`:
`LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/` diventa una
fase archiviata, con il suo `README.md` indice e lo stato di ciascun mandato.

⚠️ **Non si archivia prima del rilascio**, e **non si cancella nulla**: l'archivio della
prima campagna (`_archive-backendFirst-G0G6/`) è servito a ricostruire cosa fosse stato
deciso davvero — e a scoprire che **una cosa data per decisa non lo era mai stata**
([`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §2.4).

---

## 7. Definizione di finito

- [ ] Gli **undici** mandati verificati uno per uno, con evidenza;
- [ ] le otto verifiche trasversali di §4.2 passate;
- [ ] banner rimosso da L1, L2, L3, replay e shock; **mantenuto sulla sola simulazione**;
- [ ] Asset Detail invariato e ancora col suo banner;
- [ ] `### 🔄 Changed` creata in `[Unreleased]`, con la voce M2 nei suoi tre fatti;
- [ ] gate di integrazione verdi sulla **revisione combinata**;
- [ ] superfici condivise **rilette a mano**, non solo testate;
- [ ] nessuna porta della banda `6240` in ascolto;
- [ ] i rinvii di §5 ancora registrati e visibili;
- [ ] messaggio di commit proposto — ⚠️ **il commit lo esegue il developer**.
