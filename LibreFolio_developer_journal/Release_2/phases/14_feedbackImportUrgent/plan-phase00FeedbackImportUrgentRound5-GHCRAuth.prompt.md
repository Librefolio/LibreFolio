# Round 5 - Autenticazione pubblica GHCR nel controllo aggiornamenti

**Data:** 2026-09-09.
**Origine:** review indipendente bloccante ricevuta dal coordinatore alle 16:47.
**Precedente:** [Round 4 - badge e limiti social](plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md).
**Stato:** ✅ completato e applicato al checkout target `dev_release2` il 2026-09-09.
**Commit/SHA di integrazione:** `ef722b552433028c051ccb1207c84f1072e51bb7`.
**Sessione/worktree:** archiviati localmente il 2026-09-10.

## Difetto

Il controllo immagine inviava dal browser una `HEAD` anonima direttamente a
`https://ghcr.io/v2/librefolio/librefolio/manifests/<tag>`. GHCR richiede prima
un token pubblico e risponde `401` con challenge `WWW-Authenticate`; il codice
classificava quindi ogni immagine protetta dal normale handshake come
`image-request-failed`, senza poter raggiungere `update-available`.

## 1. Riproduzione e CORS - completato 2026-09-09

- Riprodurre il challenge pubblico senza credenziali.
- Verificare token endpoint e richiesta manifest autenticata.
- Verificare se il flusso e' eseguibile da browser, senza dedurlo dal solo HTTP 200.

> **Note implementazione:** il challenge indica realm HTTPS GHCR, service
> `ghcr.io` e scope pull del repository LibreFolio. Il token anonimo e' emesso,
> ma challenge/token non espongono header CORS utili e il preflight browser per
> `Authorization` + `HEAD` risponde 405. Un token flow nel client non puo' quindi
> leggere/completare il protocollo in modo affidabile.
>
> **⚠️ Fuori pista:** la prima ipotesi era completare il challenge nel browser.
> La verifica CORS l'ha esclusa prima di introdurre codice client o fallback
> fittizi. Nessun token e' stato salvato nei sorgenti, nei piani o nei log.

## 2. Contratto backend - core completato 2026-09-09

- Endpoint same-origin autenticato, con repository e tag strettamente delimitati.
- Parser rigoroso del challenge; realm HTTPS/host/path, service e scope verificati.
- Token pubblico richiesto senza credenziali; Bearer inviato soltanto alla seconda
  richiesta manifest.
- `HEAD` esplicita e `Accept` per OCI index/manifest e Docker list/manifest.
- Errori auth/token distinti da errori manifest; 404 resta immagine pending.

> **Note implementazione:** aggiunto servizio async `httpx`, senza dipendenze
> nuove, redirect o proxy generico. L'endpoint accetta solo tag stabili
> normalizzati `x.y.z` e richiede sessione LibreFolio attiva. La risposta e'
> tipizzata `published|pending|error`, con reason obbligatoria solo per error.
> Il probe live pubblico restituisce `published` per `1.1.0` e `pending` per un
> tag sintetico inesistente, senza stampare il token.

## 3. Integrazione frontend - core completato 2026-09-09

- Il browser continua a interrogare GitHub Releases direttamente.
- Il gate immagine usa il client API same-origin generato.
- Il tag release `vX.Y.Z` resta normalizzato a `X.Y.Z`.
- Cache, dismissal, automatic/manual flow e silenzio automatico restano invariati.
- Il manual check distingue `image-auth-request-failed` da
  `image-request-failed`, usando lo stesso messaggio localizzato di verifica
  immagine senza presentare alcun errore come "aggiornato".

> **Note implementazione:** API sincronizzata dopo l'aggiunta endpoint.
> `checkForUpdates` conserva un seam tipizzato del probe immagine per test
> deterministici; nessuna chiamata GHCR cross-origin rimane nel browser.

## 4. Test, build e nuovo freeze - ✅ completato 2026-09-09

- Test-author: challenge 401 -> token -> manifest 200; errori token; manifest
  404/401; challenge malformato/non fidato; normalizzazione tag reale.
- Preservare i casi E9 precedenti e il mapping della modale.
- Eseguire soltanto API system, unit update-check/componenti pertinenti,
  front check e build debug. Nessun DB reset/populate o E2E.
- Aggiornare changelog, manifest/inventario/evidenze e nuovo hash build.
- Ripristinare freeze come pronto tecnico/candidato integrazione; nessun
  commit, staging, merge o archivio.

> **Note implementazione:** il test HTTP pure e' registrato come
> `utils container-registry`, non nella categoria services che eseguirebbe il
> setup DB. Passano 30 casi backend (challenge/token/manifest, trust, token
> fields, endpoint), 30 casi core `updateCheck` e 24 casi componente manual
> update. `front check` e build riportano 0 errori/0 warning; API sync ripetuto
> produce gli stessi OpenAPI/client.
>
> **⚠️ Fuori pista:** due test-author hanno consegnato in ritardo matrici GHCR
> duplicate in `test_system_api.py` e nel nuovo file pure, modificando inoltre
> test frontend durante un primo gate. Quel run frontend e' stato scartato.
> Il duplicato e il delta services sono stati rimossi; coperture uniche
> (media type, credenziali, token/access_token e mapping auth UI) consolidate
> una volta nel file pure e nei test frontend. I gate finali sono stati eseguiti
> solo dopo fingerprint stabile.
> Anche il primo filtro Vitest `updateCheck` era un falso verde da zero test:
> scartato e sostituito con i nomi reali dei sei describe, che eseguono 30 casi.
>
> **Note dati:** nessun reset/populate/E2E. Gli snapshot byte-level del DB a
> inizio e fine Round 5 e il DB corrente coincidono su
> `15239d179fa1191443686f8d53cbb6d9c03f35b3e6c42bb803ae4c58be6798c9`;
> `PRAGMA integrity_check` e' `ok`, upload/sidecar e CSV manuali corrispondono.
> La differenza rispetto al vecchio hash freddo R4 era gia' presente prima dei
> gate, dopo uso/server/checkpoint, e non e' stata usata per sovrascrivere lo
> stato corrente.
>
> **Build congelata:** index on-disk e GET/
> `c53959a6c873604e64c28defaf1e23900cf73d0e8179607b7596e53dd1b3ead0`.
> Review E su `http://127.0.0.1:6041`, PID 33363, cwd del worktree E,
> senza scheduler/reload/force; endpoint immagine non autenticato risponde 401.
> Inventario finale: 116 path totali = 109 pacchetto E
> (101 applicativi/test/documentazione + 8 journal14) + 7 registri coordinatore
> esclusi. Stato formale: pronto tecnico/candidato integrazione; SHA integrazione
> e archivio restano assenti.

Riferimenti:
[Distribution token authentication](https://distribution.github.io/distribution/spec/auth/token/),
[Docker manifest v2 schema](https://distribution.github.io/distribution/spec/manifest-v2-2/).
