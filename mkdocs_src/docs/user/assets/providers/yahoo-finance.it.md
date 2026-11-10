# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance copre azioni, ETF, fondi, indici e criptovalute dalle borse di tutto il mondo, e puoi effettuare la ricerca per nome o per ticker.

## 🔍 Cosa offre

- **Prezzo corrente**: l'ultimo prezzo riportato da Yahoo per il ticker — su alcune borse è ritardato.
- **Storico**: valori giornalieri di apertura, massimo, minimo, chiusura e volume, per tutto il periodo coperto da Yahoo. Le chiusure sono salvate come le fornisce la borsa, senza la rettifica per i dividendi pagati successivamente (uno split è già nelle chiusure di Yahoo ed è registrato come evento).
- **Dividendi e split**: registrati come eventi dell'asset. Per un titolo londinese quotato in pence, il dividendo viene salvato in sterline (1,95 pence sono 0,0195 GBP).
- **Ricerca**: per nome o per ticker.
- **Dettagli**: tipo, valuta, descrizione, settore, ticker e, quando Yahoo lo fornisce, l'ISIN.
- **Dettagli del fondo**: per un ETF o un fondo, la distribuzione settoriale (a un'azione viene assegnato un unico settore), la descrizione del fondo stesso quando Yahoo non ne fornisce una sintesi dell'attività, e alla fine della descrizione le spese correnti (`TER: 0.03%`) e l'emittente (`Issuer: Vanguard`). Yahoo non fornisce le spese correnti a ogni fondo — Vanguard FTSE All-World (`VWCE.DE`) non ne ha — e in tal caso quella parte viene omessa. La distribuzione per paese proviene solo da [justETF](justetf.md).

## ✏️ Configuralo

**Cerca online** lo configura per te. Manualmente, in **Assegnazione provider**, scegli **Yahoo Finance**, imposta **Tipo di identificatore** su **TICKER** e digita il ticker come **Identificatore**. Non c'è altro da compilare.

| Asset | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milano) | `CSSPX.MI` |
| Bitcoin in dollari USA | `BTC-USD` |

Fuori dagli Stati Uniti, aggiungi al ticker il suffisso della borsa: `.DE` per Xetra, `.MI` per Milano, `.AS` per Amsterdam.

Molti titoli londinesi (suffisso `.L`) sono quotati in pence, che Yahoo riporta come valuta `GBp`. LibreFolio memorizza la valuta come `GBP` e i prezzi come li fornisce Yahoo, in pence, quindi un asset di questo tipo richiede **Unità per singolo prezzo** pari a 100, altrimenti il suo valore risulta 100 volte troppo alto. Quando Yahoo riporta `GBp`, selezionando il titolo in **Cerca online** viene impostato 100, con una nota sotto il campo, e **Chiedi al provider** lo propone se il campo indica altro ([Controlla i dati del provider](../create-edit.md#provider-data-comparison)).

## ⚠️ Limiti

- **ISIN** funziona anche come **Tipo di identificatore**, ma solo quando Yahoo riesce ad abbinarlo a un ticker: preferisci il ticker.
- **I dati salvati prima di questa modifica restano come erano.** Se hai un asset Yahoo le cui chiusure sono state salvate in precedenza, portano ancora la rettifica dei dividendi del giorno in cui sono state lette, e i dividendi di un titolo in pence sono ancora in pence. Niente li riscrive automaticamente: esegui di nuovo la **Sincronizzazione completa** dell'asset (la finestra di dialogo avvisa prima di sovrascrivere) e lo storico viene riletto da zero. Questo non cambia il comportamento sugli split descritto sotto.
- **Limite noto: gli split.** Dopo uno split azionario Yahoo riscrive le chiusure passate (e i dividendi) sul nuovo numero di azioni. Per lo split 4:1 di Apple del 31 agosto 2020, la chiusura del 28 agosto 2020 è indicata come 124,81 invece dei 499 che era realmente. Quindi il valore di una posizione nei giorni precedenti a uno split può risultare diviso per il rapporto di split (10 azioni × 124,81 = 1.248 invece di 4.990), e il rendimento salta il giorno dello split. Una correzione è prevista dopo la 1.3.
- Yahoo può limitare le richieste frequenti: LibreFolio allora mette in pausa Yahoo per un po' e continua a mostrare gli ultimi prezzi salvati. Alcuni ticker presentano giorni mancanti.

## 🔗 Correlati

- 🔌 **[Provider asset](index.md)** — Confronta i provider
- 🛠️ **Per gli sviluppatori: [Provider Yahoo Finance](../../../developer/backend/assets/provider_yahoo_finance.md)** — Richieste, caching ed eventi
