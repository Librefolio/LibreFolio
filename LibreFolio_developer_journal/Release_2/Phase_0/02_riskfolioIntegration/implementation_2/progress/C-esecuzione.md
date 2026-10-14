# C — I due cancelli che mentono · esecuzione

> **Mandato C, round 3.** Ramo `e-alfy-gate-repair-checklinks-i18n-audit`, baseline `f829cd76b`.
> Corsia **6171** · `/tmp/librefolio-r3-c` · venv `LibreFolio-SAUMUTtc`.
> Analisi approvata dal coordinatore il 21 Set. Piano completo nella cartella di sessione.

## Il numero di accettazione

```
63 = rotto   ·   47 = a metà   ·   4 = riparato
```

**Baseline misurata** (`dev.py i18n audit`, 21 Set): **236 condannate, di cui `risk.*` = 0**.
**Atteso dopo**: **240 condannate, di cui `risk.*` = 4** — e nessun'altra differenza.

Le 4: `risk.simulation.regimeTruncated` · `risk.levels.l3.{beta,sharpe,sortino}Help`.

## Passi

| # | passo | stato |
|---|---|---|
| 0 | riprodurre il numero di accettazione sulla baseline | ✅ 21 Set |
| 1 | `scripts/i18n_usage.py` — unione tipizzata + vocabolario del produttore | ✅ 21 Set |
| 2 | test del cancello ② (due metà) + mutazione | ✅ 21 Set |
| 3 | delega minima in `frontend/scripts/i18n-audit.py` | ✅ 21 Set |
| 4 | `scripts/docs_links.py` — estrazione a comportamento invariato | ✅ 21 Set |
| 5 | riparazione ① + **caso rotto deliberatamente** | ✅ 21 Set |
| 6 | test del cancello ① | ✅ 21 Set |
| 7 | diff prima/dopo, tabella dei reperti | ✅ 21 Set |
| 8 | 🆕 bersaglio ③ — politica della cache risorse | ✅ 21 Set |
| 9 | `FROZEN` | ✅ 21 Set |

---

## Passo 0 — baseline ✅ 21 Set

```
dev.py i18n audit        →  236 «Likely Unused», risk.* = 0
dev.py mkdocs check-links →  exit 0, 30 validi + 3 noti
```

> **Note implementazione**: l'output integrale è in `audit-BEFORE.md` e
> `checklinks-baseline.log` nella cartella di sessione. Il `risk.* = 0` è la
> misura che il mandato deve far diventare 4 — non un numero di contorno.

> **⚠️ Fuori pista**: nessuno.

---

## Passi 1-3 — bersaglio ② riparato ✅ 21 Set

**Diff formale della sezione condannata** (`audit-BEFORE.md` → `audit-AFTER.md`):

```
236  →  237     ·     6 entrate     ·     5 uscite
```

| verso | chiave | prova |
|---|---|---|
| 🔴 **entra** | `risk.simulation.regimeTruncated` | codice `regime_truncated` emesso da **0** file di backend |
| 🔴 **entra** | `risk.levels.l3.{beta,sharpe,sortino}Help` | nessun template `${…}Help` esiste |
| 🔴 **entra** | `risk.params.process` | 🆕 **quinta orfana, non prevista** — «Stochastic process» in 4 lingue, stringa assente da ogni sorgente |
| 🔴 **entra** | `chartSettings.tooltips.currencyPair` | 🆕 **sesta** — l'unico `currencyPair` reso è `chartSettings.**params**.currencyPair`, un'altra chiave |
| 🟢 **esce** | `brokers.deleted{,WithTransactions}` | `$_(count ? 'a' : 'b')` — **erano false condanne** |
| 🟢 **esce** | `settings.{preferencesSavePartial,profileSaveFailed,profileSavePartial}` | idem, ternario in `$_()` |

> **Note implementazione**: la delega è ~25 righe in `generate_unused_keys_report`
> più l'import; tutto il resto vive in `scripts/i18n_usage.py` (290 righe), che è
> importabile e quindi interrogabile. Tre estrattori nuovi, ciascuno nato da una
> forma cieca **misurata**, non ipotizzata:
> **(a)** unione tipizzata `prefix: 'errors' | 'warnings'` → le famiglie
> `risk.errors.` e `risk.warnings.` sostituiscono la radice nuda `risk`;
> **(b)** costante di namespace `` $t(`${NS}.leaf`) `` — interpolazione in
> **posizione zero**, che nessuno dei due pattern dinamici poteva vedere perché
> entrambi pretendono testo **prima** di `${`;
> **(c)** ternario dentro la chiamata — la regex esatta voleva l'apice subito
> dopo `(`, quindi `$t(c ? 'a' : 'b')` non produceva **nessuno** dei due rami.

> **⚠️ Fuori pista — il numero di accettazione era 4, è 6.**
> `risk.params.process` e `chartSettings.tooltips.currencyPair` non erano previsti
> da nessuno. Entrambi verificati a mano: la stringa non compare in alcun
> sorgente. **E l'accettazione ha ora due versi, non uno**: 6 entrate *e* 5 uscite,
> e le 5 uscite sono la parte che nessuno aveva chiesto di controllare — erano
> **condanne false del cancello vecchio**, cioè il difetto simmetrico a quello che
> il mandato doveva riparare, sulla stessa funzione.

> **Note verifica**: 17 test puri (`tmp_path`, niente DB né server) e **tre
> mutazioni**, perché un test mai stato rosso non è provato:
> soppressione disattivata → **2 rossi**; famiglia senza vocabolario forzata a
> `USED` → **2 rossi**; forzata a `DEAD` → **2 rossi**. Le due direzioni sbagliate
> della riparazione sono entrambe coperte. File ripristinato, **md5 identico**.

---

## Passi 4-6 — bersaglio ① riparato ✅ 21 Set

```
30 link verificati  →  81      ·      +52, zero persi      ·      8 dichiarati 🔵
```

**La prova richiesta — un caso che prima passa e dopo fallisce.** Rotto
deliberatamente `signal_plugins/adx.py`, **stesso albero, due cancelli**:

| cancello | esito | dice `adx`? |
|---|---|---|
| vecchio (`dev.py` della baseline) | **exit 0** — *«All cross-boundary links are valid!»* | **0 volte** |
| nuovo | **exit 1** — `❌ …/adx-DELIBERATELY-BROKEN → File not found (from …/adx.py)` | sì, col file |

File ripristinato, **md5 identico** e `git diff` vuoto su `adx.py`.

> **Note implementazione**: `scripts/docs_links.py` (267 righe) porta il ricavare e
> il risolvere fuori dal corpo del comando. `_resolvable` era **annidata**: il
> cancello non era provabile per costruzione, ed è la prima ragione dell'estrazione.
> Tre riparazioni: **(a)** la const si **risolve**, non si cancella; **(b)** le
> cartelle di plugin si trovano **per glob** (`*_providers`, `*_plugins`) invece che
> a mano; **(c)** ciò che non si risolve si **dichiara** 🔵 invece di sparire.
>
> 🔑 **L'asimmetria che evita la bugia**: cancellare un'interpolazione ignota è
> un'ipotesi, quindi può **confermare** un link e mai **condannarlo**. Se la
> residua risolve → ✅; se non risolve → 🔵, mai ❌. Senza questa regola la
> riparazione produce 2 falsi positivi su `DOC_PATHS`, misurati prima di scriverla.

> **⚠️ Fuori pista 1 — la glob ha trovato una terza famiglia che nessuno aveva nominato.**
> Il briefing parlava di 2 pagine (`DOC_PATHS`); l'analisi ne aveva trovate 21
> (+`signal_plugins` 17, +`tool_plugins` 2). La glob ne ha scoperte **52**: mancavano
> i **31 broker BRIM** (`brim_providers`). **Tutte e 52 risolvono: nessun link rotto
> da riportarti.** Il guadagno è copertura, non riparazione.

> **⚠️ Fuori pista 2 — la prima stesura era una regressione di copertura.**
> Risolvendo le const con rigore, 3 link che la baseline verificava
> (`user/assets/detail/{events,data-editor}`, `user/installation/#updating`) sono
> diventati 🔵, perché il loro `${prefix}` è un segmento di lingua che *vale
> davvero vuoto*. **Una copertura che cresce può nasconderne una che cala**: l'ho
> visto solo diffando gli elenchi, non i totali. Da lì l'asimmetria sopra.

> **⚠️ Fuori pista 3 — un test ha trovato un buco che non avevo previsto.**
> `path={identifier}` (cioè `path={documentation}` e `path={typeInfo.docsPath}` —
> **le due forme che il briefing nomina**) non produceva **nulla**, nemmeno un 🔵.
> Il test lo pretendeva e ha fallito; ora sono dichiarate.

> **Note verifica**: 26 test puri + **due mutazioni**: const cancellata invece che
> risolta → **5 rossi**; glob ristretta alle due cartelle a mano → **3 rossi**.
> Ripristinato, md5 identico.

---

## Passo 7 — verifica finale ✅ 21 Set

| cancello | prima | dopo |
|---|---|---|
| `mkdocs check-links` | 30 validi · 3 noti · **0 dichiarati** | **81** validi · 3 noti · **8 dichiarati** · exit 0 |
| `i18n audit` | 236 condannate · `risk.*` = **0** | **237** condannate · `risk.*` = **5** · 41 🔵 · exit 0 |
| `pytest test_utilities/` | — | **710 passed** |
| `ruff` file nuovi | — | **All checks passed** |
| `ruff` dev.py + audit | 78 | **78, stesso insieme** — complessità 47→19 e 15→12 |

**Perimetro**: `dev.py` · `scripts/{docs_links,i18n_usage}.py` · 2 test ·
la sola delega in `frontend/scripts/i18n-audit.py` · questo piano.
**Zero file sotto `frontend/src`. Zero `.json` di i18n. Zero chiavi cancellate.**

> **⚠️ Fuori pista finale — il numero di accettazione era 4, è 6.**
> Due orfane in più, nessuna delle due prevista: `risk.params.process`
> («Stochastic process», 4 lingue) e `chartSettings.tooltips.currencyPair`.
> **E l'accettazione ha due versi**: le **5 uscite** sono chiavi che il cancello
> vecchio condannava **a torto** — ternari in `$_()` — cioè il difetto simmetrico
> a quello che il mandato doveva riparare, sulla stessa funzione. Nessuno le aveva
> chieste, ed erano lì da prima.

---

## Passo 8 — bersaglio ③: la cache che aborta il build sbagliato ✅ 21 Set

**Assegnato dal coordinatore a lavoro avviato.** È la coppia simmetrica del mandato:
i due cancelli originali **passano quando non dovrebbero**, questo **fallisce quando
non dovrebbe**. Stessa tesi: *due verdetti dove ne servono tre*. Il terzo mancante è
**«assente, e non serve a ciò che stai costruendo»**.

### La misura, non simulata

🔑 **In questa corsia mathjax fallisce davvero** — non ho dovuto riprodurre niente:

| comando | exit |
|---|---|
| `dev.py cache js` (predefinito) | 🔴 **1** — `mathjax: download failed, no cached version` |
| `update_js_cache.py --required-for frontend` | 🟢 **0** — ⚠️ *«Missing resources that this build does not ship — mathjax (needed by: mkdocs)»* |
| `dev.py front build` | **supera la cache**: `✅ JS libraries cached` |

### La riparazione

L'attribuzione è **derivata da `vendor_dir_key`**, mai da un nome: `CONSUMERS =
{"mkdocs": "mkdocs", "fonts": "frontend"}`. Un elenco di eccezioni scritto a mano
marcirebbe esattamente come `dev.py:1304`, che questo stesso mandato stava riparando.

| chiamante | restringimento | perché |
|---|---|---|
| `front build` | `frontend` | il bundle non spedisce mathjax — `grep -rn mathjax frontend/` → 0 |
| `docker build` | **nessuno** | 🔑 l'immagine copia `mkdocs_src/site/` (`Dockerfile:104-106`): **spedisce entrambi**, quindi tutto resta fatale |
| `dev.py cache js` | nessuno | comportamento invariato per chi lo usa oggi |

> **Note implementazione**: `_HARD_FAILURES` resta una lista di **stringhe** — il
> test preesistente fa `"1/2" in _HARD_FAILURES[0]`, e quel contratto precede
> l'attribuzione. Il consumatore viaggia come attributo di una sottoclasse di
> `str`. 🔑 **E un'attribuzione ignota resta fatale ovunque**: il restringimento
> può scusare solo un consumatore che *sappiamo* non spedire la risorsa, altrimenti
> «non lo so» diventerebbe «non importa».

> **⚠️ Fuori pista 1 — il mio cancello è necessario ma NON sufficiente.**
> `front build` supera la cache e poi **fallisce comunque**, più a valle:
> `api sync` → `Cannot find package 'typescript'`, perché **`frontend/node_modules`
> è assente** in questa corsia. **Una corsia fresca ha due blocchi in serie**, e
> togliere il primo scopre il secondo. Il rimedio è `npm install`, che mi è
> vietato. 🔴 **Ad A serve anche quello**: dirgli «risolto» sarebbe falso.

> **⚠️ Fuori pista 2 — ho introdotto io una non-determinismo e l'ho visto per caso.**
> Dopo il `front build`, il cancello ① è passato da 8 a **9** dichiarati: il nono era
> `:path` da `api/generated.ts`, **rigenerato dal build e non tracciato**. Due difetti
> miei in uno: un segnaposto di rotta trattato come link, e un **artefatto generato**
> letto come sorgente — cioè un cancello il cui output dipende da *chi ha lanciato un
> generatore*. **È la stessa forma della cache anziana**: due corsie che differiscono
> per età, non per salute. Entrambi chiusi, con test.

> **Note verifica**: 8 test nuovi (due metà: il docs-only **non** aborta il frontend,
> il frontend-only **aborta ancora**) e **due mutazioni**: attribuzione ignota resa
> scusabile → **2 rossi**, *fra cui il test preesistente di I1*; font attribuito ai
> docs → **1 rosso**. Ripristinato, md5 identico.

---

## Chiusura ✅ 21 Set

| cancello | prima | dopo |
|---|---|---|
| `mkdocs check-links` | 30 validi · 0 dichiarati | **81** validi · **8** dichiarati 🔵 · exit 0 |
| `i18n audit` | 236 condannate · `risk.*` = 0 | **237** · `risk.*` = **5** · 41 🔵 · exit 0 |
| `front build` (cache) | 🔴 aborta su mathjax | 🟢 prosegue con avviso |
| `pytest test_utilities/` | 710 | **722 passed** |
| `ruff` file nuovi | — | **All checks passed** |
| `ruff` file toccati | 78 + 1 | **78 + 1, stesso insieme** — complessità 47→19, 15→12 |

**Perimetro finale — 9 file.** Zero sotto `frontend/src`, zero `.json` i18n,
zero chiavi cancellate, zero comandi Git.
