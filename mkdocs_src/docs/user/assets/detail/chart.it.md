# 📈 Grafico interattivo

Il grafico è il cuore della pagina dell'asset: lo storico dei prezzi, ovvero quanto si è mosso il prezzo su una finestra mobile. Scorri per ingrandire, trascina per spostarti e passa il mouse su un punto per vederne i valori.

_Ultimo aggiornamento: 2026-10-22_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Grafico dei prezzi dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Prezzi o rendimento mobile {: #primary-modes }

I due pulsanti sopra il grafico scelgono cosa disegnare:

- **Prezzi** — lo storico dei prezzi, con gli [eventi](events.md) dell'asset come marcatori.
- **Rendimento mobile** — per ogni data, la variazione del prezzo su una finestra che scegli ([sotto](#rolling-return)).

La pagina si apre nella vista che la scheda di questo asset ha nella [pagina Asset](../index.md): **Abs** o **%** aprono **Prezzi** in quella vista, **Rendimento mobile** apre **Rendimento mobile**. Cambia qui la modalità, oppure **Abs** e **%** sotto **Prezzi**, e quella diventa la vista dell'asset: la sua scheda e la tua prossima visita si apriranno così. Viene memorizzata in questo browser, per il tuo utente, insieme alle impostazioni grafico; l'interruttore della lista riporta ogni scheda, e quindi ogni pagina di dettaglio, alla propria vista.

### 🗓️ Finestra del rendimento mobile {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Grafico dell'asset in modalità Rendimento mobile con la finestra 1Y e un asset di confronto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Questa vista risponde alla domanda *quanto si è mosso il prezzo sulla finestra, a ogni data?* Ogni punto confronta la chiusura di quel giorno con la chiusura esattamente $N$ giorni di calendario prima:

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

dove $P$ è l'ultima chiusura nota in quel giorno, nella valuta del grafico → [Rendimento mobile su giorni di calendario](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Scegli $N$ con il controllo **Finestra** accanto ai due pulsanti:

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 e 365 giorni.
- **Personalizzato** — un numero intero con **W**, **M** o **Y**, dove W, M e Y valgono rispettivamente 7, 30 e 365 giorni: `3M` è 90 giorni.
- **?** apre questa sezione del manuale.

La finestra può essere più lunga dell'intervallo di date visualizzato: LibreFolio legge i prezzi più vecchi di cui ha bisogno. È la stessa della scheda dell'asset: quella scelta per questo asset o, finché non ne scegli una, una automatica, il preset più ampio che si adatta alle date visualizzate (per circa 3 mesi si usa 3M, per un anno o più 1Y, per meno di una settimana 1W). Una finestra scelta qui viene mantenuta per questo asset, in questo browser.

Come leggerlo:

- **Sopra zero**, il prezzo è più alto rispetto al prezzo di $N$ giorni prima; **sotto zero**, è più basso.
- **Passa il mouse su un punto**: ↩ indica la data con cui viene confrontato; 📅 e 💱 indicano le date del prezzo e dei tassi di cambio effettivamente usati, quando uno dei due è più vecchio.
- **[Confronti tra asset](signals.md#data-comparison)** diventano anch'essi rendimenti mobili, con la stessa finestra e la stessa valuta.
- **Solo prezzo**: dividendi, interessi e le tue transazioni non sono inclusi.

??? note "🧩 Lacune e linee corte — quando lo storico è incompleto"

    Un punto resta vuoto, mai stimato, quando manca uno dei suoi due prezzi o quando uno dei due non è positivo. Ogni linea inizia dalla prima data in cui può essere calcolata, quindi un asset recente o un tasso di cambio mancante accorcia solo la propria linea, e un prezzo mancante più avanti lascia una lacuna. Quando è calcolabile solo una parte dell'intervallo, una nota sotto il grafico lo segnala; quando non è calcolabile nulla, un messaggio sostituisce il grafico.

---

## 🎛️ Scegli cosa mostra il grafico

### 📅 Intervallo di date

L'intervallo di date nella barra degli strumenti della pagina imposta le date sullo schermo: **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **Tutto** o **Personalizzato**, un numero di giorni, settimane, mesi o anni indietro da oggi; clicca su una data per scegliere i due estremi su un calendario. I due estremi devono essere giorni diversi: il giorno che clicchi per primo non può essere cliccato di nuovo, e una data digitata uguale all'altro estremo diventa rossa. Con spazio libero sulla barra compaiono altri preset (3Y, 5Y, 10Y, WTD, MTD, QTD). L'intervallo che scegli ti segue nelle pagine dashboard, broker, asset e FX della stessa scheda del browser.

Su un intervallo lungo il grafico può raggruppare i giorni in settimane o mesi per restare leggibile: un badge **Settimanale** o **Mensile** in alto a sinistra lo indica.

### 💱 Converti in un'altra valuta

**Converti in**, accanto al prezzo, mostra il grafico in un'altra valuta, con una linea 💱 tratteggiata per il prezzo nella valuta dell'asset. Il menu elenca le valute raggiungibili dalle tue coppie FX; **Crea forex…** in fondo aggiunge una coppia mancante. Anche i rendimenti mobili vengono calcolati nella valuta scelta.

??? note "💱 Quando manca un tasso di cambio"

    Un banner sopra il grafico indica la coppia, con una scorciatoia per crearla o aprirla. **Sync** della pagina scarica i tassi delle coppie esistenti; non ne crea mai una.

### 📊 Linea o candele, Abs o %

In modalità **Prezzi**, i pulsanti in alto a sinistra del grafico alternano:

- tra una **linea** e le **candele**, che richiedono i prezzi di apertura, massimo e minimo;
- tra **Abs**, i prezzi, e **%**, la variazione dalla prima data dell'intervallo.

---

## 🧰 Strumenti sul grafico

I tre pulsanti in alto a destra del grafico:

- **📏 Aggiungi misura** — confronta due punti: vedi [Misure](measures.md). **Prezzi** e **Rendimento mobile** mantengono misure separate.
- **✏️ Modifica prezzi ed eventi** — apre l'[Editor dati](data-editor.md), solo in modalità **Prezzi**.
- **⚙️ Estetica** — **Riempimento area**, **Colori di riferimento** (verde sopra il valore iniziale, o sopra zero in %, rosso sotto), **Linee della griglia**, **Gradiente obsoleto** (attenua i punti il cui prezzo o tasso di cambio è mantenuto da un giorno precedente) e **Scala asse Y** (**Auto**, **Includi 0** o limiti **Personalizzati**). Le candele disattivano Riempimento area, Colori di riferimento e Gradiente obsoleto.

Queste impostazioni e i tuoi segnali vengono memorizzati per questo asset, in questo browser. Per modificarli per tutti gli asset contemporaneamente, usa **Impostazioni** nella [pagina Asset](../index.md): vedi [Impostazioni grafico](../../fx/chart-settings.md).

---

## 🔗 Correlati

- 📊 **[Segnali](signals.md)** — Sovrapponi indicatori tecnici
- 📐 **[Misure](measures.md)** — Misura le differenze di prezzo
- 📅 **[Eventi](events.md)** — Comprendi i marcatori degli eventi
- 📚 **[Rendimenti e tassi di crescita](../../../financial-theory/fundamentals/returns.md)** — Come vengono calcolati i rendimenti semplici, annualizzati e mobili
- 🛠️ **[Interni del grafico](../../../developer/frontend/components/charts.md)** — Per gli sviluppatori: le due modalità, dove risiede lo stato del grafico e come la pagina si sincronizza
