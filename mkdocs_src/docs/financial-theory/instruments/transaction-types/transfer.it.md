# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Trasferimento di Asset

I **trasferimenti di asset** spostano i titoli tra conti di broker **senza una vendita**. La posizione lascia un broker e arriva a un altro: non c'è scambio di contanti e, nella maggior parte delle giurisdizioni, questo non costituisce un evento imponibile.

---

## 🔑 Proprietà Chiave

| Proprietà | Da (origine) | A (destinazione) |
|----------|---------------|-------------------|
| **Codice** | `TRANSFER` | `TRANSFER` |
| **Effetto cassa** | — | — |
| **Effetto asset** | ⬇️ Diminuisce | ⬆️ Aumenta |
| **Broker** | Broker di origine | Broker di destinazione |
| **Evento fiscale** | Varia in base alla giurisdizione | Varia |

---

## 📊 Come Funziona

Un trasferimento di asset registra **due voci**: un addebito presso il broker di origine e un accredito presso il broker di destinazione. Entrambe fanno riferimento allo **stesso asset** con quantità speculari.

Scenari comuni:

- Spostamento di azioni da un broker a un altro
- Ricezione di asset in eredità
- Versamenti in natura in un conto di tipo diverso (es. ISA, 401k)

!!! info "Preservazione del Costo di Acquisizione"

    Durante il trasferimento di asset, il **costo di acquisizione originale** deve essere preservato. Il trasferimento stesso non è un evento imponibile nella maggior parte delle giurisdizioni (sebbene le norme varino). LibreFolio consente un **override del costo di acquisizione** opzionale sul lato ricevente.

    Consulta **[📊 Costo Medio Ponderato (WAC)](../../portfolio-theory/weighted-average-cost.md)** per scoprire come viene calcolato automaticamente il costo di acquisizione.

---

## 🔀 Relazione con le Rettifiche

Sotto il cofano, un Trasferimento è composto da due voci di Rettifica. LibreFolio supporta:

| Operazione | Risultato |
|-----------|--------|
| **Frazionamento** (scollega) | Trasferimento → due Rettifiche indipendenti |
| **Promote** (collega) | Due Rettifiche → Trasferimento |

**Vincoli di promozione**: stesso asset, broker diversi, quantità opposte.

---

## 🔗 Correlati

- 📊 **[Costo Medio Ponderato](../../portfolio-theory/weighted-average-cost.md)** — Come viene calcolato il costo di acquisizione sui trasferimenti
- 🏦 **[Trasferimento di Liquidità](cash-transfer.md)** — Bonifici bancari (contanti, non asset)
- 💱 **[Conversione Valutaria](fx-conversion.md)** — Cambio valuta
- 📊 **[Rettifica](adjustment.md)** — Correzioni manuali
