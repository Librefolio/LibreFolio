# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Trasferimenti e Conversione FX

I **Trasferimenti** spostano asset tra portafogli senza una vendita, mentre le **Conversioni FX** scambiano una valuta con un'altra all'interno di un portafoglio.

---

## 🔑 Proprietà Principali

| Proprietà | Trasferimento In | Trasferimento Out | Conversione FX |
|----------|------------|-------------|---------------|
| **Codice** | `TRANSFER_IN` | `TRANSFER_OUT` | `FX_CONVERSION` |
| **Effetto cassa** | — | — | ⬆️⬇️ (swap) |
| **Effetto asset** | ⬆️ Aumenta | ⬇️ Diminuisce | — |
| **Evento fiscale** | Varia a seconda della giurisdizione | Varia | Varia |

---

## 🔄 Trasferimento In / Out

I trasferimenti rappresentano il movimento di asset tra conti di broker o portafogli **senza una vendita**. Scenari comuni:

- Spostamento di azioni da un broker a un altro
- Ricezione di asset in eredità
- Contributi in natura a un diverso tipo di conto (es. ISA, 401k)

!!! info "Preservazione del costo fiscale"

    Quando si trasferiscono asset, il **costo fiscale originale** deve essere preservato. Il trasferimento in sé non è un evento tassabile nella maggior parte delle giurisdizioni (sebbene le regole varino).

---

## 💱 Conversione FX

Scambi di valuta all'interno di un portafoglio:

$$
\text{Amount}_{target} = \text{Amount}_{source} \times \text{FX Rate} - \text{Fees}
$$

Le conversioni FX possono essere:

- **Esplicite**: L'utente converte deliberatamente le valute (es. EUR → USD)
- **Implicite**: Il broker converte automaticamente all'acquisto di un asset denominato in valuta estera

---

## 📊 Rettifica

Il tipo di transazione `ADJUSTMENT` è una categoria generica per le correzioni manuali dei saldi di cassa o degli asset. Casi d'uso:

- Correzione di errori di importazione
- Registrazione di operazioni societarie non coperte dai tipi standard
- Configurazione del saldo iniziale

---

## 🔗 Correlati

- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Transazioni standard di asset
- 💵 **[Deposito e Prelievo](deposit-withdrawal.md)** — Movimenti di cassa
- 💰 **[Tassi di cambio](../../../user/fx/index.md)** — Gestione dei tassi di cambio

# 🔄 Trasferimento Titoli

!!! warning "Traduzione in attesa"

    Questa pagina non è stata ancora tradotta. Consulta la [versione inglese](transfer.en.md).
