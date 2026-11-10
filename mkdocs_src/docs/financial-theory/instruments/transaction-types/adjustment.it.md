# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Rettifica

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Modulo transazione — Rettifica">
</div>

Le **rettifiche** sono correzioni autonome della quantità di un asset. Sono senza movimenti di cassa nello schema delle transazioni fornito: la quantità cambia, la cassa no. A differenza dei tipi accoppiati (Trasferimento asset, Giroconto, Conversione FX), ogni rettifica è una riga singola e indipendente.

---

## 🔑 Proprietà principali

| Proprietà | Valore |
|----------|-------|
| **Codice** | `ADJUSTMENT` |
| **Effetto sulla cassa** | Nessuno — `ADJUSTMENT` non genera movimenti di cassa |
| **Effetto sull'asset** | Obbligatorio (± qualsiasi quantità) |
| **Evento fiscale** | No |

---

## 📊 Casi d'uso

Le rettifiche si usano quando nessun altro tipo di transazione è adatto:

- **Correzione di errori di importazione** — ad es. un'importazione del broker ha omesso un'operazione societaria
- **Split / split inversi** — rettificare la quantità senza movimenti di cassa
- **Regali** — ricevere o donare azioni
- **Posizioni ereditate o per successione** — i titoli arrivano in natura, senza movimenti di cassa del broker
- **Impostazione del saldo iniziale** — inizializzare un portafoglio da un'istantanea
- **Operazioni societarie** non coperte da altri tipi (scorpori, fusioni, ecc.)

Esempi importati: le istantanee `patrimonio` di Intesa Sanpaolo usano `ADJUSTMENT` positivi per inizializzare le posizioni esistenti con un `cost_basis_override` per unità; anche le righe di successione di Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) sono modellate come `ADJUSTMENT` positivi senza movimenti di cassa, non come `TRANSFER` accoppiati, perché il dossier di origine è esterno a LibreFolio.

!!! note "Promuovere a trasferimento asset"

    Due righe `ADJUSTMENT` con **quantità opposte**, **stesso asset** e **broker diversi** possono essere **promosse** a una coppia di trasferimenti asset. È utile quando hai inizialmente registrato rettifiche separate e in seguito vuoi collegarle come trasferimento asset. Nessuna delle due righe può essere collegata a un evento dell'asset, ad esempio uno split: un trasferimento non può portare quel collegamento, quindi LibreFolio non suggerisce né accetta una simile promozione.

---

## 📐 Impatto sul costo di carico

Le rettifiche con quantità positiva **aumentano** il numero di lotti (FIFO). Il costo di carico
dei lotti creati da una rettifica dipende dalla presenza di un **Override del costo di carico**:

- **Con override**: il valore specificato è usato come **costo di acquisizione per unità** (PMC — prezzo medio di carico), nella valuta del costo di carico stesso, che è anche la valuta del lotto FIFO aperto dalla rettifica (non la valuta della riga, spesso vuota poiché una rettifica non comporta movimenti di cassa); un override **pari a zero** registra un'acquisizione gratuita, come un airdrop
- **Senza override**: il lotto FIFO si apre a costo zero, ma il costo medio (PMC) tratta il costo come **sconosciuto**, non gratuito: le unità entrano nella posizione senza un costo, il suo PMC resta incompleto finché la posizione non viene chiusa, la Dashboard mostra il suo costo medio e il P&L latente come non disponibili, e un avviso di qualità dei dati indica l'asset (vedi [Override del costo di carico](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

Una rettifica positiva non può essere salvata senza un costo di carico: inseriscine uno, oppure scegli **Auto**, che memorizza il costo medio della posizione a cui le unità si uniscono (zero se non contiene ancora unità). Due tipi di righe possono comunque non averlo: una rettifica collegata a uno **split**, che Auto salva senza costo di carico perché lo split mantiene il costo già detenuto e lo distribuisce sulla nuova quantità, e le righe salvate prima che il costo di carico diventasse obbligatorio.

!!! info "Valore per unità"

    L'Override del costo di carico è il costo medio **per singola unità** dell'asset.
    Per ottenere il costo totale del blocco trasferito, moltiplica per la quantità:

    $$\text{Costo totale} = \text{PMC} \times \text{quantità}$$

### 📤 Rettifiche in uscita {: #outgoing-adjustments }

Le rettifiche con quantità negativa **riducono** la posizione: unità donate, inviate a un conto che LibreFolio non traccia o rimosse da una correzione. Una rettifica di questo tipo **non ha valore** — abbassa solo la quantità — quindi non accetta alcun **Override del costo di carico**:

- **Capitale e rendimenti**: nessun capitale esce, quindi la rettifica non rappresenta un flusso per la [base del capitale versato](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments), il TWRR o il MWRR: il valore delle unità esce dal NAV, e i rendimenti lo leggono come una perdita.
- **Costo medio**: la posizione rinuncia al costo medio di quelle unità, quindi il costo medio (PMC) di ciò che rimane non cambia.
- **Realizzato**: le unità escono a **zero**, quindi la rettifica realizza il negativo del loro costo, $-q \times \text{AverageCost}$ nella Dashboard. I lotti FIFO consumano i lotti aperti del broker partendo dai più vecchi, come fa una vendita, e li chiudono a zero: $q$ unità prelevate da un lotto realizzano $-q \times \text{LotUnitCost}$, senza proventi.

Per registrare unità uscite in cambio di denaro, usa una **Vendita**. L'API rifiuta un costo di carico su una rettifica in uscita (`costBasisNotAllowed`); un costo di carico memorizzato su tale riga da una versione precedente resta nel database ma viene ignorato. Una rettifica collegata a uno **split** è l'eccezione: lo split distribuisce solo il costo già detenuto sulla nuova quantità e non realizza nulla.

!!! example "Due azioni regalate"

    Ogni importo è nella valuta del report. Acquista 10 azioni a 50 (investito 500); il prezzo sale a 80, quindi la posizione vale 800 e il suo P&L totale è $800 - 500 = +300$. Una rettifica di −2 azioni ne regala due:

    - restano 8 azioni, del valore di $8 \times 80 = 640$; il capitale investito resta 500 e il costo medio 50;
    - realizzato: $0 - 2 \times 50 = -100$; P&L latente: $8 \times (80 - 50) = +240$;
    - P&L totale: $640 - 500 = +140$, cioè $-100 + 240$;
    - il TWRR del giorno: $640 / 800 - 1 = -20\%$, poiché nessun flusso compensa il valore uscito.

### 🏦 Costo di carico automatico su trasferimenti e seed

Quando si trasferiscono asset tra broker, LibreFolio **calcola automaticamente** l'Override del costo di carico sul lato ricevente usando il **prezzo medio di carico (PMC)** della posizione del broker di origine. I seed da importazione del broker possono invece impostarlo direttamente dal report di origine. Il valore è sempre **per unità**, non il valore totale della posizione; per un'istantanea con valore fiscale totale \(C\) e quantità \(q\), i plugin memorizzano:

$$\text{Override del costo di carico} = \frac{C}{q}$$

Questo registra capitale in natura, non P&L: la rettifica crea/modifica i lotti ma non crea un contributo in denaro né una plusvalenza realizzata.

!!! tip "Per saperne di più"

    Per la formula completa, esempi e casi limite, consulta la pagina dedicata:
    **[📊 Prezzo medio di carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ Quando eseguire l'override manualmente"

    La formula automatica funziona per il caso standard (stesso regime fiscale, nessun evento fiscale
    al trasferimento). Nei seguenti scenari l'utente deve impostare il valore manualmente:

    | Scenario | Cosa impostare |
    |----------|------------|
    | **Trasferimento normale** | Lascia il costo su **Auto** — calcolato dai tuoi acquisti |
    | **Imposta di uscita** | Valore di mercato alla data del trasferimento (specifico della giurisdizione) |
    | **Eredità** | Valore equo di mercato alla data del decesso (o costo di carico rivalutato) |
    | **Donazione** | Costo di carico originario del donatore (costo di carico di riporto) |
    | **Operazione societaria** | Costo di carico rettificato secondo i termini dell'operazione societaria |

    !!! warning "Responsabilità dell'utente"

        Quando esegue manualmente l'override del costo di carico, l'utente è responsabile della
        correttezza del valore. LibreFolio non convalida gli importi di override
        rispetto alle norme fiscali — consulta un consulente fiscale per indicazioni specifiche della giurisdizione.

---

## 🔗 Correlati

- 📊 **[Prezzo medio di carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Come viene calcolato il costo di carico automatico
- 🔄 **[Trasferimento asset](transfer.md)** — Due rettifiche collegate possono essere promosse a un trasferimento asset
- 🛒 **[Acquisto e vendita](buy-sell.md)** — Transazioni standard di asset con cassa
- 💰 **[Commissione e imposta](fee.md)** — Correzioni solo in cassa (usa Commissione/Imposta invece di Rettifica)
