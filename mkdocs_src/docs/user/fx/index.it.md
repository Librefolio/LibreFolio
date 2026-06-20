# 💱 FX Rates (Cambio Valute)

LibreFolio include un sistema di gestione **Foreign Exchange (FX)** completo. Ti permette di monitorare i tassi di cambio tra qualsiasi coppia di valute, con sincronizzazione automatica da fonti ufficiali di banche centrali.

---

## 📋 La Pagina Elenco FX

Naviga verso **FX Rates** dalla barra laterale per visualizzare tutte le tue coppie di valute configurate:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista Griglia a Schede" alt="Pagina Elenco FX (Griglia)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista Tabella Dati" alt="Pagina Elenco FX (Tabella)">
</div>

Ogni coppia di valute viene visualizzata con i seguenti dettagli:

- 🔀 **Layout Griglia / Tabella**: Usa l'interruttore per passare da una griglia visiva di schede a una tabella dati compatta. La selezione viene salvata nel `localStorage` del tuo browser per le sessioni future.
- 🏷️ La **coppia di valute** con le bandiere (es. 🇪🇺 EUR → 🇺🇸 USD)
- 📈 Il **tasso di cambio più recente** e il trend del prezzo
- 🏛️ Il **provider di dati attivo** (ECB, FED, BOE, SNB o MANUAL)
- 📊 Un **grafico sparkline** che mostra l'andamento del tasso negli ultimi 30 giorni
- 🖱️ **Menu Contestuale**: Fai clic con il tasto destro su qualsiasi riga nel layout a tabella per azioni rapide (Modifica, Sincronizza, Elimina)

Puoi **filtrare** per valuta per trovare rapidamente una coppia specifica:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Elenco FX Filtrato" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 Prossimi passi

- ➕ **[Aggiungere una Coppia](add-pair.md)** — Come creare una nuova coppia di valute con percorsi diretti o a catena
- 🔄 **[Sincronizzazione](sync.md)** — Sincronizzazione automatica e manuale dai provider
- 📊 **[Pagina Dettaglio Coppia](detail/index.md)** — Grafico interattivo, misure del segnale, editor dati, configurazione del provider
- ⚙️ **[Impostazioni Grafico](chart-settings.md)** — Personalizza l'aspetto del grafico e le sovrapposizioni dei segnali
- 🔌 **[Provider](providers/index.md)** — Fonti di banche centrali supportate per i tassi FX (ECB, FED, BOE, SNB)
