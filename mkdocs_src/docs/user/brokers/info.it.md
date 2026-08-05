# ⚙️ Configurazione Broker & Esportazione AI

La scheda **Info** contiene la configurazione dei metadati, i controlli di sicurezza, lo strumento di Esportazione AI circoscritto e il pannello di configurazione della condivisione.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista Info e Condivisione del Broker">
</div>

---

## ⚙️ Metadati & Impostazioni

La colonna sinistra della scheda Info mostra le proprietà chiave e le regole di validazione per questo broker:

- **Stato Broker**: Mostra se l'account è attualmente `Active`. I broker inattivi sono nascosti dai menu a tendina degli elenchi, ma i loro valori storici vengono conservati nei grafici.
- **Date**: Mostra quando l'account è stato aperto e quando è stato creato in LibreFolio.
- **Valuta Base**: La valuta base dell'account (tutte le transazioni e le valutazioni vengono internamente convertite utilizzando i tassi di cambio storici in questa valuta per il reporting locale).
- **Consenti Scoperto di Liquidità**: Un interruttore per bypassare gli errori di saldo negativo. Quando disattivato, LibreFolio blocca le transazioni (come acquisti o prelievi) che comporterebbero un saldo di liquidità negativo.
- **Consenti Posizioni Short**: Un interruttore per autorizzare quantità negative di asset. Quando disattivato, viene bloccata la vendita di una quantità superiore alla dimensione della posizione aperta in essere.

---

## 🧠 Esportazione AI Circoscritta

Nella parte superiore destra della barra degli strumenti del broker, **Esportazione AI** (:material-brain:) apre tre task dedicati del Broker—non prompt di Portfolio filtrati:

- **Revisione Broker**
- **Performance del Broker & Driver di Mercato**
- **Strategie di Compensazione delle Minusvalenze**

Lo snapshot del backend è limitato al broker selezionato e può includere la sua liquidità, le posizioni, l'attività, la performance, i costi, la concentrazione e i lotti FIFO in base al task selezionato. I controlli di accesso lato server impediscono l'esportazione di un broker a cui l'utente corrente non può accedere. LibreFolio copia solo il risultato negli appunti; rivedi i dati finanziari sensibili prima di condividerli. Vedi [Esportazione AI Broker](../ai-export/broker.md) o la [panoramica Esportazione AI](../ai-export/index.md).

---

## 🤝 Pannello di Condivisione dell'Accesso

La colonna destra della scheda Info contiene il gestore **Condivisione Broker** integrato. Qui puoi:

- Invitare altri utenti tramite il loro indirizzo email o nome utente.
- Definire il loro permesso di ruolo (Proprietario, Editor, Visualizzatore).
- Configurare le percentuali di proprietà.

Per una spiegazione dettagliata delle regole di condivisione, dei ruoli e della logica delle percentuali, fai riferimento alla pagina dedicata **[Condivisione Broker](sharing.md)**.
