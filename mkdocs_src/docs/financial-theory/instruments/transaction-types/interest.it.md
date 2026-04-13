# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Interessi (Transazione)

Una **transazione di interessi** registra gli interessi ricevuti da obbligazioni, conti di risparmio, prestiti P2P o altri strumenti a reddito fisso. Rappresenta l'impatto a livello di portafoglio di un [evento di interesse](../asset-events/interest.md).

---

## 🔑 Proprietà Chiave

| Proprietà | Dettaglio |
|----------|--------|
| **Codice** | `INTEREST` |
| **Effetto cassa** | ⬆️ Aumenta il saldo |
| **Effetto asset** | — (il capitale rimane invariato) |
| **Evento fiscale** | Sì (reddito imponibile) |

---

## 📊 Fonti di Interesse

| Fonte | Descrizione | Frequenza |
|--------|-------------|-----------|
| **Cedole obbligazionarie** | Pagamenti a tasso fisso o variabile | Semestrale / Annuale |
| **Interessi sui conti deposito** | Interessi su depositi di liquidità | Mensile / Trimestrale |
| **Pagamenti prestiti P2P** | Quota interessi dei rimborsi del prestito | Mensile |
| **Rendimenti del crowdfunding** | Rendimenti a tasso fisso su progetti | Variabile |

---

## 📐 Interesse Semplice vs Composto

### 📏 Interesse Semplice

Interesse calcolato solo sul capitale originale:

$$
I = P \times r \times t
$$

### 📈 Interesse Composto

Interesse calcolato sul capitale + interessi accumulati:

$$
A = P \times (1 + r)^t
$$

La differenza tra interesse semplice e composto è la base del confronto tra i benchmark [Linear vs Compound Growth](../../technical-analysis/synthetic-benchmarks/index.md).

---

## 🔗 Correlati

- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Meccaniche di maturazione e cedole
- 🏛️ **[Obbligazioni](../asset-types/bonds.md)** — Il principale asset che genera interessi
- 📅 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse
