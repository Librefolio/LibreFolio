# ⚙️ Configurazione del Broker & Esportazione AI

La scheda **Info** contiene la configurazione dei metadati, i controlli di sicurezza, lo strumento di Esportazione AI con ambito specifico e il pannello di configurazione della condivisione.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista Info e Condivisione del Broker">
</div>

---

## ⚙️ Metadati & Impostazioni

La colonna sinistra della scheda Info mostra le proprietà chiave e le regole di validazione per questo broker:

- **Stato del Broker**: Indica se l'account è attualmente `Attivo`. I broker inattivi sono nascosti nei menu a tendina, ma i loro valori storici sono conservati nei grafici.
- **Date**: Mostra quando l'account è stato aperto e quando è stato creato in LibreFolio.
- **Valuta di Base**: La valuta di base dell'account (tutte le transazioni e valutazioni vengono convertite internamente in questa valuta utilizzando i tassi di cambio storici per la reportistica locale).
- **Consenti Scoperto di Contante**: Un interruttore per ignorare gli errori di saldo negativo. Quando disabilitato, LibreFolio blocca le transazioni (come acquisti o prelievi) che comporterebbero un saldo di contante negativo.
- **Consenti Posizioni Corte**: Un interruttore per autorizzare quantità negative di asset. Quando disabilitato, viene bloccata la vendita di una quantità superiore alla tua posizione aperta corrente.

---

## 🧠 Esportazione AI con Ambito Specifico

Nell'angolo in alto a destra della barra degli strumenti del broker, il pulsante **Esportazione AI** (:material-brain:) copia una rappresentazione testuale strutturata dello stato corrente del broker negli appunti.

Questa esportazione ha **ambito specifico per questo broker** (a differenza del pulsante principale della dashboard che copia i dati per l'intero portafoglio). Aggrega:

- Saldi di contante locali.
- Detenzioni e quantità di asset locali.
- Pesi di allocazione attivi.

Puoi incollare questo prompt strutturato direttamente nel tuo LLM preferito (come Gemini o ChatGPT) per un'analisi mirata e personalizzata di questo specifico account.

---

## 🤝 Pannello di Condivisione dell'Accesso

La colonna destra della scheda Info ospita il gestore di **Condivisione del Broker** integrato. Qui puoi:

- Invitare altri utenti tramite la loro email o nome utente.
- Definire il loro permesso di ruolo (Proprietario, Editor, Visualizzatore).
- Configurare le percentuali di proprietà.

Per una spiegazione dettagliata delle regole di condivisione, dei ruoli e della logica delle percentuali, consulta la pagina dedicata **[Condivisione del Broker](sharing.md)**.
