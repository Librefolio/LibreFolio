# ➕ Creare e Modificare Asset

## Creazione di un Nuovo Asset

1. Fare clic su **+ New Asset** nella pagina degli asset
2. Usare la **Ricerca Intelligente** per trovare il proprio asset: digitare un nome, ISIN o ticker e LibreFolio cerca tra più provider (Yahoo Finance, justETF, CSS Scraper) in parallelo
3. Selezionare un risultato per **auto-compilare** nome, identificativi, valuta, distribuzione settoriale/geografica e configurazione del provider
4. Oppure compilare manualmente:
    - **Name** (richiesto)
    - **Category** (richiesto): Stock, ETF, Bond, Crypto, Commodity, P2P, Index, ecc.
    - **Currency** (richiesto): la valuta in cui l'asset è denominato
    - **Identifiers**: ISIN, ticker, CUSIP, SEDOL, ecc.
5. Configurare opzionalmente un **[Provider](providers/index.md)** per il recupero automatico dei prezzi
6. Aggiungere opzionalmente le distribuzioni **Sector** e **Geographic**
7. Fare clic su **Save**

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="create-modal" alt="Finestra modale di creazione asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

## 🧪 Test della Configurazione del Provider

Dopo aver configurato un provider, fare clic su **Test Configuration** per verificare che i dati dei prezzi possano essere recuperati. Il test controlla:

- **Current Price**: recupera l'ultimo prezzo
- **History**: recupera lo storico dei prezzi (se supportato)

I risultati vengono visualizzati inline con i tempi di esecuzione. Un avviso ⚠️ indica che l'operazione non è supportata da questo provider (ad esempio, CSS Scraper non supporta lo storico).

## 🔌 Assegnazione del Provider

A ogni asset può essere assegnato un provider di prezzi. Consultare [Providers](providers/index.md) per i dettagli sui provider disponibili e sulla loro configurazione.

## ⏱️ Intervallo di Recupero

L'intervallo di recupero controlla con quale frequenza LibreFolio aggiorna automaticamente i dati dei prezzi dell'asset. Il valore predefinito è 24 ore (`24:00`). Formato: `HH:MM`.

## 🛠️ Modifica di un Asset

Fare clic sul pulsante **Edit** (✏️) nella [pagina di dettaglio](detail/index.md) per aprire la finestra modale dell'asset con tutti i campi precompilati. Tutti i campi sono modificabili, inclusa la configurazione del provider e le distribuzioni.

## 🔗 Correlati

- 📊 **[Pagina di Dettaglio Asset](detail/index.md)** — Visualizzare e analizzare i dati dell'asset
- 🔌 **[Providers](providers/index.md)** — Provider di prezzi disponibili
