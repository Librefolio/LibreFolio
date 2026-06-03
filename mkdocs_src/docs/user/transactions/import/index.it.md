# 📥 Importazione da Broker (BRIM)

**BRIM** (Broker Report Import Module) ti permette di importare le transazioni direttamente dai file di esportazione del tuo broker — senza necessità di inserimento manuale. Carica un report CSV e LibreFolio analizzerà, mapperà e importerà tutte le transazioni in un unico flusso.

---

## 🚀 Come Importare

1. Esporta un report delle transazioni dal tuo broker (solitamente un file CSV — consulta il centro assistenza del tuo broker).
2. In LibreFolio, naviga alla pagina **Broker**.
3. Clicca sul pulsante **Import** (:material-file-upload:) nell'intestazione del broker.
4. Si aprirà la **finestra modale di importazione**.
5. Trascina e rilascia (**drag & drop**) o clicca per selezionare il tuo file.
6. LibreFolio **rileva automaticamente** il formato del broker e mostra un'**anteprima** delle transazioni analizzate.
7. Revisiona l'anteprima — verifica che date, importi e nomi degli asset siano corretti.
8. Clicca su **Import** per confermare tutte le transazioni.

!!! tip "Puoi usare anche la sezione Files"

    La sezione **[Files](../../files/index.md)** (scheda BRIM) ti permette di gestire i report dei broker caricati in modo centralizzato, re-importarli o eliminarli.

---

## 🏦 Broker Supportati

| Broker | Pagina |
|--------|------|
| Interactive Brokers (IBKR) | [→](ibkr.md) |
| Degiro | [→](degiro.md) |
| eToro | [→](etoro.md) |
| Directa SIM | [→](directa.md) |
| Charles Schwab | [→](schwab.md) |
| Revolut | [→](revolut.md) |
| Coinbase | [→](coinbase.md) |
| Freetrade | [→](freetrade.md) |
| Finpension | [→](finpension.md) |
| Trading212 | [→](trading212.md) |
| Generic CSV | [→](generic-csv.md) |

!!! note "Tutti i provider sono in Beta"

    I plugin di importazione sono mantenuti dalla community e migliorano nel tempo. Se un formato di report specifico presenta anomalie, il provider **[Generic CSV](generic-csv.md)** consente la mappatura manuale delle colonne come fallback.

---

## 🗂️ Mappatura Asset

Durante la fase di anteprima, LibreFolio tenta di **associare automaticamente** ogni nome di asset presente nel tuo report a un asset già esistente nella tua libreria.

- ✅ **Associato** — verrà importato nell'asset esistente.
- ⚠️ **Non associato** — seleziona o crea l'asset di destinazione prima dell'importazione.
- ❌ **Errore** — la riga non è stata analizzata correttamente.

---

## ♻️ Rilevamento Duplicati

BRIM verifica la presenza di **transazioni duplicate** basandosi su data, tipo, asset, quantità e importo. Le righe duplicate vengono segnalate nell'anteprima — puoi scegliere di saltarle o forzarne l'importazione.

---

## 🔗 Correlati

- 📋 **[Tabella Transazioni](../index.md)** — Visualizza e gestisci le transazioni importate
- 🗂️ **[Files](../../files/index.md)** — Gestisci i file dei report dei broker caricati
- 🏦 **[Brokers](../../brokers/index.md)** — Configura prima i tuoi account broker
