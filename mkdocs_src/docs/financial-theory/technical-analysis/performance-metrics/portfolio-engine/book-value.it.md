# 📖 Valore contabile

## 💡 Che cos'è il valore contabile?

Il **valore contabile** rappresenta il costo contabile storico del tuo portafoglio — costo di carico aperto più riserve di liquidità e valore contabile in transito. Non fluttua con i prezzi di mercato ed è distinto dalla [Risoluzione del prezzo](price-resolution.md).

---

## 🧮 Formula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Dove il costo di carico aperto:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w^{C^*}(a,b,t)
$$

Qui $w^{C^*}(a,b,t)$ è il [PMC](../weighted-average-cost.md) mantenuto direttamente nella valuta richiesta $C^*$: ogni acquisizione vi è stata inserita al tasso della propria data $d_i$, come $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ per un importo $P_i$ effettivamente pagato. OCB quindi non utilizza **alcun tasso di cambio alla data di valutazione** $t$: è la somma dei costi storici — ciò che è stato pagato — e non si muove quando si muovono i tassi di cambio.

Nel termine in transito, la liquidità in transito viene convertita a $t$, mentre gli asset in transito portano il loro costo congelato convertito alla data di arrivo.

!!! note "Costo incompleto"

    Quando parte del costo di una posizione è sconosciuta — nessun tasso di cambio alla data di acquisizione o a una data precedente, oppure un trasferimento o una rettifica senza costo di carico — OCB include solo la parte nota, e la posizione stessa viene segnalata: il suo prezzo medio di carico (PMC) e il suo P&L latente non vengono mostrati.

🔗 Vedi **[Portfolio Engine — §3 Stato della posizione](index.md#3-position-state)** per la derivazione completa.

---

## ⚖️ P&L latente

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

Poiché il NAV valuta gli asset al prezzo di mercato del giorno **e** al tasso di cambio, mentre il valore contabile mantiene i costi storici, il P&L latente di un asset prezzato in un'altra valuta include l'effetto del tasso di cambio. Ad esempio, 10 unità acquistate per €400 quando valevano 500 USD mantengono un OCB di €400; se valgono 550 USD in un giorno in cui 1 USD = €0,75, il loro valore di mercato è €412,50 e il P&L latente è €12,50 — la plusvalenza propria delle unità (+€37,50) meno il calo del dollaro (−€25,00). [P&L periodo](period-pnl.md#unrealized-change-by-currency) mostra come la dashboard suddivide le due componenti.

---

## 📝 Esempio

| Componente | Importo |
|-----------|--------|
| Costo di carico aperto | €27.000 |
| Liquidità | €600 |
| Valore contabile in transito | €0 |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Con NAV = €33.000:

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Correlati

- 📊 [PMC](../weighted-average-cost.md) — metodo del costo unitario per OCB
- 💼 [NAV](nav.md) — controparte al valore di mercato
- 🧭 [Risoluzione del prezzo](price-resolution.md) — prezzi di mercato/operazione usati dal NAV, non dal valore contabile
- 📈 [P&L periodo](period-pnl.md) — P&L realizzato + P&L latente combinati
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
