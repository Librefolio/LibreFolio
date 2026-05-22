# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } Conversione FX

Le **conversioni valutarie (FX)** scambiano una valuta con un'altra all'interno dello **stesso conto broker**. Il saldo di una valuta diminuisce mentre quello di un'altra aumenta — non vi è alcun cambiamento di titoli o broker.

---

## 🔑 Proprietà Principali

| Proprietà | Da (sorgente) | A (destinazione) |
|----------|---------------|-------------|
| **Codice** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Effetto cassa** | ⬇️ Valuta sorgente | ⬆️ Valuta destinazione |
| **Effetto asset** | — | — |
| **Broker** | Stesso per entrambi i lati | Stesso per entrambi i lati |
| **Valuta** | Diversa per ogni lato | Diversa per ogni lato |
| **Evento fiscale** | Varia a seconda della giurisdizione | Varia |

---

## 📊 Come Funziona

Una conversione FX registra **due voci** sullo stesso broker con **valute diverse**. Il tasso di conversione è implicito negli importi:

$$
FX_{rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
$$

Le conversioni FX possono essere:

- **Esplicite**: L'utente converte deliberatamente le valute (es. EUR → USD prima di acquistare azioni USA)
- **Implicite**: Il broker converte automaticamente l'importo durante l'acquisto di un asset denominato in valuta estera

!!! info "Implicit FX and Fees"

    Quando un broker converte automaticamente la valuta, il tasso effettivo spesso include uno spread. La differenza tra il tasso di mercato e il tasso effettivo è essenzialmente una commissione nascosta:

    $$
    \text{Implicit Fee} = \lvert\text{Amount}_{source}\rvert \times (\text{Market Rate} - \text{Effective Rate})
    $$

---

## 📈 Tasso Implicito e Spread del Broker

LibreFolio calcola automaticamente il **tasso di cambio implicito** dai due importi:

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

Questo viene confrontato con il **tasso di mercato** del sottosistema FX alla data della transazione. La differenza è lo **spread del broker**:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{%Spread} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! warning "Market Rate Availability"

    Il confronto con il tasso di mercato richiede che la coppia FX pertinente sia configurata nel sistema FX di LibreFolio. Se la coppia non è configurata o non esiste alcun tasso per la data della transazione, verrà mostrato solo il tasso implicito.

---

## 🔀 Relazione con Depositi/Prelievi

Sotto il cofano, una Conversione FX è composta da un Prelievo (valuta sorgente) e un Deposito (valuta destinazione). LibreFolio supporta:

| Operazione | Risultato |
|-----------|--------|
| **Split** (scollega) | Conversione FX → Prelievo + Deposito indipendenti |
| **Promote** (collega) | Prelievo + Deposito → Conversione FX |

**Vincoli per il Promote**: valute diverse, stesso broker.

---

## 🔗 Correlati

- 💵 **[Deposito e Prelievo](deposit-withdrawal.md)** — Movimenti di cassa unilaterali
- 🔄 **[Trasferimento Asset](transfer.md)** — Spostamento di titoli tra broker
- 🏦 **[Trasferimento di Cassa](cash-transfer.md)** — Bonifici tra broker

---

*Vedi anche: [💱 Tassi FX](../../../user/fx/index.md) — come configurare e sincronizzare i tassi di cambio in LibreFolio.*
