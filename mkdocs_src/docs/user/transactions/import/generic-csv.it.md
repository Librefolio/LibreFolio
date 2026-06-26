# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV Generico

Il provider **CSV Generico** è un fallback flessibile per i broker che non sono supportati direttamente. Consente la mappatura manuale delle colonne, permettendoti di importare dati da qualsiasi esportazione in formato CSV.

## Quando Utilizzarlo

- Il tuo broker non è presente nell'elenco dei supportati.
- Un broker supportato ha cambiato il formato di esportazione e il plugin non è ancora stato aggiornato.
- Hai un foglio di calcolo personalizzato o un CSV generato da uno script che desideri importare.

## Come Funziona

1. Carica il tuo file CSV.
2. LibreFolio mostra le colonne grezze rilevate.
3. Mappa ogni colonna al campo corrispondente di LibreFolio (data, tipo, asset, quantità, importo, valuta, descrizione).
4. Visualizza l'anteprima delle righe analizzate e conferma l'importazione.

---

## 🔄 Convertire un Report Personalizzato

Se la tua fonte dati non è supportata nativamente, puoi scrivere uno script di conversione per trasformarla nel formato CSV Generico.

!!! info "Specifiche tecniche per sviluppatori e LLM"

    La specifica completa del formato — incluse le convenzioni dei segni, quando usare ciascun tipo di transazione, i pattern P2P, la gestione degli storni ed esempi pratici — si trova nella documentazione tecnica:

    **[CSV Generico — Specifiche Tecniche](../../../developer/backend/brim/generic_csv.md)**

    Puoi incollare quella pagina direttamente in un LLM (ChatGPT, Claude, Gemini…) insieme ad alcune righe di esempio del tuo file sorgente e chiedergli di scrivere uno script Python di conversione.

---

## 📋 Riferimento Colonne

Queste sono le colonne riconosciute da LibreFolio in un file CSV Generico. I nomi delle colonne non sono case-sensitive.

| Colonna | Obbligatoria? | Alias accettati | Descrizione |
|---------|--------------|-----------------|-------------|
| **`date`** | ✅ Sempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Data della transazione |
| **`type`** | ✅ Sempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo transazione — vedi valori sotto |
| **`quantity`** | Richiesta per BUY/SELL/TRANSFER/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Numero di unità. **Negativa per SELL, positiva per BUY.** |
| **`amount`** | Richiesta per la maggior parte dei tipi | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impatto sulla liquidità. **Negativo quando esce denaro, positivo quando entra.** Vuoto per TRANSFER e ADJUSTMENT. |
| **`currency`** | Opzionale (default EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Codice valuta ISO 4217 |
| **`asset`** | Richiesta per BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, o nome consistente per asset non quotati |
| **`description`** | Opzionale | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Testo libero |

### Valori validi per `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `TRANSFER` · `ADJUSTMENT` · `FX_CONVERSION` · `CASH_TRANSFER`

---

## 🔗 Correlati

- **[CSV Generico — Specifiche Tecniche](../../../developer/backend/brim/generic_csv.md)** — Convenzioni dei segni, pattern P2P, gestione storni, suggerimento LLM
- **[Architettura BRIM](../../../developer/backend/brim/architecture.md)** — Come funziona il wizard di importazione

