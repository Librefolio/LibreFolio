# 💱 Tassi FX (Cambio valuta)

LibreFolio converte i tuoi importi tra valute utilizzando i tassi conservati qui. Ogni coppia di valute
scarica i propri tassi da una banca centrale (ECB, FED, BOE o SNB), oppure conserva i tassi che inserisci tu stesso.

---

## 📋 La pagina elenco FX

Apri **Tassi FX** dalla barra laterale per vedere le tue coppie di valute:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista a griglia di schede" alt="Pagina elenco FX (griglia)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista tabella dati" alt="Pagina elenco FX (tabella)">
</div>

Ogni coppia mostra le proprie bandiere (ad es. 🇪🇺 EUR → 🇺🇸 USD), il suo **tasso più recente**, la variazione nel
periodo selezionato e un mini grafico. Quando il grafico raggruppa i tassi per settimana o per mese perché l'area
del grafico è troppo stretta per così tanti giorni, un badge **Settimanale** o **Mensile** in alto a sinistra lo segnala, come nella
[pagina di dettaglio](detail/chart.md). Un badge ✏️ **Manuale** contrassegna le coppie senza un provider. Fai clic su una coppia per aprire
la sua [pagina di dettaglio](detail/index.md).

### 🔀 Schede o tabella

- L'interruttore di visualizzazione accanto a **Aggiungi coppia** alterna schede e tabella; LibreFolio ricorda la tua
  scelta.
- Nella tabella, le colonne **Δ** mostrano la variazione nell'ultimo giorno, nel periodo e, sui periodi lunghi,
  da 1 settimana a 5 anni. **Colonne** aggiunge quelle nascoste, come i **Provider** di ciascuna coppia.
- Seleziona le righe per intervenire su più coppie contemporaneamente, oppure fai clic con il pulsante destro su una riga.

### 🔍 Filtra per valuta

Scegli una valuta in **Filtra valuta** per elencare solo le sue coppie, e una **Seconda valuta** per restringere
l'elenco a una sola coppia; ✕ cancella entrambe.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Elenco FX filtrato" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Azioni della pagina e delle coppie

- Il selettore del **periodo** in alto imposta l'intervallo di ogni grafico e di ogni variazione; nella visualizzazione a schede,
  l'icona della linea del grafico (tooltip **Mostra assoluto**), **%** e l'icona del calendario (**Rendimento rolling**) mostrano tutte le schede come tassi, come variazione % o come rendimento rolling. L'elenco si apre su **Assoluto**; una volta scelta una visualizzazione, viene ricordata per te in questo browser.
- Il pulsante di visualizzazione di una scheda cicla **%** → **Rendimento rolling** → **Assoluto** e mostra la visualizzazione verso cui passa. La
  scheda mantiene la propria scelta tra un ricaricamento e l'altro finché non modifichi la barra degli strumenti, che reimposta ogni scheda.
  Su **Rendimento rolling** una scheda traccia il rendimento rolling del tasso nel modo in cui la scheda mostra la coppia
  (invertita con ⇄: il rendimento del tasso invertito), e sopra di esso i rendimenti rolling delle coppie FX
  confrontate in quella scheda. Il tasso e la sua variazione in alto restano invariati e, con una cronologia troppo breve, la scheda mostra un breve messaggio al posto del grafico. La finestra mobile è quella impostata in
  [Impostazioni grafico](chart-settings.md).
- Una scheda traccia i confronti salvati nelle sue [Impostazioni grafico](chart-settings.md), con un'altra coppia FX
  o con un asset. La linea di un asset è il suo prezzo nella valuta dell'asset stesso, quindi confrontala nella
  visualizzazione **%**; i prezzi vengono caricati una sola volta per tutte le schede che confrontano un asset.
- **Sincronizza tutto** scarica i nuovi tassi ([Sincronizzazione](sync.md)); **Ricarica tutto** legge di nuovo quelli
  memorizzati. **Impostazioni** imposta l'aspetto di ogni scheda ([Impostazioni grafico](chart-settings.md)). Passa
  con il mouse su uno dei tre per mezzo secondo per leggere cosa fa.
- Su una scheda, ⇄ inverte la direzione mostrata (USD → EUR invece di EUR → USD); i pulsanti in basso
  aprono le sue impostazioni grafico, eseguono **Sincronizza** o **Ricarica**, oppure la eliminano.

!!! warning "Eliminare una coppia elimina i suoi tassi"

    Eliminare una coppia rimuove le impostazioni del provider **e tutti i tassi memorizzati**, una volta confermata l'operazione.

---

## 🔮 Cosa c'è dopo?

- ➕ **[Aggiunta di una coppia](add-pair.md)** — Crea una coppia con un percorso diretto o concatenato
- 🔄 **[Sincronizzazione](sync.md)** — Scarica i tassi, manualmente o in base a una pianificazione
- 📊 **[Pagina di dettaglio della coppia](detail/index.md)** — Grafico, segnali, misure, editor dei tassi e provider
- ⚙️ **[Impostazioni grafico](chart-settings.md)** — Aspetto del grafico e segnali sovrapposti
- 🔌 **[Provider](providers/index.md)** — Le banche centrali da cui LibreFolio legge (ECB, FED, BOE, SNB)
