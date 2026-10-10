# 📈 Grafico interattivo

Il grafico è il cuore della pagina dell'asset: lo storico dei prezzi, oppure quanto il prezzo si è mosso su una finestra mobile. Scorri per zoomare, trascina per spostarti e passa il mouse su un punto per vederne i valori.

_Ultimo aggiornamento: 2026-10-08_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Grafico del prezzo dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Prezzi o Rendimento rolling {: #primary-modes }

I due pulsanti sopra il grafico scelgono cosa disegnare:

- **Prezzi** — lo storico dei prezzi, con gli [eventi](events.md) dell'asset come marcatori.
- **Rendimento rolling** — per ogni data, la variazione del prezzo su una finestra che scegli tu ([sotto](#rolling-return)).

La pagina si apre sempre su **Prezzi**.

### 🗓️ Finestra del rendimento rolling {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Grafico dell'asset in modalità Rendimento rolling con la finestra 1Y e un asset di confronto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Questa vista risponde alla domanda *quanto si è mosso il prezzo sulla finestra, a ogni data?* Ogni punto confronta la chiusura di quel giorno con la chiusura esattamente $N$ giorni di calendario prima:

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

dove $P$ è l'ultima chiusura nota in quel giorno, nella valuta del grafico → [Rendimento rolling su giorni di calendario](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Scegli $N$ con il controllo **Finestra** accanto ai due pulsanti:

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 e 365 giorni.
- **Personalizzato** — un numero intero con **W**, **M** o **Y**, contati come 7, 30 e 365 giorni: `3M` corrisponde a 90 giorni.
- **?** apre questa sezione del manuale.

La finestra può essere più lunga delle date visualizzate: LibreFolio legge i prezzi più vecchi di cui ha bisogno. Viene ricordata per questo asset, in questo browser.

Come leggerlo:

- **Sopra zero**, il prezzo è più alto di $N$ giorni prima; **sotto zero**, più basso.
- **Passa il mouse su un punto**: ↩ indica la data con cui viene confrontato; 📅 e 💱 indicano le date del prezzo e dei tassi di cambio effettivamente utilizzati, quando uno dei due è più vecchio.
- **[Confronti tra asset](signals.md#data-comparison)** diventano anch'essi rendimenti rolling, con la stessa finestra e la stessa valuta.
- **Solo prezzo**: dividendi, interessi e le tue transazioni non sono inclusi.

??? note "🧩 Lacune e linee corte — quando lo storico è incompleto"

    Un punto resta vuoto, mai stimato, quando uno dei suoi due prezzi manca o non è positivo. Ogni linea inizia dalla prima data in cui può essere calcolata, quindi un asset recente o un tasso di cambio mancante accorcia solo la propria linea, e un prezzo mancante più avanti lascia una lacuna. Quando è calcolabile solo una parte dell'intervallo, una nota sotto il grafico lo segnala; quando non è calcolabile nulla, un messaggio sostituisce il grafico.

---

## 🎛️ Scegli cosa mostra il grafico

### 📅 Intervallo di date

L'intervallo di date nella barra degli strumenti della pagina imposta le date visualizzate: **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **MAX**, oppure **Personalizzato** con un calendario. Se c'è spazio sulla barra, compaiono altri preset (3Y, 5Y, 10Y, WTD, MTD, QTD). L'intervallo che scegli ti segue nelle pagine dashboard, broker, asset e FX della stessa scheda del browser.

Su un intervallo lungo il grafico può raggruppare i giorni in settimane o mesi per restare leggibile: un badge **Settimanale** o **Mensile** in alto a sinistra lo indica.

### 💱 Converti in un'altra valuta

**Converti in**, accanto al prezzo, mostra il grafico in un'altra valuta, con una linea 💱 tratteggiata per il prezzo nella valuta propria dell'asset. Il menu elenca le valute raggiungibili dalle tue coppie FX; **Crea forex…** in fondo aggiunge una coppia mancante. Anche i rendimenti rolling vengono calcolati nella valuta scelta.

??? note "💱 Quando manca un tasso di cambio"

    Un banner sopra il grafico indica la coppia, con una scorciatoia per crearla o aprirla. Il comando **Sincronizza** della pagina scarica i tassi delle coppie esistenti; non ne crea mai una.

### 📊 Linea o candele, Abs o %

In modalità **Prezzi**, i pulsanti in alto a sinistra del grafico permettono di passare:

- tra una **linea** e le **candele**, che richiedono i prezzi di apertura, massimo e minimo;
- tra **Abs**, i prezzi, e **%**, la variazione rispetto al primo giorno dell'intervallo.

---

## 🧰 Strumenti sul grafico

I tre pulsanti in alto a destra del grafico:

- **📏 Aggiungi misura** — confronta due punti: vedi [Misure](measures.md). **Prezzi** e **Rendimento rolling** mantengono misure separate.
- **✏️ Modifica prezzi ed eventi** — apre l'[Editor dati](data-editor.md), solo in modalità **Prezzi**.
- **⚙️ Estetica** — **Riempimento area**, **Colori linea di base** (verde sopra il valore iniziale, o sopra zero in %, rosso sotto), **Linee della griglia**, **Gradiente obsoleto** (attenua i punti il cui prezzo o tasso di cambio è mantenuto da un giorno precedente) e **Scala asse Y** (**Auto**, **Includi 0** o limiti **Personalizzati**). Le candele disattivano Riempimento area, Colori linea di base e Gradiente obsoleto.

Queste impostazioni e i tuoi segnali vengono ricordati per questo asset, in questo browser. Per modificarli contemporaneamente per tutti gli asset, usa **Impostazioni** nella [pagina Assets](../index.md): vedi [Impostazioni grafico](../../fx/chart-settings.md).

---

## 🔗 Correlati

- 📊 **[Segnali](signals.md)** — Sovrapponi indicatori tecnici
- 📐 **[Misure](measures.md)** — Misura le differenze di prezzo
- 📅 **[Eventi](events.md)** — Comprendi i marcatori degli eventi
- 📚 **[Rendimenti e tassi di crescita](../../../financial-theory/fundamentals/returns.md)** — Come vengono calcolati i rendimenti semplici, annualizzati e rolling
- 🛠️ **[Funzionamento interno del grafico](../../../developer/frontend/components/charts.md)** — Per gli sviluppatori: le due modalità, dove risiede lo stato del grafico e come la pagina si sincronizza
