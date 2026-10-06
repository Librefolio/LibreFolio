# Plan Phase 00 — Translated code blocks keep the source indentation (pipeline fix + `code-block-indent` check)

**Creato**: 2026-10-06
**Baseline/target**: `a7d0b37eca78db4e0474156b1f3fb6b6196b177e` (`dev_release2`, the train D, K, L, M, N), tree `3c6421cda`, HEAD verified clean
**Workstream**: M — branch `e-alfy-cloud-resource-sizing`, worktree `LibreFolio-worktrees/e-alfy-upgraded-telegram`
**Coordinator**: session `c8328a01-f208-4ade-a352-0486d1f14de2`
**Runtime lane**: ports `6158`/`6168`, data dir `/tmp/librefolio-r2-m`; evidence outside the repo in `LibreFolio-cloud-sizing/release-images/step8/`
**Previous plan**: [plan-phase00ReleaseImages.prompt.md](plan-phase00ReleaseImages.prompt.md). Its step 6 (Tailscale) fixed the flattened compose by hand, and this plan removes the cause.
**Origin**: the coordinator's «passo 8», analysis only: `LibreFolio-cloud-sizing/release-images/step8/step8-analysis.md` (exact list `step8-list.md`)
**Autorizzazione developer**: «si mi torna, allora di ad M di correggere lo script. riguardo al correggere le pagine già convertite sono in dubbio visto che tra poco dobbiamo rifare il grande allineamento, che ne pensi? magari solo per le pagine che comunque sono fuori dallo scope?», relayed by the coordinator on 2026-10-06 at 20:00. Start relayed after the realignment to `a7d0b37ec`.

## 0. Decisions (relayed by the coordinator)

| # | Decision |
|---|---|
| D1 (changed) | The repair script touches **only the pages the next alignment does NOT re-translate** (EN not stale). The stale pages (`docker_advanced`, `service_exposure`, `create-edit`, `installation` and the rest) are regenerated correctly by the fixed pipeline. The plan lists both exactly (§3). The repair must not make the translation cache believe a page changed: no re-translation, no extra stamp. After the alignment, `translate-validate` must report 0 `code-block-indent`. |
| D2 | **B + C**: step 7 works outside fences, and the EN indentation is restored into the code blocks before the write. The helper lives in `code_blocks.py`. |
| D3 | **ERROR `code-block-indent` everywhere**. Remove «alignment stripped» from the LOCALIZED message. |
| D4 | Plan at this path, linked both ways. |
| D5 | Prose collateral stays out (backlog). |
| D6 | No hand correction of the `installation` tags: «è normale, non abbiamo ancora eseguito la pipeline». The alignment fixes them. |
| Order | Red tests with test-author, then code, the runner entry in `_backend_utils.py` (the Risk family touches only `:303`, stay away), the EN dev doc, checkpoint. Critical path: integrated before any translation. |

## Sintesi (italiano)

- **Causa**: il passo 7 di `_clean_translation` (`translate_docs.py:418-419`) comprime ogni sequenza di 2 o più spazi in tutto il documento, codice compreso. È deterministico (riprodotto estraendo la funzione): schiaccia i livelli a 0/1 e porta i fence fuori da liste e tab. La validazione non lo vedeva, perché classificava ogni differenza nel codice come LOCALIZED «alignment stripped».
- **Correzione**:
  - **B**: il passo 7 lavora solo fuori dai blocchi di codice e solo tra caratteri non-spazio. Rientri e hard break restano intatti, mentre i doppi spazi lasciati dai marker rimossi spariscono come prima.
  - **C**: prima di scrivere, ogni blocco tradotto abbinato a quello EN riprende gli spazi iniziali EN riga per riga, fence compresi, e il testo tradotto non cambia.
  - Un nuovo controllo ERROR `code-block-indent` in `translate-validate`.
- **Pagine**:
  - si ripara subito solo la lista **B**, cioè quelle che l'allineamento non ritraduce: 54 coppie, 18 pagine (17 indicatori e `price-resolution`), solo mermaid;
  - la lista **A** (9 coppie: `docker_advanced`, `service_exposure`, `create-edit`) la rigenera la pipeline corretta;
  - provato su copia: la cache non si accorge della riparazione (stesso piano di traduzione, EN e cache identici byte per byte). Le 51 segnalazioni rimaste sono tutte in A, e la pipeline corretta le porta a 0.
- **Gate di release**: `translate-validate` blocca ogni esecuzione di `release.yml` tranne quelle su `dev`, compresa una release pubblicata (`release.yml:123-126`: `continue-on-error` solo su `dev`; il workflow non gira mai su un push a `main`). Oggi è già rosso (606 errori su `a7d0b37ec`); dopo l'allineamento il nuovo controllo dà 0 per costruzione.

## 1. Current state (`a7d0b37ec`)

- **Cause:** `mkdocs_src/aphra-pipeline/translate_docs.py:418-419`, `_clean_translation()` step 7: `text = re.sub(r'  +', ' ', text)` on the whole document.
  - It is called at `:1784`, right before the only output write (`:1785`) in `_translate_one_lang` (`:1611`).
  - No code block is masked or protected.
- **Step 10 (`:432-469`)** re-pads only `!!!` admonition bodies from 1 to 4 spaces. Its comment blames the LLM.
- **Blind spots:**
  - `_structural_diff` (`:738-748`) compares only the count and language tags of code blocks.
  - `validate_translations.check_code_blocks` (`:254-302`) compares by position and files every difference as LOCALIZED «comments translated or alignment stripped».
- **Selection rule** of the next alignment (`run_translate`, `:1963-1979`): `(page, lang)` is skipped iff the EN md5 equals the cached `md5` and `lang` is in `langs_done`. Translated files never enter the decision.
  - `translate-stamp` (`:3003-3116`) also reads only the EN md5.
  - So a whitespace repair of translated files is invisible to the cache by construction.
- **Release gate:** `release.yml:123-126` runs `translate-validate --hide-localized` with `continue-on-error` only on `dev`. The workflow runs on a push to `dev`, a manual dispatch or a published release (never on a push to `main`), so the step blocks every run except `dev`, a published release included. It is red today (606 errors at `a7d0b37ec`), so the alignment must happen before the next release anyway.

## 2. Design

### 2.1 `mkdocs_src/aphra-pipeline/code_blocks.py` (new, stdlib only)

A third-party import would make `dev.py` silently drop the translate commands: its import is wrapped in `except ImportError: pass`.

- **`FencedBlock`** (frozen dataclass):
  - `start` and `end`: 0-based line indexes of the opening and closing fence;
  - `indent`: whitespace before the opening fence;
  - `lang`: first word of the info string, lower-case;
  - `lines`: the block, fences included;
  - `closed`: whether a closing fence exists.
- **`parse_fenced_blocks(text)`:** backtick and tilde fences of 3 or more characters, at any indentation. A block closes on the same character with at least the same length and nothing after it. An unclosed fence runs to the end of the text with `closed=False`.
- **`code_line_mask(text)`:** True for every line of every fenced block, fences included (unclosed blocks to the end).
- **`pair_blocks(source_blocks, translated_blocks)`:**
  - difflib over `(lang, normalized code)`, where normalization strips lines, maps hash-comment lines to `#`, drops trailing ` # comment` and maps `<placeholder>` to `<P>`;
  - inside a `replace` opcode, the leftover blocks pair in order when the language and line count match: translated Mermaid labels, HuJSON `//` comments;
  - result: `(i, j)` index pairs, monotonic.
- **`restore_code_indent(source, translated) -> (text, changed_lines)`.** For each closed pair with the same line count, line by line, fences included; blank lines on either side are left alone:
  - if the non-whitespace tokens are equal, the line becomes the EN line (trailing whitespace stripped);
  - otherwise it becomes the EN leading whitespace + the translated content, and the EN gap before an inline `#`/`//` comment is restored when the code part is identical;
  - a line is rewritten only if it differs beyond trailing whitespace.
- **`code_indent_issues(source, translated)`:** for each closed pair with the same line count, the 0-based translated line indexes whose leading whitespace differs from EN (non-blank lines only).

### 2.2 Pipeline (`translate_docs.py`)

- **B:** step 7 becomes `_collapse_inner_spaces(text)`: `re.sub(r'(?<=\S) {2,}(?=\S)', ' ', line)` on lines outside `code_line_mask`. Leading indentation and trailing hard breaks are never touched.
- **C:** new `_finalize_translation(source_text, translated) -> (text, restored_lines)` = `_clean_translation` + `restore_code_indent`. It replaces the bare call at `:1784`, and logs when lines were restored.
- Step 10 stays as a safety net; its comment says what it really repairs.

### 2.3 Validator (`validate_translations.py`)

- **`check_code_block_indent`**: an ERROR with check name `code-block-indent`.
  - It reports the line of the first drifted line, the block language, the TR line range, the lines off, and the EN → TR relative levels.
  - It is registered in `ALL_CHECKS` right after `code-blocks`.
- **`check_code_blocks`**: the LOCALIZED message loses «alignment stripped».

### 2.4 Runner and docs

- `scripts/test_runner/_backend_utils.py`:
  - `utils_translation_code_blocks`, placed before `utils_all` (`:226`);
  - `add_test(cat, "translation-code-blocks", …, isolation="pure")` before the `"all"` entry (`:372`).
  - Both are more than 60 lines from `:303`.
- `mkdocs_src/docs/developer/docs/translation-pipeline.md` §6 «Post-processing cleanup» and the «Automated Checks» table (docs-writer, EN only, developer pages are EN-only).

## 3. The two lists (computed on `a7d0b37ec` with the pipeline's own selection rule)

Script: `s8_alignment_plan.py`. It extracts `get_translatable_files`, `_extract_nav_paths`, `_detect_target_languages` and `_file_md5` by AST, without importing the module.
- The next alignment (`./dev.py mkdocs translate`, no `--force`) re-translates **177 page × language pairs on 59 pages**: 37 pages whose EN changed and 22 never translated.
- `installation` is among them: its compose is intact today, and the fixed pipeline keeps it intact.
- Lines below are block bodies, fences excluded.

**A: re-translated by the next alignment (9 pairs, 51 blocks). Not repaired: the fixed pipeline regenerates them.**

| Page | EN block | Kind | EN lines | it / fr / es TR lines | EN → TR levels | Verdict |
|---|---|---|---|---|---|---|
| `admin/docker_advanced` | #3 | text | 64-65 | 64-65 / 64-65 / 64-65 | [0, 3]→[0] | layout |
| `admin/docker_advanced` | #4 | mermaid | 79-85 | 79-85 / 79-85 / 79-85 | [0, 4]→[0, 1] | layout |
| `admin/docker_advanced` | #18 | bash | 252 | 237 / 237 / 237 | fence col 4→1 | list split |
| `admin/docker_advanced` | #19 | bash | 258 | 243 / 243 / 243 | fence col 4→1 | list split |
| `admin/docker_advanced` | #20 | bash | 264 | 249 / 249 / 249 | fence col 4→1 | list split |
| `admin/docker_advanced` | #21 | yaml | 286-288 | 271-273 / 271-273 / 271-273 | [0, 2]→[0] | same data |
| `admin/docker_advanced` | #22 | yaml | 298-324 | 283-309 / 283-309 / 283-309 | [0, 2, 4, 6, 8]→[0, 1] | **broken** |
| `admin/service_exposure` | #0 | mermaid | 24-26 | 24-26 ×3 | [0, 4]→[0, 1] | layout |
| `admin/service_exposure` | #3 | mermaid | 92-97 | 92-97 ×3 | [0, 4, 8]→[0, 1] | layout |
| `admin/service_exposure` | #5 | mermaid | 140-146 | 140-146 ×3 | [0, 4, 8]→[0, 1] | layout |
| `admin/service_exposure` | #10 | json (HuJSON) | 251-283 | 251-283 ×3 | [0, 2, 4, 6]→[0] | layout |
| `admin/service_exposure` | #11 | mermaid | 297-306 | 297-306 ×3 | [0, 4, 8]→[0, 1] | layout |
| `admin/service_exposure` | #13 | text | 324-327 | 324-327 ×3 | [0, 9]→[0, 1] | layout |
| `admin/service_exposure` | #14 | mermaid | 378-399 | 378-399 ×3 | [0, 4, 8, 12]→[0, 1] | layout |
| `admin/service_exposure` | #22 | text | 659-662 | 618-621 ×3 | [0, 9]→[0, 1] | layout |
| `user/assets/create-edit` | #0 | mermaid | 15-23 | 15-23 ×3 | [0, 4]→[0], fence col 4→1 | tabs empty |
| `user/assets/create-edit` | #1 | mermaid | 29-37 | 29-37 ×3 | [0, 4]→[0], fence col 4→1 | tabs empty |

**B: NOT re-translated by the next alignment (54 pairs, 54 blocks). Repaired now, code blocks only.**

All are `financial-theory/technical-analysis/…`, `mermaid`, block #0, it/fr/es, layout only (Mermaid ignores indentation).

| Page | EN lines | it / fr / es TR lines | EN → TR levels |
|---|---|---|---|
| `indicators/adx` | 54-62 | 54-62 ×3 | [0, 4]→[0, 1] |
| `indicators/aroon` | 50-58 | 50-58 ×3 | [0, 4]→[0, 1] |
| `indicators/atr` | 42-47 | 42-47 ×3 | [0, 4]→[0, 1] |
| `indicators/cci` | 49-57 | 49-57 ×3 | [0, 4]→[0, 1] |
| `indicators/donchian-channels` | 48-54 | 48-54 ×3 | [0, 4]→[0, 1] |
| `indicators/kama` | 58-64 | 58-64 / 59-65 / 58-64 | [0, 4]→[0, 1] |
| `indicators/mfi` | 53-62 | 53-62 ×3 | [0, 4]→[0, 1] |
| `indicators/momentum` | 47-53 | 47-53 ×3 | [0, 4]→[0, 1] |
| `indicators/natr` | 38-44 | 38-44 ×3 | [0, 4]→[0, 1] |
| `indicators/obv` | 48-54 | 48-54 / 48-54 / 49-55 | [0, 4]→[0, 1] |
| `indicators/ppo` | 50-59 | 50-59 ×3 | [0, 4]→[0, 1] |
| `indicators/roc` | 42-47 | 42-47 ×3 | [0, 4]→[0, 1] |
| `indicators/sma` | 42-46 | 42-46 ×3 | [0, 4, 8]→[0, 1] |
| `indicators/stochastic-rsi` | 56-60 | 56-60 ×3 | [0, 4]→[0, 1] |
| `indicators/trend` | 46-53 | 46-53 ×3 | [0, 4]→[0, 1] |
| `indicators/volatility` | 44-49 | 44-49 ×3 | [0, 4]→[0, 1] |
| `indicators/volume` | 39-44 | 39-44 ×3 | [0, 4]→[0, 1] |
| `performance-metrics/portfolio-engine/price-resolution` | 31-38 | 31-38 ×3 | [0, 4]→[0, 1] |

## 4. Evidence gathered before coding (scratch copies only)

- **Cache invisibility.** A B-only repair was made on a `git archive` copy of `a7d0b37ec`, with the prototype: 54 blocks, 54 files, 342 lines, 0 violations (whitespace only, inside blocks).
  - The pipeline plan is identical before and after (177 pairs).
  - The EN sources and `.translate-hashes.json` are byte-identical.
  - 51 blocks stay flagged, all in A.
- **Post-alignment proxy.** The fixed finalize (B + C) was fed today's damaged A translations as if the LLM had returned them: 51 → **0** flagged.
- **No side effects:** `--dry-run` was not used, because `_load_hashes()` can rewrite the tracked cache when it migrates entries (none need it today).

## 5. Steps

1. Plan file and cross-link.
2. Red tests (test-author): `backend/test_scripts/test_utilities/test_translation_code_blocks.py`.
3. `code_blocks.py`; pipeline B + C; validator check and message; runner entry.
4. B repair through the in-repo `restore_code_indent`, driven from outside the repo, with the same guards as §4.
5. EN dev doc (docs-writer).
6. Gates, then the checkpoint.

## 6. Gates and definition of done

- `utils translation-code-blocks` green; `utils all` green.
- `translate-validate` before and after:
  - `code-block-indent` = 105 before the repair and 51 after, all in A;
  - every other count unchanged except LOCALIZED wording.
- `mkdocs build` strict and `check-links` green.
- `git diff --check` clean.
- `.translate-hashes.json` and every `.en.md` untouched.
- **After the developer's alignment (not M's to run):** `translate-validate` reports 0 `code-block-indent`; the corpus guard then covers every page.

## 7. Risks

- **A translate run before this lands** re-flattens A, `installation` and the Tailscale compose. This is on the critical path.
- **The corpus guard covers only up-to-date pages.** A stale page is excluded until it is re-translated; that is the alignment's job. After the alignment, the guard covers everything.
- **Pairing** of translated-text blocks is in order by language and line count. A reordering translation can mis-pair and then raises an ERROR for a human to review, which is the safe direction.
- **Merges** touching the 54 B files conflict on whitespace only. Resolution: keep the other side and re-run the repair, which is idempotent.

## 8. Conflict forecast

| Surface | Overlap |
|---|---|
| `mkdocs_src/aphra-pipeline/{translate_docs,validate_translations}.py`, new `code_blocks.py` | none known (coordinator) |
| 54 TR files (B list) | code-block whitespace only |
| `scripts/test_runner/_backend_utils.py` | shared: one function before `utils_all`, one `add_test` before `"all"`; Risk family at `:303` |
| new test file | — |
| `mkdocs_src/docs/developer/docs/translation-pipeline.md` | EN dev page |
| `CHANGELOG.md` | coordinator |

## 9. Commands (lane)

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-m utils translation-code-blocks
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-m utils all
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate-validate
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs check-links
```

## Progress (after every step: ✅ with date, «Note implementazione», «Fuori pista»)

### 1. ✅ Plan file and cross-link — 2026-10-06
> **Note implementazione**: this file; forward link added to `plan-phase00ReleaseImages.prompt.md` (header + Progress §9). Lists A/B from `s8_alignment_plan_target.json` (`a7d0b37ec` export).

### 2. ✅ Red tests (test-author) — 2026-10-06
> **Note implementazione**: `backend/test_scripts/test_utilities/test_translation_code_blocks.py`, 80 tests. The fixtures mirror the real pages (annotated compose, list steps, `!!!` snippet, Mermaid tabs, `???` HuJSON, tilde ASCII art); the damaged translation is the old step 7 applied to an ideal translation. Runner entry `utils translation-code-blocks` (`_backend_utils.py`: function before `utils_all`, `add_test` before `"all"`, hunks at old lines 225/371, far from `:303`). Red run: 80 collected, 19 failed + 59 errors + 2 green by design (fixture self-check, the marker-gap regression pin), no collection error (`step8/libreFolio_m_s8_red.log`).

### 3. ✅ Code: `code_blocks.py`, pipeline B + C, validator — 2026-10-06
> **Note implementazione**:
> - `mkdocs_src/aphra-pipeline/code_blocks.py` (new, stdlib only: `difflib`, `re`, `dataclasses`). Pairing keys ignore indentation, spacing, `#`/`//` comments and `<placeholders>`; leftover blocks in a differing stretch pair in order by language and line count. Unclosed blocks and blocks of different length are never rewritten.
> - `translate_docs.py`: `from code_blocks import …`; `_collapse_inner_spaces()` replaces step 7; `_finalize_translation()` = clean + restore, the only write (`_translate_one_lang`) goes through it and logs the restored lines; step 10 and post-step comments corrected.
> - `validate_translations.py`: `check_code_block_indent` (ERROR `code-block-indent`, first drifted line, TR range, lines off, EN/TR levels) registered after `code-blocks`; the LOCALIZED message no longer says «alignment stripped».
> - Lint: `code_blocks.py` ruff + black clean; the two existing scripts stay at their baseline ruff counts (87 / 22, they are not black-formatted and were not reformatted).
> - Tests: 79 passed, 1 failed = the corpus guard, red on exactly the 54 B blocks out of 438 up-to-date pairs (`step8/libreFolio_m_s8_green1.log`).
> **⚠️ Fuori pista**: the other cleanup steps (1, 2, 4, 6, 9: tags, notes, `[N]`, `[^N]`, `.xx.md`) also run on code, but no EN code line of the 205 translatable pages matches them today (`step8/s8_steps_4_6_9_in_code.txt`). Latent, out of the approved scope (only step 7), noted for the backlog.

### 4. ✅ B repair (only the pages the next alignment does not re-translate) — 2026-10-06
> **Note implementazione**: driver outside the repo (`LibreFolio-cloud-sizing/release-images/step8/s8_repair_B.py`) importing the in-repo `code_blocks.restore_code_indent`, the same code the pipeline now runs before every write.
> - The flagged up-to-date pairs (pipeline skip rule) equal the approved B list exactly: 54 pairs, 54 Mermaid blocks, 18 pages × it/fr/es.
> - Dry run, then `--apply`: 54 files, 342 lines (+342/−342), 0 violations (whitespace only, inside fenced blocks, line count unchanged, no trailing whitespace, idempotent, 0 issues left). Bytes are read and written without newline translation.
> - **Cache blind to the repair**: the alignment plan is identical before and after (177 pairs), and the EN sources plus `.translate-hashes.json` are byte-identical (sha256 fingerprint). No re-translation, no stamp.
> - `git diff -w` on `mkdocs_src/docs` is empty; `git diff --check` is clean.
> - Tests: `utils translation-code-blocks` 80/80 (`step8/libreFolio_m_s8_green2.log`).
> - A (51 blocks, 9 pairs) is left as is, for the alignment.

### 5. ✅ EN dev doc (docs-writer) — 2026-10-06
> **Note implementazione**: `mkdocs_src/docs/developer/docs/translation-pipeline.md`:
> - §6 «Post-processing cleanup»: the whitespace rule and why it changed, and `_finalize_translation`.
> - New «Code block indentation» subsection: helpers, the `code-block-indent` check, the release gate, the test selector and the corpus guard.
> - «Caching»: only the EN side is hashed, so a translation repair needs no stamp.
> - M added `code_blocks.py` and `validate_translations.py` to the Architecture tree and the restore to the diagram's post-process node.
> - EN-only page: no stamp, no translation debt.
> **⚠️ Fuori pista**: docs-writer corrected the gate wording of this plan. `release.yml` never runs on a push to `main` (only `dev`, manual dispatch, published release), so the step blocks every run except `dev`. §1 and the Sintesi were fixed.

### 6. ✅ Gates — 2026-10-06 (lane 6158, load 5–16)

| Gate | Result |
|---|---|
| `utils translation-code-blocks` | 80/80 |
| `--workers 4 utils all` | green, 907 passed (827 + 80) |
| `translate-validate`, old code on `a7d0b37ec` (export) | 606 errors, exit 1 (baseline) |
| `translate-validate`, new code on `a7d0b37ec` before the repair | 711 = 606 + **105** `code-block-indent`; every other count identical |
| `translate-validate`, new code on the repaired worktree | 657 = 606 + **51** `code-block-indent`, all in A (`docker_advanced` 21, `service_exposure` 24, `create-edit` 6); LOCALIZED `code-block-modified` 177 → 170 and Files OK 328 → 335 (7 B blocks differed only in indentation) |
| `mkdocs build` (strict) | exit 0, 0 warnings |
| `mkdocs check-links` | 81 valid, 3 known exceptions, 1 broken `user/assets/detail/chart/#rolling-return`: pre-existing (already on `d0018a5a1`), page untouched |
| `git diff --check` · `git diff -w` on docs | clean · empty |
| `.translate-hashes.json` · `*.en.md` | untouched · 0 changed |
| Ports 6158/6168 | free |

> **Note implementazione**: logs and JSON in `LibreFolio-cloud-sizing/release-images/step8/` (`s8_tv_*.log`, `libreFolio_m_s8_*.log`, `s8_repair_B_*.json`). Scratch copies in `/tmp/librefolio-r2-m/s8` removed (they can be regenerated with `git archive`).
> **After the developer's alignment** (not M's to run): `translate-validate` must report 0 `code-block-indent`. The proxy (fixed finalize on today's damaged A pages) gives 51 → 0. The corpus guard then covers every pair.
