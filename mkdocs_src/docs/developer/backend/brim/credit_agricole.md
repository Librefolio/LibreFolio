# 🏦 Crédit Agricole Importer

`broker_credit_agricole` imports the two Italian exports of Crédit Agricole, each as CSV or XLSX:
the account movements (*Lista Movimenti Conto*) and the securities movements (*Lista Movimenti
Deposito Titoli*). It lives in `backend/app/services/brim_providers/broker_credit_agricole.py` and
is the plugin with the richest wizard integration — a causale registry, evidence tables, blocking
and splitting field todos — which the
[BRIM Plugin Guide](../../architecture/patterns/brim_plugin_guide.md#talking-to-the-import-wizard)
uses as its reference.

This page covers what is specific to Crédit Agricole. The user's view is
[Crédit Agricole](../../../user/transactions/import/credit_agricole.md), where the plugin's
`docs_url` points.

---

## 🗂️ Layouts and detection

| Layout | Bank export | Header row (`find_header_row`) | Parser |
|---|---|---|---|
| Account | *Lista Movimenti Conto* (**Conti → Lista movimenti**) | `Data Op.`, `Descrizione`, `Importo` | `_parse_account_movements` |
| Securities | *Lista Movimenti Deposito Titoli* (**Portafoglio → Lista Movimenti**) | `Data operazione`, `Causale`, `Quantità` | `_parse_securities` |

- **Reading.** `_brim_io.read_rows` gives uniform rows for both formats: CSV through the base
  class's encoding fallback and delimiter sniffer, XLSX from the first worksheet with data (values,
  not formulas).
- **`can_parse`** accepts a `.csv` or `.xlsx` whose first 40 rows contain the title
  `lista movimenti deposito titoli`, the securities trio `data operazione` + `causale` + `nome`
  (Intesa's movements use `Operazione`/`Dettagli` instead), or the account trio `data op.` +
  `descrizione` + `importo`. `parse` tries the securities header first, then the account header,
  and raises `BRIMParseError` when it finds neither.
- **Header and columns.** The header row is searched in the first 60 rows and the columns are
  mapped by label (`build_col_index`), so the XLSX preamble and its extra leading columns do not
  matter. Nothing above the header is read: the preamble's **Saldo Iniziale** is never imported,
  which is why the user page asks for a manual `DEPOSIT`.
- **Rows skipped silently**: blank rows; the XLSX recap footer (a row without a date whose label
  starts with `TOTALE`, `RIEPILOGO` or `SALDO FINALE`); any other row without a date or a causale;
  account rows whose amount is zero.
- **Numbers.** `Prezzo`, `Controvalore in Euro` (or `Ctv in Eur`), `Importo` and the figures inside
  descriptions (`NOMINALE:`, `RITENUTA:`) are Italian-formatted (`to_decimal_it`: `.` thousands,
  `,` decimal, and the leading `'` of the CSV amounts stripped). `Quantità` is plain
  (`to_decimal_plain`): dotted decimals for fund units, integers for bond nominals.
- **Currency.** Account rows take `Divisa`, EUR when empty. Securities rows take the first
  three-letter code among all the columns whose header contains `Divisa`, because the XLSX variant
  can carry the causale in the transaction `Divisa` cell. `Cambio` is never read.

---

## 📈 Securities layout

The export holds securities only and names them by `Nome`, with no ISIN: fake asset ids are keyed by
the lower-cased name, with `extracted_isin=None`. The date is `Data operazione`.

| Causale | Transactions | Cash counter-entry |
|---|---|---|
| `CEDOLA` | `INTEREST` of `Controvalore`, quantity 0 (the nominal in `Quantità` is ignored) | `WITHDRAWAL` |
| `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | `BUY` of `Quantità` | `DEPOSIT`, before the buy |
| `FONDI: RIMBORSO` | `SELL` of `Quantità` | `WITHDRAWAL` |
| `TITOLI SCADUTI` | `SELL` at par, and an `INTEREST` for the amount above par (tag `maturity_premium`) | a `WITHDRAWAL` for each |
| `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | cashless `ADJUSTMENT` of `Quantità`, `cost_basis_mode="manual"`, `cost_basis_override` = `Prezzo`/100 for a bond (`_BOND_KEYWORDS` in the name), `Prezzo` otherwise | none |
| anything else | skipped, `ca_securities_unknown_causale` | — |

- **Cash neutrality.** Each counter-entry is a same-day transaction of the same amount, with no
  asset, described `Auto cash for <TYPE> <name> (Crédit Agricole securities-only export)` and
  tagged `auto_cash`: the export adds no cash of its own, the real cash comes from the account
  export. When a `BUY` fails validation, its `DEPOSIT` is removed with it.
- **Maturity.** A `TITOLI SCADUTI` row reports `Quantità` 0, so a first pass sums each name's
  position: buys and transfer-in legs, minus fund redemptions. The shared
  `_brim_io.model_bond_maturity` (see the matured-bond tip in the
  [BRIM Plugin Guide](../../architecture/patterns/brim_plugin_guide.md)) closes that held nominal
  at par (`source="position"`). With no position it derives the nominal from `Controvalore` /
  `Prezzo` × 100 (`source="derived"`), and the plugin adds a `derived_quantity` warning todo on
  `quantity`. With neither, no split is attempted and the row keeps its reported figures.
- **Transfers in.** The succession legs are the receiving side of a transfer from an untracked
  dossier: no money was spent, so there is no `DEPOSIT`, and each source row stays its own
  `ADJUSTMENT`. They are listed together in one `ca_succession_transfer_in` info notice.

---

## 💳 Account layout

Account transactions are dated `Data Op.`, keep the bank's description verbatim (up to 500
characters; maturities compose their own) and are tagged `import`, `credit_agricole` and the
causale's slug (`_slug_causale`: `CEDOLE, DIVIDENDI, PREMI ESTRATTI` →
`cedole_dividendi_premi_estratti`).

### 🗃️ The causale registry

`_classify_account_row` returns `(type, cash, tier)`. Tiers 2 to 4 all book a `DEPOSIT` or a
`WITHDRAWAL` by sign — the cash is always right — and differ only in what the plugin declares
about the row.

| Tier | Causali | Result |
|---|---|---|
| 1 typed | `COMMISS./SPESE SU OPERAZ. TITOLI`, `COMMISSIONI/SPESE`, and `INTERESSI/COMPETENZE` debits | `TAX` when the description contains `CAPITAL GAIN`, `D.LGS 461`, `461/97`, `IMPOSTA`, `BOLLO` or `RITENUTA`, else `FEE`; a positive amount is a refund → `DEPOSIT` |
| 1 typed | `CEDOLE, DIVIDENDI, PREMI ESTRATTI`, and `INTERESSI/COMPETENZE` credits | `DIVIDEND` when the description says `DIVIDEND` and carries an ISIN, else `INTEREST`; a negative amount is a clawback → `WITHDRAWAL` |
| 1 typed | `TITOLI SCADUTI O ESTRATTI` credits | see [Matured securities](#matured-securities) |
| 2 unresolved | `COMPRAVENDITA TITOLI/FONDI/OPZIONI` rows not booked as a trade; `GIROCONTO/BONIFICO` credits that are fund redemptions | by sign, plus a `ca_account_trade_unresolved` blocker |
| 3 declared cash | `PAGAMENTO TRAMITE POS`, `PAGAMENTO UTENZE`, `PRELIEVO SPORT. AUTOM. ALTRA BANCA`, `PRELIEVO NOSTRO SPORTELLO AUTOM.`, `ACCREDITO EMOLUMENTI`, `GIROCONTO/BONIFICO` | by sign, silently |
| 4 unknown | anything else | by sign, plus one `ca_unknown_causale` info notice for all such rows |

### 🔗 Linking rows to a security

- **Income** that names an ISIN (`[A-Z]{2}[A-Z0-9]{9}[0-9]`) is linked to an asset keyed
  `isin:<ISIN>`, named after the text before the ISIN, without a leading `CEDOLA` or `DIVIDENDO`.
- **Securities charges** that name an ISIN (`SPESE STACCO CEDOLA … TIT: <ISIN> <name> MOV:…`) get
  the same key, named after the text between the ISIN and `MOV:`. The bank prints that name in full
  while coupon lines cut it at 19 characters, so `asset_id_for` keeps the longer name when one is the
  other cut short (`_is_truncation_of`).
- A `COMMISS./SPESE SU OPERAZ. TITOLI` fee or tax that names no ISIN gets a
  `ca_account_charge_unallocated` warning todo on `asset_id`, shown in the charges panel of the
  correction step: the user assigns it or keeps it on the account.
- **Withholding.** An income credit whose description spells `RITENUTA: <x>` is imported gross
  (the credited amount plus x), with a separate `TAX` of −x on the same asset (tag
  `withholding_tax`): the two sum back to the credited amount. A clawback is never grossed up.

### 🔁 Trades on the account

A `COMPRAVENDITA TITOLI/FONDI/OPZIONI` row carries the money, not the instrument or the quantity.
`try_account_trade` books a real `BUY` or `SELL` only when the file proves it:

1. **Direction** — buy words (`NOTA INF. ACQ`, `ACQUIST`, `SOTTOSC`…) or sell words
   (`NOTA INF. VEND`, `VENDIT`, `VEND.`, `DISINVEST`, `RIMBORS`), exactly one family, confirmed by
   the sign: a buy spends, a sale cashes in. Otherwise the reason is `no_keyword` or
   `sign_mismatch`.
2. **Name** — after `TIT:` (bonds) or after the order reference `ORD.:<ref>` (funds), cut before
   `DOSSIER:`, `RUB:`, `DATA:` or `MOV:`. Otherwise `no_name`.
3. **Quantity** — the `NOMINALE` stated by the coupons of that security in the same file, indexed
   by a prepass (`build_identity_indexes`) and matched by name prefix in either direction, on at
   least 6 characters. No such coupon → `no_quantity`; several securities → `ambiguous_name`;
   several nominals → `ambiguous_nominal`.

A resolved trade takes the nominal as its quantity, the coupon's ISIN as its asset key and the tag
`account_trade`. It always gets a `ca_account_trade_bundled_amount` warning todo on `cash` with
`split_hint: "trade_charges"`, because this layout never separates the price from the charges:
`compare_nominal` is set on buys only, and the `split_suggestions` name the securities charges
booked within ±3 days. A sale also gets `ca_account_trade_sell_quantity_presumed` on `quantity`,
because the coupon nominal is the whole position.

An unresolved row stays cash (tier 2) with a `ca_account_trade_unresolved` blocker on `asset_id`,
whose message and evidence comment depend on the reason (`trade_fallback_message`). It keeps the
`split_hint`, so the split zone opens as soon as the user types the row into a `BUY` or `SELL`.

### 🏦 Fund redemptions paid by transfer

A fund pays a redemption by wire, so it arrives as a `GIROCONTO/BONIFICO` credit, like a salary.
`_sct_fund_redemption_name` calls it a redemption only when three signals agree:

1. the ordering party (`ORD:<party> DT.ORD:`) has at least 8 letters and digits;
2. the operation text after it contains `RIMBORS`, `DISINVEST` or `LIQUIDAZ`;
3. the party is named again inside that text — compared on letters and digits only, so a name
   wrapped across the column width (`AMUNDI PRIMO INVES TIMENTO`) still matches.

The third signal keeps a tax refund (`RIMBORSO IRPEF`) or a utility refund out. A redemption
becomes a tier-2 `DEPOSIT` whose blocker has the reason `fund_redemption`: the user turns it into a
`SELL` and enters the units, which the file does not state.

### 🪦 Matured securities {: #matured-securities }

A `TITOLI SCADUTI O ESTRATTI` credit reads `RIMB.TIT. <name> (<code>)`. The digits of `<code>` are
matched against the ISIN digits of the coupons paid **the same day** that state a `NOMINALE`:

- **found** → `model_bond_maturity(ctv, held_qty=nominal)`: a `SELL` of the nominal at par (tag
  `account_maturity`) and an `INTEREST` for the surplus (tag `maturity_premium`), on the
  `isin:<ISIN>` asset;
- **not found** → a `ca_account_maturity_unlinked` warning, and the whole amount as one `SELL` at
  par 100 (nominal = cash) on an asset keyed `maturity:<code or name>` — never a `DEPOSIT`, so the
  proceeds close a position instead of inflating paid-in capital.

Both layouts call `attach_maturity_notices`, which puts the amber maturity banner on the
asset-create modal.

---

## 🔔 Notices and todos

Messages and evidence comments are in Italian, the language of the report. Only
`ca_succession_transfer_in` has an `importWizard.brimNotice.*` key, so the wizard shows it in the UI
language; every other message reaches the user as written.

| Code | Channel | Severity | Raised when |
|---|---|---|---|
| `ca_securities_unknown_causale` | notice | warning | a securities causale is not in the table (row skipped) |
| `ca_succession_transfer_in` | notice | info | transfer-in rows were found (one notice for all) |
| `ca_securities_empty` | notice | warning | the securities parse produced no transaction |
| `derived_quantity` | todo on `quantity` | warning | a `TITOLI SCADUTI` nominal was derived from `Controvalore` / `Prezzo` |
| `ca_account_invalid_amount` | notice | warning | an account amount cannot be read (row skipped) |
| `ca_account_maturity_unlinked` | notice | warning | an account maturity has no same-day coupon nominal |
| `ca_account_trade_unresolved` | todo on `asset_id` | blocker | every tier-2 row |
| `ca_account_trade_bundled_amount` | todo on `cash` | warning | every resolved account trade (`split_hint`) |
| `ca_account_trade_sell_quantity_presumed` | todo on `quantity` | warning | every resolved account sale |
| `ca_account_charge_unallocated` | todo on `asset_id` | warning | a securities charge names no ISIN |
| `ca_unknown_causale` | notice | info | tier-4 rows (one notice for all) |
| `ca_account_empty` | notice | warning | the account parse produced no transaction |

Except `derived_quantity` and the two `*_empty` notices, each one carries its source rows as
`BRIMEvidence`, with their line numbers and the export's own column labels.

---

## 🧪 Samples and tests

- `backend/app/services/brim_providers/sample_reports/` holds `credit_agricole-conti.csv` and
  `.xlsx` (account), `credit_agricole-export.csv` and `.xlsx` (securities), and
  `credit_agricole-conti-contract.csv`, the account sample plus an unknown causale and two ordinary
  transfer refunds. Every sample whose name contains `credit_agricole` (`test_file_pattern`) runs
  through the generic suite.
- `backend/test_scripts/test_external/test_brim_providers.py` (`./dev.py test external brim-providers`)
  pins the plugin's rules (`test_credit_agricole_*` in `TestBrokerParserCoverageHelpers`), the
  wizard contract on its samples (`TestPluginFrontendContract`) and the complete outputs with
  CSV/XLSX parity (`TestCreditAgricoleCanonicalCharacterization`).

## 🔗 Related

- [Crédit Agricole — user guide](../../../user/transactions/import/credit_agricole.md)
- [BRIM Plugin Guide → Talking to the import wizard](../../architecture/patterns/brim_plugin_guide.md#talking-to-the-import-wizard)
- [BRIM Architecture](architecture.md)
- [BRIM Providers List](providers_list.md)
