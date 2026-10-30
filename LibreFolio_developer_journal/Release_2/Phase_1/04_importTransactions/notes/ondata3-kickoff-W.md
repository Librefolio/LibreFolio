# Brief — workstream W · N78-1: a che valore esce un'unità in una rettifica in uscita (solo analisi, niente codice)

> **A cosa serve (per il developer).** È una decisione tua rimasta in sospeso da giorni perché mancava l'analisi di W insieme a MF. La domanda era tua: «in una rettifica in uscita, che PMC dovremmo segnare? Se esce, è come fosse una vendita: modifica le quantità, non il PMC». Il PMC non cambia già oggi; la scelta vera è **a che valore escono le unità** (e quindi cosa succede a realizzato, capitale e rendimento del giorno). Esempio da completare con numeri: 10 azioni comprate a 50 (PMC 50), oggi valgono 80, ne regali 2 a tuo fratello: escono a 50 (costo), a 80 (mercato) o «spariscono» (correzione di quantità)? Il documento che scrivi te lo porto domattina, con una raccomandazione.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-fluffy-meme` · **Branch**: `e-alfy-w-import-e-transazioni` (HEAD `fcf39fab0`, già tutto in `dev_release2`; il coordinatore lo porta in fast-forward a `2879ae3e4`).
**Nessuna corsia necessaria** (solo lettura). Se vuoi verificare un numero con il codice, usa un pytest o uno script **su dati di test**, mai sui dati reali.

## Fonti
- La preparazione di MF: `LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md`, sezione «N78-1 con W — preparazione» (riga ~4147) e il contesto ~4036-4049: cosa fa oggi il costo di un ADJUSTMENT in uscita nel PMC, nei prezzi, nella Dashboard (`daily_state.py` ~:418), nei lotti FIFO (`fifo/engine.py:245`), nella performance dei lotti (`lots/histories.py` ~:124), e la decisione 47 (gamba cedente d'un TRANSFER orfano). I tre modi: **(a) al costo**, **(b) al valore di mercato del giorno**, **(c) correzione di quantità**.
- Il tuo piano: `04_importTransactions/plan-phase01ImportTransactions.prompt.md`, W-B72 / N78 (righe ~5494-5510, ~5626-5640) e la «decisione notturna N78» del 17/10.
- Il codice in `dev_release2` (Form e Bulk: come si dichiara oggi un costo su un ADJUSTMENT in uscita; i plugin che producono ADJUSTMENT in uscita; i messaggi `costBasisNotAllowed`, `costBasisModeIncompatible`).

## Cosa produrre
Un file `N78-1-analisi.md` in `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/salvataggi-worktrees-20261021/ondata3/`, in **italiano semplice**, per il developer:
1. La domanda in una frase, e che cosa fa oggi LibreFolio (con i file:riga).
2. **Un esempio numerico unico** (quello sopra, o uno migliore) calcolato per (a), (b), (c): quantità, PMC, realizzato, capitale, P&L totale, TWRR del giorno, Dashboard e lotti. Una tabella.
3. Cosa vede l'utente nel Form/Bulk/import in ciascun caso (campo del costo sì/no, testo, avvisi).
4. Coerenza con la decisione 47 e con le gambe al bordo di J-10.
5. Pro e contro, costo di implementazione di ciascuna (file toccati, migrazione dei dati già salvati sì/no), e **una raccomandazione** di W (MF ha preparato i fatti; se la sua lettura differisce dalla tua, scrivi entrambe).
6. Le domande che restano al developer, numerate (Q-N78-1a, …).
Aggiorna anche il tuo piano con una sezione breve che rimanda al file.

## Non fare
- Nessun codice di prodotto, nessun test nuovo nel repo, nessuna decisione: è una proposta.
- Non toccare file di altre sessioni.

## Fatto quando
Il file c'è, i numeri dell'esempio sono verificati (con il codice o a mano, dillo), il piano rimanda al file: **CHECKPOINT READY** e **FROZEN**.
