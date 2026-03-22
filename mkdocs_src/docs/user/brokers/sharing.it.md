# 🤝 Condivisione Broker

LibreFolio ti permette di condividere l'accesso ai tuoi broker con altri utenti. Questo è utile per famiglie, consulenti finanziari o commercialisti che hanno bisogno di visibilità sul tuo portafoglio.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Finestra di condivisione Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Come Condividere

1. Vai alla pagina dei dettagli del broker
2. Fai clic sul pulsante **Condividi** (:material-share-variant:) nell'header
3. Si apre la **finestra di condivisione**
4. **Cerca** l'utente tramite nome utente
5. **Seleziona un ruolo** (Visualizzatore, Editore o Proprietario)
6. **Imposta la percentuale di possesso** (trascina il cursore o digita il valore)
7. Fai clic su **Salva** per applicare le modifiche

!!! warning "Solo i Proprietari possono gestire l'accesso"
    Devi essere il **titolare** del broker per aggiungere, rimuovere o modificare l'accesso di altri utenti.

---

## 🛡️ Ruoli di Accesso

Quando condividi un broker, assegni un **ruolo** che determina cosa l'altro utente può fare:

| Funzionalità | Visualizzatore | Editore | Proprietario |
|:------------------------------------------|:--------------:|:-------:|:------------:|
| **Visualizza Dettagli Broker** | ✅ | ✅ | ✅ |
| **Visualizza Transazioni** | ✅ | ✅ | ✅ |
| **Visualizza Report e Grafici** | ✅ | ✅ | ✅ |
| **Aggiungi/Modifica Transazioni** | ❌ | ✅ | ✅ |
| **Importa File (BRIM)** | ❌ | ✅ | ✅ |
| **Modifica Impostazioni Broker** | ❌ | ✅ | ✅ |
| **Gestisci Accesso (Aggiungi/Rimuovi Utenti)** | ❌ | ❌ | ✅ |
| **Elimina Broker** | ❌ | ❌ | ✅ |

- 👁️ **Visualizzatore**: Accesso in sola lettura. Ideale per commercialisti o membri della famiglia che devono solo visualizzare i dati.
- ✏️ **Editore**: Può gestire le operazioni quotidiane (transazioni, importazioni) ma non può eliminare il broker o modificare l'accesso.
- 👑 **Proprietario**: Controllo completo. Può fare di tutto, incluso aggiungere/rimuovere altri utenti.

---

## 📊 Percentuale di Possesso

Ogni utente con accesso a un broker ha una **percentuale di possesso** (da 0% a 100%). Questa rappresenta quanto del valore del portafoglio del broker appartiene a quell'utente.

!!! example "Conto Cointestato"
    Tu e il tuo coniuge condividete un conto di intermediazione al 50/50:

    - Tu (Proprietario): **50%**
    - Coniuge (Editore): **50%**

    Quando si calcola il valore totale del portafoglio, il sistema conta il 50% del valore di questo broker per ciascuno di voi.

!!! example "Consulente Finanziario"
    Il tuo consulente finanziario deve vedere il tuo portafoglio ma non ne possiede nessuna parte:

    - Tu (Proprietario): **100%**
    - Consulente (Visualizzatore): **0%**

La somma di tutte le percentuali di possesso per un broker **non deve superare il 100%**, ma può essere minore (es. un conto cointestato dove il cointestatario non è nel sistema).

---

## 💡 Scenari Comuni

| Scenario | Configurazione Consigliata |
|----------------------|-----------------------------------------------|
| **Coniuge / Partner** | Editore o co-titolare, 50% ciascuno |
| **Consulente Finanziario** | Visualizzatore, 0% di possesso |
| **Commercialista** | Visualizzatore, 0% di possesso |
| **Membro della famiglia** | Visualizzatore o Editore, percentuale personalizzata |

!!! note "Aggregazione del Portafoglio"
    La **percentuale di possesso** è progettata per future funzionalità di aggregazione del portafoglio. Quando queste saranno implementate, la dashboard di ogni utente mostrerà la quota proporzionale di tutti i broker a cui ha accesso.
