# 💱 Tassi FX (Cambio valuta)

LibreFolio converte i tuoi importi tra valute con i tassi conservati qui. Ogni coppia FX
scarica i suoi tassi da una banca centrale (ECB, FED, BOE o SNB), oppure conserva i tassi che
inserisci tu stesso.

---

## 📋 La pagina dell'elenco FX

Apri **Tassi FX** dalla barra laterale per vedere le tue coppie FX:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista griglia a schede" alt="Pagina elenco FX (Griglia)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista tabella dati" alt="Pagina elenco FX (Tabella)">
</div>

Ogni coppia FX mostra le sue bandiere (ad es. 🇪🇺 EUR → 🇺🇸 USD), il suo **ultimo tasso**, la variazione
nel periodo selezionato e un mini grafico. Un badge ✏️ **Manuale** contrassegna le coppie FX senza un
provider. Fai clic su una coppia FX per aprire la sua [pagina di dettaglio](detail/index.md).

### 🔀 Schede o tabella

- L'interruttore di visualizzazione accanto a **Aggiungi coppia** passa tra schede e tabella; LibreFolio
  ricorda la tua scelta.
- Nella tabella, le colonne **Δ** mostrano la variazione nell'ultimo giorno, nel periodo e, sui
  periodi lunghi, da 1W a 5Y. **Colonne** aggiunge quelle nascoste, come i **Provider** di ogni
  coppia FX.
- Seleziona le righe per agire su più coppie FX contemporaneamente, oppure fai clic con il tasto destro
  su una riga.

### 🔍 Filtra per valuta

Scegli una valuta in **Filtra valuta** per elencare solo le sue coppie FX, e una **Seconda valuta** per
restringere l'elenco a una coppia FX; ✕ cancella entrambe.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Elenco FX filtrato" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Azioni della pagina e della coppia FX

- Il selettore **periodo** in alto imposta l'intervallo di ogni grafico e variazione; nella vista a
  schede, **Abs** / **%** mostra tutte le schede come tassi o come variazione %.
- **Sincronizza tutto** scarica i nuovi tassi ([Sincronizzazione](sync.md)); **Ricarica tutto** legge
  di nuovo quelli memorizzati. **Impostazioni** imposta l'aspetto di ogni scheda ([Impostazioni
  grafico](chart-settings.md)).
- Su una scheda, ⇄ inverte la direzione mostrata (USD → EUR invece di EUR → USD); i pulsanti in basso
  aprono le sue impostazioni grafico, **Sincronizza** o **Ricarica**, oppure lo eliminano.

!!! warning "Eliminare una coppia FX elimina i suoi tassi"

    L'eliminazione di una coppia FX rimuove le impostazioni del provider **e tutti i suoi tassi memorizzati**, dopo la conferma.

---

## 🔮 Cosa c'è dopo?

- ➕ **[Aggiungere una coppia FX](add-pair.md)** — Crea una coppia FX con un percorso diretto o a catena
- 🔄 **[Sincronizzazione](sync.md)** — Scarica i tassi, manualmente o secondo una pianificazione
- 📊 **[Pagina di dettaglio della coppia FX](detail/index.md)** — Grafico, segnali, misure, editor dei tassi e provider
- ⚙️ **[Impostazioni grafico](chart-settings.md)** — Aspetto del grafico e segnali sovrapposti
- 🔌 **[Provider](providers/index.md)** — Le banche centrali da cui LibreFolio legge (ECB, FED, BOE, SNB)
