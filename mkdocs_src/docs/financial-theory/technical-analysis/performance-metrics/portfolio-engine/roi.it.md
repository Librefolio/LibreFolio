# 📉 ROI semplice (ritorno sull'investimento)

## 💡 Che cos'è?

Il ROI semplice misura il valore generato rispetto al capitale investito. Nell'attuale motore di portafoglio, il denominatore del capitale investito è la **baseline del capitale** proveniente da `cumulative_external_cash_flow`, non soltanto i depositi in denaro.

## 🧮 Formula

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

La stessa baseline è alla base del valore principale `total_gain_loss`:

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` include i flussi di cassa esterni ordinari e il capitale in natura valorizzato tramite ADJUSTMENT/TRANSFER. Ciò evita che portafogli ereditati o inizializzati mostrino un ROI assurdo perché un asset è stato inserito senza un versamento in denaro.

## 🪟 Il ROI di un periodo {: #dashboard-period-roi }

Il ROI nella scheda Rendimenti della Dashboard e la sua linea nel grafico `%` misurano il periodo selezionato, non l'intera cronologia. Il loro capitale è il valore con cui il periodo si apre, più i depositi e meno i prelievi effettuati successivamente:

$$
\mathrm{ROI}_{\mathrm{period}}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{NetInvested}(t)}{\mathrm{NetInvested}(t)},
\qquad
\mathrm{NetInvested}(t)=\max\!\left(0,\ \mathrm{NAV}(t_0)+\sum_{t_0<s\le t}\mathrm{CF}_s\right)
$$

dove $t_0$ è l'ultimo giorno della cronologia pari o precedente all'inizio del periodo, e $\mathrm{CF}_s$ conta i flussi esterni — depositi positivi, prelievi negativi, capitale in natura incluso come per la baseline del capitale sopra. Il valore della scheda corrisponde all'ultimo punto della linea; dove $\mathrm{NetInvested}(t)$ è zero il ROI è $0$, mai un valore mancante.

Quando il periodo inizia **prima del primo giorno del portafoglio**, non c'è un valore con cui aprire il periodo e i flussi di quel primo giorno — il primo deposito — resterebbero fuori dalla somma. Il periodo contiene quindi l'intera cronologia, per cui il suo capitale è costituito da tutti i flussi, incluso il primo deposito: il ROI è lo stesso che si otterrebbe senza alcuna data di inizio, sia sulla scheda sia in ogni punto della linea.

## 🎯 Quando usarlo

- Per leggere il guadagno o la perdita complessivi del portafoglio rispetto al capitale economico conferito.
- Per confrontare il NAV attuale con la baseline attuale del capitale.
- Per verificare rapidamente la performance rettificata per i flussi di cassa prima di passare a TWRR/MWRR.

## 📈 Rendimento netto annualizzato della posizione

Le posizioni aperte mostrano anche un CAGR netto:

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

L'annualizzazione usa:

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La finestra parte dalla prima transazione che influisce sul lotto: BUY, SELL, ADJUSTMENT o TRANSFER. I valori relativi a periodi inferiori a 30 giorni vengono soppressi. Le definizioni complete sono in [Rendimento netto annualizzato](net-annualized-return.md).

## ⚠️ Il difetto: diluizione dei flussi di cassa

Il ROI semplice resta sensibile all'importo e alla tempistica del capitale aggiunto. Se aggiungi un apporto consistente dopo che i guadagni si sono già verificati, il rapporto può calare anche se il valore di mercato non è diminuito. Usa [P&L periodo](period-pnl.md), [TWRR](twrr.md) e [MWRR](mwrr.md) per separare il profitto assoluto, il rendimento della strategia e il rendimento dell'investitore ponderato per il denaro.
