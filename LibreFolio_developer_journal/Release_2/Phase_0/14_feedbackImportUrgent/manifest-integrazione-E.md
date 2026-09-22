# Manifest di integrazione - Gruppo E

**Baseline:** `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`, `refs/heads/dev_release2`.
**Aggiornato:** 2026-09-10.
**Stato pacchetto:** R1-R5 verificati tecnicamente e applicati al checkout target
`dev_release2` il 2026-09-09. Badge e sottotesti R4 accettati dal dev il
2026-09-09 alle 15:51.
**Commit/SHA di integrazione:** `ef722b552433028c051ccb1207c84f1072e51bb7`
(`feat: ship urgent import and UX fixes`). **Sessione/worktree:** archiviati
localmente il 2026-09-10; piano versionato ancora in `Phase_0`.
**Ultima build pronta:** R5,
`c53959a6c873604e64c28defaf1e23900cf73d0e8179607b7596e53dd1b3ead0`.
**Ultimo punto:** ingresso diretto Crea Instagram valutato e non adottato;
il limite resta esplicito, non dichiarato accettato. Nessuna integrazione
autorizzata qui.

Questo documento e' il riferimento portabile del pacchetto E. Il contenuto e'
presente e committato nel checkout target allo SHA indicato sopra.
Le scritture del coordinatore presenti nello stesso worktree sono escluse dal
pacchetto automatico. Nessun dato, backup, log o CSV privato appartiene al manifest.

## 1. Catena dei piani

| Documento | Stato tecnico | Ruolo |
|-----------|---------------|-------|
| [Piano principale](plan-phase00FeedbackImportUrgent.prompt.md) | E1-E9 e U1/U4/U5/U7/U9 implementati; seguito nei round | Cause riprodotte, confini finanziari e ownership |
| [Round 1](plan-phase00FeedbackImportUrgentRound1-Review.prompt.md) | Completato 2026-09-09 | Feedback operativi import, broker, bulk, update e UX approvata |
| [Round 2](plan-phase00FeedbackImportUrgentRound2-Share.prompt.md) | Completato 2026-09-09 | Icone social e Copia e vai, fallback clipboard e referrer |
| [Round 3](plan-phase00FeedbackImportUrgentRound3-SocialFeedback.prompt.md) | Completato 2026-09-09 | Cinque social/locali, broker reopen e testo aggiornamenti |
| [Round 4](plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md) | Verificato 2026-09-09; badge/sottotesti accettati 15:51 | TikTok Upload; ingresso Crea Instagram investigato, non adottato |
| [Round 5](plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md) | Completato e congelato 2026-09-09 | Challenge/token GHCR pubblico attraverso backend same-origin |
| [Checklist portabile](checklist-review-E.md) | Corrente, non prova di accettazione | Riproduzione delle superfici senza artifact personali |

I round contengono date, note e detour. I riferimenti a vecchi PID/hash sono
cronologia delle prove, non indirizzi da riutilizzare. Nessuna istruzione di
manutenzione richiede accesso a una cartella di sessione.

## 2. Task inclusi e accettazione distinta

| Task | Pronto tecnico | Feedback dev registrato | Integrato con SHA | Archiviato |
|------|----------------|-------------------------|-------------------|------------|
| E1/E2 inspector asset | Si, API/UI round trip | OK 2026-09-09 12:36 | No | No |
| E3 FX manuale | Si, staging/commit/rifiuto saldo | Prova manuale positiva nel primo giro | No | No |
| E4 matching/manualita' | Si; nessun cambio parser | Primo import manuale chiarito; Create asset OK 12:36 | No | No |
| E5 broker duplicato/reopen/toast | Si, R3 | OK 2026-09-09 15:18 | No | No |
| E6 Generic CSV guide | Si, tabella HTML e link | Richiesta documentale recepita; non dichiarare una nuova review umana della guida | No | No |
| E7/E8 bulk e sort | Si | OK 2026-09-09 12:36 | No | No |
| E9 update check | Si | OK 2026-09-09 15:18 | No | No |
| U1 provider lifecycle | Si, regressioni automatiche | Proposta approvata; non inventare una prova umana di ogni race | No | No |
| U4 uploader | Si | Files OK 2026-09-09 12:36 | No | No |
| U5 tooltip valuta | Si | Testo breve richiesto e consegnato | No | No |
| U7 condivisione | Si, incluso R4 | X/Reddit e cinque siti OK 15:18; badge/sottotesti OK 15:51; ingresso Crea Instagram non adottato, limite da distinguere dalla promozione | No | No |
| U9 header | Si | Desktop/mobile OK 2026-09-09 12:36 | No | No |

## 3. Inventario applicativo incluso

Percorsi relativi alla root del repository. Ogni file va integrato con la sua
responsabilita', non copiato intero sopra eventuale lavoro B/C/D.

Il confronto esatto rileva 116 path modificati totali: 109 appartengono al
pacchetto E (101 file applicativi/test/documentazione elencati qui e 8 file
portabili in `14_feedbackImportUrgent/`); 7 sono registri del coordinatore esclusi
(4 file in `09_feedbackJobs/`, 2 note wiki e `TODO_FUTURI.md`). La riga directory
`Phase_0/14_feedbackImportUrgent/` non e' conteggiata come file.

### Backend - E2/E5

```text
backend/app/api/v1/brokers.py
backend/app/schemas/assets.py
backend/app/services/asset_source.py
backend/app/services/broker_service.py
```

La serializzazione delle classificazioni preserva omissione e null espliciti;
il merge resta per blocco. Il testo duplicato broker resta inglese nel backend,
con status e ownership invariati. Nessuna migrazione o nuovo error_code.

### Controllo immagine aggiornamenti - E9/R5

```text
backend/app/api/v1/system.py
backend/app/schemas/system.py
backend/app/services/container_registry.py
```

Il backend segue il challenge pubblico GHCR per il solo repository LibreFolio,
senza credenziali private o proxy arbitrario. Realm/service/scope/tag sono
vincolati; gli errori token e manifest restano distinti e fail-closed.

### Asset e provider - E1/E2/U1/U5

```text
frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte
frontend/src/lib/components/assets/AssetModal.svelte
frontend/src/lib/components/assets/ProviderAssignmentSection.svelte
frontend/src/lib/components/assets/ProviderComparisonModal.svelte
frontend/src/lib/components/assets/assetEditData.ts
frontend/src/lib/components/assets/assetPayload.ts
frontend/src/lib/components/assets/providerProbeState.svelte.ts
frontend/src/lib/components/ui/input/DistributionEditor.svelte
frontend/src/lib/components/ui/media/AssetPickerModal.svelte
frontend/src/lib/components/ui/media/ImageEditModal.svelte
frontend/src/lib/components/ui/media/ImagePickerWrapper.svelte
frontend/src/routes/(app)/assets/+page.svelte
```

### Import, FX e bulk - E3/E4/E7/E8 e R1

```text
frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte
frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte
frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte
frontend/src/lib/utils/transactions/bulkDisplay.ts
frontend/src/lib/utils/transactions/importMerge.ts
frontend/src/lib/utils/transactions/importTypes.ts
frontend/src/lib/utils/transactions/txPayloadHelpers.ts
```

### Broker e Files - E5/U4

```text
frontend/src/lib/components/brokers/BrokerModal.svelte
frontend/src/lib/components/files/FilesTable.svelte
frontend/src/routes/(app)/brokers/+page.svelte
frontend/src/routes/(app)/files/+page.svelte
```

### Shell, condivisione e aggiornamenti - E9/U7/U9

```text
frontend/src/lib/components/auth/DonationPopupModal.svelte
frontend/src/lib/components/auth/UpdateAvailableModal.svelte
frontend/src/lib/components/layout/ChangelogModal.svelte
frontend/src/lib/components/layout/Header.svelte
frontend/src/lib/components/layout/HelpMenu.svelte
frontend/src/lib/components/layout/LanguageSelector.svelte
frontend/src/lib/components/settings/tabs/AboutTab.svelte
frontend/src/lib/components/support/SocialIcon.svelte
frontend/src/lib/components/support/SocialShareModal.svelte
frontend/src/lib/components/support/SupportActions.svelte
frontend/src/lib/components/support/shareNavigation.ts
frontend/src/lib/components/support/supportLinks.ts
frontend/src/lib/features/update-check/updateCheck.ts
frontend/src/lib/utils/clipboard.ts
frontend/src/lib/utils/layout/headerScroll.ts
frontend/src/routes/(app)/+layout.svelte
```

### Primitivi condivisi e traduzioni

```text
frontend/src/lib/components/table/DataTable.svelte
frontend/src/lib/components/table/DataTableColumnFilter.svelte
frontend/src/lib/components/table/DataTablePagination.svelte
frontend/src/lib/components/ui/modals/ModalBase.svelte
frontend/src/lib/i18n/en.json
frontend/src/lib/i18n/it.json
frontend/src/lib/i18n/fr.json
frontend/src/lib/i18n/es.json
```

Focus trap/restore di ModalBase sono opt-in, default false. DataTable espone
getSortedRowIds senza modificare la selezione; stickyActions=false vale anche per
l'header. Filtro uploader riusa enum multiplo; UserSearchSelect non cambia.

### Documentazione e attribuzioni

```text
CHANGELOG.md
THIRD_PARTY_LICENSES.md
mkdocs_src/docs/developer/backend/brim/generic_csv.md
LibreFolio_developer_journal/Release_2/Phase_0/14_feedbackImportUrgent/
```

La guida Generic CSV resta nell'autorevole percorso senza suffisso `.en.md`.
Changelog sotto Unreleased, preparazione v1.1.1: nessuna data/tag di rilascio.

## 4. Test e runner inclusi

### Backend

```text
backend/test_scripts/test_api/test_assets_crud.py
backend/test_scripts/test_api/test_brokers_api.py
backend/test_scripts/test_db/test_brim_bulk_candidates.py
backend/test_scripts/test_services/test_container_registry.py
```

### Componenti, helper e harness

```text
frontend/src/__tests__/AssetSearchSelectionHarness.svelte
frontend/src/__tests__/ProviderProbeLifecycleHarness.svelte
frontend/src/__tests__/harness/ReviewSupportModalBaseHarness.svelte
frontend/src/lib/components/assets/AssetCurrencyChangeModal.test.ts
frontend/src/lib/components/assets/AssetModal.providerLifecycle.test.ts
frontend/src/lib/components/assets/ProviderAssignmentSection.test.ts
frontend/src/lib/components/assets/assetPayload.test.ts
frontend/src/lib/components/assets/providerProbeState.test.ts
frontend/src/lib/components/auth/DonationPopupModal.test.ts
frontend/src/lib/components/auth/UpdateAvailableModal.test.ts
frontend/src/lib/components/brokers/BrokerModal.test.ts
frontend/src/lib/components/files/FilesTable.test.ts
frontend/src/lib/components/layout/ChangelogModal.test.ts
frontend/src/lib/components/layout/Header.test.ts
frontend/src/lib/components/support/SocialShareModal.test.ts
frontend/src/lib/components/support/SupportActions.test.ts
frontend/src/lib/components/support/shareNavigation.test.ts
frontend/src/lib/components/support/supportLinks.test.ts
frontend/src/lib/components/table/DataTableColumnFilter.test.ts
frontend/src/lib/components/transactions/modals/TransactionFormModal.test.ts
frontend/src/lib/components/ui/modals/ModalBase.test.ts
frontend/src/lib/features/update-check/updateCheck.test.ts
frontend/src/lib/utils/clipboard.test.ts
frontend/src/lib/utils/layout/headerScroll.test.ts
frontend/src/lib/utils/transactions/bulkDisplay.test.ts
frontend/src/lib/utils/transactions/importMerge.test.ts
```

### Browser e registrazione

```text
frontend/e2e/brokers/broker-create-feedback.spec.ts
frontend/e2e/brokers/broker-recovery.spec.ts
frontend/e2e/files-uploader.spec.ts
frontend/e2e/layout/header-scroll.spec.ts
frontend/e2e/support-copy-and-go.spec.ts
frontend/e2e/transactions/tx-bulk-diagnostics.spec.ts
frontend/e2e/transactions/tx-fx-completeness.spec.ts
frontend/e2e/transactions/tx-import-asset-inspector.spec.ts
frontend/e2e/transactions/tx-import-file-selection.spec.ts
frontend/e2e/transactions/tx-import-matching.spec.ts
scripts/test_runner/_frontend_broker.py
scripts/test_runner/_frontend_transaction.py
scripts/test_runner/_frontend_utility.py
scripts/test_runner/_backend_utils.py
```

Tutte le fixture nuove sono sintetiche. I test producono e rimuovono le proprie
identita'; non richiedono il ledger o i CSV di una review manuale.

## 5. Esclusioni e riconciliazione del coordinatore

| Escluso dall'integrazione automatica E | Motivo |
|--------------------------------------|--------|
| `09_feedbackJobs/01_ux_dashboard.md`, `06_piano_sprint.md`, `README.md`, `07_feedback_import_critici.md` | Owner coordinatore; riconciliare sul master, non sovrascrivere dal worktree E |
| `TODO_FUTURI.md`, `TODO_Completati.md` | Owner coordinatore, non parte del fix applicativo |
| `LibreFolio_devWiki/wiki/decisions/brim-broker-scoped.md`, `wiki/entities/import-wizard-modal.md` | Note E da riconciliare a cura del coordinatore; non copiare automaticamente sopra la wiki corrente |
| DB, WAL/SHM, uploads, sidecar, log, screenshot e backup privati | Mai nel repository o nel pacchetto di merge |
| Cartella personale della review e CSV manuali | Non richiesti per manutenzione: usare la checklist e le fixture test portabili |
| `frontend/build/`, client API/OpenAPI generati e output MkDocs | Output rigenerabili; non sostituiscono i sorgenti |
| Lock/dependency manifest e migrazioni | Nessuna modifica richiesta da E |
| Diff B/C/D, ToolAboutPanel e 102 chiavi C | Nessuna integrazione incrociata autorizzata qui |
| `scripts/test_runner/_frontend_common.py` | Nessun delta finale E; rimossa precedente differenza di solo EOF |

## 6. Evidenze riproducibili e revisioni

Ogni riga descrive un'esecuzione avvenuta; non richiede il log privato per capire
il contratto verificato. I round conservano i dettagli di triage e i limiti.

| Revisione | Esito registrato | Limite |
|-----------|------------------|--------|
| Prima consegna, index `3f50bf24...` | Metadata round trip e FX reali, matching e bulk | Superata dai feedback R1; non e' la build finale |
| R1/R2, index `ab8b1458...` | Inspector 5, FX 4, matching 4+2, bulk 2, file selection 2, broker recovery 5, uploader 6, header 4; API classificazioni 4, broker 2, candidati 7 | Count di casi specifici, non copertura totale del prodotto |
| R2 supporto | Componenti e popup nativo desktop/mobile: copia riuscita/rifiutata, opener nullo e Referer assente | Destinazioni social intercettate nei test, nessuna pubblicazione reale |
| R3, index `e5f091dd6d5521e473281fdbbde6d01140fcef20008615edc4b4516bf6906256` | Typecheck 0/0; core 5 e componenti 103; 8 social e 2 broker desktop/mobile | Include messaggi localizzati e titolo/corpo nel link Reddit, non una garanzia del composer remoto |
| R4, index `99a7587a1a1ff3b09a3a676fa01151bcbb98f351f26ce9fe3d4f72e730e75b05` | Core 5, componenti 41, typecheck 0/0, quattro casi browser desktop/mobile per geometria di cinque badge e TikTok Upload senza Referer | Upload/media/didascalia restano azioni dell'utente; accettazione umana distinta |
| R5, index `c53959a6c873604e64c28defaf1e23900cf73d0e8179607b7596e53dd1b3ead0` | Utils container-registry 30, core update-check 30, componenti manual update 24; lint/format mirati verdi, API sync idempotente, front check/build 0/0; live `1.1.0` published e tag sintetico pending | Nessun E2E/DB setup; backend necessario per CORS GHCR, errori auth/manifest fail-closed |

Stato dati alla consegna R4: originali restituiti al percorso TEST dopo chiusura
dei processi temporanei; hash DB freddo, upload/sidecar e CSV verificati contro la
cattura precedente. Non serve distribuire quei dati per riprodurre le regressioni.
L'indagine Instagram successiva al feedback delle 15:51 e' solo ricerca e
tracciamento: nessun nuovo bundle o cambiamento dei dati.

Comandi mirati, dal checkout E riprodotto e con dipendenze del lock:

```bash
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py front check
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test --workers 1 utils container-registry
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test --workers 1 front-utility core-unit 'compareVersions|shouldPrompt|isProbeDue|probeLatestRelease|checkForUpdates|readCache robustness'
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test --workers 1 front-utility component-unit 'manual update check'
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test --workers 1 front-utility core-unit supportLinks
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test --workers 1 front-utility component-unit 'SocialShareModal|SupportActions|BrokerModal|ChangelogModal'
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py test check-orphans
pipenv run python dev.py i18n audit
pipenv run python dev.py mkdocs build
pipenv run python dev.py mkdocs check-links
```

Per i percorsi browser usare le action registrate `support-copy-and-go`,
`broker-create-feedback`, `broker-recovery`, `files-uploader`, `header-scroll`,
`tx-import-asset-inspector`, `tx-fx-completeness`, `tx-import-matching`,
`tx-bulk-diagnostics`, `tx-import-file-selection` nelle rispettive categorie.

**Attenzione:** i runner browser possono popolare/recreare TEST. Mai lanciarli
contro una review umana attiva. Conservare il DB via backup SQLite coerente,
mettere al sicuro l'intera directory originale a processi fermi, usare un
temporaneo sintetico e ripristinare a fine run. Una sola suite alla volta.
`LF_SETUP_DONE=1` e' lecito solo dopo aver preparato davvero DB e utenti.

## 7. Vincoli per l'integrazione futura

- Non ricostruire editData asset dalla sola projection: conservare loader completo,
  patch omissione/null, provider tickets e z-index relativo.
- Callback AssetModal restano `oncreated(assetId)` / `onupdated()`. Il toast e il
  full-history background di creazione sono preesistenti; il secondo sync della
  pagina globale e' anch'esso preesistente, non risolto qui. B gestisce il proprio
  opt-in toast/link senza cambiare i contesti wizard/form.
- Conservare i mount About di supporto/versione; integrare successivamente C tramite
  seam e dipendenze sue, mai sostituendo il file intero.
- Calcoli e validazioni finanziarie restano backend; niente FX/autocreazione asset
  impliciti, saldi inventati o permessi ampliati.
- Dopo la decisione del dev, registrare separatamente SHA di integrazione e stato
  archivio. Finche' mancano, le relative colonne restano No.

## 8. Need e ultimo feedback

Il piano principale e tutti i Round riportano il completamento tecnico dei
rispettivi passi; questo manifest separa le accettazioni effettive.
Il [Round 4](plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md)
conserva anche l'evidenza negativa del candidato Instagram, evitando di
trasformarla in una promessa di implementazione.

Il 2026-09-09 e' stato richiesto al coordinatore di riconciliare i need E1-E9
e U1/U5/U4/U7/U9 nei registri canonici 09/01, 09/04, 09/07, master, README,
TODO e note wiki pertinenti. Questi file hanno ownership distinta: le copie
storiche presenti nel worktree E non vanno sovrascritte sul master corrente.
**Riconciliazione completata nel checkout target il 2026-09-09**; nessun task
estraneo a E e' stato chiuso per trascinamento. Archivio e SHA restano sospesi
fino al commit manuale del pacchetto integrato.
