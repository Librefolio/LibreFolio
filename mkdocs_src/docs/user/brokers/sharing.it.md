# 🤝 Condivisione Broker

LibreFolio ti consente di condividere l'accesso ai tuoi conti di brokerage con altri utenti. Questo è utile per famiglie, consulenti finanziari o commercialisti che necessitano di visibilità sul tuo portafoglio.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modale di condivisione broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Come condividere

1. Vai alla pagina dei dettagli di un broker
2. Clicca sul pulsante **Condividi** (:material-share-variant:) nell'intestazione
3. Si apre la **finestra modale di condivisione**
4. **Cerca** l'utente tramite il nome utente
5. **Seleziona un ruolo** (Visualizzatore, Editor o Proprietario)
6. **Imposta la percentuale di condivisione** (trascina lo slider o digita il valore)
7. Clicca su **Salva** per applicare le modifiche

!!! warning "Solo i proprietari possono gestire l'accesso"

    Devi essere un **proprietario** del broker per aggiungere, rimuovere o modificare l'accesso di altri utenti.

---

## 🛡️ Ruoli di accesso

Quando condividi un broker, assegni un **ruolo** che determina cosa l'altro utente può fare:

| Funzionalità | Visualizzatore | Editor | Proprietario |
|:-------------------------------------|:------:|:------:|:-----:|
| **Visualizza dettagli broker** | ✅ | ✅ | ✅ |
| **Visualizza transazioni** | ✅ | ✅ | ✅ |
| **Visualizza report e grafici** | ✅ | ✅ | ✅ |
| **Aggiungi/Modifica transazioni** | ❌ | ✅ | ✅ |
| **Importa file (BRIM)** | ❌ | ✅ | ✅ |
| **Modifica impostazioni broker** | ❌ | ✅ | ✅ |
| **Gestisci accesso (Aggiungi/Rimuovi utenti)** | ❌ | ❌ | ✅ |
| **Elimina broker** | ❌ | ❌ | ✅ |

- 👁️ **Visualizzatore**: Accesso in sola lettura. Ideale per commercialisti o membri della famiglia che hanno solo bisogno di vedere i dati.
- ✏️ **Editor**: Può gestire le operazioni quotidiane (transazioni, importazioni) ma non può eliminare il broker o modificare l'accesso.
- 👑 **Proprietario**: Controllo totale. Può fare tutto, inclusa l'aggiunta o la rimozione di altri utenti.

---

## 📊 Percentuale di condivisione

Ogni utente con accesso a un broker ha una **percentuale di condivisione** (da 0% a 100%). Questa rappresenta quanta parte del valore del portafoglio del broker appartiene a quell'utente.

!!! example "Conto cointestato"

    Tu e il tuo coniuge condividete un conto di brokerage al 50/50:

    - Tu (Proprietario): **50%**
    - Coniuge (Editor): **50%**

    Nel calcolo del valore totale del portafoglio, il sistema conteggia il 50% del valore di questo broker per ciascuno di voi.

!!! example "Consulente finanziario"

    Il tuo consulente finanziario deve vedere il tuo portafoglio ma non ne possiede alcuna parte:

    - Tu (Proprietario): **100%**
    - Consulente (Visualizzatore): **0%**

La somma di tutte le percentuali di condivisione per un broker **non deve superare il 100%**, ma può essere inferiore (ad esempio, un conto cointestato dove il co-intestatario non è presente nel sistema).

---

## 💡 Scenari comuni

| Scenario | Configurazione suggerita |
|----------|----------------|
| **Coniuge / Partner** | Editor o co-proprietario, 50% di quota ciascuno |
| **Consulente finanziario** | Visualizzatore, 0% di quota |
| **Commercialista** | Visualizzatore, 0% di quota |
| **Membro della famiglia** | Visualizzatore o Editor, percentuale di quota personalizzata |

!!! note "Aggregazione del portafoglio"

    La percentuale di condivisione è progettata per future funzionalità di aggregazione del portafoglio. Quando verranno implementate, la dashboard di ogni utente mostrerà la propria quota proporzionale di tutti i broker a cui ha accesso.
