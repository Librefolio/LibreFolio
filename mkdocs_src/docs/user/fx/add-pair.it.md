# ➕ Aggiungere una coppia di valute

Una coppia indica a LibreFolio da dove proviene il tasso di cambio tra due valute: un provider di banca centrale, una catena di provider o tassi inseriti manualmente.

Clicca su **Add Pair** nella [pagina FX](index.md). La stessa finestra si apre dalla dashboard, dalla pagina di un asset e dal passaggio FX dell'allocatore PAC.

---

## 🧭 Aggiungere una coppia passo per passo

### 💱 Passaggio 1: scegli le due valute

In **Add New Currency Pair**, scegli la **Base Currency** e la **Quote Currency**. Ogni elenco nasconde le valute già abbinate all'altra, quindi una coppia non può essere aggiunta due volte.

### 🛤️ Passaggio 2: scegli un percorso

Clicca su **Add conversion route** per vedere tutti i modi in cui i provider possono produrre questo tasso:

- 🔗 **Conversione diretta (1 passaggio)** — un provider pubblica la coppia;
- 🔀 **Conversione a catena** — passa attraverso altre valute, raggruppate per numero di passaggi;
- 🚫 **Non utilizzabile** — provider che non riescono a raggiungere questa coppia.

Filtra con la casella di ricerca (provider, valuta o paese), poi clicca su un percorso per aggiungerlo.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Percorsi diretti" alt="Aggiungi coppia — Percorsi diretti">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Percorsi a catena (multi-hop)" alt="Aggiungi coppia — Percorsi a catena">
</div>

??? tip "🛟 Percorsi di backup — quando ne aggiungi più di uno"

    LibreFolio usa prima il percorso **#1** e prova il **#2** se fallisce durante una sincronizzazione, e così via. Trascina i percorsi per riordinarli; 🗑️ ne rimuove uno e ⚠️ mostra una nota del suo provider.

??? note "🔀 Crea anche le coppie intermedie — quando scegli un percorso a catena"

    Spunta **Also create intermediate pairs** per salvare ogni passaggio come coppia a sé stante. Puoi poi sincronizzare ogni passaggio separatamente e convertire anche nella valuta intermedia: una catena memorizza solo il tasso della propria coppia.

??? note "✏️ Nessun percorso — solo tassi manuali"

    Puoi salvare senza un percorso e inserire poi i tassi manualmente nell'[editor dati](detail/data-editor.md) della coppia.

### 💾 Passaggio 3: salva

Clicca su **Save Configuration**; la finestra si chiude subito.

- **Con un provider**, LibreFolio scarica l'**intera cronologia** della coppia fino a oggi, qualunque periodo mostri la pagina, comprese le coppie intermedie. Un messaggio riporta il risultato, in verde solo se tutto ha funzionato.
- **Senza un provider**, un messaggio conferma che la coppia è stata creata.

Clicca sul nome della coppia nel messaggio per aprirne la pagina.

---

## 🛤️ Percorsi diretti e a catena

Un **percorso diretto** usa un unico provider che pubblica entrambe le valute, come la BCE per EUR 🇪🇺 / USD 🇺🇸. Quando nessuna banca centrale pubblica la coppia, un **percorso a catena** moltiplica i tassi dei suoi passaggi. RON 🇷🇴 / USD 🇺🇸, per esempio, va RON → EUR → USD, entrambi i passaggi dalla BCE, che pubblica EUR/RON e EUR/USD:

$$
r_{\text{RON}\to\text{USD}} = r_{\text{RON}\to\text{EUR}} \times r_{\text{EUR}\to\text{USD}}
$$

- Una catena ha un tasso solo nei giorni in cui **ogni passaggio** ne ha uno.
- Se un passaggio fallisce durante una sincronizzazione, l'intera catena fallisce: le catene più corte sono più affidabili.
- Il tasso di una catena può discostarsi leggermente da una quotazione diretta di mercato.

---

## 🔗 Voci correlate

- 🔄 **[Sincronizzazione](sync.md)** — Scarica di nuovo i tassi più tardi
- 🔌 **[Configurazione provider](detail/provider.md)** — Cambia i percorsi di una coppia dopo averla creata
- 🧑‍💻 Per gli sviluppatori: **[Configurazione e routing FX](../../developer/backend/fx/configuration.md)** e **[Algoritmo della catena FX](../../developer/frontend/fx-chain-algorithm.md)**
