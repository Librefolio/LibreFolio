# Mandato G — Gerarchia cromatica nei grafici di allocazione

| | |
|---|---|
| **Flusso** | W7 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | frontend dashboard |
| **Taglia** | M |
| **Lane** | porta `6246` · data dir `backend/data/test-risk-g` |
| **Dipende da** | **B** (bloccante) |
| **Riceve** | contratto **K2** da B |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste — e la dichiarazione onesta

⚠️ **Questo flusso non è rischio. È dashboard.**

Entra nel piano per due ragioni, e vanno dette entrambe:

1. la tassonomia del mandato **B** lo rende *possibile* — oggi un portafoglio tutto in
   ETF mostra **una fetta al 100%** che non informa di nulla, mentre «azionario 60% /
   obbligazionario 30% / materie prime 10%» è la risposta alla domanda L2, *«sono
   diversificato come credo?»*;
2. se ignorato, la tassonomia lo rende *sbagliato*: fette nuove con **etichetta cruda e
   icona grigia**.

> È espansione di ambito **consapevole e dichiarata**, non scoperta a metà strada.

---

## 2. La decisione, e il compromesso che elimina

Tre strade erano sul tavolo: fette separate per sottotipo (informa ma frammenta),
tutto raggruppato sul contenitore (non frammenta ma non informa), oppure dipende dal
punto.

Il developer non ne ha scelta nessuna: **ha eliminato il compromesso** (**D71**).

> ## 🔑 I sottotipi restano dentro la massa del primario
>
> Con un **colore lievemente diverso**, e i numeri distinti **nel tooltip**.
> Stessa regola nello storico: le sotto-serie impilate prendono tonalità **vicine** a
> quella del genitore.
>
> **Un asset non specializzato usa il colore primario puro** — non è un caso da
> gestire, è il grado zero della scala.

La lettura d'insieme resta sulla massa cromatica; il dettaglio sta nel tooltip per chi
lo cerca.

---

## 3. Cosa leggere prima

1. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **Q12**, sezione *«Il residuo
   sulla torta, chiuso da D71»* — contiene la tabella dei costi verificati e le due
   trappole.
2. **D71** e **D72** nel registro.

---

## 4. Il costo verificato — cinque punti, nessuno gratis

| Cosa | Dove | Nota |
|---|---|---|
| Il colore è assegnato **per indice** | `AllocationPieChart:338` (`color: palette`) · `AllocationHistoryChart:531-533` e `:585` | Va sostituito con colore **per dato**: nella torta `itemStyle.color` sul singolo item; nello storico `lineStyle`, `areaStyle`, `itemStyle` **e il tooltip** — quattro punti, non uno |
| Manca `hexToHsl` | `utils/colors.ts` ha **solo** `hslToHex` (`:123`) | Le due tavolozze sono esadecimali scritti a mano «a massima distanza cromatica»: per ricavarne sfumature serve la conversione inversa, che oggi non esiste |
| L'alfa è concatenazione di stringa | `AllocationHistoryChart:532` — `palette[i] + '88'` | Funziona finché il colore è esadecimale a 6 cifre. Una sfumatura calcolata deve mantenere quel formato o passare a `rgba()` |
| **Due temi** | `PALETTE_LIGHT` è **scura** (`#1a4031`), `PALETTE_DARK` è **chiara** (`#4ade80`) | La sfumatura **non può andare sempre verso il chiaro**: va calcolata rispetto al tema, o due sottotipi diventano indistinguibili in uno dei due |
| La legenda si affolla | commento «up to 12» in `AllocationHistoryChart:107`; la torta ha già la paginazione | Con i sottotipi le voci possono superare la dozzina. Valutare se la legenda elenca i **primari** e il dettaglio resta al tooltip |

---

## 5. Le due condizioni senza cui D71 non funziona

### 5.1 L'ordinamento deve diventare gerarchico

Oggi le fette sono ordinate per **valore decrescente**
(`AllocationPieChart:179`). Con quell'ordinamento due sottotipi dello stesso genitore
finiscono **in punti opposti del cerchio**, e la parentela cromatica diventa
invisibile: si vedono due colori simili scollegati, che è **peggio** che non averli
sfumati affatto.

> Genitori ordinati per totale, figli per valore **dentro** il genitore.
> Senza questo, il mandato produce un peggioramento.

### 5.2 Il primario si deriva da una mappa, mai da una stringa

⚠️ `rawKey` conserva gli underscore (`AllocationPieChart:210`, regex `/[^A-Z_]/g`),
quindi spezzare `ETF_STOCK` su `_` **funzionerebbe** — ed è proprio questo che rende la
trappola pericolosa.

**Ma `REAL_ESTATE` è un tipo primario**, e si spezzerebbe in `REAL` + `ESTATE`,
producendo un genitore inesistente.

La derivazione arriva dal contratto **K2**:

```typescript
primaryAssetType(type: string): string   // mappa esplicita, da assetTypes.ts
```

`assetTypes.ts` è del mandato **B** ([`README.md`](./README.md) §2.3): questo mandato
**consuma, non scrive**.

---

## 6. Il ripiego, se un anello solo non basta

**D72**: **ciambella a due anelli**, primari all'interno e sottotipi all'esterno.

Costa meno di quanto sembri: **il grafico è già una ciambella** —
`radius: ['35%', '70%']` alla riga 274 — quindi il secondo anello è una banda dentro un
buco che esiste già, non una riscrittura. Gli angoli combaciano per costruzione, perché
l'arco di un genitore è la somma dei figli. I sottotipi vanno **all'esterno**, dove c'è
più lunghezza d'arco per grado.

> ⚠️ **Una trappola da conoscere prima**, perché questo file ne ha già collezionate tre.
> Il percorso di aggiornamento veloce alla riga 193 scrive `series: [{data: chartData}]`
> — **una sola serie**. Con due anelli, quel ramo aggiornerebbe l'interno e lascerebbe
> l'esterno fermo all'ultimo disegno completo: **dati vecchi, nessun errore, nessun
> sintomo**.
>
> È esattamente la famiglia dei tre «Bugfix» già annotati nel file: `lastRawTypeKeys`,
> il `$effect` che leggeva la verità dell'array invece del contenuto, e la chiave
> rich-text che sbagliava nelle lingue diverse dall'inglese.

**Scartata la barra impilata polare**: mappa il valore sul **raggio**, e l'area cresce
col quadrato. Due quote uguali a distanze diverse dal centro occupano aree diverse — e
in un grafico che serve a dire «quanta parte del totale» l'occhio legge proprio l'area.
È l'attrezzo giusto per dimensioni cicliche (mesi, ore), non per parti di un tutto.

---

## 7. Confini

**Di questo mandato**:

- `frontend/src/lib/components/charts/AllocationPieChart.svelte` (383 righe)
- `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte` (740 righe)
- `frontend/src/lib/utils/colors.ts` — aggiunge `hexToHsl`

**Fuori**, tassativamente:

- `assetTypes.ts` → **del mandato B**, si consuma soltanto;
- `ExposureTreemap.svelte` → raggruppa per tipo (`:84`) ma **non** fa parte di questo
  mandato: se serve, si chiede al coordinatore;
- **il backend**: nessuna modifica. Il motore continua a produrre `by_type` piatto
  (`portfolio_engine.py:1448`), la gerarchia si costruisce **nel frontend**.

---

## 8. Test

| Cosa | Come |
|---|---|
| Unitari | Vitest su `hexToHsl` e sull'ordinamento gerarchico |
| **I due temi** | verifica che le sfumature restino distinguibili in chiaro **e** in scuro |
| E2E | `portfolio/dashboard.spec.ts` (210 righe, **condiviso con E**, che vi monta i livelli) |
| Statici | lint + `svelte-check` |

> ## ⚠️ Questo mandato invalida qualcosa che non possiede: la galleria
>
> `e2e/gallery.spec.ts:605` genera *«dashboard allocation charts — all languages and
> themes»*, cioè gli **screenshot della documentazione**. Cambiando i colori dei due
> grafici, quelle immagini diventano **stantie**: mostrano una tavolozza che il prodotto
> non usa più.
>
> Non è un conflitto — nessuno scrive lo stesso file — è una **dipendenza invisibile**.
> **Non rigenerarla qui**: produrrebbe immagini di uno stato intermedio. La
> rigenerazione è di **J**, dopo l'integrazione. Va solo **dichiarata** nel checkpoint.

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6246 --data-dir backend/data/test-risk-g \
  <categoria> <azione>
```

---

## 9. Definizione di finito

- [ ] Colore **per dato** in entrambi i grafici — quattro punti nello storico, non uno;
- [ ] `hexToHsl` in `utils/colors.ts`, con test;
- [ ] **ordinamento gerarchico**: figli adiacenti al genitore;
- [ ] primario derivato da `primaryAssetType` (K2), **mai** da `split('_')`;
- [ ] asset non specializzato = colore primario puro;
- [ ] tooltip con i numeri dei sottotipi distinti;
- [ ] **sfumature distinguibili in entrambi i temi**, verificato;
- [ ] legenda non affollata, o primari in legenda e dettaglio nel tooltip;
- [ ] **`git diff` sul backend vuoto**;
- [ ] lint, `svelte-check`, Vitest ed E2E verdi;
- [ ] nessun processo in ascolto su `6246`.
