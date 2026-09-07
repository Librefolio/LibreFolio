# 💸 Transazioni

Le transazioni rappresentano ogni attività finanziaria all'interno del tuo portafoglio. Ogni acquisto, vendita, dividendo, commissione, trasferimento di asset e movimento di cassa viene registrato qui per mantenere aggiornate le statistiche del portafoglio, le performance e la documentazione fiscale.

Ogni conto broker in LibreFolio ha il proprio registro delle transazioni dedicato, che mostra tutti i movimenti in ordine cronologico inverso.

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="list" alt="Lista Transazioni">
</div>

---

## 🚀 Primi Passi

Gestire le tue transazioni è semplice:

* 📝 **Inserimento Manuale e Modifica**: Apri il **[Modulo Transazione](form.md)** interattivo per aggiungere, modificare o regolare manualmente le singole operazioni.
* 📥 **Importazione Broker Super-Facile**: Non è necessario digitare tutto a mano! LibreFolio ti permette di caricare esportazioni CSV o XLSX dal tuo broker e di mapparle e importarle automaticamente in pochi secondi. Scopri di più nella guida **[Importazione da Broker](import/index.md)**.

---

## 🛠️ Funzionalità della Pagina

إcco un riepilogo delle operazioni e degli strumenti disponibili direttamente all'interno della pagina delle transazioni:

| Funzionalità | Descrizione | Riferimento |
|---------|-------------|-----------|
| **Aggiungi e Modifica** | Clicca su **Aggiungi Transazione** per aprire il modulo, oppure clicca su qualsiasi riga esistente per modificarne i dettagli. | [Modulo Transazione](form.md) |
| **Importazione Broker** | Clicca su **Importa** per caricare un estratto conto del broker e importare automaticamente la tua cronologia. | [Importazione da Broker](import/index.md) |
| **Ordinamento e Filtro** | Clicca su qualsiasi intestazione di colonna per ordinare la lista. Usa la barra di ricerca per filtrare per nome dell'asset, tipo o note. | |
| **Eliminazione e Azioni in blocco** | Clicca con il tasto destro su qualsiasi riga per aprire il Menu Contestuale per azioni rapide. L'eliminazione di una singola riga e la selezione di più righe per l'eliminazione multipla aprono entrambe lo stesso **workspace di blocco**, dove le righe vengono preparate per l'eliminazione prima della conferma; un partner collegato (operazione FX o gamba di trasferimento) viene preparato automaticamente insieme alla riga scelta. | |

La duplicazione funziona allo stesso modo: **Clona** dal menu contestuale prepara una copia nel workspace di blocco — mantenendo la **data originale** (la clonazione è il modo in cui una riga storica mal classificata viene corretta, quindi la data deve sopravvivere) — dove la modifichi e la salvi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Bulk workspace with a cloned transaction row">
</div>

| **Transazioni Composte e Promozione** | Collega due operazioni singole in una **Transazione Composta** tramite la **Promozione** per consentire tracciamenti e analisi più sofisticate, o suddividi (split) una transazione composta in operazioni singole. | [Modulo Transazione](form.md#composite-transactions) |

---

## 🔗 Correlati

* 📝 **[Modulo Transazione](form.md)** — Campi, convalida e opzioni specifiche per tipo
* 📥 **[Importazione da Broker](import/index.md)** — Workflow di importazione BRIM
* 📖 **[Tipi di Transazione](../../financial-theory/instruments/transaction-types/index.md)** — Teoria finanziaria dietro ogni tipo
