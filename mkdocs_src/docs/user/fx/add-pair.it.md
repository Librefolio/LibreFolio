# ➕ Aggiungere una Coppia di Valute

Per aggiungere una nuova coppia di valute alla tua dashboard FX:

1. Clicca su **"Add Pair"** nella pagina della lista FX
2. Seleziona le **due valute** utilizzando il menu a tendina di ricerca
3. Il sistema scopre automaticamente i **percorsi dati** disponibili — sia percorsi diretti che a catena
4. Seleziona il percorso preferito e clicca su **Confirm** — la coppia viene creata e la sincronizzazione dei dati inizia automaticamente

---

## 🔗 Percorsi Diretti

Se un provider supporta entrambe le valute direttamente (ad esempio, ECB per EUR→USD), visualizzerai la sezione **Direct Routes**:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Aggiungi Coppia — Percorsi Diretti" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Percorsi a Catena

Per le coppie esotiche (ad esempio, RON→JPY) in cui nessun singolo provider copre entrambe le valute, il sistema costruisce delle **catene di conversione** — percorsi multi-step attraverso valute intermedie:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Aggiungi Coppia — Percorsi a Catena" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Chain Example"

    **RON → JPY** via ECB:

    1. RON → EUR (ECB fornisce RON/EUR)
    2. EUR → JPY (ECB fornisce EUR/JPY)

    Il tasso finale è calcolato moltiplicando i tassi intermedi.

---

## 🧭 Come Funziona la Scoperta dei Percorsi

Quando selezioni due valute, LibreFolio interroga tutti i provider installati per trovare:

- 🔗 **Percorsi diretti**: un singolo provider che copre entrambe le valute
- 🔀 **Percorsi a catena**: due o più provider che insieme possono collegare le valute attraverso una valuta intermedia (ad esempio, EUR)

Ogni percorso mostra:

- 🏛️ Il nome e l'icona del **provider**
- ➡️ La **direzione** (base → quotazione)
- 🔢 Per le catene: la **valuta intermedia** e il **numero di passaggi**

Puoi scegliere qualsiasi percorso disponibile in base alla tua preferenza per la sorgente dei dati, il periodo di copertura o la frequenza di aggiornamento.

Per i dettagli tecnici sull'algoritmo di routing, consulta la documentazione per sviluppatori: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
