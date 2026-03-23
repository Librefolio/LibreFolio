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

1. Recupera i tassi dall'API del provider configurato (BCE, FED, BOE, SNB, ecc.)
2. **Sovrascrive** i dati esistenti nell'intervallo di date scaricato con i valori del provider — il provider è considerato la fonte autorevole
3. Aggiunge nuovi punti per le date non ancora presenti nel database
4. Se il provider primario fallisce, il sistema passa automaticamente al provider di ripiego

Dopo la sincronizzazione, vengono mostrati il numero di **punti scaricati** e quanti erano **effettivamente nuovi** (non già presenti nel database).

!!! warning "Il provider è autorevole"

    Risincronizzare una coppia sovrascriverà qualsiasi valore modificato manualmente nell'intervallo sincronizzato. Se desideri preservare le modifiche manuali, configura la coppia con il provider MANUAL (nessuna fonte di dati automatica).

!!! info "Precisione nelle conversioni a catena"

    Quando si usano percorsi a catena (es. RON → EUR → JPY), ogni conversione intermedia introduce un minimo errore di arrotondamento. Sebbene trascurabile nella maggior parte dei casi, i tassi convertiti tramite catena possono differire leggermente dalle quotazioni dirette di mercato.

---

## 🌐 Flusso dei Dati FX

Per utenti avanzati: LibreFolio utilizza un **sistema di routing** sofisticato per i dati FX. Ogni coppia di valute può avere più fornitori configurati con priorità e catene di ripiego.

Ciò significa:

- 🔄 Se il tuo fornitore primario (es. BCE) non è disponibile, il sistema passa automaticamente al fornitore di ripiego (es. FED)
- 🔀 Le coppie esotiche utilizzano catene con più passaggi attraverso valute intermedie (es. RON → EUR → JPY)
- ⚙️ Puoi personalizzare quale fornitore utilizzare per ogni coppia

Per l'elenco dei fornitori supportati, consulta l'[Elenco Fornitori FX](../../developer/backend/fx/providers_list.md).

Per i dettagli tecnici sull'algoritmo di instradamento e la configurazione, consulta la documentazione per sviluppatori: [Configurazione e Instradamento FX](../../developer/backend/fx/configuration.md).
