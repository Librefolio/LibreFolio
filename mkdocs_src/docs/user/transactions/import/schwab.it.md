# <img src="https://www.schwab.com/favicon.ico" alt=""> Charles Schwab

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare la cronologia delle transazioni da Charles Schwab:

1. Accedi al [Portale Clienti di Charles Schwab](https://www.schwab.com).
2. Vai alla scheda **Accounts** e seleziona **History**.
3. Seleziona l'account che desideri esportare (se ne possiedi più di uno).
4. Seleziona l'intervallo di date desiderato.
5. Clicca sul link **Export** (solitamente situato nell'angolo in alto a destra della tabella delle transazioni) e seleziona **CSV**.
6. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Charles Schwab Portal - History tab and Export link] -->
</div>

## ⚠️ Errori Comuni

!!! warning "Non Modificare le Intestazioni"

    I file CSV di Schwab hanno un layout specifico con righe di metadati in fondo (che solitamente iniziano con "Transactions Total"). Il parser BRIM rileva e ignora automaticamente queste righe di metadati. Non rimuovere manualmente le righe finali del CSV.

## 📝 Note

- Supporta i parametri CSV in formato USA (strutture data MM/GG/AAAA e valuta USD).
- Analizza transazioni di acquisto/vendita, pagamenti di dividendi, reinvestimenti e commissioni di transazione.

## 🔗 Riferimento per Sviluppatori

→ [Charles Schwab Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
