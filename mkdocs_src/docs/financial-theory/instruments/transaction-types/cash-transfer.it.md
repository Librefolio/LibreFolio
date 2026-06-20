# ![](../../../static/icons/transactions/cash-transfer.png){: width="32" style="vertical-align: middle;" } Trasferimento di Liquidità

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-cash-transfer" alt="Transaction Form — Cash Transfer">
</div>

I **trasferimenti di liquidità** (bonifici) spostano denaro tra conti di broker. Il saldo diminuisce alla fonte e aumenta alla destinazione — non sono coinvolti asset.

---

## 🔑 Proprietà Chiave

| Proprietà | Da (origine) | A (destinazione) |
|----------|---------------|-------------------|
| **Codice** | `CASH_TRANSFER` | `CASH_TRANSFER` |
| **Effetto liquidità** | ⬇️ Diminuisce | ⬆️ Aumenta |
| **Effetto asset** | — | — |
| **Broker** | Broker di origine | Broker di destinazione |
| **Valuta** | Uguale su entrambi i lati | Uguale su entrambi i lati |
| **Evento fiscale** | No | No |

---

## 📊 Come Funziona

Un trasferimento di liquidità registra **due voci**: un prelievo presso il broker di origine e un deposito presso il broker di destinazione. Entrambi condividono la stessa valuta con importi speculari. I due lati possono avere **date differenti** — ad esempio, un bonifico inviato lunedì potrebbe arrivare mercoledì.

Scenari comuni:

- Trasferimento di fondi da un broker a un altro
- Spostamento di liquidità verso un conto di risparmio
- Invio di denaro tra conti personali

!!! note "Date differenti"

    A differenza dei trasferimenti di asset, dove entrambi i lati solitamente si regolano nella stessa data, i bonifici possono richiedere più giorni. LibreFolio supporta date separate per ogni lato.

---

## 🔀 Relazione con Depositi/Prelievi

Sotto il cofano, un Trasferimento di Liquidità è composto da un Prelievo e un Deposito. LibreFolio supporta:

| Operazione | Risultato |
|-----------|--------|
| **Frazionamento** (scollegamento) | Trasferimento Liquidità → Prelievo + Deposito indipendenti |
| **Promote** (collegamento) | Prelievo + Deposito → Trasferimento Liquidità |

**Vincoli di promozione**: stessa valuta, broker differenti, importi di liquidità con segno opposto.

---

## 🔗 Correlati

- 🔄 **[Trasferimento Asset](transfer.md)** — Spostamento di titoli (non asset)
- 💵 **[Deposito e Prelievo](deposit-withdrawal.md)** — Movimenti di liquidità unilaterali
- 💱 **[Conversione FX](fx-conversion.md)** — Cambio valuta
