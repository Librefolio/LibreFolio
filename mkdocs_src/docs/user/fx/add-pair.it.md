# ➕ Aggiungere una Coppia di Valute

Per aggiungere una nuova coppia di valute alla tua dashboard FX:

1. Clicca su **"Add Pair"** nella pagina dell'elenco FX
2. Seleziona le **due valute** utilizzando il menu a tendina di ricerca
3. Il sistema scopre automaticamente i **percorsi dati** disponibili — sia i percorsi diretti che quelli a catena
4. Seleziona il percorso preferito e clicca su **Confirm** — la coppia viene creata e la sincronizzazione dei dati inizia automaticamente

---

## 🛤️ Percorsi di Conversione (Diretti e a Catena)

Quando selezioni una valuta di base e una di quotazione, LibreFolio interroga tutti i provider installati per scoprire i migliori percorsi di tasso di cambio disponibili.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Percorsi Diretti" alt="Aggiungi Coppia — Percorsi Diretti">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Percorsi a Catena (Multi-hop)" alt="Aggiungi Coppia — Percorsi a Catena">
</div>

### 🔗 Percorsi Diretti
Se un provider supporta direttamente i tassi di cambio tra entrambe le valute (ad esempio, la BCE che fornisce i tassi per EUR 🇪🇺 / USD 🇺🇸), il sistema lo visualizza come un percorso diretto.

### 🔀 Percorsi a Catena
Per coppie esotiche (ad esempio, RON 🇷🇴 / JPY 🇯🇵) in cui nessuna singola banca centrale pubblica i tassi direttamente, il sistema costruisce automaticamente **catene di conversione** — percorsi multi-step attraverso valute intermedie (tipicamente EUR 🇪🇺 o USD 🇺🇸).

!!! example "Esempio di Catena"

    **RON 🇷🇴 → JPY 🇯🇵** via BCE:

    1. RON 🇷🇴 → EUR 🇪🇺 (la BCE fornisce RON 🇷🇴 / EUR 🇪🇺)
    2. EUR 🇪🇺 → JPY 🇯🇵 (la BCE fornisce EUR 🇪🇺 / JPY 🇯🇵)

    Il tasso finale è calcolato moltiplicando i tassi intermedi.

---

## 🧭 Come Funziona la Scoperta dei Percorsi

Quando selezioni due valute, LibreFolio interroga tutti i provider installati per trovare:

- 🔗 **Percorsi diretti**: un singolo provider che copre entrambe le valute
- 🔀 **Percorsi a catena**: due o più provider che insieme possono collegare le valute attraverso una valuta intermedia (ad esempio, EUR 🇪🇺)

Ogni percorso mostra:

- 🏛️ Il nome e l'icona del **provider**
- ➡️ La **direzione** (base → quotazione)
- 🔢 Per le catene: la **valuta intermedia** e il **numero di hop**

Puoi scegliere qualsiasi percorso disponibile in base alla tua preferenza per la fonte dei dati, il periodo di copertura o la frequenza di aggiornamento.

!!! info "Per i Curiosi: Dietro le Quinte"

    Se sei interessato ai dettagli matematici su come vengono calcolate e instradate le catene di conversione multi-hop, puoi leggere la documentazione per sviluppatori: [FX Configuration & Routing](../../developer/backend/fx/configuration.md) e [FX Chain Algorithm](../../developer/frontend/fx-chain-algorithm.md). 
 
    *Nota: Questa documentazione tecnica è rivolta solo agli sviluppatori e non è necessaria per utilizzare questa funzionalità.*
