# W · ondata 4 · analisi del primo turno (solo lettura)

Base `c042f2481` (= `dev_release2`), worktree pulito. Quattro lotti, nell'ordine del brief: **Q-N78-1k**, l'helper legacy, la regola
dei plugin in beta con Fineco su `RowSkips`, **W-BS**. Nessun file toccato.

---

## 1. Q-N78-1k · la coppia di rettifiche collegate fra due broker propri

### 1.1 Prima una verifica: queste coppie esistono davvero?
- Due ADJUSTMENT collegati (`related_transaction_id` nei due sensi, stesso asset, quantità opposte, broker diversi) **si possono
  creare solo da API** (due creazioni con lo stesso `link_uuid`: `batch_creates.py:338`, `_validate_linked_pair` accetta due righe dello
  stesso tipo e, per l'ADJUSTMENT, non controlla altro) o arrivano da dati vecchi. Non ho trovato nessun punto del Form, del Bulk o dei
  plugin che li crei: il Form propone di **promuovere** due ADJUSTMENT *non* collegati a un TRANSFER (`promote_from` in
  `type_metadata.py:297`), e i plugin collegano solo FX_CONVERSION e coppie di cassa.
- Oggi i motori li trattano così: `daily_state.py:1179` («ADJUSTMENT pairs are left out» dei flussi interni), quindi A realizza −costo (N78-1)
  e B porta capitale al suo costo. È il caso 15b di `test_broker_internal_flows.py`, che il test-author ha fissato «alla lettera» il 22/10.

### 1.2 L'esempio (10 azioni a 50, valgono 80; spostate da A a B con due rettifiche collegate; la gamba di B porta costo 50)
Calcolato a mano sulle formule del codice (`daily_state.py:418-428`, `:1157-1171`, `scope_boundary.py:95-104`); i rossi lo fissano.

| | Oggi (N78-1 alla lettera) | **P** · uscita al PMC (la decisione) | M · come una gamba di TRANSFER |
|---|---|---|---|
| **Tutti i broker**: capitale | 1000 | **500** | 500 |
| realizzato | −500 | **0** | 0 |
| P&L totale | −200 | **300** | 300 |
| TWRR del giorno | −62,5 % | **0 %** | 0 % |
| **Solo A, dopo lo spostamento**: capitale | 500 | 0 | −300 |
| realizzato | −500 | 0 | 0 |
| P&L totale | −500 → perde anche il guadagno | **0** (il guadagno di 300 esce con le unità) | 300 (resta ad A) |
| TWRR del giorno | −100 % | **−37,5 %** | 0 % |
| **Solo B**: capitale | 500 | 500 | 800 |
| P&L totale | 300 | **300** (eredita il guadagno) | 0 |

**Come si legge.**
- Tutte e due le regole nuove rendono **0 il totale** («uno spostamento interno non cambia niente») e **uguali** i numeri dei broker presi
  insieme. Oggi invece il totale perde 500.
- **P** (quella che hai scelto): il guadagno viaggia con le unità: A lo perde (P&L 300 → 0), B lo eredita (0 → 300). Con il solo A il
  TWRR del giorno segna **−37,5 %**: il flusso è il costo (500), ma il valore cala di 800. È un rendimento finto, come quello che N78-1 ti ha
  mostrato per (a). Me lo hai confermato (domanda 10): lo scrivo qui perché il numero è grande.
- **M**: ogni gamba vale quanto una gamba di TRANSFER al bordo dell'ambito (lotto 41 per la Dashboard, J-10 per i lotti): al valore di mercato. Il guadagno
  resta ad A, B parte da 800, il TWRR resta neutro. È la regola già in vigore per i TRANSFER.

### 1.3 La regola in una frase, e dove sta
**P**: *un ADJUSTMENT in uscita collegato a un ADJUSTMENT in entrata (stesso asset, quantità opposte, broker diversi) cede le unità al PMC del
suo broker (ai lotti, al costo FIFO di ogni pezzo), non a zero; la gamba in entrata resta com'è.*
Un solo modulo nuovo in `financial_math/`: **`linked_adjustments.py`**, con il predicato `is_internal_adjustment_exit(tx, partner)` (i criteri sopra) e il
suo calcolatore del valore d'uscita. Lo leggono:
1. **Dashboard** (`daily_state.py`, il ramo N78-1 `:418-428`): se la gamba è di una coppia, il capitale scende del PMC × q e il realizzato è 0
   (`proceeds = cost`), come il vecchio J-24 con il PMC; la gamba in entrata resta com'è (`_is_capital_adjustment`).
2. **Lotti FIFO** (`fifo/engine.py`, `FifoLotEngine.__init__` normalizza le righe): la gamba in uscita di una coppia riceve `hands_over_at_own_cost=True`, che
   il motore già conosce (J-10): realizzato 0.
3. **Performance dei lotti** (`lots/histories.py:146-152`): un flusso in uscita pari al costo per quella gamba (oggi nessun flusso).
4. **Bordo dell'ambito** (`lots/scope_boundary.py`, 4 punti `_type_of(tx) == _TRANSFER`): la gamba in uscita con la partner fuori dall'ambito si legge come in J-10 oggi
   **solo per i TRANSFER**; per P le gambe di una coppia di rettifiche non cambiano lettura (l'uscita al PMC la dà già il punto 2), ma `partner_ids_to_load` deve
   caricare anche i partner delle rettifiche (per sapere che la gamba è di una coppia).
5. **Yield on cost** (`yield_on_cost.py:252`, `:421`): solo se legge la gamba; verificare con un rosso (il YOC guarda gli arrivi).
Con **M** i siti sono di più (otto: classificatore, `_internal_pairs`, passo 3b, `_transfer_leg_capital`, FIFO, bordo, performance, yield on cost) e si
sostituisce ovunque `type == TRANSFER` con «agisce da TRANSFER»; **P** ne tocca cinque e riusa meccanismi esistenti (`hands_over_at_own_cost`, il flusso J-24).

### 1.4 Il lavoro, in ordine
- **Rossi** (test-author): nei file che hai nominato — `services financial-math`, `lots-analysis-pure`, `portfolio-engine`, `transaction-cost-basis-rule` — il caso
  «coppia collegata A→B» con le tre viste (tutti, solo A, solo B), più due guardie: due rettifiche **non** collegate restano come N78-1; una coppia con broker
  uguale o quantità non opposte non è una «coppia» (resta senza valore). Il test 15b (`test_case_15b_adjustment_pair_out_leg_has_no_value_and_in_leg_brings_its_cost`) si
  rovescia ai numeri di P.
- **Cura**: il modulo, poi i quattro punti sopra, in un solo giro. Nessun codice che riscrive dati.
- **Doc**: la frase di N78-1 in `user/transactions/`; la sezione di teoria («Outgoing Adjustments», `deposited-capital`) con la coppia.
- **MF rivede**; **J-68** in `lots_analysis_service.py` non lo tocco; se J-68 sfiora `scope_boundary.py` mi fermo.
- File che tocco: `financial_math/linked_adjustments.py` (nuovo), `portfolio/daily_state.py`, `fifo/engine.py`, `lots/histories.py`, `lots/scope_boundary.py`,
  `yield_on_cost.py` (forse), i test sopra, le pagine utente e di teoria. Peso: **medio** (≈ 1 giorno).

### 1.5 Domande
- **Q-N78-1k-1 · P o M.** La decisione è P (uscita al PMC), che con il solo A fa vedere **−37,5 %** di TWRR e fa sparire il guadagno di 300 da A. M è la regola
  che i TRANSFER hanno già (neutra, un solo concetto, otto siti). *Consiglio di W: come hai deciso, P, perché è più semplice e coerente con il PMC; M solo se il
  −37,5 % ti disturba.* Se scegli P non serve altro; se M, dimmelo prima dei rossi.
- **Q-N78-1k-2 · Le coppie collegate di rettifiche si possono ancora creare?** L'API le accetta. Due vie: (a) restano e le leggiamo come sopra *(consiglio: costa
  quasi niente, e i dati vecchi le possono contenere)*; (b) l'API le rifiuta per le righe nuove, con un codice. È una scelta di prodotto: l'analisi consiglia (a).

---

## 2. L'helper delle righe legacy in `frontend/e2e/fixtures/`
- Le copie sono **due**: `portfolio/data-quality-legacy.spec.ts:231` (`writeLegacyRows`, quantità costanti) e `portfolio/yield-on-cost-real.spec.ts:180` (quantità come
  argomenti). `data-quality-real.spec.ts` non ne ha. Il corpo è lo stesso, riga per riga.
- Nuovo `frontend/e2e/fixtures/legacy-cost-rows.ts`: la funzione con le quantità come argomenti, il tipo `LegacyRows`, il tipo `LegacyRequest`, `HELPER_MODULE`.
  `PROJECT_ROOT`: vedere come lo definiscono i due spec (verificare che `fixtures/` abbia già un equivalente, `global-setup`); i due spec lo importano. Nessun
  comportamento cambia.
- Doc: la docstring di `backend/test_scripts/test_db/legacy_cost_rows.py` («Who uses it») dice già i due spec.
- Rosso: nessuno nuovo (refactoring puro); le prove sono i due spec verdi (`front-portfolio data-quality-legacy`, `yield-on-cost-real`) nello slot. Peso: **piccolo**.

---

## 3. La regola dei plugin in beta, e Fineco su `RowSkips`
**La regola** (da scrivere, in inglese): *un plugin in beta può scrivere stringhe di avviso per le righe che salta; uscire dalla beta significa adottare `RowSkips` (o
codici propri con `report_issue`), non un lotto a parte.* Livelli: riga nota → silenzio o log; riga ignota o illeggibile → avviso con `report_issue`. Da fissare in
`.claude/skills/brim-plugin/SKILL.md` (la regola 10, dove oggi non si parla di beta) e in `brim_plugin_guide.md` (la riga ~251 dice «the *pending* set … may still write a
plain string … migrated later» senza la regola; cita `RowSkips` alla ~94). Fonte: `PROSSIMI_LAVORI.md`, «W-B86 e W-B87», «Esito 22/10».

**Fineco** (`broker_fineco/plugin.py`) oggi ha quattro stringhe: righe troppo corte (`:319`), data non valida (`:329`), descrizione vuota (`:340`), operazione ignota
(`:347`). Con `io.RowSkips(header)`: le prime tre → `rows_unreadable` (motivo: colonne / data / descrizione), l'ultima → `rows_not_recognized` (motivo: l'operazione). Le due
note blu (`fineco_not_yet_settled`, `fineco_incomplete_rows`) restano. Versione **1.4.0 → 1.5.0**.
- **Rossi**: `test_brim_row_skips.py` — Fineco esce da `ROW_SKIPS_PENDING` (`:60-73`) ed entra in `ROW_SKIPS_BY_PLUGIN` con un caso «operazione ignota» e uno «data illeggibile»; il
  test di versione; in `test_brim_providers.py` il guardia `test_guard_fineco_a_row_without_a_readable_date_is_skipped` oggi si aspetta un avviso `legacy` (cambia a `rows_unreadable`).
- Verdi: `external brim-row-skips`, `external brim-providers`, `api brim`, la pagina utente di Fineco (una frase: le righe ignote hanno il link per segnalarle) e `architecture.md` («Fineco»).
- File: il plugin, due file di test, skill, guida, doc. Peso: **piccolo-medio** (≈ ½ giorno).
- Domanda **Q-Fineco-1**: la descrizione vuota è «illeggibile» (come la data) o «ignota»? *Consiglio: illeggibile.*

---

## 4. W-BS · le impostazioni dei plugin BRIM, predisposte
### 4.1 Cosa ho trovato
- La fondazione (`services/plugin_settings/*`) conosce due famiglie, `asset` e `fx`: `FAMILY_RULES` (`fields.py:92`), `FAMILY_REGISTRIES` e `FAMILY_ICON_ATTRIBUTES`
  (`service.py:62-66`), `PluginSettingFamily` (`schemas/plugin_settings.py:22`). Un plugin BRIM con `settings_fields` oggi è rifiutato dal registro
  (`provider_registry.py:285`: la famiglia è `None`).
- **Dove il plugin BRIM viene istanziato per un parse**: **un solo punto di produzione**, `api/v1/brokers.py:983`, `parse_file_offloaded(file_id, plugin_code, broker_id)`, con
  `current_user` a portata di mano. Da lì `brim_parse_pool.py:129` manda `brim_provider.parse_file` al **sottoprocesso** (pool `forkserver`/`spawn`), e **il figlio**
  fa `get_provider_instance(plugin_code)` (`brim_provider.py:1765`). Altri usi dell'istanza: `brokers.py:883, 904` (controllo del file: `can_parse`), `brim_report_sets.py:122`,
  `brim_gap_fix.py:55`, `brim_provider.py:909/917/1618` (combinazione dei file e rilevamento), `registry.auto_detect_plugin` (istanzia tutti i plugin: legge il file, non i valori).
- **Il passaggio al figlio costa poco**: `BoundSettings` (`contract.py:28`) ha `__slots__` ma si serializza (pickle); i valori si risolvono nel **padre** (`configure_instance`
  legge il DB) e si passano come argomento extra a `parse_file`, che fa `plugin.bind_settings(bound)` nel figlio. Con **zero campi** dichiarati il gancio non legge il DB e non passa
  niente (`runtime.py:58`). I segreti viaggiano nel canale del pool (stessa macchina, in memoria), mai nei log; il padre maschera gli errori del parse con `mask_exception` /
  `mask_text` (`utils/runtime/secret_masking.py`), come `assets/core.py:204`.

### 4.2 Cosa faccio (con i rossi prima)
1. `BRIMProvider(PluginSettingsMixin, ABC)` (`brim_provider.py:121`): `settings_fields=()`, `test_only`, `settings`.
2. `BRIMProviderRegistry.settings_family()` → `"brim"`.
3. `FAMILY_RULES["brim"] = FamilyRules(user_scope=True, secrets=True)`; `PluginSettingFamily.BRIM`; `FAMILY_REGISTRIES["brim"]`; `FAMILY_ICON_ATTRIBUTES["brim"] = "icon_url"`.
4. Il gancio: `parse_file_offloaded(..., user_id=…)` risolve il `BoundSettings` nel padre, solo se il plugin dichiara campi; `parse_file(..., settings=None)` lo lega nel figlio; maschera gli errori.
   Gli altri punti (rilevamento, set di report, gap-fix) restano come sono: non hanno valori da usare finché nessun plugin li chiede (CP12).
5. Frontend: `SettingsFamily`, `FAMILIES`, `FAMILY_ICONS` (un'icona lucide), `FAMILY_TITLE_KEYS`, la chiave `pluginSettings.family.brim` nelle 4 lingue; `api sync`.
6. **Nessun plugin reale dichiara campi.** Per i test: un plugin BRIM `test_only` con un campo `select` personale, uno d'istanza e un `secret`.
- **Un rischio del plugin di prova**: i registri trovano i plugin leggendo la cartella `brim_providers/`; un plugin di prova lì dentro entrerebbe nei test che ciclano su tutti i plugin
  (`test_brim_row_skips`, la lista fissa di `test_brim_report_sets`, i campioni di `test_brim_providers`). *Proposta: dichiararlo nel modulo di test e registrarlo solo per la durata del test*
  (registro ripulito alla fine), così nessuna cartella nuova e nessun contratto da aggiornare.
- **Rossi**: `plugin-settings-contract` (famiglia `brim`), `plugin-settings-service` (catalogo con il plugin di prova, segreto solo «impostato»), `plugin-settings-crypto`,
  `plugin-settings-runtime` (il gancio senza campi non legge il DB; con il plugin di prova lega i valori e maschera il segreto), `api plugin-settings`, `api brim` invariato, Vitest della
  scheda (un gruppo `brim`), `plugin-settings-guards` invariato (nessuna variabile in `.env.example`).
- File: `brim_provider.py`, `brim/registry.py`, `brim_parse_pool.py`, `api/v1/brokers.py`, `plugin_settings/{fields,service}.py`, `schemas/plugin_settings.py`, `features/plugin-settings/*.ts`,
  `i18n/pluginSettings/*.json`, i test, `architecture.md` (BRIM) e la skill (una riga). Peso: **medio** (≈ 1-1,5 giorni). X rivede. Nessuna riga CHANGELOG: è una predisposizione.
### 4.3 Domande
- **Q-BS-1 · Quale utente.** Il parse gira per l'utente che importa: i valori **personali** sono i suoi (`user_id=current_user.id`), quelli d'istanza sono di tutti, come per la ricerca degli asset.
  *Consiglio: sì.*
- **Q-BS-2 · Il plugin di prova.** Nel modulo di test, non in `brim_providers/` (§4.2). *Consiglio: sì.*
- **Q-BS-3 · Gli altri punti** (rilevamento, set di report, gap-fix): fuori dalla predisposizione, da collegare con il primo campo vero (CP12)? *Consiglio: sì, scritto nella doc come «da fare con il primo campo».*

---

## 5. Ordine e stima
1. **Q-N78-1k** (≈ 1 giorno, MF rivede) → 2. **helper legacy** (≈ 1 ora, nello stesso giro) → 3. **regola in beta + Fineco** (≈ ½ giorno) → 4. **W-BS** (≈ 1-1,5 giorni, X rivede).
I lotti 3 e 4 non toccano gli stessi file del lotto 1; il lotto 1 e J-68 si sfiorano al più in `lots/`.

## 6. Cosa aspetto
Il via ai quattro lotti e le risposte: **Q-N78-1k-1** (P o M), **Q-N78-1k-2** (le coppie si possono ancora creare), **Q-Fineco-1**, **Q-BS-1…3**. Con i consigli sopra posso partire subito dai rossi.
