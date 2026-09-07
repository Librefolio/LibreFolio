# 💼 Valore Patrimoniale Netto (NAV) / Patrimonio Netto

## 💡 Cos'è il NAV?

Il **Valore Patrimoniale Netto (NAV)** è la valutazione complessiva di mercato del tuo portafoglio in un istante $t$. Risponde alla domanda: *"Quanto vale il portafoglio in questo momento?"*

---

## 🧮 Formula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Dove:

$$
\mathrm{MV}(t)=
\sum_{(a,b)\in S}
\frac{q(a,b,t)}{qbq(a)}
\cdot \operatorname{mark}(a,t)
\cdot \mathrm{fx}(\mathrm{ccy}_{mark}, C^*, t)
$$

🔗 Vedi **[Portfolio Engine — §5 Aggregation](index.md#5-portfolio-aggregation)** per la derivazione completa.

---

## 🔗 Catena del Prezzo di Valutazione {: #valuation-price-chain }

La quotazione $\operatorname{mark}(a,t)$ proviene dal resolver unificato:

1. **MARKET** — quotazione di chiusura di mercato del giorno stesso.
2. **TRADE_AVG** — osservazione media BUY/SELL/ADJUSTMENT del giorno stesso.
3. **CARRIED** — ultima osservazione antecedente a $t$, riportata in avanti (LOCF).
4. **MISSING** — nessuna osservazione il giorno $t$ o in precedenza.

I mark restano in valuta nativa fino alla valutazione; la conversione FX avviene a $t$. Il PMC **non** viene mai utilizzato per la valutazione. Vedi [Risoluzione Prezzi](price-resolution.md).

---

## 📝 Esempio

| Componente | Importo |
|------------|---------|
| Valore di Mercato delle Attività | €32.759 |
| Saldo di Cassa | €631 |
| In Transito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinzioni Chiave

- **NAV vs [Valore Contabile](book-value.md)**: NAV = valore di mercato; Valore Contabile = costo di acquisizione. La differenza = plusvalenze non realizzate.
- **NAV vs [PnL Periodico](period-pnl.md)**: NAV = istantanea; PnL Periodico = variazione corretta per i flussi nel tempo.

---

## ⚠️ Qualità dei Dati

| Fonte di Valutazione | Affidabilità |
|----------------------|--------------|
| `MARKET_PRICE` | Piena — quotazione reale, esatta o riportata |
| `LAST_TRADE_PRICE` | Parziale — mark del resolver da transazione |
| `MISSING` | Nessuna — escluso dal NAV |

`estimated=True` si applica solo ai mark di origine TRADE. Una quotazione MARKET obsoleta è stale ma non estimated.

Le valutazioni di origine TRADE più vecchie del periodo di grazia di 14 giorni generano l'avviso "asset valutati al costo / nessun prezzo di mercato da più di due settimane" alla data di valutazione.
