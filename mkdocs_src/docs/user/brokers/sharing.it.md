# 🤝 Condivisione del Broker

LibreFolio ti consente di condividere l'accesso ai tuoi conti titoli con altri utenti. Questo è utile per famiglie, consulenti finanziari o commercialisti che hanno bisogno di visibilità sul tuo portafoglio.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Come condividere

Solo un **Proprietario** del broker può gestire gli accessi. Puoi aprire il pannello di condivisione in due modi:

- **Dall'elenco dei broker**: fai clic sull'icona **Condividi** (:material-share-variant:) sulla scheda del broker — si apre la **Modale di condivisione**.
- **Dalla pagina di dettaglio del broker**: fai clic sul pulsante **Condividi** nell'intestazione — approdi alla scheda **Info**, che ospita il pannello di condivisione.

Poi:

1. **Cerca** l'utente per nome utente
2. **Seleziona un ruolo** (Visualizzatore, Editor o Proprietario)
3. **Imposta la percentuale di proprietà** — solo per il ruolo *Proprietario* (trascina il cursore o digita un valore; Visualizzatori ed Editor hanno sempre 0%)
4. Fai clic su **Salva** per applicare le modifiche

!!! warning "Solo i proprietari possono gestire gli accessi"

    Devi essere un **Proprietario** del broker per aggiungere, rimuovere o modificare l'accesso di altri utenti. I non proprietari vedono lo stesso pannello in modalità di sola lettura.

---

## 🛡️ Ruoli di accesso

Quando condividi un broker, assegni un **ruolo** che determina cosa può fare l'altro utente:

| Funzionalità | Visualizzatore | Editor | Proprietario |
|:-------------------------------------|:------:|:------:|:-----:|
| **Visualizza Dettagli Broker** | ✅ | ✅ | ✅ |
| **Visualizza Transazioni** | ✅ | ✅ | ✅ |
| **Visualizza Report e Grafici** | ✅ | ✅ | ✅ |
| **Aggiungi/Modifica Transazioni** | ❌ | ✅ | ✅ |
| **Importa File (BRIM)** | ❌ | ✅ | ✅ |
| **Modifica Impostazioni Broker** | ❌ | ✅ | ✅ |
| **Gestisci Accessi (Aggiungi/Rimuovi Utenti)** | ❌ | ❌ | ✅ |
| **Elimina Broker** | ❌ | ❌ | ✅ |

- 👁️ **Visualizzatore**: accesso in sola lettura. Ideale per commercialisti o familiari che devono solo vedere i dati.
- ✏️ **Editor**: può gestire le operazioni quotidiane (transazioni, importazioni) ma non può eliminare il broker o modificare gli accessi.
- 👑 **Proprietario**: controllo totale. Può fare tutto, inclusa l'aggiunta/rimozione di altri utenti. Un broker può avere **più di un Proprietario** — consulta la percentuale di condivisione qui sotto.

---

## 📊 Percentuale di condivisione

Ogni **Proprietario** di un broker ha una **percentuale di condivisione** (da 0% a 100%). Questa rappresenta la quota del valore del portafoglio del broker che appartiene a quel proprietario. Visualizzatori ed Editor hanno sempre 0% — lo schema rifiuta qualsiasi quota diversa da zero per loro.

!!! example "Conto cointestato"

    Tu e il tuo coniuge siete contitolari di un conto titoli al 50/50. Entrambi siete Proprietari:

    - Tu (Proprietario): **50%**
    - Coniuge (Proprietario): **50%**

    Ognuno di voi vede il 50% del valore di questo broker conteggiato nella propria dashboard.

!!! example "Consulente finanziario"

    Il tuo consulente finanziario deve vedere il tuo portafoglio, ma non ne possiede alcuna quota:

    - Tu (Proprietario): **100%**
    - Consulente (Visualizzatore): **0%**

La somma di tutte le percentuali di condivisione per un broker **non deve superare il 100%**, ma può essere inferiore (ad esempio, un conto cointestato in cui il cointestatario non è nel sistema). Il pannello mostra i totali **Assegnato** e **Disponibile** mentre effettui le modifiche.

!!! note "Aggregazione del portafoglio"

    La percentuale di condivisione è **già applicata** all'aggregazione del tuo portafoglio: la Dashboard e le statistiche a livello di portafoglio scalano ogni importo di un broker condiviso in base alla tua quota di proprietà. Un Proprietario con il 50% vede conteggiati nei propri totali metà del valore, del reddito e del P&L di quel broker. Visualizzatori ed Editor, la cui quota è sempre 0% per regola, vedono invece gli importi **completi** del broker — la quota scala solo ciò che *possedi*.

---

## 🚪 Uscire da un broker condiviso (in autonomia)

Non hai mai bisogno dell'intervento di un Proprietario per uscire da un broker a cui hai accesso. Nel pannello di condivisione, la sezione **Il tuo accesso** ti consente di:

- **Abbandona il broker** — rimuove immediatamente il tuo accesso. Il broker scompare dai tuoi elenchi.
- **Passa a Visualizzatore** — un Editor può declassarsi a Visualizzatore; un Proprietario può promuoverlo di nuovo in seguito.

!!! danger "Ultimo proprietario: l'uscita elimina il broker"

    Se sei l'**unico Proprietario** rimasto, l'azione di uscita diventa **Abbandona ed elimina broker**: l'uscita *elimina definitivamente il broker insieme a tutte le sue transazioni e ai file di report importati*. Questa operazione non può essere annullata. Se non è quello che vuoi, assegna prima a un altro utente il ruolo di Proprietario, poi esci.

---

## 💡 Scenari comuni

| Scenario | Configurazione consigliata |
|----------|----------------|
| **Coniuge / Partner** | Due Proprietari, quota 50% ciascuno |
| **Consulente finanziario** | Visualizzatore, quota 0% |
| **Commercialista** | Visualizzatore, quota 0% |
| **Familiare** | Visualizzatore o Editor, quota 0% |
