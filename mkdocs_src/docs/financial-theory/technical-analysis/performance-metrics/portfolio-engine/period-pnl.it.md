# 📊 PnL di Periodo (Profitto e Perdita)

## 💡 Cos'è il PnL di Periodo?

L'importo monetario assoluto del guadagno o della perdita generato dal tuo portafoglio nell'intervallo $[t_0, t_1]$, rettificato per i flussi di cassa esterni.

---

## 🧮 Formula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

La variazione della baseline deriva da `cumulative_external_cash_flow`, quindi include i flussi di cassa e il capitale in natura valorizzato relativo ad ADJUSTMENT/TRANSFER.

---

## 🧮 Scomposizione

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definizione |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variazione della plusvalenza/minusvalenza non realizzata nel periodo |
| Realized | Somma dei (proventi di vendita − costo base) per le operazioni SELL nel periodo |
| Income | DIVIDENDO + INTERESSE nel periodo |
| FeesTaxes | COMMISSIONE + IMPOSTA nel periodo |
| Other | Residuo che chiude l'identità |

Il residuo è calcolato come:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

---

## 🎯 Contributo per Asset

Per ogni posizione $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'insieme delle posizioni include **tutta l'attività** nel periodo:

$$
\mathcal{P} = \text{posizioni con attività BUY/SELL/ADJUSTMENT/TRANSFER o quantità di confine}
$$

Il rendimento annualizzato del periodo fissa l'inizio della finestra alla più recente tra la data di inizio richiesta e quella del lotto aperto più vecchio. Utilizza $|\mathrm{StartValue}|$ come base di annualizzazione, ripiegando sul costo base finale per le posizioni aperte a metà periodo. Vedi [Rendimento Annualizzato Netto](net-annualized-return.md).

🔗 Vedi **[Portfolio Engine — §7 Contributo di Periodo](index.md#7-period-contribution)** per i dettagli.

---

## 📝 Esempio

- NAV a $t_0$: €27.000
- Aumento della baseline di capitale nel periodo: €1.000
- NAV a $t_1$: €33.000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — punto finale di ogni formula PnL
- 💸 [Capitale Depositato](deposited-capital.md) — PnL totale dall'inizio
- ⚙️ [Portfolio Engine](index.md) — modello matematico completo
- 📈 [Panoramica delle Metriche di Performance](../index.md) — tutte le metriche di performance a colpo d'occhio
