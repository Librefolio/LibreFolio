# Round 3 - Ultimi feedback social, broker e aggiornamenti

**Data:** 2026-09-09.
**Origine:** review diretta del dev alle 12:36; rettifica successiva: piani in italiano.
**Precedente:** [Round 2 - Copy and go](plan-phase00FeedbackImportUrgentRound2-Share.prompt.md).
**Seguito:** [Round 4 - badge e limiti social](plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md).
**Stato:** ✅ completato 2026-09-09; originali ripristinati e build R3 disponibile per la review.

## Accettazioni operative del dev

Confermati: selezione file, creazione asset, inspector/persistenza, bulk workspace,
Files, header desktop/mobile. La nuova UI del donation popup e il flusso X sono
confermati, salvo i raffinamenti social seguenti. Il toast eliminazione broker e'
confermato; quello aggiornamenti funziona ma richiede un testo piu' diretto.

Questi sono feedback umani reali, distinti dai precedenti test automatici.
Il changelog mantiene le modifiche accettate nella preparazione di v1.1.1,
senza indicare una release gia' pubblicata.

## 1. Messaggi e piattaforme social - ✅ completato 2026-09-09

- Rimuovere il tooltip delle icone; mantenere nomi accessibili.
- Messaggio diverso per ciascuno di X, Reddit, Facebook, Instagram e TikTok,
  in EN/IT/FR/ES, derivato dalla lingua effettiva dell'interfaccia.
- X: invito breve nella prima riga, hashtag direttamente nella seconda.
- Reddit: titolo breve separato; introduzione discorsiva e descrizione nel corpo.
- Usare il colore del social anche per Copia e vai.
- Link pubblico del progetto sempre incluso nella copia; nessun account sociale,
  dato finanziario o indirizzo privato dell'istanza.
- Conservare il flusso copia riuscita -> nuova scheda, i messaggi di errore e
  le guardie su cambio lingua/piattaforma/sessione e chiusura.

> **Note implementazione (2026-09-09):** sorgenti aggiornati: cinque piattaforme e
> icone CC0 locali, nessun tooltip, palette condivisa fra icona e Copia e vai.
> Testo/titolo/hint sono derived dalla lingua i18n attiva e il textarea usa value
> esplicito; cambio lingua o contenuto invalida una copia in corso. Reddit separa
> titolo e body testuale, Facebook usa solo il link sharer, IG/TikTok aprono il sito
> con istruzioni reali di incolla. Traduzioni specifiche nelle quattro lingue
> applicate tramite CLI; verifica esecutiva ancora in attesa della corsia.

> **Note implementazione (2026-09-09, verifica):** cinque builder di destinazione
> e matrice messaggi per cinque social/quattro lingue verificati nei test locali.
> I percorsi browser desktop/mobile confermano X, titolo/corpo Reddit in francese,
> didascalia Instagram in spagnolo, copia rifiutata, popup senza opener/Referer e
> mantenimento della schermata iniziale. Facebook usa soltanto il link pubblico,
> Instagram/TikTok nessun parametro di precompilazione inventato.
>
> **⚠️ Fuori pista:** un'asserzione confrontava stringhe CSS equivalenti in
> notazione oklab/oklch durante una transizione. La UI aveva lo stesso colore:
> la prova ora confronta il colore RGBA realmente dipinto e attende la relativa
> condizione, senza sleep o confronto ridotto alle classi. Retry X desktop/mobile
> superato; nessuna modifica applicativa aggiunta per aggirare il test.

```text
About / popup
    [ X ] [ Reddit ] [ Facebook ] [ Instagram ] [ TikTok ]

Modale
    [logo social] Condividi su ...
    [Titolo suggerito - solo Reddit]
    [Messaggio specifico nella lingua UI]
    [Indicazione concreta sui limiti della piattaforma]
    [Chiudi]                 [Copia e vai - colore social]
```

### Contratto browser, senza promesse fittizie

- X: intent tweet con testo e URL pubblico.
- Reddit: richiesta di post testuale, titolo nel parametro title e corpo completo
  nel parametro text; niente parametro url da link-post. Il testo e' comunque
  negli appunti se il sito non lo precompila.
- Facebook: sharer pubblico con il link; il messaggio copiato va incollato
  dall'utente. Non inventare un parametro per precompilare il messaggio.
- Instagram/TikTok: copia didascalia e apertura del sito; nessun intento browser
  pubblico verificato per precompilare testi senza integrazione/media. La modale
  deve dirlo chiaramente, senza fingere pubblicazione o caricamento.

Riferimenti controllati:
[Meta Share Button](https://developers.facebook.com/documentation/plugins/share-button.md/),
[Instagram Content Publishing](https://developers.facebook.com/documentation/instagram-platform/content-publishing),
[TikTok Content Posting](https://developers.tiktok.com/docs/en/content-posting-api-get-started).
I parametri del composer Reddit non hanno una garanzia pubblica aggiornata:
il fallback e' il corpo completo gia' copiato, non una diagnosi cross-origin.

## 2. Ciclo di vita aggiunta broker - ✅ completato 2026-09-09

- Alla chiusura/nuova apertura azzerare errore, conferma di scarto e stato della
  precedente apertura, senza resettare i campi mentre l'utente sta scrivendo.
- Risposte tardive di una precedente apertura non possono chiudere o sporcare
  la nuova modale.
- Toast verde localizzato solo dopo creazione effettivamente riuscita, emesso
  dal componente condiviso per coprire pagina broker e apertura dalle transazioni.
- Preservare BRCreateResult testuale, status, ownership e vincoli finanziari.

> **Note implementazione (2026-09-09):** introdotta generazione dell'apertura
> (open/mode/broker) che resetta il feedback, non i cambi digitati. Risposte/finally
> di una generazione precedente vengono ignorati. Il componente condiviso emette
> broker.created con toast verde localizzato solo dopo il successo reale.

> **Note implementazione (2026-09-09, verifica):** unit test di reopen, digitazione,
> risposta tardiva e ordine evento/callback superati. Due E2E reali desktop/mobile:
> errore duplicato, X, conferma scarto, nuova apertura senza errore/draft vecchio,
> creazione tramite API e toast verde con nome escaped, scheda individuata per ID.
> Fixture e cleanup limitati ai broker creati dalla prova.

## 3. Testo aggiornamenti - ✅ completato 2026-09-09

Esito positivo: «Sei aggiornato alla versione piu' recente!».
Seconda riga: «Versione rilevata online: {version}».
Aggiornare le quattro lingue tramite CLI; nessuna modifica al confronto versioni,
alle sorgenti online o alla gestione degli errori.

> **Note implementazione (2026-09-09):** chiavi esistenti aggiornate via CLI nelle
> quattro lingue. Formato a due righe e versione remota effettiva invariati.

> **Note implementazione (2026-09-09, verifica):** ChangelogModal incluso nel
> blocco componenti mirato; versione remota, esiti distinti e struttura del toast
> restano invariati. Solo formulazione positiva e dicitura online cambiate.

## 4. Verifica e handoff - ✅ completato 2026-09-09

Test-author scrive fixture/regressioni senza eseguire suite. E esegue la coda
mirata solo dopo riassegnazione dal coordinatore. Prima di E2E/populate:
nuovo backup privato coerente dello stato dopo questa review, senza sovrascrivere
o considerare aggiornato il backup precedente. Originali messi al sicuro a
server fermo, dati sintetici temporanei, ripristino prima dell'handoff.

Verificare lingua runtime, titolo/corpo Reddit, payload pubblico, flussi solo-copia,
colori/assenza tooltip, reopen broker e toast creazione, nuovo testo update.
Aggiornare subito ogni step con data, nota e detour; nessun commit/staging/push.

> **Backup nuovo: ✅ completato 2026-09-09 alle 13:14.** Autorizzazione specifica
> del coordinatore: sola lettura coerente/WAL-aware del DB E e copia dei file E.
> Nuovo artifact privato `private-e-test-backup-20260909-round3`, senza sovrascrivere
> quello precedente. Integrita' SQLite, CRC/hash file e stabilita' della cattura
> verificati; directory 700 e file 600. Manifest SHA256
> `4b990f00fe2504d1f78339bf43ddbb67495cd8bdefa4b5350383a5b88d80b1d2`.
> Include le modifiche della review umana recente, gli upload/sidecar, CSV e note
> correnti. Build conservata: R2 `ab8b1458...`, non una R3 dichiarata gia' compilata.
> Nessun accesso o intervento su processi B/6041, nessun reset, suite o build.

> **Note implementazione (2026-09-09, 14:52):** con un nuovo VIA limitato del
> coordinatore eseguito `pipenv run python dev.py front check`: zero errori e
> zero warning, exit 0. Non eseguiti build, API sync, HTTP o operazioni DB.
> Broker e social hanno le regressioni autore gia' riconciliate; la nuova E2E
> `broker-create-feedback` e' registrata. Il successivo blocco Vitest attende
> l'assegnazione locale esplicita, mentre 6041 resta dedicata alla corsia B.

> **Note implementazione (2026-09-09, 15:02):** ricevuto prima il VIA Vitest
> (5 test core e 103 componenti passati), poi il VIA E completo dopo il rilascio
> verificato di B da parte del coordinatore. Nuovo backup immediatamente prima
> dell'esecuzione: `private-e-test-backup-20260909-round3-execution`, manifest
> `35125e40ec9eaf321d1e630a8daf5f2792693db75f6c5eda3e66425ab5800c2c`.
> Il DB coerente coincide con la copia delle 13:14; nessun dato di B letto.
>
> Originale TEST E spostato intero in area privata a server fermo. Popolata una
> directory temporanea vuota **senza force**; i runner preparano gli utenti e
> `LF_SETUP_DONE=1` evita il populate ridondante del global setup Playwright.
> Server E temporaneo PID 89774, senza scheduler/reload/force. Build/API sync
> completati con zero errori e warning. Otto scenari social e due broker
> desktop/mobile superati, incluso il retry circoscritto del solo caso colore.
> Rimangono controlli finali non distruttivi e ripristino dell'originale prima
> della disponibilita' per la prossima review umana.

> **Note implementazione finali (2026-09-09, 15:04):** catalogo e raggiungibilita'
> dei test verificati, 2563 chiavi complete nelle quattro lingue. Fermato il solo
> server E temporaneo; verificati porta e handle DB chiusi. Ripristinata la directory
> originale completa, controllato hash freddo DB identico e tutti gli hash degli
> upload/sidecar rispetto al backup immediatamente precedente. CSV manuali invariati.
> Risultati temporanei conservati privatamente, nessun dato della review rimpiazzato
> dal seed sintetico. Nessun `--force`, merge B/C, commit, staging o produzione.
>
> **Runtime di consegna:** `http://127.0.0.1:6041`, PID `94074`, cwd del worktree E,
> HEAD `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`, no scheduler/reload.
> `index.html` su disco e servito via HTTP:
> `e5f091dd6d5521e473281fdbbde6d01140fcef20008615edc4b4516bf6906256`.
> Checklist in `~/Documents/test-ui-urgenti/REVIEW-E-R3.md`.
> La consegna tecnica non anticipa l'accettazione del dev; nessun passo di
> implementazione o verifica richiesto resta pendente.
