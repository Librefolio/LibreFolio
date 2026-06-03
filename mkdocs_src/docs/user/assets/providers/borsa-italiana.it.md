# 🇮🇹 Borsa Italiana

**Borsa Italiana** è la borsa valori italiana, gestita da Euronext. LibreFolio include un **provider asset** dedicato che recupera prezzi, serie storiche e metadati degli strumenti direttamente dal sito web di Borsa Italiana.

---

## 🔍 Cosa Fornisce

| Dato | Descrizione |
|------|-------------|
| **Prezzo attuale** | Ultimo prezzo ufficiale di mercato |
| **OHLCV Storico** | Serie giornaliere di open/high/low/close/volume |
| **Metadati strumento** | ISIN, segmento di mercato, valuta |

Gli asset scambiati su Borsa Italiana includono azioni italiane (segmento MTA/MIL), ETF (ETFplus), obbligazioni (MOT) e fondi.

---

## ⚙️ Configurazione

Non è richiesta alcuna chiave API o registrazione: lo scraper effettua lo scraping dei dati pubblici dal sito web di Borsa Italiana. La configurazione è disponibile per singolo asset nel pannello **Provider Config** nella pagina di dettaglio dell'asset.

1. Naviga verso l'asset che desideri monitorare.
2. Apri il pannello **⚙️ Provider Config**.
3. Seleziona **Borsa Italiana** dall'elenco dei provider.
4. Inserisci l'**ISIN** o il codice ticker di Borsa Italiana.
5. Salva — LibreFolio recupererà la prima serie storica durante la sincronizzazione successiva.

!!! tip "Trovare l'ISIN"

    Puoi cercare l'ISIN su [borsaitaliana.it](https://www.borsaitaliana.it) cercando il nome dello strumento. L'ISIN è visualizzato in ogni pagina di dettaglio dello strumento.

---

## 🔄 Sincronizzazione

Il provider Borsa Italiana partecipa al ciclo standard di **sincronizzazione asset**. Avvialo manualmente dalla pagina di dettaglio dell'asset tramite il pulsante **🔄 Sync**, oppure lascia che il job pianificato in background venga eseguito durante la notte.

!!! note "Rate limiting"

    Il provider applica un throttling automatico per evitare di essere bloccato da Borsa Italiana. Se possiedi molti asset di questo mercato, la sincronizzazione completa potrebbe richiedere alcuni minuti.

---

## 🔗 Documentazione per Sviluppatori

Per i dettagli di implementazione (formato delle richieste, strategia di parsing HTML, mappatura dei campi), consulta:

→ [Developer Manual — Borsa Italiana Provider](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Correlati

- 📋 **[Panoramica Asset](../index.md)** — Gestisci la tua libreria di asset
- 🏦 **[Asset Providers](./index.md)** — Altre sorgenti di dati
- 📡 **[justETF](./justetf.md)** — Sorgente alternativa per i dati ETF
