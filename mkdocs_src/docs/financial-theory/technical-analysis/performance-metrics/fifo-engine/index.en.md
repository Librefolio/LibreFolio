# 🧬 FIFO Engine — Lot Lifecycle & Matching Model

*[⬅️ Back to Performance Metrics Overview](../index.md)*

## 💡 Overview

While [Weighted Average Cost](../weighted-average-cost.md) blends every acquisition of a position into one running average, LibreFolio's FIFO engine keeps track of **individual lots** — one per acquisition batch — through their entire lifecycle: opening, partial closures, transfers between brokers, splits, and eventual full closure.

This page describes the **mechanics** of that engine: how lots are created, matched, and closed. For the **metrics** derived from this engine (Open/Total Return, qbq scaling, income allocation, a worked example), see [FIFO Lot Analysis](fifo-lot-analysis.md).

!!! info "Two engines, two questions"

    [Portfolio Engine](../index.md) (WAC-based) answers: _"What is my blended cost basis for this position?"_

    FIFO Engine answers a structurally different question: _"Which specific batch of units am I selling, and how did that exact batch perform?"_

---

## 🧱 What is a Lot?

A **lot** is one economic acquisition batch for one asset: a single BUY, the open remainder of an inventory adjustment, or a transfer-in that preserves its original cost basis. A lot keeps its own identity for its entire life, even as it moves between brokers or splits into pieces.

| Property | Meaning |
|----------|---------|
| Direction | `LONG` (bought first) or `SHORT` (sold first, only where the broker allows shorting) |
| Opening date & broker | Where and when the lot came into existence |
| Original quantity & cost | Fixed at opening, later rescaled only by splits — never by transfers |
| Open quantity | How much of the lot has **not** yet been matched by an opposite transaction |
| Custody | Which broker (or brokers, over time) currently holds the open quantity |

---

## 🔁 Lot Lifecycle States

| State | Meaning |
|-------|---------|
| **OPEN** | Nothing has been matched yet — the full original quantity is still held |
| **PARTIALLY_CLOSED** | Some, but not all, of the lot has been matched by later opposite transactions |
| **CLOSED** | The entire lot has been matched — nothing remains open |

A lot moves OPEN → PARTIALLY_CLOSED → CLOSED strictly forward in time as matching consumes it; it never reopens. Independently of this lifecycle, a lot can also be tagged:

- **IN_TRANSIT** — part of its open quantity is currently mid-transfer between brokers
- **DISTRIBUTED** — its open quantity is currently split across more than one custody location at once
- **DEGRADED** — a data-quality issue was recorded against this specific lot (see [Data Quality](#data-quality-best-effort-not-all-or-nothing) below)

---

## 📅 Chronological Event Processing

LibreFolio replays every transaction for an asset **in chronological order**, classifying each into one event kind:

| Event | Effect |
|-------|--------|
| BUY | First closes any open SHORT lots on that broker; any remainder opens a new LONG lot |
| SELL | Closes open LONG lots in FIFO order on that broker; any remainder opens a new SHORT lot only where the broker allows shorting |
| Adjustment in / out | Same matching logic as BUY/SELL, at zero cost |
| SPLIT | Rescales quantity and unit cost for every open lot of the asset |
| Transfer (depart / arrive) | Moves custody of a lot's open quantity from one broker to another |

!!! info "Same-day ordering"

    When several events fall on the same date, LibreFolio always processes them in a fixed order — transfer departures, then transfer arrivals, then splits, then ordinary buys/sells/adjustments — so that same-day transfers and splits always see a consistent custody state.

---

## ⛏️ FIFO Matching

When a closing event (a SELL, or the opposite-direction leg of an adjustment) needs to consume a quantity $Q$, LibreFolio always matches against the **oldest still-open lot first**, on that same broker:

$$
\text{MatchOrder} = \text{sort by } (\text{OpeningDate}, \text{LotId})
$$

It walks this ordered list, closing quantity from the oldest lot until $Q$ is fully matched, only moving to the next-oldest lot once the current one is exhausted. Realized profit or loss is computed **per matched piece**, using the price carried by the exact lot fragment consumed:

$$
\text{RealizedPnL}_{\text{LONG}} = \text{MatchedQuantity} \times (\text{ClosePrice} - \text{LotUnitCost})
$$

$$
\text{RealizedPnL}_{\text{SHORT}} = \text{MatchedQuantity} \times (\text{LotUnitCost} - \text{ClosePrice})
$$

This is why two lots of the same asset, bought at different times and prices, can show very different realized results even though they are later matched on the same day at the same price — see the worked example in [FIFO Lot Analysis](fifo-lot-analysis.md).

---

## ✂️ Splits — Quantity/Price Rescaling

A stock split (or reverse split) with ratio $r$ rescales every **currently open** fragment of every affected lot:

$$
\text{NewQuantity} = \text{Quantity} \times r
\qquad
\text{NewUnitCost} = \frac{\text{UnitCost}}{r}
$$

The economic cost of the position is invariant across a split — only quantity and per-unit cost move, in opposite directions, so $\text{Quantity} \times \text{UnitCost}$ stays constant for every lot.

---

## 🚚 Transfers — Custody Movement, Not a Sale

A transfer between brokers is modeled as a **custody change**, never as a disposal:

- **Depart** — LibreFolio extracts the transferred quantity from the source broker in FIFO order. If the transfer takes more than one day to settle, it opens a temporary **in-transit** custody fragment in the meantime.
- **Arrive** — On arrival, the in-transit fragment closes and an equivalent fragment reopens at the destination broker, carrying over the **same quantity and unit cost**.

The lot's identity, opening date, and original cost never change because of a transfer — only *where* it is currently held. No profit or loss is ever realized by a transfer.

This custody history — which broker (or in transit) held a lot's open quantity, and how much, at every point in time — is exactly what powers the **Lot Life & Custody** timeline in the [FIFO Lots Analysis panel](../../../../user/dashboard/positions.md#fifo-lots-analysis): each bar segment is colored by the custody broker holding it, and its thickness reflects the quantity held during that segment.

---

## ⚠️ Data Quality: Best-Effort, Not All-or-Nothing {: #data-quality-best-effort-not-all-or-nothing }

If the transaction history contains something the engine cannot fully resolve — for example a closing transaction with no matching open lot on that broker, or a transfer whose paired leg is missing — LibreFolio does **not** abort the whole calculation. It records the specific issue, marks the affected lot(s) as degraded, and continues processing the rest of the history with the best available data.

The overall result is then marked **complete** or **degraded** as a whole, but charts and tables built on a degraded result still render normally for every lot that was **not** affected. You may see this reflected as a data-quality banner in the [FIFO Lots Analysis panel](../../../../user/dashboard/positions.md#fifo-lots-analysis).

---

## 🔗 Related

- 🔬 **[FIFO Lot Analysis](fifo-lot-analysis.md)** — Metrics derived from this engine: Open/Total Return per lot, qbq scaling, income allocation, worked example
- ⚙️ **[Portfolio Engine](../index.md)** — The complementary aggregate/WAC-based engine, and how the two relate
- 📊 **[Weighted Average Cost](../weighted-average-cost.md)** — Blended, position-level cost basis
- 🧬 **[FIFO Lot Engine (Developer Manual)](../../../../developer/backend/transactions/fifo_lot_engine.md)** — Implementation deep-dive: classes, event dispatch, code-level constraints
