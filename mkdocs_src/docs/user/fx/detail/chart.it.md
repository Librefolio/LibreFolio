# 📉 Grafico interattivo

Il cuore della pagina di dettaglio della coppia: lo storico dei tassi della coppia nel periodo selezionato.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Grafico di dettaglio FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vista Abs o %

Cambia vista con **Abs** / **%** nell'angolo in alto a sinistra del grafico; la pagina si apre in vista %.

- 📊 **%** — la variazione rispetto al primo giorno del periodo. Anche gli overlay partono da 0 %, così i loro movimenti si confrontano a colpo d'occhio.
- 📈 **Abs** — il tasso stesso, ad es. 1 EUR = 1.0845 USD.

---

## 🔍 Zoom, pan e periodo

| Azione | Desktop | Mobile |
|--------|---------|--------|
| **Zoom** | Rotellina del mouse | Pinch |
| **Pan** | Fai clic e trascina | Trascina con due dita (un dito scorre la pagina) |

- **Periodo**: le preimpostazioni da **1W** a **2Y**, **YTD** e **All**, oppure **Custom** (un numero di giorni, settimane, mesi o anni indietro rispetto a oggi); fai clic sulle date per sceglierle su un calendario. I due estremi devono essere giorni diversi: il giorno che clicchi per primo non può essere cliccato di nuovo, e una data inserita uguale all'altro estremo diventa rossa. Compaiono altre preimpostazioni quando c'è spazio nella barra degli strumenti. Le pagine della stessa scheda del browser condividono il periodo.
- Su un periodo lungo, il grafico raggruppa i tassi per settimana o mese e mostra un badge **Weekly** o **Monthly**: ingrandisci per ottenere i tassi giornalieri.
- Su uno schermo stretto, l'asse mostra meno date e più corte; la prima e l'ultima restano sempre.

??? info "📅 Storico più breve del periodo — quando il grafico inizia più tardi"

    Un banner mostra la data a partire dalla quale i dati sono disponibili. **Sync** può recuperare tassi più vecchi, se il provider li pubblica; altrimenti inseriscili nel [Editor dati](data-editor.md).

---

## 💬 Tooltip

Passa il mouse sul grafico, o toccalo su mobile, per vedere:

- 📅 la **data** (o la settimana o il mese, quando il grafico raggruppa i tassi);
- 💱 il **tasso** e il valore di ciascun overlay;
- 📊 la **variazione dall'inizio del periodo**: Δ e % in vista Abs, % in vista %;
- ⚠️ **Obsoleto: vecchio di N giorno/i** nei giorni senza un nuovo tasso, come i fine settimana e le festività bancarie.

---

## 🔁 Rolling Return {: #rolling-return }

Due pulsanti sopra il grafico scelgono cosa disegna: **Prezzi** (lo storico dei tassi, come sopra) e **Rolling Return**.

In **Rolling Return** ogni punto risponde a *quanto si è mosso il tasso negli ultimi N giorni?* Confronta il tasso di quel giorno con quello di N giorni di calendario prima. Esempio: su EUR → USD con la finestra **3M** (90 giorni), se il tasso è 1.0845 oggi ed era 1.0500 novanta giorni fa, il punto indica **+3.3 %**. Sopra lo zero la prima valuta acquistava più della seconda rispetto a N giorni prima; sotto lo zero, meno.

- 🗓️ **Finestra** — accanto ai due pulsanti: **1W**, **1M**, **3M**, **1Y** o **Custom** (un numero intero di settimane, mesi o anni). Finché non ne scegli una, la finestra è automatica: la preimpostazione più grande che rientra nel periodo visualizzato. La finestra può essere più lunga del periodo: LibreFolio legge i tassi più vecchi di cui ha bisogno. Il pulsante **?** apre la [stessa spiegazione](../../assets/detail/chart.md#rolling-return) fornita per gli asset, e l'anteprima di [Impostazioni grafico](../chart-settings.md#rolling-return-view) disegna anch'essa questa vista.
- 💱 **Confronta con un'altra coppia** — aggiungi una **coppia FX** nel pannello [Segnali](signals.md#data-comparison): ogni coppia confrontata disegna il proprio rolling return, con la stessa finestra. In questa modalità il pannello offre solo questi confronti; i tuoi altri segnali restano salvati e tornano con **Prezzi**.
- 🔄 **Direzione** — il rendimento segue la direzione mostrata dalla pagina, EUR → USD o USD → EUR.
- 📏 ✏️ I pulsanti **Misura** e **Modifica tassi** sono nascosti: lavorano sui tassi, quindi appartengono a **Prezzi**.
- 💾 **Memorizzato** — la modalità e la finestra vengono salvate con le impostazioni grafico di questa coppia, in questo browser. La scheda della coppia nell'elenco FX le condivide: una scheda in **Rolling Return** apre la pagina in quella modalità, e la pagina si riapre nella modalità in cui l'hai lasciata. Il ritorno a **Prezzi** è immediato.

Cambiando il periodo, la finestra, la direzione o le coppie confrontate, oppure facendo clic su **Refresh**, il rendimento viene ricalcolato e uno spinner resta visibile finché non arriva la risposta. Se non è possibile calcolare alcun rendimento, il grafico mostra il motivo al posto della curva.

---

## 🧰 Pulsanti del grafico

- 📏 **Misura** — vedi [Misure](measures.md). Solo **Prezzi**.
- ✏️ **Modifica tassi** — vedi [Editor dati](data-editor.md). Solo **Prezzi**.
- ⚙️ **Estetica** — colori, riempimento, griglia e intervalli degli assi, come in [Impostazioni grafico](../chart-settings.md).
- 📊 Il pannello **Segnali** sopra il grafico — vedi [Segnali](signals.md).

---

## 🔗 Correlati

- ⚙️ **[Impostazioni grafico](../chart-settings.md)** — Aspetto del grafico e segnali overlay
- 📈 **[Segnali](signals.md)** — Indicatori tecnici sul grafico
