# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

L'importatore **Generic CSV** legge un file CSV che hai preparato tu. Assegna alle sue colonne i nomi
indicati nel [riferimento delle colonne](#column-reference) — almeno `date` e `type` — e LibreFolio le
riconosce dai loro nomi: non c'è nulla da mappare a mano.

## 🎯 Quando usarlo

- Il tuo broker non è nell'[elenco dei broker supportati](index.md).
- Il tuo broker ha cambiato il formato di esportazione e il suo importatore non lo legge ancora.
- Tieni un tuo foglio di calcolo, oppure uno script scrive il CSV per te.

## ⚙️ Come importarlo

1. **Prepara il file.** Salvalo come `.csv` (da Excel, salva una copia come CSV). La sua prima riga
   contiene i nomi delle colonne, come nel [riferimento delle colonne](#column-reference); le altre
   colonne vengono ignorate.
2. **Caricalo** nella **[procedura guidata di importazione](how-to.md)** e assegnalo al suo broker.
3. **Controlla il plugin** in **Seleziona file**: se **Generic CSV** non è già scelto, sceglilo
   nella colonna **Plugin** del file.
4. **Analizza e controlla.** Ogni riga diventa una transazione.

!!! tip "Un file per broker — non un file per valuta"

    Ogni riga di un file viene importata nel broker che assegni a quel file, quindi non mescolare mai
    due broker in un unico CSV. Righe in valute diverse possono stare nello stesso file, dato che ogni
    riga porta la propria `currency`; puoi anche dividere la cronologia di un broker in più file, uno
    per anno ad esempio, e importarli insieme.

!!! tip "Più colonne data? Usa la data dell'operazione"

    LibreFolio legge **una sola** colonna data per file, mai due. Se l'intestazione contiene più colonne
    con un nome di data accettato (ad esempio `trade_date` e `settlement_date`, vedi il
    [riferimento delle colonne](#column-reference)), prende **la prima, leggendo da sinistra a destra**,
    e ignora le altre. Una colonna con un altro nome, come `order date`, non viene letta affatto.

    Nella colonna data inserisci la **data dell'operazione**: il giorno in cui è stato effettuato lo
    scambio o la transazione, non il giorno di regolamento o di registrazione, che può arrivare giorni
    dopo. Questo è particolarmente importante quando scrivi il CSV a mano o lo fai scrivere a un'altra
    IA: dille di usare la data dell'operazione e di lasciare fuori dal file le altre date.

### 🧯 Se qualcosa va storto

- **"colonna obbligatoria 'date' non trovata"** (o `type`): la prima riga non ha quella colonna, oppure
  la nomina diversamente. Aggiungila, o rinomina la colonna con un nome accettato, e carica di nuovo il
  file.
- **Manca una riga**: le righe che LibreFolio non riesce a leggere — un tipo sconosciuto, una data in un
  formato sconosciuto, una `currency` vuota — vengono saltate ed elencate tra gli avvisi della fase di
  **analisi**; le righe con un segno sbagliato compaiono come problemi di validazione. Correggile nel
  file e caricalo di nuovo.
- **Il workspace bulk richiede un costo su una riga `ADJUSTMENT`**: inserisci il costo di **una**
  unità, non il valore totale della posizione. Solo una riga che aggiunge unità lo richiede: una che
  rimuove unità (quantità negativa) non richiede alcun valore.

### 📅 Formato della data {: #day-month-order }

Una data come `03/04/2025` può significare 3 aprile o 4 marzo, e un anno può essere scritto con due cifre
(`03/04/26`). LibreFolio ti permette di scegliere come l'importatore Generic CSV legge le date dei tuoi
file. La scelta è solo tua: gli altri utenti dello stesso LibreFolio mantengono la propria scelta.

Apri **Impostazioni › Plugin**, trova **Importazioni broker** e imposta il **Formato data**. Ogni opzione
mostra la forma della data e un esempio completo:

| Opzione | Esempio |
|--------|---------|
| `dd/mm/yyyy` (predefinito) | `03/04/2025` = **3 aprile 2025** |
| `mm/dd/yyyy` | `03/04/2025` = **4 marzo 2025**, come si scrive negli Stati Uniti |
| `dd/mm/yy` | `03/04/26` = **3 aprile 2026** |
| `mm/dd/yy` | `03/04/26` = **4 marzo 2026** |
| `yy/mm/dd` | `26/04/03` = **3 aprile 2026** |
| `yyyy-mm-dd` | `2026-04-03` = **3 aprile 2026** |

`dd/mm/yyyy` è il formato con cui LibreFolio ha sempre letto le date, quindi non cambia nulla se non apri
mai l'impostazione. Con `dd/mm/yyyy` e `mm/dd/yyyy`, una data che può essere interpretata in un solo
ordinamento viene sempre letta correttamente: `25/12/2025` è il 25 dicembre, perché non esiste il mese 25.
Con le opzioni a due cifre per l'anno l'ordinamento che hai scelto è l'unico applicato, e `yy` segue la
regola abituale: `00`–`68` sono 2000–2068, `69`–`99` sono 1969–1999. Le date scritte come `2025-12-25`,
`20251225` o `25 Dec 2025` hanno un solo significato e non vengono mai interpretate diversamente.

Una riga la cui data non può essere letta nel formato scelto viene esclusa, e l'analisi lo segnala per
ogni riga (*Riga 4: 25/12/26 non è una data valida nel formato mm/dd/yy…*), indicando dove correggerla:
correggi la data nel file, oppure cambia il **Formato data** in **Impostazioni › Plugin** e premi
**Rianalizza tutto**. Dopo la ventesima riga di questo tipo, una sola nota riporta il numero delle righe
restanti.

!!! tip "Analizza di nuovo il file dopo averlo modificato"

    Un file che hai già analizzato conserva le date con cui è stato letto. Dopo che hai cambiato
    l'impostazione, il file mostra l'avviso che deve essere **analizzato di nuovo**: analizzalo di nuovo,
    poi controlla le righe.

---

## 🔄 Convertire un report personalizzato

Se i tuoi dati provengono da un altro strumento, un breve script può convertirli in un Generic CSV. La
**[specifica tecnica del Generic CSV](../../../developer/backend/brim/generic_csv.md)** descrive il
formato in dettaglio — segni, quale tipo usare e quando, esempi svolti. Puoi incollarla in un assistente
IA (ChatGPT, Claude, Gemini…) insieme ad alcune righe di esempio del tuo file e chiedere lo script.

---

## 📋 Riferimento delle colonne {: #column-reference }

Queste sono le colonne che LibreFolio riconosce in un file Generic CSV. I nomi delle colonne non
distinguono maiuscole e minuscole, e gli spazi che li circondano vengono ignorati.

| Colonna | Obbligatoria? | Alias accettati | Descrizione |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Sempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Data della transazione |
| **`type`** | ✅ Sempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo di transazione — vedi i valori qui sotto |
| **`quantity`** | Obbligatoria per BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Numero di unità. **Negativo per SELL, positivo per BUY.** |
| **`amount`** | Obbligatoria per la maggior parte dei tipi | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impatto sulla liquidità. **Negativo quando la liquidità esce, positivo quando entra.** Vuoto per ADJUSTMENT. |
| **`currency`** | Facoltativa (valore predefinito: EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Codice valuta ISO 4217. EUR si applica solo quando il file non ha una colonna valuta: se ce l'ha, compilala su ogni riga con un `amount`, altrimenti quella riga viene saltata. |
| **`asset`** | Obbligatoria per BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN o una stringa di nome coerente per asset non quotati |
| **`description`** | Facoltativa | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Note di testo libero |

### 🏷️ Valori `type` validi

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "Non supportati: TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Richiedono due righe collegate, cosa che un CSV non può esprimere: tali righe vengono saltate con un
    avviso. Inseriscile a mano dalla pagina Transazioni, oppure usa l'importatore del tuo broker.

---

## 🔗 Correlati

- 🧙 **[Come importare](how-to.md)** — la procedura guidata di importazione, passo per passo
- 🏦 **[Broker supportati](index.md)** — verifica prima se il tuo broker ha un proprio importatore
- 🛠️ **[Specifica tecnica del Generic CSV](../../../developer/backend/brim/generic_csv.md)** — il formato completo, per script e sviluppatori
