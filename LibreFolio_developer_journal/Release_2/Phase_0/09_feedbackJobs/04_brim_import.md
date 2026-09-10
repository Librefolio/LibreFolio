# 04 — BRIM & Import

Task sui plugin di import e sul wizard. Approvati dall'utente il 07/09/2026.
Skill di riferimento per chi esegue: `brim-plugin`.

> **Chiusura urgente E — 2026-09-09:** matching/refresh degli asset nel wizard
> Generic CSV e vincolo "un file piatto per broker" sono stati corretti e
> documentati in [14_feedbackImportUrgent](../14_feedbackImportUrgent/manifest-integrazione-E.md).
> Il parser resta verbatim, non genera FX e il primo asset resta una scelta
> esplicita. Le voci eToro B1 e delete-asset B3 sotto restano aperte.

---

## 🔍 eToro — "Withdraw Fee" / "Conversion Fee" scartate invece di importate come FEE

**Complessità**: S–M · **Tipo**: bug sospetto · **Origine**: verifica 18/07/2026 (bug BRIM FEE/TAX)

### Contesto
`backend/app/services/brim_providers/broker_etoro.py` — la docstring (riga ~20) dice
*"Withdraw Fee / Conversion Fee → FEE"* ma il codice (righe 72-78, `SKIP_TYPES`) le mette tra
i tipi **scartati a monte**: queste righe non diventano una transazione `FEE`.
Lo scarto è confermato; il fatto che manchi un ulteriore addebito economico va provato,
perché la riga potrebbe descrivere un costo già compreso nel prelievo.

### Da valutare (decisione prima del codice)
- **Verifica 2026-09-07**: il sample `etoro-export.csv:6-8` **contiene** le righe:
  Withdraw Fee `0.00`, Withdrawal Conversion Fee Amount `-1.36` con Realized Equity Change
  `0.00`, accanto a un Withdraw Request. La precedente nota "sample assente" era errata.
- Prima di spostarle in `TYPE_MAPPINGS`, riconciliare addebito effettivo, prelievo associato
  e valuta di regolamento. Serve un esempio non-zero di Withdraw Fee o conferma del formato;
  una FEE zero non soddisfa il contratto cash strettamente negativo.
- Se lo scarto è intenzionale (es. per evitare doppio conteggio): correggere la docstring per
  riflettere il comportamento reale.
- Nella ricognizione mirata degli altri skip list non sono emersi altri bug confermati
  dello stesso tipo. Nessuna campagna speculativa; B1 resta condizionale all'evidenza.

---

## 💸 BRIM: FEE/TAX e lotti — ✅ ALLOCAZIONE ECONOMICA GIÀ CONSEGNATA

**Complessità residua**: XS documentale · **Origine**: TODO_FUTURI (Fase 1 completata il 18/07)

### Stato (dalla nota)
- **Fase 1 (fatta)**: Directa e Schwab corrette (bug reale confermato sui sample bundled);
  Finpension/Revolut fix difensivo (FEE strutturalmente di conto); eToro spostata nella voce
  sopra; Freetrade/Trading212/generic_csv non affette.
- **Pattern di riferimento validi**: `broker_ibkr.py:229-247` (FEE riusa l'`asset_id` della
  riga madre), `broker_coinbase.py:283-303`, `broker_degiro.py:87-103` (mappa tipo→
  requires_asset caso per caso), `broker_generic_csv.py` (collega se il campo asset è pieno).

### Stato reale verificato — 2026-09-07
- **FIFO v4 alloca già FEE/TAX collegati all'asset** e produce metriche nette:
  `fifo_lot_engine.py:1038,1199,1281`; `lots_analysis_service.py:616,1335-1393`.
- FEE usa trade stesso giorno, precedente, holdings, orphan; TAX privilegia prima i redditi.
  Niente D+1; i costi senza asset restano al livello broker/portfolio.
- L'allocazione economica non muta quantità, frammenti e closure. **WAC di acquisizione
  lordo e metriche nette restano separati per scelta**: non è prova di costi ignorati.
- Non implementare una nuova Fase 2 dalla nota del 18/07. Capitalizzare ritenute, custodia
  o ratei nel WAC sarebbe un'altra policy, con rischio di doppia sottrazione, fuori scope.
- Rimandi: [piano FIFO v4](../../../RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md)
  e [analisi B2](06_piano_sprint.md). Regime fiscale futuro non riaperto.

---

## 🔗 Link transazioni nella Asset Delete Modal

**Complessità**: M · **Origine**: 26/03/2026, scope riesaminato 2026-09-07

### Richiesta
Quando un asset non si può eliminare perché ha transazioni (`error_code: HAS_TRANSACTIONS`),
il messaggio è generico. Ora che la pagina transazioni esiste:
1. Delete modal: conteggio + link diretto alla pagina transazioni filtrata
   (es. "This asset has 3 transactions: [View → /transactions?asset_id=123]").
2. Pagina dettaglio asset: sezione con link alle transazioni collegate.
3. Backend: `transaction_count: int` in `FAAssetDeleteResult` quando `error_code == "HAS_TRANSACTIONS"`.

### Nota
Il filtro `?asset_id=` **esiste già**; riusare `buildTransactionsFiltersUrl` senza
trascinare filtri precedenti. Il dettaglio asset non ha ancora il link richiesto.

**Analisi 2026-09-07**: la UI è in `assets/+page.svelte` e usa `ConfirmModal`, non un
componente autonomo AssetDeleteModal. Il ramo singolo chiude anche se bloccato; la bulk
mostra solo testo per risultato. Servono risultati persistenti con azione-link tipizzata.

Il backend ha difetti strettamente accoppiati da includere: NOT_FOUND senza `deleted_count`
richiesto; rollback di un item che può annullare successi già dichiarati; commit finale
fallito soltanto loggato. Verificare cancellazione reale, non solo contatori response.

Il conteggio bloccante globale può superare le transazioni accessibili al chiamante:
questa distinzione è già prevista dalla policy degli asset. Non usare `tx_count_own`
come equivalente dei permessi VIEWER/EDITOR e non esporre record privati tramite il link.
API sync prima della UI; coordinare col successivo spostamento di `asset_source.py`.

**Gate UX 2026-09-07:** prima ASCII del risultato bloccato singolo/bulk e del link nel
dettaglio, con approvazione del dev. Dopo: istruzioni per raggiungere la modale e provare
fixture eliminabili/bloccate, conteggi e navigazione filtrata, raccogliendo feedback
operativo senza cancellare dati reali. Backend e UI possono avanzare su DTO concordati;
il raccordo in asset_source precede il trasloco P4-1.

## Analisi per task — 2026-09-07

Baseline `a9138140`; rischi, dipendenze e DoD in [06_piano_sprint.md](06_piano_sprint.md).

| ID | Esito | Sprint |
|---|---|---|
| B1 | Scarto confermato, effetto economico da provare; S–M se cambia parser, blocco esplicito altrimenti. | SP09 condizionale |
| B2 | ✅ Allocazione/net FIFO v4 già consegnati; WAC lordo separato intenzionalmente. | Nessun codice |
| B3 | Aperto, M con correttezza della persistenza, count e link singolo/bulk/dettaglio. | SP03 |
