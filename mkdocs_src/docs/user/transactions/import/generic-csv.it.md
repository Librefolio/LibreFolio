# 📄 CSV Generico

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
