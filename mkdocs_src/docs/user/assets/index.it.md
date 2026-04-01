# 💼 Asset

Gli asset sono il cuore di LibreFolio. Rappresentano qualsiasi strumento finanziario che possiedi o monitori: azioni, ETF, obbligazioni, criptovalute o strumenti personalizzati come conti deposito con interessi programmati.

## 📌 Cos'è un Asset?

Un asset in LibreFolio è uno strumento finanziario con:

- **Identità**: nome, ISIN, ticker o altri identificativi
- **Categoria**: azione, ETF, obbligazione, crypto, commodity, ecc.
- **Provider**: un fornitore di prezzi opzionale che recupera automaticamente prezzi attuali e storici
- **Transazioni**: operazioni di acquisto, vendita, dividendo, interesse collegate a un portafoglio

## ➕ Creare un Asset

1. Vai alla sezione **Asset** nella barra laterale
2. Clicca **+ Nuovo Asset**
3. Compila le informazioni di base:
    - **Nome** (obbligatorio)
    - **Categoria** (obbligatorio)
    - **Valuta** (obbligatorio)
    - **Identificativi**: ISIN, ticker, CUSIP, SEDOL, ecc.
4. Configura opzionalmente un **Provider** per il recupero automatico dei prezzi
5. Clicca **Salva**

## 🛠️ Gestione degli Asset

### ✏️ Modifica

Clicca su qualsiasi riga asset per aprire il modale di dettaglio. Tutti i campi sono modificabili.

### 🗑️ Eliminazione

Usa il pulsante elimina (🗑️) sulla riga, oppure seleziona più asset e usa l'eliminazione in blocco.

### 🧪 Test Configurazione Provider

Dopo aver configurato un provider, clicca **Test Configurazione** per verificare che i dati di prezzo possano essere recuperati. Il test verifica:

- **Prezzo Attuale**: recupera l'ultimo prezzo
- **Storico**: recupera i dati storici dei prezzi (se supportato)

I risultati vengono mostrati inline con i tempi di esecuzione. Un ⚠️ avviso indica che l'operazione non è supportata dal provider (es. CSS Scraper non supporta lo storico).

## 🔌 Assegnazione Provider

Ogni asset può avere un provider di prezzi assegnato. Vedi [Provider](providers/index.en.md) per dettagli sui provider disponibili e la loro configurazione.

## ⏱️ Intervallo di Fetch

L'intervallo di fetch controlla quanto spesso LibreFolio aggiorna automaticamente i dati di prezzo dell'asset. Il valore predefinito è 24 ore (24:00). Formato: `HH:MM`.
