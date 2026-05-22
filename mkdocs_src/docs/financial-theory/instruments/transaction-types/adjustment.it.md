# ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Rettifica

Le **Rettifiche** sono un tipo di transazione generico per correzioni manuali dei saldi di cassa o degli asset. A differenza dei tipi a coppie (Trasferimento, Trasferimento di Liquidità, Conversione FX), le rettifiche sono **autonome**: ogni rettifica è una riga singola e indipendente.

---

## 🔑 Proprietà Chiave

| Proprietà | Valore |
|----------|-------|
| **Codice** | `ADJUSTMENT` |
| **Effetto cassa** | Opzionale (± qualsiasi importo) |
| **Effetto asset** | Obbligatorio (± qualsiasi quantità) |
| **Evento fiscale** | No |

---

## 📊 Casi d'Uso

Le rettifiche vengono utilizzate quando nessun altro tipo di transazione è adatto:

- **Correzione di errori di importazione** — ad esempio, l'importazione di un broker ha omesso un'operazione societaria
- **Frazionamento / frazionamento inverso** — rettifica della quantità senza movimento di cassa
- **Regali** — ricezione o donazione di azioni
- **Configurazione del saldo iniziale** — inizializzazione di un portafoglio da uno snapshot
- **Operazioni societarie** non coperte da altri tipi (spin-off, fusioni, ecc.)

!!! note "Promuovi a Trasferimento"

    Due righe `ADJUSTMENT` con **quantità opposte**, **stesso asset** e **broker diversi** possono essere **promosse** a una coppia di Asset Transfer. Questo è utile quando inizialmente sono state registrate rettifiche separate e successivamente si desidera collegarle come un trasferimento.

---

## 📐 Impatto sul Cost Basis

Le rettifiche con quantità positiva **aumentano** il numero di lotti (FIFO). Il Cost Basis per i lotti creati tramite rettifica dipende dalla presenza di un **Cost Basis Override**:

- **Con override**: il valore specificato viene utilizzato come **costo di acquisizione per unità** (WAC — Weighted Average Cost)
- **Senza override**: il lotto viene creato con costo zero (acquisizione gratuita — ad esempio regali, airdrop)

!!! info "Valore per unità"

    Il Cost Basis Override è il costo medio **per singola unità** dell'asset.
    Per ottenere il costo totale del blocco trasferito, moltiplicare per la quantità:

    $$\text{Costo totale} = \text{WAC} \times \text{quantità}$$

### 🏦 Cost Basis Automatico nei Trasferimenti

Quando si trasferiscono asset tra broker, LibreFolio **calcola automaticamente** il
Cost Basis Override sul lato ricevente utilizzando il **Weighted Average Cost (WAC)** della
posizione del broker di origine.

!!! tip "Scopri di più"

    Per la formula completa, gli esempi e i casi limite, consulta la pagina dedicata:
    **[📊 Weighted Average Cost (WAC)](../../portfolio-theory/weighted-average-cost.md)**

??? note "✏️ Quando Sovrascrivere Manualmente"

 La formula automatica funziona per il caso standard (stesso regime fiscale, nessun evento
 fiscale al momento del trasferimento). Nei seguenti scenari l'utente deve impostare il valore manualmente:

 | Scenario | Cosa impostare |
 |----------|------------|
 | **Trasferimento normale** | Lasciare vuoto — calcolato automaticamente |
 | **Exit Tax** | Valore di mercato alla data del trasferimento (specifico per giurisdizione) |
 | **Eredità** | Valore equo di mercato alla data del decesso (o stepped-up basis) |
 | **Regalo** | Cost Basis originale del donatore (carryover basis) |
 | **Operazione societaria** | Cost Basis rettificato secondo i termini dell'operazione societaria |

 !!! warning "Responsabilità dell'Utente"

 Quando si sovrascrive manualmente il Cost Basis, l'utente è responsabile della
 correttezza del valore. LibreFolio non valida gli importi di override
 rispetto alle norme fiscali — consulta un consulente fiscale per indicazioni specifiche per la tua giurisdizione.

---

## 🔗 Correlati

- 📊 **[Weighted Average Cost (WAC)](../../portfolio-theory/weighted-average-cost.md)** — Come viene calcolato il Cost Basis automatico
- 🔄 **[Asset Transfer](transfer.md)** — Due rettifiche collegate possono essere promosse a un trasferimento
- 🛒 **[Buy & Sell](buy-sell.md)** — Transazioni standard di asset con cassa
- 💰 **[Fee & Tax](fee.md)** — Correzioni solo di cassa (utilizzare Fee/Tax invece di Rettifica)
