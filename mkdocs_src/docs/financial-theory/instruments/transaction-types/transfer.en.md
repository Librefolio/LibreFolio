# 🔄 ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Asset Transfer

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-transfer" alt="Transaction Form — TRANSFER">
</div>

**Asset transfers** move securities between broker accounts **without a sale**. The position leaves one broker and arrives at another — no cash changes hands, and in most jurisdictions this is not a taxable event.

---

## 🔑 Key Properties

| Property | From (source) | To (destination) |
|----------|---------------|-------------------|
| **Code** | `TRANSFER` | `TRANSFER` |
| **Cash effect** | — | — |
| **Asset effect** | ⬇️ Decreases | ⬆️ Increases |
| **Broker** | Source broker | Destination broker |
| **Tax event** | Varies by jurisdiction | Varies |

---

## 📊 How It Works

An asset transfer records **two entries**: one debit at the source broker and one credit at the destination broker. Both reference the **same asset** with mirrored quantities.

Common scenarios:

- Moving shares from one broker to another
- Inheriting assets
- In-kind contributions to a different account type (e.g., ISA, 401k)

!!! info "Cost Basis Preservation"

    When transferring assets, the **original cost basis** should be preserved. The transfer itself is not a taxable event in most jurisdictions (though rules vary). LibreFolio allows an optional **cost basis override** on the receiving side.

    See **[📊 Weighted Average Cost (WAC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** for how the automatic cost basis is computed.

---

## 🔀 Relationship with Adjustments

A Transfer is stored as two `TRANSFER` rows, one per broker, each linked to the other through `related_transaction_id`. Splitting the pair turns the two rows into independent `ADJUSTMENT`s, and promoting two Adjustments turns them back into a Transfer:

| Operation | Result |
|-----------|--------|
| **Split** (unlink) | Transfer → two independent Adjustments |
| **Promote** (link) | Two Adjustments → Transfer |

**Cost basis on split and promote**: on a split, the incoming Adjustment keeps its cost basis, and the outgoing one takes the sending broker's average cost on the transfer date as its own, so its units are handed over at cost rather than written off (see [Outgoing Adjustments](adjustment.md#outgoing-adjustments)); when that average needs a missing exchange rate, the split is refused. On a promote, the outgoing Adjustment's cost basis is dropped, since the sending side of a Transfer carries none.

**Promote constraints**: same asset, different brokers, opposite quantities, and neither row linked to an asset event (a split, for instance), since a transfer cannot carry that link.

---

## 👵 Succession and Untracked Source Brokers

A true `TRANSFER` needs two brokers in LibreFolio: source and destination. If the source dossier is outside LibreFolio, the incoming leg is better modeled as a positive cashless `ADJUSTMENT` with a per-unit `cost_basis_override`, not as a paired transfer. Crédit Agricole succession rows (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) use this pattern: the inherited securities enter as in-kind capital, no cash `DEPOSIT` is created, and the origin causale remains in the description for auditability.

---

## 🔗 Related

- 📊 **[Weighted Average Cost](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — How cost basis is computed on transfers
- 🏦 **[Cash Transfer](cash-transfer.md)** — Wire transfers (cash, not assets)
- 💱 **[FX Conversion](fx-conversion.md)** — Currency exchange
- 📊 **[Adjustment](adjustment.md)** — Manual corrections
