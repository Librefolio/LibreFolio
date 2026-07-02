# 📊 PnL del Periodo (Profit and Loss)

*[⬅️ Torna a Panoramica Metriche di Performance](index.md)*

## 💡 Cos'è il PnL del Periodo?

Il guadagno o la perdita monetaria assoluta generata dal tuo portafoglio nell'intervallo $[t_0, t_1]$, rettificata per i flussi di cassa esterni.

---

## 🧮 Formula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \mathrm{ECF}_{[t_0, t_1]}}
$$

Dove $\mathrm{ECF}$ = Flussi di Cassa Esterni Netti (depositi − prelievi nel periodo).

---

## 🧮 Decomposizione

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{Fees} + \mathrm{Other}
$$

| Componente | Definizione |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variazione di guadagni/perdite non realizzati nel periodo |
| Realized | Somma di (proventi vendita − costo di acquisizione) per le vendite nel periodo |
| Income | DIVIDENDO + INTERESSE nel periodo |
| Fees | FEE + TAX nel periodo |
| Other | Residuo (effetti FX, arrotondamenti) |

---

## 🎯 Contributo per Asset

Per ogni posizione $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

L'insieme delle posizioni include **tutta l'attività** nel periodo:

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \text{keys(Realized)} \cup \text{keys(Income)} \cup \text{keys(Fees)}
$$

🔗 Vedi **[Portfolio Engine — §7 Contributo di Periodo](portfolio-engine.md#7-period-contribution)** per i dettagli.

---

## 📝 Esempio

- NAV a $t_0$: €27.000
- Depositi nel periodo: €1.000
- NAV a $t_1$: €33.000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — risultato finale di ogni formula PnL
- 💸 [Capitale Depositato](deposited-capital.md) — PnL Totale dall'inizio
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modello matematico completo
