# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Depositi e Prelievi ![](../../../static/icons/transactions/withdrawal.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-deposit" alt="Transaction Form — DEPOSIT">
</div>

I **depositi** e i **prelievi** tracciano il movimento di liquidità in entrata e in uscita da un conto broker. Non coinvolgono alcun asset — cambia solo il saldo di cassa.

---

## 🔑 Proprietà Principali

| Proprietà | Deposito | Prelievo |
|----------|---------|------------|
| **Codice** | `DEPOSIT` | `WITHDRAWAL` |
| **Effetto cassa** | ⬆️ Aumenta il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Evento fiscale** | No | No |

---

## 💡 Perché sono Importanti

I depositi e i prelievi non modificano il valore di mercato del tuo portafoglio, ma sono fondamentali per la **misurazione delle performance**:

- **Money-Weighted Return (MWR)**: tiene conto della tempistica e dell'entità dei flussi di cassa — è direttamente influenzato da depositi/prelievi
- **Time-Weighted Return (TWR)**: elimina l'effetto dei flussi di cassa per misurare la performance "pura" del portafoglio

Senza un tracciamento accurato di depositi e prelievi, è impossibile distinguere tra i rendimenti *generati* dal portafoglio e i rendimenti *causati* dall'aggiunta o rimozione di liquidità.

!!! tip "Learn more"

    Consulta **[📈 Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** per le formule e la metodologia.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Calcolo TWR vs MWR
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Transazioni che utilizzano la liquidità depositata
