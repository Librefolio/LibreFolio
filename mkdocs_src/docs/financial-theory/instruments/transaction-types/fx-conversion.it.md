# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } Conversione valutaria

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-fxconversion" alt="Modulo Transazione — Conversione valutaria">
</div>

Le **conversioni valutarie** scambiano una valuta con un'altra all'interno dello **stesso conto broker**. Il saldo di una valuta diminuisce mentre quello di un'altra aumenta — non vi è alcun cambiamento di titoli o di broker.

---

## 🔑 Proprietà Principali

| Proprietà | Da (origine) | A (destinazione) |
|----------|---------------|-------------|
| **Codice** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Effetto Cassa** | ⬇️ Valuta di origine | ⬆️ Valuta di destinazione |
| **Effetto Asset** | — | — |
| **Broker** | Lo stesso per entrambi | Lo stesso per entrambi |
| **Valuta** | Diversa su ciascun lato | Diversa su ciascun lato |
| **Evento Fiscale** | Varia in base alla giurisdizione | Varia |

---

## 📊 Come Funziona

Una conversione valutaria registra **due registrazioni** sullo stesso broker con **valute diverse**. Il tasso di conversione è implicito negli importi:

$$
FX_{rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
$$

Le conversioni valutarie possono essere:

- **Esplicite**: L'utente converte deliberatamente le valute (ad es. EUR → USD prima di acquistare azioni USA)
- **Implicite**: Il broker converte automaticamente quando si acquista un asset denominato in valuta estera

!!! info "Conversione FX Implicita e Commissioni"

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

Questo valore viene confrontato con il **tasso di mercato** del sottosistema FX alla data della transazione. La differenza è lo **spread del broker**:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{%Spread} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! warning "Disponibilità del Tasso di Mercato"

    Il confronto con il tasso di mercato richiede che la relativa coppia FX sia configurata nel sistema FX di LibreFolio. Se la coppia non è configurata o non esiste un tasso per la data della transazione, verrà mostrato solo il tasso implicito.

---

## 🔀 Relazione con Depositi/Prelievi

Sotto il cofano, una Conversione valutaria è composta da un Prelievo (valuta di origine) e un Deposito (valuta di destinazione). LibreFolio supporta:

| Operazione | Risultato |
|-----------|--------|
| **Split** (scollega) | Conversione valutaria → Prelievo + Deposito indipendenti |
| **Promote** (collega) | Prelievo + Deposito → Conversione valutaria |

**Vincoli Promote**: valute diverse, stesso broker.

---

## 🔗 Correlati

- 💵 **[Deposito e Prelievo](deposit-withdrawal.md)** — Movimenti di cassa unilaterali
- 🔄 **[Trasferimento Asset](transfer.md)** — Spostamento di titoli tra broker
- 🏦 **[Trasferimento di Cassa](cash-transfer.md)** — Bonifici tra broker

---

*Vedi anche: [💱 Tassi FX](../../../user/fx/index.md) — come configurare e sincronizzare i tassi di cambio in LibreFolio.*
