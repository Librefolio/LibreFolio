# 📉 ROI Semplice (Return on Investment)

## 💡 Cos'è?

Il ROI semplice misura il valore generato rispetto al capitale investito. Nel motore di portafoglio attuale, il denominatore del capitale investito è la **capital baseline** derivata da `cumulative_external_cash_flow`, non solo i depositi in contanti.

## 🧮 Formula

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

La stessa baseline determina il `total_gain_loss` principale:

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` include i flussi di cassa esterni ordinari e il capitale da ADJUSTMENT/TRANSFER in natura prezzati. Ciò impedisce che portafogli ereditati o avviati con asset iniziali mostrino un ROI assurdo perché un asset venga inserito senza un deposito in contanti.

## 🎯 Quando usarlo

- Per leggere l'utile/perdita principale del portafoglio rispetto al capitale economico conferito.
- Per confrontare il NAV corrente con la capital baseline corrente.
- Per verificare la performance corretta per i flussi di cassa prima di analizzare TWRR/MWRR.

## 📈 Rendimento Annualizzato Netto della Posizione

Le partecipazioni aperte espongono anche un CAGR netto:

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

L'annualizzazione utilizza:

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La finestra inizia dalla prima transazione che influisce sul lotto: BUY, SELL, ADJUSTMENT o TRANSFER. I valori inferiori a 30 giorni vengono soppressi. Le definizioni complete sono in [Rendimento Annualizzato Netto](net-annualized-return.md).

## ⚠️ Il Difetto: Diluizione dei Flussi di Cassa

Il ROI semplice è ancora sensibile all'importo e alla tempistica del capitale aggiunto. Se si aggiunge un grande contributo dopo che i guadagni si sono già verificati, il rapporto può diminuire anche se il valore di mercato non è cambiato. Utilizza [P&L di Periodo](period-pnl.md), [TWRR](twrr.md) e [MWRR](mwrr.md) per separare il profitto assoluto, il rendimento della strategia e il rendimento dell'investitore ponderato per il denaro.
