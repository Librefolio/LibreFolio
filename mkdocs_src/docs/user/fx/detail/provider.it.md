# 🔌 Configurazione Provider

Ogni coppia di valute in LibreFolio è supportata da uno o più **provider di dati** — banche centrali che forniscono i dati sui tassi di cambio. La Configurazione Provider consente di visualizzare e modificare quali provider vengono utilizzati per una coppia specifica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configurazione Provider" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Come Accedere

Fai clic sul pulsante **Provider** (⚙️) nella barra degli strumenti del grafico nella pagina dei Dettagli della Coppia. Questo aprirà la finestra modale di configurazione del provider che mostra l'attuale configurazione del percorso.

---

## 📋 Cosa Visualizzi

La finestra modale mostra:

- 🛤️ **Percorsi attuali** — I provider di dati attivi per questa coppia, in ordine di priorità
- 🔀 **Tipo di Percorso** — Se si tratta di un percorso **Direct** (provider singolo) o di un percorso **Chain** (multi-hop attraverso una valuta intermedia)
- 🏛️ **Dettagli Provider** — Nome, icona e valuta di base di ogni provider nel percorso

---

## 🔧 Cambiare Provider

È possibile configurare **uno o più** provider di dati per ogni coppia. Più provider agiscono come una **catena di fallback** — se il provider primario fallisce, il sistema prova automaticamente il successivo.

Per cambiare o aggiungere provider:

1. Apri la finestra modale di Configurazione Provider
2. **Rimuovi** il percorso attuale, se necessario
3. **Aggiungi un nuovo percorso** — il sistema scoprirà i percorsi disponibili (come quando si [aggiunge una nuova coppia](../add-pair.md))
4. **Riordina** i percorsi per impostare le priorità (tramite drag & drop o pulsanti a freccia)
5. Fai clic su **Salva** — la sincronizzazione successiva recupererà i dati dal provider disponibile con la priorità più alta

---

## 🔢 Priorità e Fallback

Quando più percorsi sono configurati per una coppia:

- I percorsi vengono provati **in ordine di priorità** (in alto = priorità massima)
- Se il provider primario fallisce (timeout, errore API), il sistema effettua automaticamente il fallback al percorso successivo
- È possibile **riordinare** i percorsi per cambiare le priorità

!!! example "Esempio di Fallback"

    EUR/USD configurato con:

    1. **ECB** (primario) — Banca Centrale Europea
    2. **FED** (fallback) — Federal Reserve

    Se l'API di ECB non è raggiungibile durante la sincronizzazione, il sistema utilizzerà automaticamente FED.

---

## 📚 Correlati

- ➕ **[Aggiungere una Coppia](../add-pair.md)** — Scoperta completa dei percorsi (percorsi Direct + Chain)
- 🔄 **[Sincronizzazione](../sync.md)** — Come la sincronizzazione utilizza i provider configurati
- 🔌 **[Provider FX](../providers/index.md)** — Guida per l'utente e dettagli su ciascun provider (ECB, FED, BOE, SNB)

!!! tip "🔗 Come vengono calcolati i percorsi chain"

    Per l'algoritmo matematico dietro le catene di conversione multi-hop, consulta [FX Chain Algorithm](../../../developer/frontend/fx-chain-algorithm.md).
