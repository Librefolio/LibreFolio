# <img src="../../../../static/scheduled_investment.png" alt=""> Investimento Programmato

Il provider Investimento Programmato calcola il valore di un asset dal suo piano interessi invece
di leggere un prezzo di mercato. Usalo per conti di risparmio, depositi a termine, prestiti P2P o crowdfunding,
e obbligazioni che segui tramite i loro interessi maturati. Nella lista **Provider** è chiamato
**Calcolatore Investimento Programmato**.

## 🔍 Cosa Offre

- ✅ **Prezzo corrente** e **storico**, calcolati dal tuo piano interessi: non viene interrogato nessun sito web, e
  lo stesso piano dà sempre gli stessi valori.
- ✅ **Eventi**: con **Genera Cedola**, pagamenti di interessi e un regolamento finale a scadenza, più
  gli eventi che aggiungi tu stesso.
- ❌ **Ricerca** e **dettagli**: non applicabile. Non c'è nemmeno un identificatore da digitare: LibreFolio
  ne crea uno per te.

## 📋 Editor del piano interessi {: #interest-schedule-editor }

Scegliendo il provider in **Assegnazione Provider** si apre l'editor **Piano interessi**. Inizia con
le impostazioni per l'intero piano interessi:

- **Valore Iniziale** e **Valuta**: l'importo investito, o il valore nominale — ad es. 10.000 EUR.
- **Tipo di Interesse**: **Semplice** o **Composto** — vedi
  [Come viene calcolato il valore](#how-value-is-calculated).
- **Conteggio Giorni**: come vengono contati i giorni di un anno — **ACT/365**, **ACT/360**, **ACT/ACT** o
  **30/360**. Vedi [Convenzioni di conteggio dei giorni](../../../financial-theory/fundamentals/day-count.md).

Poi aggiungi i periodi con **Aggiungi Primo Periodo**, e **Aggiungi Periodo** per i successivi:

| Colonna | Cosa inserire |
|---|---|
| **Periodo** | Data di inizio e fine, entrambe incluse |
| **Tasso %** | Il tasso annuo come percentuale: `5.00` significa 5% all'anno |
| **Frequenza** | Ogni quanto matura l'interesse: Giornaliero, Settimanale, Mensile, Trimestrale, Semestrale o Annuale |
| **Genera Cedola** | Selezionalo per pagare gli interessi maturati a ogni data di scadenza |

I periodi devono susseguirsi, senza interruzioni o sovrapposizioni. **Dividi** taglia un periodo in due; seleziona
periodi adiacenti e clicca **Unisci** per unirli.

### ⚡ Interessi di Mora {: #late-interest }

Per un prestito rimborsato in ritardo, attiva **⚡ Interessi di Mora** sotto i periodi: l'asset continua a crescere
dopo la fine dell'ultimo periodo. Appare una riga di mora con il proprio **Tasso %**, **Frequenza** e
**Genera Cedola**. Clicca il suo periodo per impostare i giorni di grazia, e scegli **Semplice** o
**Composto** (il predefinito) accanto all'interruttore.

- Durante i giorni di grazia, gli interessi continuano a maturare al tasso dell'ultimo periodo.
- Dopo di essi, si applica il tasso di mora.

### 📅 Eventi dell'asset

Aggiungi eventi singoli con **Aggiungi Evento**: una **Data**, un **Tipo**, un **Valore** e **Note** opzionali.
Ogni evento conta dalla sua data in poi.

| Tipo | Effetto sul valore |
|---|---|
| **Interesse** | Un pagamento di interessi che hai ricevuto: il valore diminuisce di quell'importo |
| **Rettifica prezzo** | Una svalutazione (negativa) o una rivalutazione (positiva) |

## 🧮 Come Viene Calcolato il Valore {: #how-value-is-calculated }

LibreFolio percorre il piano interessi giorno per giorno. Nel giorno $d$ il valore è

$$
V(d) = V_0 + I(d) - \sum \text{Eventi di interesse} + \sum \text{Rettifiche prezzo}
$$

dove $V_0$ è il **Valore Iniziale**, $I(d)$ l'interesse maturato finora, e le somme coprono gli
eventi fino al giorno $d$. Ogni giorno aggiunge interesse al tasso annuo del periodo $r$ su $\Delta t$, la
quota di un giorno dell'anno secondo il **Conteggio Giorni** (ad esempio $1/365$ con ACT/365):

- **Semplice** — interesse solo sul valore iniziale: $\Delta I = V_0 \, r \, \Delta t$
- **Composto** — interesse anche sull'interesse già maturato: $\Delta I = (V_0 + I) \, r \, \Delta t$

Con **Genera Cedola**, a ogni data di scadenza il guadagno $V(d) - V_0$, quando positivo, viene pagato
come evento di interesse: il valore riparte da $V_0$, e $I$ e le somme ripartono da zero.

- **Prima del primo periodo**, il valore è il Valore Iniziale.
- **Dopo l'ultimo periodo**, rimane al suo importo finale, a meno che gli interessi di mora siano attivi. Con
  **Genera Cedola** sull'ultimo periodo e nessun interesse di mora, un evento di regolamento a scadenza chiude
  l'asset a quell'importo.
- **Il grafico** riceve un punto a ogni data di **Frequenza**: scegli **Giornaliero** per una linea continua.

??? example "🧮 Un prestito di €10.000 al 5%, con una cedola ogni mese"

    Interesse semplice, ACT/365, un periodo che inizia il 1 gennaio, **Frequenza** Mensile,
    **Genera Cedola** selezionato. La prima data di scadenza è il 1 febbraio, 31 giorni dopo: il prestito ha
    maturato circa €42,47 ($10\,000 \times 0.05 \times 31/365$). Quell'importo viene pagato come
    evento di interesse, e il valore torna a €10.000 per crescere di nuovo a febbraio.

## 🔗 Correlati

- 📅 **[Eventi dell'asset](../detail/events.md)** — Come gli eventi vengono mostrati sul grafico dell'asset
- 🛠️ **Per gli sviluppatori: [Provider Investimento Programmato](../../../developer/backend/assets/provider_scheduled_investment.md)** — Motore, eventi e cache
