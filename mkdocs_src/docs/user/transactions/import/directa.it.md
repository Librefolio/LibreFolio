# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

## 📥 Come Esportare

Per esportare le tue transazioni da Directa SIM:

1. Accedi al tuo [Portale Directa](https://www.directatrading.com) (utilizzando l'interfaccia dLite o Classic).
2. Vai su **INFO** o **Operazioni** nel menu principale, quindi seleziona **Movimenti** (Cash Movements) o **Tabella Ordini** (Order History).
3. Seleziona l'intervallo di date da esportare.
4. Clicca sull'icona di download **CSV** o sul pulsante di esportazione in alto a destra della tabella.
5. Salva il file direttamente senza aprirlo o modificarlo in Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Directa SIM Portal - Movimenti Cash / Transazioni CSV export page] -->
</div>

## ⚠️ Problemi Comuni

!!! warning "Righe di Intestazione"

    I file di Directa SIM contengono un blocco di intestazione con metadati (solitamente 9 righe) prima della tabella dati effettiva. Il parser è progettato per saltare automaticamente questo blocco. **Non eliminare manualmente queste righe di intestazione**, altrimenti il parser non riuscirà a trovare le colonne di dati corrette.

!!! warning "Avvertenze sui Delimitatori"

    Le esportazioni di Directa utilizzano il punto e virgola `;` come delimitatore e la formattazione numerica standard italiana (virgola `,` per i decimali). Il parser elabora queste impostazioni automaticamente. Evita di salvare il CSV tramite software che convertono questi delimitatori (come aprire e salvare in Microsoft Excel senza le impostazioni di testo semplice).

## 📝 Note

- Supporta operazioni su azioni, obbligazioni ed ETF, dividendi, tasse (ritenute fiscali) e commissioni di transazione.
- Le operazioni del conto sono denominate in EUR.

## 🔗 Riferimenti per Sviluppatori

→ [Directa SIM Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
