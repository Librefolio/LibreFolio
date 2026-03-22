# 🔄 Sincronizzazione Valute

Una volta configurata una coppia di valute con un fornitore di dati, LibreFolio può **sincronizzare automaticamente** i tassi di cambio da fonti ufficiali delle banche centrali.

---

## 🔄 Sincronizza Tutto

Dalla pagina dell'elenco FX, utilizza il pulsante **Sincronizza Tutto** per sincronizzare tutte le coppie configurate in una volta:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progresso Sincronizzazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La finestra di dialogo della sincronizzazione mostra:

- 📊 **Progresso** per ogni coppia in fase di sincronizzazione
- ✅ **Indicatori di stato** (successo, errore, ignorato)
- 🆕 Conteggio dei **nuovi dati** per ogni coppia

---

## 🎯 Sincronizzazione Coppia Singola

Puoi anche sincronizzare una singola coppia dalla sua [pagina dei dettagli](detail/index.md) utilizzando il pulsante di sincronizzazione. Questo è utile quando desideri aggiornare solo una coppia specifica.

---

## ⚙️ Come Funziona la Sincronizzazione

Il processo di sincronizzazione:

1. Recupera i tassi dall'API del fornitore selezionato (BCE, FED, BOE, SNB, ecc.)
2. Memorizza i nuovi dati nel database locale
3. Ignora le date già esistenti (nessun duplicato)
4. Se il fornitore primario fallisce, il sistema passa automaticamente al fornitore di ripiego

!!! tip "Nessun dato duplicato"
 Risincronizzare una coppia è sempre sicuro — i dati esistenti non vengono mai sovrascritti o duplicati.

---

## 🌐 Flusso dei Dati FX

Per utenti avanzati: LibreFolio utilizza un **sistema di routing** sofisticato per i dati FX. Ogni coppia di valute può avere più fornitori configurati con priorità e catene di ripiego.

Ciò significa:

- 🔄 Se il tuo fornitore primario (es. BCE) non è disponibile, il sistema passa automaticamente al fornitore di ripiego (es. FED)
- 🔀 Le coppie esotiche utilizzano catene con più passaggi attraverso valute intermedie (es. RON → EUR → JPY)
- ⚙️ Puoi personalizzare quale fornitore utilizzare per ogni coppia

Per l'elenco dei fornitori supportati, consulta l'[Elenco Fornitori FX](../../developer/backend/fx/providers_list.md).

Per i dettagli tecnici sull'algoritmo di instradamento e la configurazione, consulta la documentazione per sviluppatori: [Configurazione e Instradamento FX](../../developer/backend/fx/configuration.md).
