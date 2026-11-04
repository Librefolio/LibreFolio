# 25_taxonomySelect — i lotti del workstream K (24/09 – 09/10)

> **Stato (09/10): FINITA, archiviata.** Ogni piano è fatto e integrato in `dev_release2`.
>
> - Verifica in sola lettura sul codice di `249f5a9aa`: le consegne di ogni piano ci sono, e ogni commit è un antenato
>   (`git merge-base --is-ancestor`).
> - I residui ancora veri sul codice di oggi sono proposti per `Phase_0/38_postReleaseBacklog/README.md`, voci K-5 …
>   K-26 (elenco sotto). K-1 … K-4 vengono dallo step 23 e sono già lì.
> - Il nome della cartella viene dal primo lotto, la tassonomia dei tipi di asset e le select. Poi il workstream K ha
>   raccolto qui i lotti successivi, uno per piano.
> - Fino allo step 16 i lotti sono entrati per fast-forward di `dev_release2`, prima dei treni con nome.

| Piano | Data | Lotto | Stato | Commit | Treno |
|---|---|---|---|---|---|
| [`analysis-phase00TaxonomySelect.md`](analysis-phase00TaxonomySelect.md) | 24/09 | Analisi d'ingresso: stato verificato, decisioni D-K1 … D-K5 | ✅ | — | — |
| [`plan-phase00TaxonomySelect.prompt.md`](plan-phase00TaxonomySelect.prompt.md) | 24/09 | Tassonomia e select: ranking a fasce (R13), `CROWDFUND_REAL_ESTATE` (R17), `TreeSelect` e `AssetTypeSelect` a due livelli, icone composte, confronto col provider trattenuto (R18), doc | ✅ | `b4a929971` | — |
| [`plan-phase00TaxonomySelectStep9ImportDuplicates.prompt.md`](plan-phase00TaxonomySelectStep9ImportDuplicates.prompt.md) | 24/09 – 28/09 | Import: un duplicato che il DB ha già non si tiene mai (C1); le scelte del resolver sopravvivono ai ricontrolli (C2); campi di sola scrittura tolti (C6) | ✅ | `34e2e9dd7`, `2faa2994a`, `9b9d015b9`, `1b88e52a5` | — |
| [`plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md`](plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md) | 25/09 – 28/09 | Broker: i campi delle icone si chiedono una volta per broker (C3) | ✅ | `66df32355` | — |
| [`plan-phase00TaxonomySelectStep11BulkCreationOrder.prompt.md`](plan-phase00TaxonomySelectStep11BulkCreationOrder.prompt.md) | 25/09 – 28/09 | Bulk: le righe nuove tengono l'ordine di creazione (C4); allineamento della guida (11.5) | ✅ | `0d4fd4438`, `f7b348101` | — |
| [`plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md`](plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md) | 29/09 | Seguiti della review: il titolo dell'app su ogni pagina, la selezione azzerata dopo il salvataggio, le bandiere con un solo font (`LF Flags`) | ✅ | `d27fe6660`, `826ca514d`, `92e8a83b6` | — |
| [`plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md`](plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md) | 30/09 – 01/10 | Note del developer: XSS memorizzata nei sink HTML, Borsa Italiana (valuta, libreria 0.3.2), prezzi stantii con la CTA, login e gestori di password, icone PWA, layout da telefono, barre degli strumenti | ✅ | `6f5ab544e`, `8cc2e2a6f`, `8c176e019`, `feb945634`, `1ddedfeec`, `50aebf2f7`, `63bdcf058`, `51de5dc75` | — |
| [`plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md`](plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md) | 01/10 | Teardown del Tooltip (timer annullati); fixture del test della coppia collegata | ✅ | `0fad7edf2`, `192a3a4f3` | — |
| [`plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md`](plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md) | 02/10 – 05/10 | Sweep delle barre: misura del gutter; etichetta lunga del filtro dei broker | ✅ | `78f90eb53`, `72a7b07cb` | — |
| [`plan-phase00TaxonomySelectStep16AssetDetailUx.prompt.md`](plan-phase00TaxonomySelectStep16AssetDetailUx.prompt.md) | 06/10 | Dettaglio asset: tooltip del prezzo sul telefono, hashtag di condivisione, navigazione ‹ n/N › fra gli asset | ✅ | `858cc4be6`, `6072ad58d`, `b116301c9` | — |
| [`plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md`](plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md) | 06/10 | `TreeSelect`: timer annullati alla distruzione | ✅ | `6dfe06560` | — |
| [`plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md`](plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md) | 06/10 | Note dai dispositivi: footer di AssetModal sul telefono, tipo nel confronto col provider; Android e iPhone nel backlog | ✅ | `6a80215d0`, `c91d79820` | 4 |
| [`plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md`](plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md) | 07/10 – 08/10 | Triage dei rossi della coverage: l'Esc chiude solo lo strato in cima, la modifica rifiutata del broker resta nel form, tre rossi E2E | ✅ | `8780697db`, `f2066621d`, `46fe8bf9d` | 11 |
| [`plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md`](plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md) | 08/10 | Avvio dell'app: un server lento non è un logout, `?redirect=`, sfondo delle modali, Esc sul trigger di SearchSelect | ✅ | `e6174d56a`, `00854daf6`, `d82d9c4d6` | 12 |
| [`plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md`](plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md) | 08/10 | Esc di SimpleSelect (la lista «Read as» del wizard) | ✅ | `6f4e0d2a7` | 13 |
| [`plan-phase00TaxonomySelectStep21PureDefects.prompt.md`](plan-phase00TaxonomySelectStep21PureDefects.prompt.md) | 08/10 | Difetti puri: l'avatar dopo una preferenza, `{n}` in 8 messaggi, la guardia ICU | ✅ | `c719a2f05`, `888ac066c` | 18 |
| [`plan-phase00TaxonomySelectStep22RegisterLinkProfileDate.prompt.md`](plan-phase00TaxonomySelectStep22RegisterLinkProfileDate.prompt.md) | 09/10 | «Register here» a registrazione chiusa; data del profilo e dimensioni della griglia nella lingua dell'app | ✅ | `bf993445f`, `77d068c73`, `ef0894762` | 23 |
| [`plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md`](plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md) | 09/10 | Bulk: clone delle coppie; falso «Scartare le modifiche?» dopo un Reset o prima dei tipi; Reset della riga sulle coppie | ✅ | `49fe38341` | 25 |

Ogni piano ha anche il suo commit `docs(journal)`.

## Residui rinviati (`Phase_0/38_postReleaseBacklog/README.md`)

| Voce | Titolo | Peso | Da |
|---|---|---|---|
| K-1 … K-4 | Già nel 38: riparazione delle coppie, riapertura nel percorso lento, crash di *Reset all*, `$currentLanguage` fuori da `untrack` | basso | step 23 |
| K-5 | Registrazione aperta senza utenti anche se l'admin l'ha chiusa (`is_first_user`) | minimo, decisione | step 22, punto 7 |
| K-6 | iPhone: nessuna immagine d'avvio (`apple-touch-startup-image`) | medio-basso | step 17, voce 13 |
| K-7 | Android: quadrato nero sull'icona della PWA | basso | step 17, voce 12 |
| K-8 | E2E `tx-split-promote` C3: commit di uno split mai ripristinato | medio-basso | step 18, 18.4 |
| K-9 | E2E `multi-user`: nomi con `Date.now()` e due broker mai cancellati | minimo | step 18, 18.2 |
| K-10 | `test_update_js_cache.py` esegue l'aggiornamento reale, con la rete | medio-basso | step 12, 12.3 |
| K-11 | `entityStore.merge` alza la versione anche a dati identici | medio-basso | step 10 |
| K-12 | Handle di timer tenuti in `$state` (`DataTable`, Dashboard) | basso | step 14, 14.6 |
| K-13 | Bandiere nei grafici ECharts (D-b1) | medio | step 12, backlog |
| K-14 | Bandiere: pile scritte a mano senza `'LF Flags'` e nome del file (D-b3) | basso | step 12, backlog |
| K-15 | Formatter dei tooltip ECharts senza un `sanitizeHtml` finale né un gate | basso | step 13, segnalazioni |
| K-16 | Borsa Italiana: ETC/ETN classificati come `ETF` generico | basso | step 13, segnalazioni; step 17, 17.7 |
| K-17 | `PasswordInput`: pulsante «occhio» con `title` inglese fisso e `tabindex="-1"` | basso | step 13, segnalazioni |
| K-18 | Dashboard: nei 2 s di debounce il filtro nomina già il broker | basso | step 15, 15.5 |
| K-19 | Lista degli asset: i filtri non si ritrovano al ritorno dal dettaglio (2b) | medio-basso | step 16, backlog |
| K-20 | Dettaglio dell'asset: il cambio di tab rimette le date vecchie | medio-basso | step 16, segnalazioni |
| K-21 | AssetModal (wizard): il prompt di riuso può aprirsi sopra il confronto | basso | piano madre, passo 2 |
| K-22 | AssetModal: una lettura del catalogo dei provider sprecata alla riapertura | minimo | piano madre, passo 2 |
| K-23 | `TreeSelect`: dopo l'Esc il focus cade su `<body>` | basso | piano madre, passo 4 |
| K-24 | Doc della qualità dei dati: due codici mancanti, «5 codes», «valued at purchase cost» | basso | step 13, 13.4 |
| K-25 | devWiki: quattro pagine mai scritte (teardown di Svelte 5, regole di escape, `valuation_stale`, taratura delle barre) | minimo | step 13 e 14 |
| K-26 | Intestazione superata in `catalogIcuLocale.test.ts` («Red today with three keys») | minimo | step 21, 21.2 |

Debito di traduzione, nel giro Aphra di I-08: K ha riscritto in inglese otto pagine senza toccare IT/FR/ES, e nessuna è
stata timbrata.

- `financial-theory/instruments/asset-types/`: `index`, `etfs` e `real-estate`.
- `user/assets/`: `create-edit`, `index` e `detail/index`.
- `user/dashboard/index`.
- `user/transactions/import/how-to`.

Non sono residui, e quindi non sono rinviati:

- **Già nel 38**, con un'altra voce:
  - le date nella lingua del browser (C-10) e `formatBytes` senza traduttore tracciato (C-11), dallo step 22;
  - l'Esc di AiExportMenu (C-12), dagli step 18 e 20;
  - i timer di SearchSelect (C-13), dallo step 16 R1;
  - la guardia ICU che non legge `get(t)` (C-15) e il prefisso «Asset data:» (O-8), dallo step 21;
  - `npx` nel runner (I-06), i due errori di `tsc` degli E2E (I-07) e l'àncora `#rolling-return` (I-08).
- **Decisioni e limiti dichiarati**:
  - l'ordine del menu dei tipi, approvato in review;
  - l'ordine alfabetico fra risultati equivalenti;
  - le frecce che fanno il giro e lo Spazio che scrive nella ricerca di `TreeSelect`, conservati apposta;
  - «Inactivos» tagliato di 4 px a 320 px, lasciato così (13.10);
  - il punto 4 dello step 15, non autorizzato.
- **Chiusi dopo**:
  - il link profondo perso a un controllo di autenticazione lento (step 19);
  - il falso «Scartare le modifiche?» sulle coppie e il clone di due righe singole (step 23);
  - `stressAssetClasses` e la mappa emoji di `AllocationHistoryChart`;
  - il commento di `allocationHierarchy.ts`;
  - la doc della lista che prometteva ISIN e ticker.
- **Non di K**:
  - i rossi preesistenti girati ad altri workstream (step 7, 9 e 13);
  - «Riprova» della scheda Correlazione, girato a Risk;
  - lo screenshot `assets/create-modal` della gallery, che non è versionato e si rigenera a ogni giro;
  - la verifica manuale delle bandiere sui dispositivi, che spetta al developer.
