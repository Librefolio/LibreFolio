# 📈 Rendimento Annualizzato Netto

## 💡 Scopo

LibreFolio riporta il rendimento annualizzato solo quando la finestra osservata è sufficientemente lunga da rendere significativa la capitalizzazione composta. La conversione utilizzata è:

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

dove $d$ sono i giorni di calendario. È l'inverso di:

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

L'implementazione restituisce `None` quando:

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- il calcolo genera overflow

!!! warning "Limite di trenta giorni"

    Un rendimento settimanale annualizzato a 365 giorni può esplodere in percentuali prive di significato. LibreFolio quindi sopprime l'annualizzazione al di sotto dei 30 giorni e mostra un valore vuoto invece di un CAGR matematicamente corretto ma fuorviante.

## 🧾 Vista delle Posizioni

Per una posizione aperta in "Le tue posizioni" / riepilogo del portafoglio:

$$
r_{\mathrm{net}} =
\frac{
\mathrm{ComponenteDiMercato}
+ \mathrm{Reddito}
- \mathrm{CommissioniImposte}
}{
\mathrm{BaseDiCosto}
}
$$

dove:

$$
\mathrm{ComponenteDiMercato} =
\begin{cases}
\mathrm{ValoreCorrente}-\mathrm{BaseDiCosto}, & \text{esiste un valore di mercato}\\
0, & \text{senza prezzo / valutato al costo}
\end{cases}
$$

Finestra di annualizzazione:

$$
d = t_{\mathrm{report}} - t_{\mathrm{primo\ lotto\ influente}}
$$

I tipi di transazione che influenzano i lotti sono:

$$
\{\text{ACQUISTO},\ \text{VENDITA},\ \text{RETTIFICA},\ \text{TRASFERIMENTO}\}
$$

Questo include successioni in natura, trasferimenti tra broker e posizioni avviate tramite rettifica. La vecchia rilevazione basata solo su ACQUISTO/VENDITA non riuscirebbe a cogliere tali posizioni.

## 🪟 Vista per Periodo

Per il contributo di periodo di ciascun asset:

$$
\mathrm{PnL}_{periodo} =
\Delta \mathrm{PLN}
+ \mathrm{Realizzato}
+ \mathrm{Reddito}
- \mathrm{CommissioniImposte}
$$

La percentuale di periodo visualizzata rimane:

$$
r_{\mathrm{periodo}} = \frac{\mathrm{PnL}_{periodo}}{|\mathrm{ValoreIniziale}|}
$$

quando `ValoreIniziale` è diverso da zero. L'annualizzazione può ripiegare sulla base di costo finale per gli asset aperti a metà periodo:

$$
\mathrm{base\_ann}=
\begin{cases}
|\mathrm{ValoreIniziale}|, & |\mathrm{ValoreIniziale}|>0\\
\mathrm{BaseDiCosto}_{fine}, & \text{altrimenti}
\end{cases}
$$

L'inizio della finestra è vincolato al lotto FIFO più vecchio ancora aperto alla fine del periodo:

$$
t_{\mathrm{inizio}}=\max(t_{\mathrm{da}},\ t_{\mathrm{lotto\ aperto\ più\ vecchio}})
$$

Quindi:

$$
r_{\mathrm{ann}} =
\operatorname{annualizza}\left(\frac{\mathrm{PnL}_{periodo}}{\mathrm{base\_ann}},\ t_{\mathrm{fine}}-t_{\mathrm{inizio}}\right)
$$

## 🧬 Lotti FIFO

Il rendimento annualizzato del lotto FIFO è netto di reddito allocato, commissioni e imposte:

$$
\mathrm{PnLNettoTotale}_i =
\mathrm{PnLDiMercato}_i
+ \mathrm{PnLRealizzato}_i
+ \mathrm{Reddito}_i
- \mathrm{Commissioni}_i
- \mathrm{Imposte}_i
$$

$$
\mathrm{RendimentoNettoTotale}_i =
\frac{\mathrm{PnLNettoTotale}_i}{\mathrm{ValoreDiApertura}_i}
$$

Il valore annualizzato utilizza `rendimento_netto_totale`, non il `rendimento_totale` lordo:

$$
r_{\mathrm{ann},i} =
\operatorname{annualizza}
\left(
\mathrm{RendimentoNettoTotale}_i,\ 
t_{\mathrm{fine\ lotto}}-t_{\mathrm{apertura}}
\right)
$$

dove $t_{\mathrm{fine\ lotto}}$ è la data di chiusura per i lotti completamente chiusi, altrimenti la data di fine analisi.

## 🔗 Correlati

- 🧭 [Risoluzione del Prezzo](price-resolution.md) — origine delle valutazioni di mercato e da transazione
- 📉 [ROI Semplice](roi.md) — contesto del rendimento principale e a livello di posizione
- 📊 [PnL di Periodo](period-pnl.md) — scomposizione del periodo
- 🔬 [Analisi dei Lotti FIFO](../fifo-engine/fifo-lot-analysis.md) — metriche nette per lotto
- ⚙️ [Portfolio Engine](index.md) — modello matematico completo
