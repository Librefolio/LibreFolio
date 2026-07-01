# ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Rettifica

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Modulo Transazione — Rettifica">
</div>

Le **Rettifiche** sono un tipo di transazione generica per correzioni manuali dei saldi di cassa o di asset. A differenza dei tipi accoppiati (Trasferimento Asset, Trasferimento di Cassa, Conversione FX), le rettifiche sono **autonome**: ogni rettifica è una riga singola e indipendente.

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

- **Correzione di errori di importazione** — ad es., l'importazione dal broker ha omesso un'operazione societaria
- **Frazionamento / frazionamento inverso** — regolazione della quantità senza movimento di cassa
- **Regali** — ricezione o donazione di azioni
- **Configurazione saldo iniziale** — avvio di un portafoglio partendo da uno snapshot
- **Operazioni societarie** non coperte da altri tipi (spin-off, fusioni, ecc.)

!!! note "Promuovi a Trasferimento"

    Due righe `ADJUSTMENT` con **quantità opposte**, **stesso asset** e **broker differenti** possono essere **promosse** a una coppia di Trasferimento Asset. Questo è utile quando inizialmente sono state registrate rettifiche separate e successivamente si desidera collegarle come un Trasferimento Asset.

---

## 📐 Impatto sul Costo di Carico

Le rettifiche con quantità positiva **aumentano** la quantità dei lotti (FIFO). Il costo di carico per i lotti creati tramite rettifica dipende dalla presenza di un **Cost Basis Override**:

- **Con override**: il valore specificato viene utilizzato come **costo di acquisizione per unità** (PMC — Prezzo Medio di Carico)
- **Senza override**: il lotto viene creato con costo zero (acquisizione gratuita — ad es. regali, airdrop)

!!! info "Valore per unità"

    Il Cost Basis Override è il costo medio **per singola unità** dell'asset.
    Per ottenere il costo totale del blocco trasferito, moltiplicare per la quantità:

    $$\text{Costo totale} = \text{PMC} \times \text{quantità}$$

### 🏦 Costo di Carico Automatico nei Trasferimenti

Quando si trasferiscono asset tra broker, LibreFolio **calcola automaticamente** il Cost Basis Override lato ricevente utilizzando il **Prezzo Medio di Carico (PMC)** della posizione del broker di origine.

!!! tip "Scopri di più"

    Per la formula completa, esempi e casi particolari, consulta la pagina dedicata:
    **[📊 Prezzo Medio di Carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Quando effettuare l'Override Manualmente"

    La formula automatica funziona per il caso standard (stesso regime fiscale, nessun evento fiscale al trasferimento). Nei seguenti scenari l'utente deve impostare il valore manualmente:

    | Scenario | Cosa impostare |
    |----------|------------|
    | **Trasferimento normale** | Lasciare vuoto — calcolato automaticamente |
    | **Exit Tax** | Valore di mercato alla data del trasferimento (specifico per giurisdizione) |
    | **Eredità** | Valore equo di mercato alla data del decesso (o stepped-up basis) |
    | **Regalo** | Costo di carico originale del donante (carryover basis) |
    | **Operazione societaria** | Costo di carico rettificato secondo i termini dell'operazione societaria |

    !!! warning "Responsabilità dell'Utente"

    Quando si effettua l'override manuale del costo di carico, l'utente è responsabile della correttezza del valore. LibreFolio non valida gli importi di override rispetto alle norme fiscali — consultare un consulente fiscale per indicazioni specifiche per la propria giurisdizione.

---

## 🔗 Correlati

- 📊 **[Prezzo Medio di Carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Come viene calcolato il costo di carico automatico
- 🔄 **[Trasferimento Asset](transfer.md)** — Due rettifiche collegate possono essere promosse a un Trasferimento Asset
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Transazioni standard di asset con cassa
- 💰 **[Commissioni e Tasse](fee.md)** — Correzioni di sola cassa (usare Commissioni/Tasse invece di Rettifica)
