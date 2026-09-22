# Mandato I — Documentazione

| | |
|---|---|
| **Flusso** | W9 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | `mkdocs_src/` |
| **Taglia** | M |
| **Lane** | nessuna — questo mandato **non avvia server** |
| **Dipende da** | nulla — **il primo tempo va eseguito subito** |
| **Consegna** | contratto **K7** a **E**, **F**, **H** |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.
> **Agente**: si lavora tramite **`docs-writer`**, che conosce le convenzioni MkDocs
> del progetto.

---

## 1. Perché il primo tempo va eseguito subito

**D4** prevede un link alla documentazione **per riga** della scala L1. Se le pagine
non esistono quando il mandato **E** scrive i `DocsLink`, succedono due cose, entrambe
brutte: i link restano appesi, e il gate `check-links` diventa rosso per settimane —
così smette di segnalare qualcosa e comincia a essere ignorato.

> **D55, tre tempi, e il primo è adesso:**
>
> 1. **All'avvio**: per ogni pagina che servirà, un **mock di due righe, solo in
>    inglese**, registrato **subito** nell'indice di `mkdocs_src/mkdocs.yml`.
> 2. **Durante**: le pagine si riempiono **in inglese**, in parallelo al codice.
> 3. **Alla fine di tutta la documentazione**: le traduzioni in un **blocco unico**,
>    mai pagina per pagina.

Il vantaggio non è solo organizzativo: un mock in indice rende `check-links` **verde
dal primo giorno**, quindi la documentazione mancante si presenta come **pagina vuota**
invece che come collegamento rotto. La differenza fra un gate che informa e un gate che
si impara a ignorare.

---

## 2. Cosa esiste già, e cosa manca

`mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/` contiene già, in
quattro lingue:

```text
index · max-drawdown · sharpe-ratio · sortino-ratio · volatility
```

**Manca tutto il resto.** Le pagine da creare, raggruppate per livello — l'elenco esatto
va concordato con **E**, **F** e **H**, che sanno quali `DocsLink` scriveranno:

| Livello | Pagine mancanti |
|---|---|
| **L1** | VaR · **CVaR** · drawdown corrente e underwater · durata del drawdown e recupero richiesto · worst realization |
| **L2** | correlazione · contributo al rischio (MCTR/CCTR/PCTR) · indice di concentrazione (NEA) e diversification ratio |
| **L3** | beta e active return · il benchmark e come sceglierlo |
| **L4** | replay storico e proxy · shock ipotetico · simulazione: cosa assume ogni modalità |
| trasversale | qualità del dato · annualizzazione osservata |

---

## 3. Le lezioni sono già scritte: non si reinventano

⚠️ **Il punto che fa risparmiare più tempo in tutto questo mandato.**

[`../02-verdetti-per-strumento.md`](../02-verdetti-per-strumento.md) contiene, per ogni
strumento, una **mini-lezione già scritta e già verificata**: cosa fa, perché serve,
qual è il suo difetto. Quel documento è la fonte da cui le pagine si derivano — non un
riferimento da consultare, **la sorgente**.

Alcune cose che vivono lì e che devono finire in pagina, perché altrove non esistono:

- **perché il CVaR batte il VaR**: il VaR dichiara una soglia e **tace su cosa c'è
  oltre**, e non è subadditivo — in casi patologici può segnalare che diversificare
  *aumenta* il rischio;
- **l'asimmetria del recupero**: −38% richiede +62% per tornare in pari. Perdere il 10%
  non richiede +10% ma +11,1%; a −50% servono +100%. È il motivo per cui il drawdown
  conta più della volatilità;
- **perché «ho 12 ETF» non significa «sono diversificato»**: se sono correlati 0,92 si
  è comprata dodici volte la stessa cosa;
- **il contributo non è il peso**: un asset al 5% del capitale può portare il 20% del
  rischio, e **può essere negativo**;
- **perché lo Sharpe penalizza le salite violente**: usa la volatilità totale, quindi
  tratta un +8% come un −8%.

E due che vengono dal registro delle decisioni:

- **la lezione sulla gaussiana** (**D22**): esclusa dal grafico di L1, ma **valida** —
  la sua casa è la pagina wiki sul VaR. Le code grasse *sono* la norma per i rendimenti
  finanziari, e la campana descrive un mondo che non esiste;
- **l'annualizzazione osservata** (`A = osservazioni × 365 / giorni di calendario`) è
  una scelta sopra la media del settore: per l'equity tende naturalmente a ~252, per le
  crypto 24/7 a ~365, **senza costanti hardcoded**. Va conservata **e spiegata**.

---

## 4. Il CVaR ha una pagina con un compito in più

M2 del mandato **A** corregge lo stimatore, e il numero mostrato **cambia** per gli
utenti esistenti.

La pagina sul CVaR deve poter essere il posto dove chi si accorge del cambiamento trova
la spiegazione. Va scritta con questo in mente, e va coordinata con la voce di
CHANGELOG del mandato **J**
([`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §6).

> La frase chiave, che vale sia in pagina sia nel changelog: Acerbi-Tasche **è** «la
> media delle giornate peggiori», con l'ultima contata in proporzione a quanto rientra
> nel 5%. Non è una convenzione diversa: la stima precedente era **sistematicamente più
> bassa**.

---

## 5. Confini

**Di questo mandato**: `mkdocs_src/**` e `mkdocs_src/mkdocs.yml`. **Scrittore unico**:
nessun altro mandato tocca la documentazione.

**Fuori**: qualunque file di codice. Se una pagina rivela che il codice fa una cosa
diversa da quella documentata, **si riporta al coordinatore** — non si corregge il
codice da qui, e non si documenta il comportamento sbagliato come se fosse voluto.

---

## 6. Le due regole che non si negoziano

### 6.1 Solo inglese, fino alla fine

Si scrivono **solo** file `.en.md`. Mai `.it`, `.fr`, `.es` a mano.

Le traduzioni avvengono **in un blocco unico alla fine di tutta la documentazione**
(**D55**), tramite la pipeline del progetto, e **solo su richiesta esplicita del
developer**.

### 6.2 Niente `mkdocs serve`

⚠️ `dev.py mkdocs serve` usa la porta fissa **`6042`**, fuori dal modello di lane: in un
worktree coordinato collide con chiunque altro.

La validazione si fa con:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs check-links
```

Per le pagine che hanno già traduzioni e ricevono una modifica **puntuale**, vale la
regola dello stamp della cache Aphra — la conosce l'agente `docs-writer`.

---

## 7. Contratto K7 → mandati E, F, H

**Gli slug delle pagine, consegnati prima che i `DocsLink` vengano scritti.**

Un `DocsLink` con uno slug sbagliato non fallisce a compilazione: fallisce in faccia
all'utente. La lista va concordata **all'inizio**, insieme ai tre mandati, e congelata:
se uno slug deve cambiare, lo si comunica, non lo si cambia e basta.

---

## 8. Definizione di finito

**Primo tempo** (subito, prima che E scriva un solo `DocsLink`):

- [ ] mock di due righe **in inglese** per ogni pagina prevista;
- [ ] tutte registrate in `mkdocs_src/mkdocs.yml`;
- [ ] `mkdocs build` (strict) e `check-links` **verdi**;
- [ ] **K7 consegnato** a E, F, H.

**Secondo tempo** (durante):

- [ ] ogni pagina riempita in inglese, derivata da
      [`../02-verdetti-per-strumento.md`](../02-verdetti-per-strumento.md);
- [ ] la pagina CVaR spiega il cambiamento di stimatore, coordinata con J;
- [ ] la lezione sulla gaussiana nella pagina VaR;
- [ ] `build` e `check-links` ancora verdi.

**Terzo tempo** (solo su richiesta esplicita del developer, a documentazione finita):

- [ ] traduzioni in blocco unico tramite la pipeline;
- [ ] `translate-validate` verde.
