# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV Generico

Il provider **CSV Generico** è un fallback flessibile per i broker che non sono supportati direttamente. Consente la mappatura manuale delle colonne, permettendoti di importare dati da qualsiasi esportazione in formato CSV.

## Quando Utilizzarlo

- Il tuo broker non è presente nell'elenco dei supportati.
- Un broker supportato ha cambiato il formato di esportazione e il plugin non è ancora stato aggiornato.
- Hai un foglio di calcolo personalizzato che desideri importare.

## Come Funziona

1. Carica il tuo file CSV.
2. LibreFolio mostra le colonne grezze rilevate.
3. Mappa ogni colonna al campo corrispondente di LibreFolio (data, tipo, asset, quantità, prezzo, importo, valuta, commissione).
4. Visualizza l'anteprima delle righe analizzate e conferma l'importazione.

!!! tip "Aggiungi un plugin nativo"

    Se utilizzi frequentemente un broker, considera la possibilità di contribuire con un plugin nativo. Consulta il [Manuale dello Sviluppatore → Guida Plugin BRIM](../../../developer/backend/brim/generic_csv.md) per le istruzioni.

## 🔗 Riferimenti per Sviluppatori

→ [Provider CSV Generico — Dettagli di Implementazione](../../../developer/backend/brim/generic_csv.md)
