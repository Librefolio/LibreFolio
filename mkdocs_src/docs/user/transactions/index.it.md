# 💸 Transazioni

Le transazioni sono il **cuore di LibreFolio** — ogni acquisto, vendita, dividendo, commissione, trasferimento e movimento di cassa che registrate risiede qui. Ogni broker ha la propria lista di transazioni, accessibile dalla pagina di dettaglio del broker.

## 📋 Tabella delle Transazioni

La tabella delle transazioni mostra tutti i movimenti di un broker in ordine cronologico inverso. Ogni riga mostra:

| Colonna | Descrizione |
|--------|-------------|
| **Data** | Data di esecuzione della transazione |
| **Tipo** | Icona + etichetta: BUY, SELL, DIVIDEND, FEE, TRANSFER, ecc. |
| **Asset** | Nome dell'asset collegato (vuoto per le operazioni di cassa) |
| **Quantità** | Numero di unità acquistate/vendute/trasferite |
| **Prezzo** | Prezzo unitario all'esecuzione |
| **Importo** | Valore totale (quantità × prezzo ± commissioni) |
| **Valuta** | Valuta della transazione |
| **Note** | Nota utente opzionale |

### Ordinamento e Filtraggio

- Cliccate su qualsiasi **intestazione di colonna** per ordinare in modo crescente/decrescente.
- Usate la **barra di ricerca** per filtrare per nome dell'asset, tipo o note.
- Usate i pulsanti del **filtro per tipo** per mostrare solo tipi specifici di transazioni.

---

## ➕ Aggiungere Transazioni

Cliccate su **+ Nuova Transazione** per aprire il [Modulo di Transazione](form.md). Potete:

- Creare una **singola transazione** (un modulo per operazione)
- Creare **transazioni in blocco** tramite il modale di importazione massiva — incollate o caricate una tabella di righe

---

## ✏️ Modifica e Cancellazione

- Cliccate su qualsiasi riga per **aprire il modulo** precompilato con i dati di quella transazione.
- Cliccate sull'**icona del cestino** (:material-delete:) per eliminare una transazione.
- Selezionate più righe tramite la colonna con le **caselle di controllo**, quindi usate la barra degli strumenti per la **cancellazione in blocco**.

!!! warning "Le cancellazioni sono permanenti"

    Non è possibile annullare l'eliminazione delle transazioni. Effettuate prima un backup tramite esportazione se non siete sicuri.

---

## ✂️ Frazionamento e Promote

Due operazioni speciali sono disponibili per le **transazioni composite** (TRANSFER e FX_CONVERSION):

### Frazionamento { #split }

Un **frazionamento** scompone una transazione composta nelle sue due componenti costitutive. Usate questa funzione quando una singola riga importata rappresenta in realtà due eventi separati (ad esempio, un CSV di un broker che registra un trasferimento tra valute diverse come un'unica riga).

1. Selezionate la riga della transazione composta.
2. Cliccate su **Frazionamento** nella barra degli strumenti delle azioni.
3. LibreFolio la separa in due transazioni indipendenti.

### Promote

**Promote** eleva una coppia di transazioni registrate individualmente (ad esempio, un PRELIEVO (WITHDRAWAL) dal broker A e un VERSAMENTO (DEPOSIT) nel broker B) in un **TRANSFER** composto e collegato. Questo è il modo standard per registrare lo spostamento di un asset tra i propri broker.

1. Selezionate **esattamente due transazioni** di tipi compatibili.
2. Cliccate su **Promote** nella barra degli strumenti.
3. LibreFolio convalida la compatibilità (stesso asset, direzioni opposte, quantità corrispondente) e le collega.

---

## 📊 WAC — Weighted Average Cost

La tabella delle transazioni integra il **WAC (Weighted Average Cost)** inline. Quando aggiungete o modificate un BUY/SELL:

- Un'**anteprima del WAC** appare nel modulo mostrando la base di costo prevista prima del salvataggio.
- Dopo il salvataggio, le righe che influenzano la base di costo sono contrassegnate con un **indicatore ⚡**.
- Il WAC viene calcolato al runtime utilizzando le regole FIFO/WAC — non è necessario alcun passaggio separato.

Consultate [Teoria Finanziaria → Weighted Average Cost](../../financial-theory/portfolio-theory/weighted-average-cost.md) per la metodologia sottostante.

---

## 📥 Importazione dal Broker (BRIM)

Invece di inserire le transazioni manualmente, potete importarle direttamente dal file di esportazione del vostro broker. Consultate **[Importazione dal Broker](import/index.md)** per la guida passo dopo passo.

---

## 🔗 Correlati

- 📝 **[Modulo di Transazione](form.md)** — Campi, convalida e opzioni specifiche per tipo
- 📥 **[Importazione dal Broker](import/index.md)** — Workflow di importazione BRIM
- 📖 **[Tipi di Transazione](../../financial-theory/instruments/transaction-types/index.md)** — Teoria finanziaria dietro ogni tipo
