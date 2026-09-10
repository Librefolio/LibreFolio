# Piano Phase 00 — BRIM mirato

**Creato**: 2026-09-10
**Baseline/target**: `8b99e0020c92a945daf0821ee0654a0a2a21efd0` (`dev_release2`)
**Workstream**: G — `e-alfy-brim-targeted-analysis`
**Coordinator**: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`
**Runtime lane**: porta `6155`, data dir assoluta `/tmp/librefolio-r2-g-brim`
**Autorizzazione developer verbatim**: `Approva G completo con eToro FEE (Consigliato)`
**Decisione eToro verbatim**: `Sì: -1.36 come FEE separata; zero ignorato (Consigliato)`.

## Obiettivo

Consegnare due slice separate:

1. **P4-3 parity-first** — caratterizzare l'output completo Crédit Agricole su layout
   titoli/conto CSV e XLSX; estrarre le closure del parser conto in fasi nominate con
   contesto ristretto; condividere soltanto l'helper delle notice di maturity con un
   secondo consumer reale, Intesa.
2. **B1 eToro** — importare `Withdrawal Conversion Fee` con `Amount` non-zero come
   `FEE` separata; ignorare fee con `Amount == 0`; lasciare invariato il withdrawal
   originale.

## Decisioni e assunzioni vincolanti

- Crédit Agricole deve mantenere **parità assoluta di output**: ordine e cardinalità
  delle transazioni, fake ID, tutti i campi `TXCreateItem`, warnings/notices, evidence,
  validation issues, field todo e relativi `tx_index`, extracted assets/notices.
- Il contratto fake-ID reale è positivo alto e decrescente da
  `FAKE_ASSET_ID_BASE = 2**31 - 1`.
- Il layout titoli CA sintetizza contropartite `auto_cash`; il layout conto non deve
  sintetizzarle perché la riga è già il movimento reale.
- Refactor CA senza cambio output: `plugin_version` resta `1.4.3`.
- Nessuna generalizzazione dei fake-ID allocator o campagna sui 35 siti C901.
- Helper condiviso solo con secondo consumer provato: attachment delle maturity notice
  per CA e Intesa. Il testo provider-specific resta parametro del chiamante.
- eToro: il sample repository disponibile mostra `Withdrawal Conversion Fee` con
  `Amount = -1.36`, `Realized Equity Change = 0.00`, accanto al withdrawal. Per decisione
  di prodotto, `Amount` non-zero è trattato come addebito `FEE` separato.
- Questa è un'**assunzione sul formato osservato**, non prova universale della semantica
  economica eToro. Le regressioni devono rendere visibile il possibile doppio conteggio
  tramite cardinalità, segno/importo e somma cash.
- Fee eToro con importo zero non produce transazioni. Il `Withdraw Request` resta
  invariato.
- eToro cambia output sullo stesso file: bump SemVer del plugin.
- Nessun dato/export privato o di produzione. Solo sample repository e fatti sintetici.
- Coordinator mantiene ownership di `CHANGELOG.md`, master backlog, runner registration,
  MkDocs nav e generazioni condivise.

## Superfici

- `backend/app/services/brim_providers/broker_credit_agricole.py`
- `backend/app/services/brim_providers/broker_intesa.py`
- Nuovo helper privato ristretto in `backend/app/services/brim_providers/`
- `backend/app/services/brim_providers/broker_etoro.py`
- `backend/test_scripts/test_external/test_brim_providers.py`
- `mkdocs_src/docs/user/transactions/import/etoro.en.md`
- `mkdocs_src/docs/developer/backend/brim/providers_list.md`, solo se necessario

## Step

### 1. ✅ Congelare decisioni, baseline e ownership — 2026-09-10

> **Note implementazione**: creato questo piano prima di codice/test; registrate
> autorizzazione eToro, assunzione economica, confine parity CA, lane e file condivisi.

### 2. ✅ Caratterizzare output completo Crédit Agricole — 2026-09-10

- Aggiungere una rappresentazione canonica leggibile e completa del
  `BRIMParseOutput`.
- Coprire titoli e conto sui sample CSV; provare equivalenza dei corrispondenti XLSX.
- Congelare ordine, fake ID, campi annidati, evidence e indici.

> **Note implementazione**: aggiunta caratterizzazione leggibile del sample conto,
> confronti completi per canale CSV/XLSX su entrambi i layout e regressioni mirate
> per ordine, fake ID, evidence annidate e `tx_index`. Nessun digest/blob opaco:
> i valori attesi compatti restano revisionabili nel test.
>
> **⚠️ Fuori pista**: il primo selector ha mostrato che il fixture XLSX titoli
> contiene nove righe di preambolo più del CSV. Il contenuto evidence coincide,
> mentre i `row_numbers` source-local sono correttamente `CSV + 9`; l'oracolo ora
> congela esplicitamente questa differenza anziché imporre una falsa uguaglianza.

### 3. ✅ Estrarre parser conto CA in fasi nominate — 2026-09-10

- Introdurre un context/state privato e ristretto.
- Estrarre header/evidence, prepass identità/nominali/spese, asset registry,
  trade resolution/suggestions, emissione righe/notices.
- Lasciare `_parse_account_movements` come orchestratore.
- Nessun cambio di output e nessun bump `1.4.3`.

> **Note implementazione**: introdotto `_CAAccountParseContext` per stato, registry
> asset/fake ID, evidence, prepass identità/nominali/spese, lookup nominali,
> suggerimenti split, fallback e risoluzione trade. Il metodo context è il consumer
> attivo. Confronto diretto contro il parser del commit baseline sui quattro fixture
> repository (titoli/conto CSV+XLSX): output `model_dump(mode="json")` identico in
> tutti i casi. Rimossa fisicamente la closure trade legacy; nel parser conto non
> restano closure locali.

### 4. ✅ Condividere attachment maturity CA + Intesa — 2026-09-10

- Estrarre helper schema-aware separato da `_brim_io` se necessario per conservarne il
  confine IO.
- Adottarlo in CA e Intesa con reason provider-specific.
- Nessuna adozione speculativa ulteriore.

> **Note implementazione**: creato `_brim_output.attach_maturity_notices`, separato
> dal modulo IO; adottato solo da Crédit Agricole e Intesa, mantenendo testi reason
> provider-specific e indici restituiti da `detect_maturity_hits`.

### 5. ✅ Implementare B1 eToro — 2026-09-10

- Riconoscere `Withdrawal Conversion Fee`/fee supportate.
- Scartare amount assente/zero.
- Emettere `FEE`, quantità zero, cash negativo verbatim, senza asset.
- Conservare il withdrawal.
- Bump plugin version.

> **Note implementazione**: le fee eToro riconosciute vengono valutate sul campo
> `Amount`: assente/zero resta ignorato, non-zero produce `FEE` senza asset e con cash
> negativo. `Withdraw Request` segue il mapping precedente. Versione plugin `1.0.0` →
> `1.1.0`.

### 6. ✅ Riallineare documentazione EN — 2026-09-10

- Dichiarare fee conversione non-zero come riga separata.
- Dichiarare onestamente l'assunzione sul sample osservato e rischio di conteggio
  separato rispetto al withdrawal.
- Nessuna traduzione automatica salvo istruzione esplicita.

> **Note implementazione**: aggiunto warning EN dedicato: fee conversione non-zero
> separata, fee zero ignorate, withdrawal originale invariato. Esplicitato che la
> scelta deriva dal solo sample repository osservato e non prova una semantica eToro
> universale. MkDocs strict build e translation dry-run verdi; IT/FR/ES restano
> debito reale, quindi nessun translation-cache stamp.

### 7. ✅ Verificare selettori mirati e gate finali — 2026-09-10

Comando canonico:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6155 \
  --data-dir /tmp/librefolio-r2-g-brim \
  external brim-providers <selector>
```

Selettori:

- caratterizzazione completa CA;
- `test_credit_agricole`;
- `TestPluginFrontendContract`;
- maturity CA + Intesa;
- regressioni eToro cardinalità/importo/segno/somma cash;
- intero `external brim-providers` solo nella lane G e senza concorrenza interna.

Gate statici finali:

- lint/format backend mirato;
- `git diff --check`;
- porta `6155` libera;
- nessun artefatto runtime/generated/private.

> **Note implementazione**: lane esclusiva `6155` +
> `/tmp/librefolio-r2-g-brim`: nuovi selector `18 passed`; regressori
> `test_credit_agricole` + `TestPluginFrontendContract` `66 passed`; suite completa
> `external brim-providers` `520 passed`. Black/Ruff mirati verdi e `dev.py lint`
> globale verde.

### 8. ✅ Review finale coordinator — robustezza FEE e baseline CA — 2026-09-10

- Forzare `quantity = Decimal("0")` per ogni FEE eToro supportata, ignorando `Units`.
- Regressione sintetica `Withdrawal Conversion Fee` con `Amount = -1.36`,
  `Units = 2`: una FEE qty-zero, withdrawal invariato, nessuna issue `qtyZero`.
- Congelare l'intero `BRIMParseOutput` baseline per entrambi i layout CA.
- Nella parità CSV/XLSX normalizzare soltanto l'offset source-row documentato
  (`+9` titoli, `0` conto), senza proiettare message/context/reason o altri campi.
- Rieseguire focused, CA contract, suite BRIM completa e gate statici sulla lane G.

> **⚠️ Fuori pista**: la review finale ha individuato due lacune negli oracoli
> iniziali: una `Units` eToro non-zero poteva attivare `qtyZero` prima che la FEE
> fosse forzata a quantità zero; la caratterizzazione CA congelava integralmente
> solo il layout conto e usava la parità same-parser come protezione principale per
> il layout titoli. G riaperto esclusivamente per chiudere questi due punti.

> **Note implementazione**: ogni FEE eToro supportata forza ora
> `quantity = Decimal("0")` prima della validazione, indipendentemente da `Units`.
> La regressione sintetica usa il trio fee-zero/conversion-fee/withdrawal con
> `Units = 2`, congela cardinalità 3→2, FEE `-1.36` qty-zero, withdrawal `-100.11`,
> somma cash `-101.47` e assenza di `qtyZero`. La caratterizzazione CA contiene
> valori letterali completi per entrambi i `BRIMParseOutput` CSV; gli XLSX sono
> confrontati allo stesso baseline normalizzando esclusivamente `row_numbers`
> evidence (`-9` titoli, `0` conto), preservando ogni altro campo.
>
> **Note verifica review**: focused `6 passed`; `test_credit_agricole` +
> `TestPluginFrontendContract` `66 passed`; suite completa `external
> brim-providers` `508 passed`.

## Definition of done

- Output CA CSV/XLSX completamente caratterizzato e invariato dopo refactor.
- `_parse_account_movements` orchestra fasi nominate; closure complesse rimosse.
- Un helper maturity condiviso ha esattamente due consumer reali CA + Intesa.
- CA resta `plugin_version = 1.4.3`.
- eToro produce una sola FEE `-1.36` per la conversion fee non-zero del sample, ignora
  fee zero, conserva withdrawal `-100.11`; totale cash e cardinalità esplicitamente
  testati.
- eToro plugin version incrementata.
- Documentazione EN esplicita l'assunzione.
- Test/lint mirati verdi; server fermo e porta libera.
