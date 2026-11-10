# 💼 Valore netto (NAV) / Patrimonio netto

## 💡 Che cos'è il NAV?

**Il valore netto (NAV)** è la valutazione di mercato complessiva del tuo portafoglio in un determinato momento $t$. Risponde alla domanda: *"Quanto vale il portafoglio in questo momento?"*

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

e la liquidità di ciascun broker, mantenuta nelle valute in cui è stata registrata e valorizzata al tasso di $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

con $N_{b,c}(t)$ il saldo che il broker $b$ detiene nella valuta $c$ al tempo $t$, moltiplicato per la [quota di proprietà](../../../../user/brokers/sharing.md) del broker, e $\mathrm{fx}(c, C^*, t)$ il tasso più recente alla data $t$ o precedente ($1$ per $c = C^*$). La liquidità detenuta in un'altra valuta fa quindi variare il NAV quando varia il suo tasso di cambio.

Una posizione il cui asset non ha ancora un mark — nessuna quotazione, nessuna operazione di acquisto o vendita e nessuna [stima del costo di trasferimento](price-resolution.md#transfer-cost-estimate) alla data $t$ o precedente — entra invece in $\mathrm{MV}(t)$ al suo costo di carico $\mathrm{CB}(a,b,t)$ quando tale costo è completo, e in caso contrario è esclusa dal NAV.

🔗 Consulta **[Portfolio Engine — §3 Stato della posizione](index.md#3-position-state)** e **[§5 Aggregazione](index.md#5-portfolio-aggregation)** per la derivazione completa.

---

## 🔗 Risolutore unificato dei prezzi {: #valuation-price-chain }

Il mark $\operatorname{mark}(a,t)$ proviene dal risolutore unificato:

1. **MARKET** — quotazione dello stesso giorno del sistema dell'asset.
2. **TRADE_AVG** — media delle osservazioni di acquisto/vendita dello stesso giorno, oppure il costo di un trasferimento in entrata per un asset che non ha ancora nient'altro ([stima](price-resolution.md#transfer-cost-estimate)).
3. **CARRIED** — ultima osservazione precedente a $t$, mantenuta (LOCF).
4. **MISSING** — nessuna osservazione alla data $t$ o precedente.

Una rettifica non è mai un'osservazione, con o senza costo di carico: registra un costo, non un prezzo. Il costo di un trasferimento in entrata conta solo come stima, e solo finché l'asset non ha alcuna quotazione e nessun'altra operazione a quella data o precedente.

I mark restano nella valuta nativa fino alla valutazione, e così anche i saldi di cassa, ciascuno nella valuta in cui è stato registrato; la conversione FX avviene al tempo $t$. Il PMC non è **mai** un prezzo: solo una posizione del tutto priva di mark viene conteggiata al suo costo di carico, una stima dichiarata (`ESTIMATED_AT_COST`) che mantiene i tassi di cambio delle sue date di acquisizione. Vedi [Risoluzione dei prezzi](price-resolution.md).

---

## 📝 Esempio

| Componente | Importo |
|-----------|--------|
| Valore di mercato degli asset | €32,759 |
| Saldo di cassa | €631 |
| In transito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinzioni chiave

- **NAV vs [Valore contabile](book-value.md)**: NAV = valore di mercato; valore contabile = costo di acquisizione. La differenza = plusvalenze non realizzate.
- **NAV vs [P&L periodo](period-pnl.md)**: NAV = istantanea; P&L periodo = variazione rettificata per i flussi nel tempo.

---

## ⚠️ Qualità dei dati

| Fonte di valutazione | Affidabilità |
|-----------------|------------|
| `MARKET_PRICE` | Completa — quotazione reale, esatta o mantenuta |
| `LAST_TRADE_PRICE` | Parziale — mark del risolutore proveniente da un'operazione |
| `ESTIMATED_AT_COST` | Stima — nessun prezzo disponibile: il costo di carico, senza plusvalenze o minusvalenze non realizzate |
| `MISSING` | Nessuna — nessun prezzo e un costo incompleto: esclusa dal NAV |

`estimated=True` si applica solo ai mark di origine TRADE. Una quotazione MARKET obsoleta e mantenuta è obsoleta ma non stimata.

Per un asset con un provider di prezzi, la dashboard avvisa alla data di valutazione: una valutazione derivante da un'operazione, quando l'asset non ha avuto alcuna quotazione di mercato per più del periodo di tolleranza di 14 giorni — conteggiato dall'arrivo del trasferimento per un asset mai quotato, acquistato o venduto, valorizzato al costo di un trasferimento —, genera l'avviso “valorizzati al prezzo della loro ultima transazione”; e una valutazione al costo, più di 14 giorni dopo la prima acquisizione dell'asset, genera l'avviso “valorizzato al costo”. Un asset senza provider non genera nessuno dei due avvisi: le sue operazioni, o il suo costo, sono il valore previsto.
