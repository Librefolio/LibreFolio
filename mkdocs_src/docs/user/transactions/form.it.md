# 📝 Modulo Transazione

Il Modulo Transazione si apre ogni volta che **crei** o **modifichi** una transazione. Si adatta dinamicamente al tipo di transazione selezionato, mostrando solo i campi pertinenti a quell'operazione.

---

## 🏷️ Tipi di Transazione

| Tipo | Icona | Descrizione |
|------|------|-------------|
| **BUY** | 🟢 | Acquisto di un asset |
| **SELL** | 🔴 | Vendita di un asset |
| **DIVIDEND** | 💰 | Dividendo in contanti ricevuto |
| **INTEREST** | 📈 | Interessi (obbligazioni, P2P) |
| **FEE** | 💸 | Commissione del broker o costo della piattaforma |
| **DEPOSIT** | ⬇️ | Contanti depositati nel conto del broker |
| **WITHDRAWAL** | ⬆️ | Contanti prelevati dal conto del broker |
| **ADJUSTMENT** | 🔧 | Correzione manuale di quantità o prezzo |
| **TRANSFER** | 🔄 | Asset spostato tra due dei tuoi broker (composita) |
| **FX_CONVERSION** | 💱 | Cambio valuta all'interno di un broker (composita) |

Consulta [Financial Theory → Transaction Types](../../financial-theory/instruments/transaction-types/index.md) per la definizione concettuale di ogni tipo.

---

## 📋 Campi Comuni

Questi campi appaiono per **tutti** i tipi di transazione:

| Campo | Obbligatorio | Descrizione |
|-------|:--------:|-------------|
| **Type** | ✅ | Selettore del tipo di transazione |
| **Date** | ✅ | Data di esecuzione (AAAA-MM-GG) |
| **Currency** | ✅ | Valuta della transazione |
| **Amount** | ✅ | Importo lordo totale |
| **Fee** | ❌ | Commissione di intermediazione o tassa trattenuta |
| **Notes** | ❌ | Nota a testo libero |

---

## 🏦 Operazioni su Asset (BUY / SELL / TRANSFER)

Quando è coinvolto un asset, appaiono campi aggiuntivi:

| Campo | Obbligatorio | Descrizione |
|-------|:--------:|-------------|
| **Asset** | ✅ | L'asset oggetto dello scambio (ricercabile) |
| **Quantity** | ✅ | Numero di unità |
| **Unit Price** | ✅ | Prezzo per unità |

!!! tip "Calcolo automatico"

    Se compili **Quantity** e **Unit Price**, l'**Amount** viene calcolato automaticamente, e viceversa.

---

## 💰 Anteprima WAC

Per le transazioni **BUY** e **SELL**, un pannello di **anteprima WAC (Weighted Average Cost)** appare sotto i campi principali. Mostra in tempo reale:

- Il **costo medio attuale** prima di questa transazione
- Il **nuovo costo medio previsto** dopo il salvataggio
- Il **guadagno/perdita realizzato** (solo per SELL)

Questa anteprima viene calcolata live — non è necessario salvare preventivamente.

!!! note "Override manuale WAC"

    Puoi cambiare la modalità WAC da **Auto** (calcolato da LibreFolio) a **Manual** (inserisci il tuo costo medio). Questo è utile quando si migrano dati storici da un altro sistema.

---

## 🔄 Transazioni Composite

**TRANSFER** e **FX_CONVERSION** sono *composite* — collegano due componenti:

- **TRANSFER**: specifica un **broker di origine** e un **broker di destinazione**, oltre all'asset e alla quantità. LibreFolio registra entrambe le componenti in modo atomico.
- **FX_CONVERSION**: specifica l'**importo della valuta di origine** e l'**importo della valuta di destinazione** all'interno dello stesso broker.

Per frazionare una transazione composita in due transazioni indipendenti, usa l'operazione [Split](index.md#split) nella tabella delle transazioni.

---

## ✅ Validazione

Il modulo effettua la validazione al salvataggio:

- Le date devono essere in un intervallo valido (per impostazione predefinita, non nel futuro).
- Quantità e prezzo devono essere positivi.
- Per SELL: la quantità non può superare la posizione attuale (avviso, non un blocco rigido).
- L'importo deve corrispondere a quantità × prezzo entro una piccola tolleranza.

---

## 🔗 Correlati

- 📋 **[Tabella Transazioni](index.md)** — Vista elenco, filtraggio, operazioni massive
- 📥 **[Importazione dal Broker](import/index.md)** — Salta l'inserimento manuale con l'importazione BRIM
