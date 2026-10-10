# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

L'importatore **Generic CSV** legge un file CSV che prepari tu stesso. Assegna alle sue colonne i nomi
indicati nel [riferimento colonne](#column-reference) — almeno `date` e `type` — e LibreFolio le
riconosce dai loro nomi: non c'è nulla da mappare manualmente.

## 🎯 Quando usarlo

- Il tuo broker non è nell'[elenco supportato](index.md).
- Il tuo broker ha modificato l'esportazione e il suo importatore non la legge ancora.
- Tieni un tuo foglio di calcolo, oppure uno script scrive il CSV per te.

## ⚙️ Come importarlo

1. **Prepara il file.** Salvalo come `.csv` (da Excel, salva una copia come CSV). La sua prima riga
   assegna i nomi alle colonne, come nel [riferimento colonne](#column-reference); le altre colonne vengono ignorate.
2. **Caricalo** nella **[Procedura guidata di importazione](how-to.md)** e assegnalo al suo broker.
3. **Controlla il plugin** in **Seleziona file**: se **Generic CSV** non è già selezionato, scegliilo
   nella colonna **Plugin** del file.
4. **Analizza e controlla.** Ogni riga diventa una transazione.

!!! tip "Un file per broker — non un file per valuta"

    Ogni riga di un file viene importata nel broker che assegni a quel file, quindi non mescolare
    mai due broker in un unico CSV. Righe in valute diverse possono condividere lo stesso file,
    poiché ogni riga porta con sé la propria `currency`; puoi anche dividere la cronologia di un
    broker in più file, ad esempio uno per anno, e importarli insieme.

### 🧯 Se qualcosa va storto

- **"required column 'date' not found"** (o `type`): la prima riga non contiene quella colonna, oppure
  le assegna un nome diverso. Aggiungila, o rinomina la colonna con un nome accettato, e carica di nuovo il file.
- **Manca una riga**: le righe che LibreFolio non riesce a leggere — un tipo sconosciuto, una data in
  un formato sconosciuto, una `currency` vuota — vengono saltate ed elencate tra gli avvisi del
  passaggio **Analisi**; le righe con un segno errato appaiono come problemi di validazione. Correggile nel file e caricalo di nuovo.
- **Il workspace bulk richiede un costo su una riga `ADJUSTMENT`**: inserisci il costo di **una**
  unità, non il valore totale della posizione.

---

## 🔄 Convertire un report personalizzato

Se i tuoi dati provengono da un altro strumento, un breve script può convertirli in un Generic CSV.
La **[specifica tecnica di Generic CSV](../../../developer/backend/brim/generic_csv.md)** descrive
il formato completo — segni, quale tipo usare e quando, esempi svolti. Puoi incollarla in un
assistente AI (ChatGPT, Claude, Gemini…) insieme ad alcune righe di esempio del tuo file e chiedere lo script.

---

## 📋 Riferimento colonne {: #column-reference }

Queste sono le colonne che LibreFolio riconosce in un file Generic CSV. I nomi delle colonne non distinguono tra maiuscole e minuscole e gli spazi che li circondano vengono ignorati.

| Colonna | Obbligatoria? | Alias accettati | Descrizione |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Sempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Data della transazione |
| **`type`** | ✅ Sempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo di transazione — vedi i valori di seguito |
| **`quantity`** | Obbligatoria per BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Numero di unità. **Negativo per SELL, positivo per BUY.** |
| **`amount`** | Obbligatoria per la maggior parte dei tipi | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impatto sulla liquidità. **Negativo quando la liquidità esce, positivo quando entra.** Vuoto per ADJUSTMENT. |
| **`currency`** | Opzionale (valore predefinito EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Codice valuta ISO 4217. EUR si applica solo quando il file non ha una colonna valuta: se ce l'ha, compilala su ogni riga con un `amount`, altrimenti quella riga viene saltata. |
| **`asset`** | Obbligatoria per BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN o un nome coerente per asset non quotati |
| **`description`** | Opzionale | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Note in testo libero |

### 🏷️ Valori `type` validi

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "Non supportati: TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Queste operazioni richiedono due righe collegate, cosa che un CSV non può esprimere: tali righe
    vengono saltate con un avviso. Inseriscile manualmente dalla pagina Transazioni, oppure usa l'importatore del tuo broker.

---

## 🔗 Correlati

- 🧙 **[Come importare](how-to.md)** — la procedura guidata di importazione, passo dopo passo
- 🏦 **[Broker supportati](index.md)** — controlla prima se il tuo broker ha il suo importatore
- 🛠️ **[Specifica tecnica di Generic CSV](../../../developer/backend/brim/generic_csv.md)** — il formato completo, per script e sviluppatori
