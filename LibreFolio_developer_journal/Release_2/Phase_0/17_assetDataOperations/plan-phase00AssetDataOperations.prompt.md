# Asset data operations — bond classification, distribution CSV, delete links

**Avvio:** 2026-09-10. **Owner:** workstream F coordinato da Release 2.
**Baseline:** `8b99e0020c92a945daf0821ee0654a0a2a21efd0`
(`dev_release2`).
**Scope:** SP03 A1, A2 e B3 da
[`06_piano_sprint.md`](../09_feedbackJobs/06_piano_sprint.md).
**Autorizzazione developer:** `Approva F con queste decisioni (Consigliato)`.
**Vincolo Git:** nessun commit, push, rebase, reset o altra mutazione della
cronologia.

## Contratto approvato

- Le categorie canoniche sono `Corporate Bonds` e `Government Bonds`.
- Le obbligazioni sovranazionali restano `Financials`; nessuna migrazione o
  riclassificazione dei dati esistenti.
- L'import distribuzioni usa `name,weight`; `weight` e' sempre una percentuale
  0-100. Nessuna inferenza 0-1, una sola conversione `/100`, nessun
  auto-bilanciamento.
- L'import distribuzioni e' strict all-or-nothing.
- Paesi: match esatto ISO-2, ISO-3 o nome localizzato. Settori: match esatto
  chiave canonica o label localizzata. Entrambi ignorano maiuscole/minuscole e
  spazi esterni; nessun fuzzy matching.
- La delete asset restituisce un conteggio globale opzionale. NOT_FOUND e
  persistenza sono veritieri; ogni elemento usa un savepoint e un errore di
  commit non produce una risposta di successo.
- I link aprono `/transactions?asset_id=<id>` senza ereditare altri filtri.
  Gli access control esistenti non cambiano. La modale singola resta aperta
  quando la cancellazione e' bloccata.

## Ownership e lane

- Lane esclusiva: porta `6154`, data root
  `/tmp/librefolio-r2-f-asset-data`.
- Prefisso obbligatorio:
  `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py`.
- Il coordinatore mantiene ownership di `CHANGELOG.md`, cataloghi i18n EN/IT/FR/ES,
  API sync/client generato, registrazioni runner, navigazione MkDocs e backlog
  master. F prepara solo matrici/delta di handoff per queste superfici.
- Nuovi test o test riparati: `test-author`. Documentazione MkDocs:
  `docs-writer`.

## 0. Baseline, decisioni e piano — ✅ completato 2026-09-10

- [x] Verificare HEAD, branch, worktree pulito e file agente tracciato.
- [x] Leggere istruzioni applicabili, backlog, codice e devWiki disponibile.
- [x] Verificare drift e conflitti con Tool C + PAC D.
- [x] Ricevere autorizzazione developer verbatim e decisioni di contratto.
- [x] Creare questo piano prima di modificare codice.

> **Note implementazione (2026-09-10):** HEAD esatto
> `8b99e0020c92a945daf0821ee0654a0a2a21efd0`, branch
> `e-alfy-asset-data-operations`, worktree pulito. Il grafo devWiki ignorato non
> e' disponibile nel worktree; consultate direttamente le pagine committed
> `data-editor-unification` e `F-095`. Tool C e PAC D non toccano le superfici
> produttive F; i soli conflitti previsti sono file condivisi gia' assegnati al
> coordinatore.

## 1. A1 — categorie bond canoniche ✅ 2026-09-10

- [x] Aggiungere enum, alias, API/portfolio emoji e fallback frontend.
- [ ] Riallineare i mapping espliciti Borsa Italiana per government/corporate.
- [ ] Conservare sovranazionali in `Financials` e dati esistenti invariati.
- [x] Far aggiungere/aggiornare i test mirati dal `test-author`.
- [x] Eseguire i selettori A1 nella lane F.

> **Note implementazione (2026-09-10):** aggiunte le categorie canoniche,
> alias controllati, emoji backend/frontend e mapping Borsa espliciti. Il
> `test-author` ha aggiornato i test enum/API/provider senza toccare produzione
> o runner. `utils sector-normalization` e i due test Borsa mirati sono verdi
> (60 + 2 test).
>
> **⚠️ Fuori pista (2026-09-10):** il comando concatenato A1 ha creato il DB
> isolato della lane e completato i primi due selettori, ma `api utilities` si
> e' fermato prima della collection: shared backend su 6154 uscito in startup
> con code 1, output nascosto dal runner non verbose. Nessun listener e' rimasto
> sulla porta. Triage: errore ambiente/setup, non test prodotto; prossimo passo
> e' ripetere il solo selettore con `--verbose` per ottenere l'errore reale.
>
> **⚠️ Fuori pista (2026-09-10, seguito):** il coordinatore ha autorizzato il
> bootstrap locale ignorato di MathJax. Creato solo
> `mkdocs_src/docs/javascripts/vendor/mathjax/`, scaricato l'URL canonico con
> `curl --fail --location --proto '=https' --tlsv1.2`, verificato file non vuoto
> e regola ignore. L'unica ripetizione autorizzata di `api utilities` ha ancora
> fallito prima della collection: shared backend startup code 127. Nessun
> listener resta su 6154; come richiesto, sospesi i gate server-backed senza
> workaround aggiuntivi.
>
> **⚠️ Fuori pista (2026-09-10, diagnosi exit 127):** Python e `pipenv` sono
> entrambi risolti dalla lane corretta. L'avvio foreground autorizzato ha
> mostrato la causa: dipendenze frontend assenti nel worktree
> (`@sveltejs/adapter-static` non trovato, `.svelte-kit/tsconfig.json` assente,
> `vite: command not found`). API export/client generation e' arrivata prima del
> fallimento ma gli artefatti sono ignorati; health mai raggiunta, porta libera.
> Nessuna installazione o ulteriore ripetizione autorizzata.
>
> **Note implementazione (2026-09-10, gate conclusivo):** il coordinatore ha
> autorizzato un solo `npm --prefix frontend ci` dal lock esistente. Gli SHA-256
> di `package.json` e `package-lock.json` sono rimasti rispettivamente
> `76014d1a...e9bc` e `0dbeb7bd...67c6a`. Il gate canonico `api utilities` ha
> quindi raccolto e superato 9/9 test; shared backend spento e porta 6154 libera.

## 2. A2 — core CSV condiviso ✅ 2026-09-10

- [x] Rendere configurabile l'identita' primaria del parser mantenendo `date`
  come default tipizzato.
- [x] Aggiungere validazione/canonicalizzazione configurabile e strict mode
  opt-in.
- [x] Gestire BOM, campi quotati, numeri completi/finiti e duplicati canonici
  senza cambiare i tre import dated.
- [x] Far aggiungere regressioni component dal `test-author`.

> **Note implementazione (2026-09-10):** `CsvEditor` ora usa una union tipizzata
> dated/identified, parser quotato con BOM, numeri completi e finiti, hook di
> parse/validate e duplicati sull'identita' canonica. `DataImportModal` mantiene
> partial import come default e aggiunge strict/cross-row validation opt-in.

## 3. A2 — import distribuzioni ✅ 2026-09-10

- [x] Aggiungere wrapper di dominio con preview canonica `name,weight`.
- [x] Integrare l'azione nelle distribuzioni sector/geographic.
- [x] Applicare al solo draft selezionato dopo preview interamente valida.
- [x] Verificare totale con la stessa tolleranza verde della UI e conversione
  `/100` unica.
- [x] Eseguire component test e regressioni Asset Price/Event + FX dated.

> **Note implementazione (2026-09-10):** wrapper distribuzioni strict
> `name,weight`; country exact ISO-2/ISO-3/nome localizzato e sector exact
> key/label localizzata, normalizzati trim/case. Nessun fuzzy/autobalance;
> tolleranza totale `<0.005`, unica conversione `/100`. Gate component combinato:
> 23 pass, 1722 deselected.

## 4. B3 — delete backend veritiera ✅ 2026-09-10

- [x] Aggiungere `transaction_count` opzionale a `FAAssetDeleteResult`.
- [x] Implementare precheck batch, NOT_FOUND completo, savepoint per elemento e
  guardia FK di race.
- [x] Propagare errori finali di commit senza risposta success-shaped.
- [x] Coprire ordini mixed valid/missing/blocked e persistenza reale.

> **Note implementazione (2026-09-10):** preload asset/conteggi globali, DTO
> NOT_FOUND completo, blocker count, savepoint per item, race FK ricontata,
> commit finale propagato. Gate: service commit/race 2 pass; API delete 9 pass.
>
> **⚠️ Fuori pista:** il primo test commit-failure ha scoperto che SQLite
> rilasciava il primo SAVEPOINT come commit reale perche' i SELECT non avviavano
> una write transaction. Aggiunto no-op UPDATE prima dei savepoint: rollback
> finale ora ripristina davvero le delete tentative. Un primo filtro `-k` non
> valido non ha eseguito test; corretto con due nomi separati.

## 5. B3 — link e stato frontend ✅ 2026-09-10

- [x] Estendere i risultati `ConfirmModal` con azione link tipizzata.
- [x] Mantenere aperta la modale singola bloccata con conteggio/link.
- [x] Aggiungere conteggio/link ai risultati bulk e link nel dettaglio asset.
- [x] Riutilizzare `buildTransactionsFiltersUrl({asset_id})` senza filtri
  precedenti; mantenere gli access control.
- [x] Eseguire test component/E2E mirati.

> **Note implementazione (2026-09-10):** action link tipizzata nei result,
> singola bloccata persistente, count/link bulk e detail senza filtri ereditati.
> Count globale non altera la query/access visibility. Gate: component incluso
> nei 23 pass; asset-list 3 pass; asset-detail 1 pass.

## 6. Documentazione, shared delta e verifica finale

- [x] Delegare al `docs-writer` gli aggiornamenti EN MkDocs. ✅ 2026-09-10
  > **Note implementazione**: aggiornate le pagine EN provider Borsa Italiana,
  > creazione/modifica e lista asset; build MkDocs strict verde.
- [x] Preparare matrice i18n ×4, richiesta API sync e registrazioni test per il
  coordinatore.
  > **Note implementazione**: consegnata matrice bond EN/IT/FR/ES; API sync,
  > runner, CHANGELOG, nav e JSON i18n lasciati al coordinatore come richiesto.
- [x] Eseguire lint/typecheck e selettori finali nella lane F. ✅ 2026-09-10
  > **Note implementazione**: gate A1/A2/B3 e fingerprint FX verdi; lint Ruff,
  > Black e Prettier verdi sui delta pertinenti.
  > **⚠️ Fuori pista**: il full component gate ha trovato due assertion fuzzy
  > obsolete dopo la soppressione intenzionale dell'errore totale con zero righe
  > valide; test-author le ha riallineate al row error e import bloccato.
- [x] Verificare `git diff --check`, nessun artifact privato/generato e porta
  `6154` libera.
  > **Note implementazione**: diff check pulito, nessun artifact API/i18n
  > generato o privato aggiunto; i soli artifact graphify sono il frammento
  > semantic scoped intenzionale e relativo indice. Porta 6154 libera.
- [x] Inviare handoff strutturato al coordinatore e tornare FROZEN. ✅ 2026-09-10
  > **Note implementazione**: handoff finale inviato con scope, shared delta,
  > contratto helper per H, gate e artifact intenzionali; workstream F congelato.

## 7. Detour autorizzato — fingerprint FX portfolio

> **⚠️ Fuori pista autorizzato (2026-09-10):** la developer ha esteso lo scope F
> al sottosistema portfolio: fingerprint FX generale condiviso per L1 blob e
> futura L2 H. Ownership verificata: `portfolio_engine.py` era gia' F-owned per
> il delta emoji A1; `portfolio_service.py` e' pulito/fuori ownership e non sara'
> toccato. Preservare clear espliciti e aggiungere quello mancante su
> `delete_rates_bulk()`.

- [x] Definire dependency set FX bounded per scope/currency/intervallo. ✅ 2026-09-10
  > **Note implementazione**: dependency set limitato alle valute presenti nelle
  > transazioni dello scope, negli asset detenuti e nella loro price history,
  > normalizzate contro la target currency; query rate limitata alle coppie e a
  > `date_to`.
- [x] Calcolare fingerprint deterministico di rate e route/config selezionabile. ✅ 2026-09-10
  > **Note implementazione**: serializzazione ordinata di coppie, rate effettivamente
  > selezionabili tramite backward-fill e route/config relative, hash SHA-256.
- [x] Integrare la stessa identita' nel blob key L1 ed esporla a H. ✅ 2026-09-10
  > **Note implementazione**: helper pubblico
  > `compute_portfolio_fx_cache_identity(db, scope_broker_ids, target_currency, date_to)`
  > usato direttamente dalla chiave blob L1; H puo' importare lo stesso contratto
  > senza duplicare la definizione per L2.
- [x] Correggere invalidazione delete FX confermata. ✅ 2026-09-10
  > **Note implementazione**: delete con almeno una riga rimossa pulisce
  > `portfolio_layer2` e `portfolio_blob` dopo commit riuscito.
- [x] Delegare test upsert/delete/route change/cache hit invariato e validarli. ✅ 2026-09-10
  > **Note implementazione**: test-author ha coperto identita' stabile, miss su
  > rate insert/update/delete/replace, route/provider change, esclusione di pair,
  > broker e rate futuri irrilevanti, hit/miss blob L1 e clear delete/no-op.
  > Validazione finale: 8 test portfolio fingerprint + 2 test delete cache verdi.
  > **⚠️ Fuori pista**: il primo run ha scoperto l'import locale `clear_cache`
  > mancante dopo il commit; corretto con lo stesso pattern gia' usato da sync/upsert.

## 8. Review finale — label duplicati CSV

> **⚠️ Fuori pista review (2026-09-10):** il coordinatore ha rilevato che la
> status bar condivisa mostrava sempre `duplicate dates`, anche per le
> distribuzioni identificate da `name`.

- [x] Riutilizzare `identityLabel` nel testo duplicati. ✅ 2026-09-10
  > **Note implementazione**: la status bar mantiene `dates` per gli editor
  > datati e mostra `names` per i CSV distribuzione, senza nuove chiavi i18n.
- [ ] Aggiungere/regolare il test minimo e rieseguire gate component/format.
- [ ] Inviare delta/evidenza al coordinatore e tornare FROZEN.

## Definition of done

- API, selettori, fallback ed emoji espongono entrambe le categorie bond; i
  provider assegnano solo le tipologie esplicite approvate.
- Nessuna migrazione DB, mass rewrite o riclassificazione implicita.
- CSV distribuzioni accetta solo `name,weight` con peso 0-100, mostra preview
  canonica e non applica nulla in presenza di qualsiasi errore.
- Price/Event/FX conservano formato, typing e comportamento partial esistenti.
- Delete mixed batch restituisce risultati e conteggi coerenti con il DB; nessun
  rollback tardivo annulla successi gia' dichiarati e nessun commit fallito
  produce successi.
- Link singolo, bulk e dettaglio puntano al filtro asset corretto senza ampliare
  la visibilita' delle transazioni.
- Entrambi i layer portfolio possono usare la stessa identita' FX bounded;
  variazioni rate/route rilevanti muovono la chiave, dipendenze irrilevanti no,
  e le clear esplicite restano difesa aggiuntiva.
- Test, documentazione EN e handoff delle superfici condivise sono completi.
