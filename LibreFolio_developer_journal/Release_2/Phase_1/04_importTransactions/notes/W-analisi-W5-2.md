# W5-2 · W-B87 — analisi del primo turno (W, 24/10/2026, base `e5c5608d2`)

Letti: il codice dei cinque plugin, i `sample_reports/`, `type_metadata.py`, `financial_math/splits.py`, la cartella `bulk/` e `events/` del frontend.

## 1. Il formato vero della riga di split

**Revolut** (`revolut-invest-export.csv:9`): `2022-08-25…,TSLA,STOCK SPLIT,0.16431924,,$0,USD,0.0947`. La colonna `Quantity` è
**l'azione aggiunta**, non il totale dopo lo split. Prova dal file stesso: il 9/9/2023 un `TRANSFER` di TSLA porta `0.24647886`
= 0,08215962 (la posizione prima) + 0,16431924 (la riga di split): è un 3 per 1. Prezzo e totale sono vuoti/0.
→ rettifica in entrata di `Quantity`, senza costo. Se `Quantity` fosse negativa: split inverso (avviso, non importato). Nessun
caso negativo nel campione: la regola è un'ipotesi dichiarata.

**Trading 212** (`trading212-export.csv:13-14`): due righe, `Stock split close` (azioni tolte) e `Stock split open` (azioni date),
stesso ISIN, `Time` a 9 millisecondi di distanza (`07:24:24.095` e `.104`), `ID` diversi. Nel campione: close 29,80478 → open 7,451195,
cioè **uno split inverso 4 a 1** (le azioni calano). Non c'è nessun caso moltiplicativo nel campione: servirà **un file sintetico**
(open > close) per i rossi, costruito come il vero. Regola: `open − close > 0` → rettifica in entrata di quella differenza, senza costo;
`< 0` → avviso «non importato» con `report_issue`, come oggi (è il caso del campione); una riga close senza open (o viceversa) → avviso.
Abbinamento: stesso ISIN, `Time` entro 1 secondo.

## 2. Il costo: ADJUSTMENT in entrata

Una `ADJUSTMENT` con quantità > 0 *richiede* un costo (`cost_basis_required`, regola 12). Lo split ha costo **0** (valore ammesso: «le azioni
nuove di uno split»). Il plugin emette `cost_basis_override = 0` esplicito. Senza evento collegato quelle azioni diluirebbero il costo medio
come azioni regalate: per questo la riga porta il flag. Collegata a un evento SPLIT, `financial_math/splits.py` ridistribuisce il costo.

## 3. Il flag gestito: la proposta

`BRIMFieldTodo` (`field="asset_event_id"`, `severity="warning"`, `reason_code="possible_split"`, `context={ratio_hint?, source_row}`) con evidenza
(la riga del file). Il Bulk già riceve i todo (`ImportTodo`, `bulkTodos.ts`); un todo su `asset_event_id` **si chiude da solo** quando la riga
ha un evento (`remainingTodos`). Quello che manca è la parte visibile, tutta nel Bulk:
- avviso in alto («potrebbe essere uno split»: N righe) con le due azioni;
- su ogni riga flaggata: «Crea l'evento SPLIT e collega» (apre il mini-modale di creazione evento) e «Collega a un evento esistente»
  (il selettore di eventi);
- una nota a fine wizard.

**Da verificare nel codice prima dei rossi** (lo dico perché potrebbe cambiare il lavoro): `EVENT_TYPES_TX_COMPATIBLE` in `events/eventTypes.ts:8`
è `['DIVIDEND','INTEREST','PRICE_ADJUSTMENT']`: **senza SPLIT**. Il backend accetta un'ADJUSTMENT collegata a un evento SPLIT
(`event_compatible`, `compatible_tx_types=["ADJUSTMENT"]`), ma il mini-modale di creazione e il selettore oggi non offrono SPLIT per una riga ADJUSTMENT.
Se è così, serve estendere `eventTypes.ts` e il mini-modale (campo rapporto).

## 4. File del Bulk che toccherei (chiedo l'ok, come da kickoff)

Tutti sotto `frontend/src/lib/features/transactions/`:
| File | Perché | Note |
|---|---|---|
| `bulk/TransactionBulkModal.svelte` (3498 righe) | le azioni sulla riga, l'avviso in alto | grosso: una sola zona, nuovo componente a parte |
| `bulk/TxBulkBanners.svelte` | l'avviso «potrebbe essere uno split» | |
| `bulk/bulkTodos.ts` (+ test) | riconoscere il todo gestito `possible_split` | |
| `bulk/PossibleSplitRow.svelte` (nuovo) | i due pulsanti per riga | |
| `events/eventTypes.ts`, `events/EventCreateMiniModal.svelte` (+ test) | offrire SPLIT per una riga ADJUSTMENT, con il rapporto | da confermare (sopra) |
| `import/ImportWizardModal.svelte` o il passo finale | la nota a fine wizard | mio |
| `i18n/importWizard/*.json` | testi della nota (miei) | |
| `i18n/transactions/*.json` | testi dell'avviso del Bulk e dei pulsanti | **di W2**: righe additive; propongo di metterli sotto `transactions.bulk.possibleSplit.*` |
| `frontend/e2e/transactions/` (spec nuovo) | E2E del Bulk con la riga flaggata | |
Non tocco: `routes/(app)/transactions/+page.svelte` (X), `TransactionFormModal.svelte` (W2), `txPayloadHelpers.ts` (W2: leggo `ImportTodo`).

Nessun endpoint nuovo: «crea evento» usa `upsert_events_bulk` (già nel mini-modale); «collega» scrive `asset_event_id` sulla riga, poi il salvataggio normale.

## 5. Gli altri plugin (commissioni, tasse, rimborsi, forex)

**eToro** (`:73-79`, `:239-242`): `Overnight fee` (negativo), `Overnight refund` (positivo), `SDRT` (negativo, imposta di bollo UK) sono oggi in `NOT_IMPORTED_TYPES`.
- `Overnight fee` → `FEE` (come `withdraw fee`, già in `FEE_TYPES`). **Quarantena del campione**: 3 righe (`Overnight fee` ×2, `refund` ×1), CFD, `Details` = «Daily».
- `SDRT` → `TAX`, con l'asset della riga (`Details` = `HNKE/USD`: ticker).
- **Il rimborso (`Overnight refund`, importo positivo)**: `FEE` e `TAX` vogliono cassa < 0. Un rimborso non può essere una FEE positiva. Le scelte reali sono `INTEREST` (cassa > 0, senza asset, entra come reddito) o `DEPOSIT` (ma un deposito è capitale versato: falserebbe i rendimenti). **Domanda 1** (sotto): propongo `INTEREST` con descrizione «Overnight refund» e tag `import`/`etoro`.

**Trade Republic** (`:213-216`): colonne `Kosten` e `Belasting`, ora in un avviso. **Il rischio principale del lotto**: la colonna dell'importo si chiama `Waarde (netto)` — *netto*. Nel campione: `Buy;-690.25;Kosten -1.0` e `Sell;86.714375;Kosten -1.0`. Se il netto **include già** la commissione (come Fineco, dove il Controvalore la conteneva: il lotto del 1.4.0), aggiungere una FEE di −1,00 **la conta due volte**. Il campione è sintetico e non permette di dirlo (non so se 690,25 è 689,25 + 1,00 o 690,25 + 1,00). **Domanda 2**: il developer ha un file vero (o un estratto conto) che dica se `Waarde (netto)` contiene `Kosten`/`Belasting`? Fino ad allora **non scrivo i rossi di TR** (non si può testare «giusto» senza sapere l'ipotesi). Se il netto contiene la spesa, il modello è quello di Fineco: il BUY/SELL prende il netto *senza* la spesa e la FEE/TAX la tiene separata, a totale invariato; se non la contiene, basta aggiungere la FEE/TAX.

**Swissquote** (`:204-206`): `Forex credit`/`Forex debit` con lo stesso `Order #` e la stessa ora (campione: 4 righe, due coppie, es. `EUR +1995,39` / `USD −2000,00`, ordine `114723639`). Si abbinano per `Order #` + timestamp in una coppia `FX_CONVERSION` con `link_uuid`, come DEGIRO (`broker_degiro/plugin.py:580`). Una gamba sola → avviso. Fattibile.

**IBKR** (`:182-189`): la riga forex non ha ISIN, ma il report d'esempio **non ha né la colonna `Symbol` né la valuta base** (`Buy/Sell, TradeDate, ISIN, Quantity, TradePrice, TradeMoney, CurrencyPrimary, IBCommission…`) e **nessuna riga forex nel campione**: da questo export non si ricava la coppia di valute (`CurrencyPrimary` è solo la valuta del prezzo). **Non si può importare come FX_CONVERSION senza inventare la valuta base.** Proposta: resta l'avviso `report_issue` (con il testo che dice «serve la colonna Symbol/valuta base»), finché non arriva un export vero con la colonna. **Domanda 3**: ok lasciare IBKR com'è?

**Trading 212** (`:93-97`): oltre a «stock split», restano in avviso «stock distribution» (campione: `Stock distribution`, PALAF, 11,056 azioni a 0 USD: una distribuzione di azioni, come uno spin-off) e «currency conversion». Il kickoff parla degli split di T212; distribuzione e conversione le lascio come oggi, **salvo ordine diverso**.

## 6. Ordine proposto (un lucchetto per blocco)

1. Backend, plugin con il formato certo (rossi → cura, `external` e test del plugin): eToro (FEE/TAX/rimborso), Swissquote (coppie FX), Revolut e T212 (ADJUSTMENT in entrata, costo 0, todo `possible_split`, split inverso in avviso). Test su `sample_reports/` + un campione sintetico T212 moltiplicativo.
2. Trade Republic: dopo la risposta alla domanda 2.
3. Frontend del Bulk (file della tabella): rossi Vitest + E2E, poi cura; nota a fine wizard; doc utente (`user/transactions/`, in inglese).
4. `MF` rivede il checkpoint (la rettifica senza costo cambia i numeri).

## 7. Domande (nessuna ferma tutto: ognuna ferma solo il suo pezzo)

1. **Rimborso overnight di eToro**: `INTEREST` (proposta) o altro? (`DEPOSIT` falsa il capitale; `FEE` positiva non è ammessa.)
2. **Trade Republic**: `Waarde (netto)` contiene già `Kosten`/`Belasting`? Serve un file vero. Ferma solo TR.
3. **IBKR**: resta l'avviso finché non c'è un export con `Symbol`?
4. **Trading 212**: «stock distribution» e «currency conversion» restano avvisi?
5. **Revolut split**: confermo `Quantity` = azioni aggiunte (prova: il campione), split inverso = `Quantity` negativa (ipotesi, nessun caso reale).
6. L'ok sui file del Bulk e sulle chiavi `transactions.bulk.possibleSplit.*` in `i18n/transactions` (file di W2).
