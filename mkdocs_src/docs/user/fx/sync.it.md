# 🔄 Sincronizzazione FX

Una volta che una coppia di valute è stata configurata con un provider di dati, LibreFolio può **sincronizzare automaticamente** i tassi di cambio da fonti ufficiali di banche centrali.

---

## 🔄 Sincronizza Tutto

Dalla pagina dell'elenco FX, utilizza il pulsante **Sincronizza Tutto** per sincronizzare tutte le coppie configurate contemporaneamente:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progresso Sincronizzazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il modale di sincronizzazione mostra:

- 📊 **Progresso** per ogni coppia in fase di sincronizzazione
- ✅ Indicatori di **Stato** (successo, errore, saltato)
- 🆕 Conteggio dei **Nuovi punti dati** per ogni coppia

---

## 🎯 Sincronizzazione Singola Coppia

È possibile sincronizzare anche una singola coppia dalla sua [pagina di dettaglio](detail/index.md) utilizzando il pulsante di sincronizzazione. Questo è utile quando si desidera aggiornare solo una coppia specifica.

---

## ⚙️ Come Funziona la Sincronizzazione

Il processo di sincronizzazione:

1. Recupera i tassi dall'API del provider configurato (ECB, FED, BOE, SNB, ecc.)
2. **Sovrascrive** i punti dati esistenti nell'intervallo di date scaricato con i valori del provider — il provider è trattato come la fonte autorevole
3. Aggiunge nuovi punti dati per le date non ancora presenti nel database
4. Se il provider primario fallisce, il sistema effettua il fallback al provider successivo configurato

Dopo la sincronizzazione, vedrai il numero di **punti scaricati** e quanti di questi erano **effettivamente nuovi** (non precedentemente presenti nel database).

!!! warning "Il provider è autorevole"

    La risincronizzazione di una coppia sovrascriverà qualsiasi valore modificato manualmente nell'intervallo di date sincronizzato. Se è necessario conservare le modifiche manuali, considera l'utilizzo di una coppia configurata con il provider MANUAL (nessuna fonte dati automatica).

!!! info "Precisione della conversione a catena"

    Quando si utilizzano percorsi a catena (es. RON → EUR → JPY), ogni conversione intermedia introduce un minimo errore di arrotondamento. Sebbene trascurabile per la maggior parte degli scopi, tieni presente che i tassi convertiti a catena potrebbero differire leggermente dalle quotazioni di mercato dirette.

---

## 🌐 Catene di supply dei dati

Per utenti avanzati: LibreFolio utilizza un sofisticato **sistema di routing** per i dati FX. Ogni coppia di valute può avere più provider configurati con priorità e catene di fallback.

Ciò significa che:

- 🔄 Se il provider primario (es. ECB) è offline, il sistema effettua il fallback al provider successivo (es. FED)
- 🔀 Le coppie esotiche utilizzano catene multi-step attraverso valute intermedie (es. RON → EUR → JPY)
- ⚙️ Puoi personalizzare quale provider utilizzare per ogni coppia

Per l'elenco dei provider supportati, consulta la [Lista Provider FX](../../developer/backend/fx/providers_list.md).

Per i dettagli tecnici sull'algoritmo di routing e sulla configurazione, consulta la documentazione per sviluppatori: [Configurazione e Routing FX](../../developer/backend/fx/configuration.md).
