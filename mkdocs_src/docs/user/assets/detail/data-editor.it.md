# ✏️ Editor Dati

L'Editor Dati ti consente di visualizzare, aggiungere, modificare o eliminare manualmente i punti dati dei prezzi e gli eventi degli asset direttamente dalla pagina di dettaglio dell'asset.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Editor Dati Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Come Usarlo

1. Clicca sul pulsante **Modifica Dati** (✏️📊) nella barra degli strumenti
2. Si apre il pannello dell'editor con due schede: **Prezzi** ed **Eventi**
3. In ogni scheda puoi:
 - **Aggiungere** una nuova riga: clicca su ➕ Aggiungi Riga e compila i campi
 - **Modificare** una riga esistente: clicca su una cella per modificarla
 - **Eliminare** una riga: selezionala e clicca su 🗑️ Elimina
 - **Importare CSV**: clicca su 📥 Importa CSV per aggiungere dati in massa
4. Le modifiche sono tracciate da un badge con il conteggio delle modifiche non salvate. Clicca su **Salva** per confermare tutte le modifiche, oppure su **Annulla** per scartarle.
5. Clicca su **Chiudi** (✕) per uscire — gli altri pannelli (segnali, misure) verranno ripristinati automaticamente.

---

## 💰 Scheda Prezzi

La scheda Prezzi mostra tutti i punti dati dei prezzi per l'asset. Colonne:

| Colonna | Obbligatoria | Descrizione |
|--------|----------|-------------|
| **Data** | ✅ | Data nel formato YYYY-MM-DD |
| **Valuta** | ✅ | Codice valuta ISO 4217 (es. USD, EUR) |
| **Chiusura** | ✅ | Prezzo di chiusura |
| **Apertura** | | Prezzo di apertura |
| **Massimo** | | Prezzo più alto della giornata |
| **Minimo** | | Prezzo più basso della giornata |
| **Volume** | | Volume di trading |

### Formato Importazione CSV

```
date;currency;close
2024-01-15;USD;145.50
2024-01-16;USD;146.10
```

Formato esteso con colonne opzionali:
```
date;currency;close;open;high;low;volume
2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
```

---

## 📅 Scheda Eventi

La scheda Eventi mostra tutti gli [eventi dell'asset](../../../financial-theory/instruments/asset-events/index.md) (dividendi, split, ecc.). Colonne:

| Colonna | Obbligatoria | Descrizione |
|--------|----------|-------------|
| **Data** | ✅ | Data nel formato YYYY-MM-DD |
| **Valuta** | | Codice ISO 4217 |
| **Tipo** | ✅ | Tipo di evento (DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT) |
| **Importo** | ✅ | Valore numerico (es. dividendo per azione, rapporto di split) |
| **Note** | | Descrizione opzionale |

!!! info "Eventi Automatici vs Manuali"

    Gli eventi generati da un provider (es. Investimento Programmato) sono contrassegnati come **auto** e appaiono come righe di sola lettura. Possono essere eliminati ma non modificati. Gli eventi manuali sono completamente modificabili.

### Formato Importazione CSV

```
date;currency;type;amount;notes
2024-03-15;USD;DIVIDEND;1.25;Q1 payout
2024-06-01;;SPLIT;2;2:1 split
```

---

## ⚠️ Interruttore Righe Obsolete

La barra degli strumenti include un **interruttore per le righe obsolete**. Le righe obsolete sono punti dati riempiti a ritroso (backward-filled) — voci di riempimento dei gap copiate dal punto dato reale più vicino. L'interruttore ti permette di mostrarle/nasconderle per concentrarti sui dati effettivi. Un contatore mostra quante righe obsolete sono presenti.

---

## 🖱️ Navigazione Grafico ↔ Editor

Fai **doppio clic** su un punto nel grafico dei prezzi (o tieni premuto su mobile) per scorrere direttamente a quella riga nell'editor:

- Doppio clic su un **punto di prezzo** → scorre alla scheda Prezzi
- Doppio clic su un **marcatore di evento** → scorre alla scheda Eventi

---

!!! note "Quando usare l'Editor Dati"

    L'Editor Dati è utile per:

    - Correggere dati dei prezzi errati provenienti da un provider
    - Aggiungere dati storici per asset senza un provider
    - Colmare lacune nella cronologia dei prezzi (es. date mancanti)
    - Registrare eventi societari (dividendi, split) non rilevati dai provider

---

## 🔗 Correlati

- 📈 **[Grafico Interattivo](chart.md)** — Visualizzazione del grafico con marcatori di eventi
- 📅 **[Eventi dell'Asset](events.md)** — Tipi di eventi e le loro fonti
- 📚 **[Eventi Asset (Teoria Finanziaria)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata dell'impatto per ogni tipo di evento
- 🔌 **[Provider](../providers/index.md)** — Recupero automatico dei prezzi
