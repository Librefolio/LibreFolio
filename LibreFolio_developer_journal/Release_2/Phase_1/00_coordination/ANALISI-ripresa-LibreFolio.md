# LibreFolio 1.3.0 — analisi di ripresa (21/10/2026)

Solo lettura. Nessuna sessione figlia avviata, nessun commit, merge o patch, nessun test pesante.
Fonti incrociate: **(1)** backlog e piani del journal, **(2)** decisioni §36–§52 del vecchio coordinatore, **(3)** ultimi turni nel DB e `events.jsonl` (20/10 fino alle 14:36), **(4)** git (branch, worktree, log).
Orari = ora locale del Mac (UTC+2). SHA a 9 caratteri.

---

## 0. In breve

1. **`dev_release2` = `b844f83f2`**, uguale a `origin/dev_release2` secondo il ref locale (non ho fatto fetch). Dentro ci sono 4 treni del 20/10 più G-28. **Il gate del treno 4 è tutto verde** (finito alle 15:04, dopo la morte del coordinatore perché lo script era staccato): all-backend 7/7, core-unit 9771, component-unit 5154, E2E mirati ok.
2. Il coordinatore è morto alle **14:36 con un errore 403** (credenziali scadute) e **tutte** le sessioni figlie con lui. Gli ultimi ~10 messaggi dei figli non hanno mai avuto risposta, e due decisioni del developer delle 14:32 (TC-23 → (a), e la voce E-26) potrebbero non essere arrivate a destinazione.
3. **Lavoro vero non in dev**: 4 commit su branch (A, E, H, J), 5 gruppi di file non committati (Y-39a: 11 file; Z-29s-a: 6; E: 9; J: 2; H CP2: 3 test non tracciati). Esiste un backup completo: `~/Documenti/EmaEnel20261020/LibreFolio_all.tar.gz` (25,9 GB, 20/10 17:26). Non ho verificato il contenuto.
4. **Il REPORT è in parte vecchio**: B-51, J-57 v3, A-CL1, X-R45b-ui, `gate_b8` risultano "da fare" ma sono già in dev e verdi (§1).
5. **Due strozzature decidono la data**: (a) la catena grafici Y-39a → Z-29b → Z-29s → Y-40 (~8-9 giorni di lavoro anche con il parallelo), (b) il backup "tutto assieme" (L3 + replica): la stima è 4-6 settimane. Il 19/10 si parlava di "1.3 fra due settimane": le due cose non stanno insieme.
6. **Il cancello colori blocca il tag** e aspetta una tua decisione (D-T28: interruttori e serie dei grafici). Non so dire quanto manchi: il ratchet dice "pulito", ma non misura la completezza.
7. **Ambiente Linux**: pipenv/Python 3.13, npm e Playwright (chromium) ok. Ma: il nome del venv nei documenti (`LibreFolio-SAUMUTtc`) qui non esiste; `.claude/` e `CLAUDE.md` non sono tracciati da git (i figli nei worktree non li vedrebbero); **Docker non c'è**; RAM 15 GB.
8. Ti propongo: **ondata 0** (messa in sicurezza, nessun figlio), poi **3 ondate con al massimo 3 sessioni** (Y, H, Z per prime). Tutto il resto resta fermo.

---

## 1. Dove il REPORT è superato (verificato)

| Il REPORT dice | Realtà | Prova |
|---|---|---|
| A: "poi A-CL1 (analisi bug changelog)" | A-CL1 è **in dev** dal 19/10 | `c0cc8330b`, §51 |
| W: "B-51 fatto, CHECKPOINT READY in attesa di commit" | **In dev** (treno 3). Worktree W pulito, 0 commit avanti | `00c5d9014` |
| J: "J-57 v3 con `slot_part2.sh`" | J-57 è **in dev** (treno 2). J ora ha J-60 committato e L1b con GO | `706257542`, `cd44e6531` |
| X: "X-R45b-ui, N61-form (cura non applicata)" | **In dev** (treno 1) | `08e23108a` |
| E: "E-AI503, N62, E-20 (in lavorazione)" | E-AI503/E-20/E-24 **in dev** (treno 2), E-23 (treno 4) | `58846c7e1`, `4efc68bad` |
| H: "H-60 (review)" | H-60 + H-60r **in dev** (treno 2), N70 + mappa guide (treno 3) | `e8c970379`, `6ba039f01` |
| MF: "P1b decisione aperta" | **Deciso (A)**, in dev, sui dati reali **0 cambi** | `3b3e91e6d` |
| "`gate_b8.sh` pronto, mai eseguito" | B-8 gate **verde** il 20/10; all-backend verde su ogni treno | `logs/allbackend-20261020.summary`, `gate-train1..4` |
| Z-29a "campionamento" | Z-29a v3 **in dev**; Z-29a-f in dev (treno 4) | `746920b83`, `bbc668d02` |
| Elenco "decisioni aperte": Litestream a/b, E-AI503, E-23, MF-P1b, D-W85-3, TC-23, E-26 | **Chiuse o superate** (§5) | DB `ask_user` |
| Backlog `Z-29`: "dopo la 1.3, analisi, Z-29a sospesa" | **Vecchio**: Z-29 è in 1.3 (N90 + 20/10) | `BACKLOG_POST_1.2.md:8155` |

---

## 2. Inventario dei lotti

Stati: **DEV** = in `dev_release2` · **BR** = committato su un branch, non in dev · **WT** = nel worktree, non committato · **GO** = deciso e autorizzato, codice non iniziato · **AN** = solo analisi o domanda · **IDEA** = solo idea/dopo.
Colonna "4 fonti": B=backlog, P=piani, D=decisioni/DB, G=git. `!` = manca in una fonte dove dovrebbe stare.

### 2.1 DEV — entrati dopo il push del 19/10 (`ecc7ac667`)

| Treno | Lotti (merge) |
|---|---|
| 1 `701054da9` | Z-29a v3 + Z-29r (`746920b83`) · B-8 rifinitura (`7d597ed90`) · N69a (`3e82ed2e0`) · X-R45b-ui + N61-form (`08e23108a`) · L1a (`2a8e3f3f8`) |
| 2 `f73514a77` | H-60 + H-60r (`e8c970379`) · E-AI503 + E-20 + E-24 (`58846c7e1`) · X wac-inf (`bb295763f`) · Z-29d-0 + Y-38 (`ba16706cb`) · B-50 (`4b592ca93`) · B-52 Fineco/Danske (`a79a223cd`) · MF-P1b (`3b3e91e6d`) · J-57 (`706257542`) · Z-32(d) backend (`5f2f8e056`) |
| 3 `6e1761121` | Z-32(d) frontend (`ecbad6861`) · J-66 + §29 (`c4f037f62`) · W-B89 + B-51 (`00c5d9014`) · E-24.2 (`b56e46b37`) · B-53/54/55 (`414683c81`) · MF-E2 (`8d8d345e6`) · H-60 fix W-B37 + mappa guide + N70 (`6ba039f01`) · X P3 funzione a gradini + Z-39 (`cac0ab76e`) |
| 4 `15fa228ef` | E-23 (`4efc68bad`) · Z-29a-f (`bbc668d02`) · J-67 (`89fd61c83`) · MF-E2b + P3 consumatore (`015094472`) · N69b (`1e711253a`) |
| dopo | G: note N69 (`a820bd4dd`) · G-28 fixture sicurezza "ok" (`b844f83f2`) |

### 2.2 BR — committati sul branch del figlio, **non in dev**

| Lotto | WS | Commit | Stato | Chi lo aspetta |
|---|---|---|---|---|
| H-61 · funzione `admin_setup_status()` | A | `64b8b9fa3` feat, `bdb083782` doc, `50d1f29c6` journal (branch A; già fusi nel branch H) | verde: 310 test | H (per la rotta R1) |
| H-61 · CP1 intermedio (L1: token per scopo, limite, log, tag "Hosting panel", controllo `platform.hosting_panel`, Q5 sospensione) | H | `e917659c9` + merge `f9f417bfa` | **rosso voluto**: `api panel-status` 20, `hosting-panel-routes` 4/15, `instance-block` 1, finché non c'è R1 | coordinatore (merge di dev in H), poi H scrive R1 |
| J-60 · costo di carico negativo rifiutato | J | `cd44e6531` + `7321c8b9b` | verde, riga CHANGELOG 🐛 proposta | treno 5 |
| E · scatto galleria `settings/email` (8 pagine, 4 lingue) | E | `b02611402` + `a7c7de18d` | solo doc, mkdocs strict ok | treno 5 |

### 2.3 WT — nel worktree, **non committato** (il rischio più alto)

| Lotto | Worktree / branch | Cosa c'è | Stato / cosa manca |
|---|---|---|---|
| **Y-39a** · modulo unico `chartSignalRendering.ts` per schede e anteprima | `e-alfy-redesigned-spork` (Y) | 11 file: 4 nuovi (modulo, test del modulo, `ChartSettingsModal.test.ts`, gate `signalRendering.gate.test.ts`) + 7 modificati (modale, due pagine, test, runner +3 righe, piano, backlog Y-41/Y-42) | Vitest 375/375 e 1044/1044, svelte-check 0/0. **E2E (~25 min) mai partita**: nessun log. Base `a91ff36cd`, 200 commit indietro; merge simulato con dev: 0 conflitti |
| **Z-29s-a** · metà backend del campionamento dei segnali | `e-alfy-potential-sniffle` (Z) | 6 file: rossi in `test_assets_prices.py`, `test_price_query_sampling.py`, `test_signal_aggregation.py`, `timeSeriesAggregation.test.ts`, nuova tabella `signal_sampling_cases.v1.json`, piano | solo rossi scritti, nessun codice |
| **E · voce X della galleria in it/fr/es + timbro** | `e-alfy-stunning-fortnight` (E) | 9 file, "CHECKPOINT READY" delle 14:36 | non committato. **`.translate-hashes.json` e BACKLOG sono cambiati anche in dev** → un merge con l'albero sporco non parte, e dopo il commit il JSON può confliggere |
| J · journal J-70 + promemoria L1b/R1/CP-8-9 | `e-alfy-crispy-goggles` (J) | 2 file, messaggio già concordato `docs(journal): J-70, L1b R1 CP-8/9 memo` | da committare prima di aggiornare la base |
| H-61 · CP2 (biglietti Ed25519) | `e-alfy-sturdy-memory` (H) | 3 test non tracciati (~320 casi, mai girati) | il codice di bozza sta fuori dal worktree, nella cartella di sessione di H |
| A-62 | `e-alfy-legendary-winner` (A) | **niente su disco** (i rossi li stava scrivendo un test-author) | da rifare |
| solo piani | X, T, A, MF (1 file ciascuno) | note di journal | basso |

### 2.4 GO — deciso e autorizzato, codice non iniziato

| Lotto | WS | Deciso | Dipende da |
|---|---|---|---|
| H-61 CP2 · L2 (JWT Ed25519, `jti` su file in `DATA_DIR`) | H | developer 20/10 | CP1 chiuso |
| Y-39b · anteprima come asset detail + colore linea di base sulle card (F-2) | Y | developer 20/10 | Y-39a |
| Z-29b · lista Assets con serie ridotte | Z | developer N90 | **Y-39a in dev** (stesso file `assets/+page.svelte`) |
| Z-29s · resto del campionamento (rendimento mobile) | Z | developer 20/10 | Z-29s-a |
| Y-40 · tre viste (abs, %, rendimento mobile) su card, anche cambi | Y | developer 20/10 | Z-29s |
| Z-29d ridotto | Y/Z | developer D-Z29d | Z-29b |
| Z-29fx · riduzione su `/fx/currencies/convert` | Z | coordinatore, in coda | dopo Y-40 |
| E-25 · conferma con clic su `/verify-email` | E | developer 20/10 | — |
| E-26 (b) · campo "email trattenuta" in `POST /auth/register` | E + A | developer 20/10 ~14:30 (E l'ha ricevuta) | A rivede; dopo A-62 |
| A-62 · nome tradotto del menu + segnale `data-security-checks` | A | coordinatore | — |
| N69c/N69d · modo iscrizione in Utenti, bottone "Guida" (la mappatura c/d segue l'ordine di costo di A: non verificata sul piano) | A | developer D1-D11 | mappa guide di H (in dev) |
| L1b · lotti sui gradini FX | J | coordinatore 14:32 | base aggiornata |
| TC-23 · "Aggiungi coppia FX" unico, opzione (a) ovunque | J (+T2 in dev) | **developer 14:32 — non inoltrato a J** | — |
| P4 · motore a segmenti, `daily_states` pigri | MF | coordinatore 14:28 | D-P4; collide con CP-8 di J su `portfolio_service.py` |
| H-55 v2 · CSP sempre applicata | H | developer 19/10 | dopo H-61 |
| X-Q1…Q3/S1 · "formule veloci" lato X | X | piano MF-FV | Z-29a (ora in dev) |
| N64 · cache dei segnali "come quella dei prezzi" | X | developer ha approvato il principio | **conferma delle domande (mai fatte)** |

### 2.5 AN — analisi o domanda, serve una decisione

N78-1/N78-bis (W+MF) · W-B86/W-B87/W-B88 (W) · D-W85-1/2/4 · E-7 (E) · Q-G29-1 / J-68 (J) · D-P4 (MF) · MF-P1c · X-R48b (sospeso) · L3 + backup "tutto assieme" · D-T28 (colori) · E-21 / C-70b · J-70 (conteggio su dati reali) · R1 di J (aspetta Q1 di X).

### 2.6 Lotti 1.3 "mai partiti" (`PROSSIMI_LAVORI.md`)

W3 router broker · W4/CP7 taglio `brim_provider.py` · W5-W6 icone/report per plugin · K2b/K2c (K2b = C-70b) · **K3a** (5 difetti Bulk/Form, 26 rossi parcheggiati) · V-37b ("⚡ Validate now") · Crédit Agricole sui report set (esplorazione) · X: CP5, CP7/FE4, FE5a, CP12.

### 2.7 IDEA / dopo la 1.3 (già etichettati)

Litestream F25 · B-56 · B9 arm64 · BZ parte 2 · B5b · B-33 · Z-4, Z-7, Z-23, Z-31, Z-35 · E-22, E-2/3/6 (1.4) · X-R44b/R49b/R67/R76/R78/R80-R83 · H-48 · A-49, A-58 · J-56 · MF-A6, MF-A13 · richieste utenti #47-#52.

---

## 3. Pezzi che rischiamo di aver perso (una fonte sì, le altre no)

| # | Cosa | Dove compare / dove manca | Rischio |
|---|---|---|---|
| 1 | **Y-39a/b, Y-40, Y-41, Y-42, Z-29b/s/d/fx, H-61, A-62** | Piani e DB sì. **Non nel piano generale 1.3** (`plan-phase01Release13`) e **non nel backlog di dev**. Y-41/Y-42/J-70 solo nel backlog sporco dei worktree | Sono ~10-12 giorni di lavoro deciso il 20/10 e invisibili a chi legge solo il piano generale |
| 2 | **Y-39a** | Solo nel worktree sporco | Se il worktree si perde, 1,5 giorni di Y |
| 3 | **Domande promesse al developer e mai fatte**: N64, E-7, Q-G29-1, D-P4, Q-Q7 (pence), N78-1 | Nel DB: "le porto io" senza `ask_user` corrispondente. X e E dichiarano di aspettare | Tu non sai che sono aperte; i figli aspettano |
| 4 | **Decisione TC-23 (a) del 14:32** | `ask_user` risposto, ma J risulta fermo ad aspettarla (ultimo messaggio J 14:32/14:36) | J riparte senza saperlo |
| 5 | **P4 GO (14:28), slot Y E2E (14:28), L1b** | Inviati nei 20 secondi prima della morte; MF e Y non hanno risposto | Non so se li hanno ricevuti |
| 6 | **N78-1** | Il 20/10 (09:06) "aspetta la bozza di W dopo B-52"; B-52 è in dev; W è **fermo dalle 11:56**, senza un lotto assegnato | L'analisi W+MF non esiste: la decisione non si può prendere |
| 7 | **Z-29 nel backlog** dice ancora "dopo la 1.3, Z-29a sospesa" | Backlog vs decisioni | Contabilità sbagliata |
| 8 | **Contabilità ✅**: ~150 voci con ID citato nei commit di dev ma senza ✅; 14 con ✅ solo nel testo | Stima mia con script (approssimata) | Il vecchio coordinatore l'aveva già indicato: "una-due ore, solo contabilità" |
| 9 | **Lotti 1.3 mai partiti** (§2.6) | Sono ancora "1.3" nel piano, ma "dopo lo sprint" | Se nessuno decide, il tag aspetta lavoro mai pianificato |
| 10 | **Messaggio per la issue #26 (Danske)** | Testo pronto (`issue26-danske-messaggio-20261019.md`), B-52 è in dev (treno 2) | Solo tu puoi pubblicare |
| 11 | **Nightly Linux** del tuo server: comandi dentro il container | `nightly-fix-dentro-container.md` | Non so se l'hai già eseguito |
| 12 | **CHANGELOG `[1.3.0]`**: oggi c'è solo `[Unreleased]`; mancano le righe di J-60 e dei lotti nuovi | `CHANGELOG.md` | Normale, ma va chiuso al tag |
| 13 | **Debito di traduzione** (E getting-started, J form, B backup_restore, ecc.) | decisione: solo su tua richiesta | Va deciso prima del tag |
| 14 | **Backup architettura**: "dammi il tempo di rifletterci" | Documento scritto 14:28, 12 decisioni | Nessuno lo ha ancora letto |
| 15 | **Messaggio non risposto al coordinatore cloud** (11:15 UTC, "stai aspettando me o la 1.3?") | REPORT, non nel DB di questo repo | Il pannello aspetta il contratto di H-61 |
| 16 | Branch/worktree avanzi: `preview-colori-1015` (+2, 2615 indietro), `gate-coord`, `copilot-prewarm-*`, `hotfix-1.2.1` | git | Pulizia, non urgente |

---

## 4. Decisioni aperte del developer (con la mia raccomandazione)

### A. Backup e cloud — la più pesante
**Cosa è cambiato:** la domanda "Litestream (a) o (b)?" è **superata**. La ricerca L3 dice che Litestream non sa più cifrare verso una chiave pubblica; il documento `backup-architettura-cloud-20261020.md` propone un'architettura B (l'app stessa fa copie cifrate di DB **e** file, verso la chiave pubblica del pannello, senza Litestream). Costo: 29-37 giorni sul prodotto + 8-10 sul pannello = **4-6 settimane**.

- **Esempio:** il DB pesa 13 MB e i file 25 MB: copiare spesso costa poco. Perdi al massimo 5 minuti da sveglia e niente a fine sessione (oggi fino a 24 ore).
- **Le 12 decisioni** (architettura, chi decifra, quando copiare, conservazione, bucket, chiave L3, self-hosted, Litestream, volume vuoto, "com'era ieri", data limite, informativa). **Raccomando di accettarle come scritte** (B, K2, 60 s dopo l'ultima modifica con massimo ogni 5 minuti, un bucket per istanza, Litestream fuori).
- **Decisione 11 è quella che ti serve oggi:** tu hai detto che la funzione deve uscire "tutta assieme". Allora **o si fa un tetto di tempo** (fine spike + 4 settimane; oltre, la funzione intera va in 1.3.1 con l'interruttore spento) **o la 1.3 slitta**. Raccomando il tetto di tempo, e **L1 + L2 restano in 1.3** (sono H-61, già in corso).
- D1-D10 di Litestream: non rispondere ora, sono quasi tutte superate. Restano valide due idee: "mai partire vuoti sopra un backup buono" (D2) e "cosa fa la replica dopo un ripristino" (D6).

### B. Colori — blocca il tag
- **D-T28:** anticipare ora, con i ruoli più vicini e l'etichetta "da rivedere", (1) gli **interruttori** (109 classi → `bg-lf-checked`) e (2) le **serie dei grafici** (145 letterali)? **Raccomando sì**: è proprio il mandato "migra veloce, rifinisci dopo" (D-T27/T28) e il tag non può uscire senza la conversione di neutri e stati.
- Le risposte della designer (verde Liquidità, flussi neutri, serie di crescita, posizione del pallino) non sono tue: non bloccano.
- Dato che manca: quanto è lontana la conversione di neutri e stati. Il ratchet dice "pulito" ma conta le regressioni, non la completezza (590 classi legacy ancora nel `m1`).

### C. Import e transazioni
| Decisione | Raccomandazione |
|---|---|
| **D-W85-1** motivi d'esclusione di Danske | Come proposto da W: tipo sconosciuto/riga non valida/ambigua → avviso con link issue; fuori periodo → avviso senza link; coperte da file più nuovo → silenzio e log |
| **D-W85-2** righe non ancora regolate (Fineco, Danske) | **Tieni la nota blu**: senza, l'utente crede la riga persa |
| **D-W85-3** gli altri plugin | Una funzione condivisa con due codici; nella 1.3 solo i 4 plugin stabili (DEGIRO, Crédit Agricole, Scalable, Directa); gli altri dopo |
| **D-W85-4** plugin che saltano righe con effetto economico (Revolut: split; Trading 212: split e conversioni; eToro: commissioni notturne e SDRT) | **Nella 1.3 almeno l'avviso con link issue**; l'import vero dopo. È l'unico pezzo "numeri sbagliati in silenzio" |
| **Q-N78-1** costo di consegna in uscita nel Form | **Non decidere ancora**: manca l'analisi W+MF (§3 punto 6). Chiederla è il primo lavoro di W |
| **K3a** (K-4: cambio lingua col Bulk aperto perde le modifiche) | **Tienila in 1.3**: perde dati. Le altre (K2b/c, V-37b) dopo |
| **C-70b / E-21** (errori import tradotti) | Opzione (a), e **tutte e due dopo la 1.3** |

### D. Numeri
- **D-P4** (MF): con "un punto al giorno", un refuso all'anno 1 darebbe ~740.000 punti per serie: ~1,3 GB di JSON e ~200 s. **A** (l'API resta un punto al giorno, la Dashboard chiede la storia campionata sui grafici lunghi), come già fa Z-29 per le schede. **Raccomando A.**
- **P4 stesso** (motore a segmenti, 2-3 giorni, rischio medio-alto): servirebbe solo a togliere i "pavimenti" di data, che nessun criterio di rilascio chiede. **Raccomando dopo la 1.3**, insieme ai pavimenti e a MF-P1c.
- **J-70** (contare i costi negativi già salvati): solo se vuoi, richiede una copia dei tuoi dati reali.

### E. Altri
- **N64** (X): conferma il "come i prezzi" e tre domande (token/rotellina, dopo il recupero, coda). **Raccomando sì, ma dopo la catena grafici.**
- **E-7** (segno "in attesa di verifica" in Utenti): **raccomando dopo la 1.3**; le domande vanno comunque poste a E.
- **Q-G29-1** (etichette dei marcatori nel Gantt, include J-68): da chiedere; raccomando dopo la 1.3.
- **TC-23** è già deciso (a); **E-26** già (b); **E-25** già sì. Vanno solo ricomunicati.
- **Traduzioni**: restano debito, la pipeline parte solo su tua richiesta (raccomando una passata sola, prima del tag).
- **Housekeeping tuo**: pubblicare il messaggio #26; eseguire i comandi nightly; rispondere al coordinatore cloud (sblocca il contratto di H-61).

---

## 5. Mappa delle dipendenze

```
CATENA GRAFICI (cammino critico)
 Y-39a ──► [Y-39b ∥ Z-29b] ──► Z-29s (resto) ──► Y-40 ──► (Z-29fx) ──► GALLERIA completa (pausa macchina)
   ▲            ▲                    ▲
   │            │ stesso file assets/+page.svelte (Z aspetta che Y-39a entri)
   │            └ LineChart: Y-39b/F-2 e Z-29b toccano parti diverse (condizioni DV: non toccare chartInitOptions)
   Z-29s-a (backend) è indipendente: può correre durante Y-39a
 X ↔ Y: `lib/charts/chartSignalRendering.ts` (di Y). Gate `signalRendering.gate.test.ts`: la lista delle due pagine di X (dettaglio asset, dettaglio cambio) può solo accorciarsi → Y-42 (X adotta il modulo) prima di FE4/FE5a

CLOUD
 A: admin_setup_status (BR) ─► H-61 CP1 (R1 + 18ª voce fixture) ─► CP2 (L2) ─► contratto per il coordinatore cloud
 G: gallerySecurity.ts (in dev) ◄─ H aggiunge `platform.hosting_panel` (permesso di G già dato)
 H-61 tocca test di B (BACKUP-001) e Z (WAKE-025): una riga ciascuno, già approvata
 H-55 v2 (CSP) dopo H-61; tocca `app.html` → condizioni del coordinatore colori (anti-FOUC)
 Backup L3 + replica ─► decisione A (§4) ─► spike ─► eventuale 1.3.1
 R3 nightly (SQL di fusione migrazioni) ─► push del developer

NUMERI
 X: funzione a gradini (DEV) ─► MF P3 consumatore (DEV) ─► J L1b (base: serve P3 in dev: c'è)
 X Q1 ─► J R1 (rischio legge solo osservazioni)
 MF P4 ─► D-P4 ─► pavimenti, uno per lotto (N74 per ultimo)
 P4 e J CP-8/CP-9: stesso file `portfolio_service.py` → una finestra tranquilla annunciata, dopo L1b

COLORI → TAG
 D-T28 ─► T / DV / G ─► cancello colori ─► tag
 GALLERIA dopo Y-39b: N69a/b + G-28 + card verdi/rosse; mai insieme a un'altra corsia
 T2 (DEV) ─► TC-23 (J)

EMAIL / ACCOUNT
 E-25 (E) ; E-26(b): E scrive, A rivede (schema risposta, RegisterCard) dopo A-62
 N69d ◄ mappa guide di H (DEV)
```

---

## 6. Ambiente Linux

| Voce | Stato |
|---|---|
| Python 3.13.16, venv `LibreFolio-OqaCk-or` (fastapi, pytest, yfinance, pandas, numpy, scipy importano) | ✔ |
| **Nome venv nei documenti** `LibreFolio-SAUMUTtc` (Mac) | ✘ non esiste qui. Opzioni: symlink `~/.local/share/virtualenvs/LibreFolio-SAUMUTtc → LibreFolio-OqaCk-or` (consigliata, niente da riscrivere) oppure sostituire il nome nei documenti. C'è anche `LibreFolio-Vq4lufoF` (Python 3.14, vecchio path): **non usarlo** |
| Node v26.12.0, npm 12.2.1; `node_modules` presente in main e nei worktree attivi (non in `copilot-prewarm-*`); binari vitest, playwright, svelte-check, prettier, vite ✔ | ✔ (Node 26 mai provato su questo progetto: nessun campo `engines`) |
| **`node_modules` dei worktree** | ✘ scoperto il 21/10: sono quelli del Mac (`@esbuild/darwin-arm64`, `@rollup/rollup-darwin-arm64`), quindi **inutilizzabili su Linux**. Serve `npm ci` in `frontend/` di ogni worktree prima di usarlo (665 MB ciascuno). Fatto solo per `gate-coord`; Y, H, Z lo richiedono prima dell'ondata 1 |
| `theme-roles --check` | ✔ "clean" |
| Playwright 1.61, chromium-1208 installato; il progetto `mobile` forza Chromium | ✔ |
| Corsie in `/tmp/librefolio-*` | ✘ spariti (come previsto). `/tmp` è tmpfs 7,7 GB, conta come RAM. Tabella vecchia: coord. 6180, H 6181, A 6182, X 6183, W 6184, J 6185, Z 6186, B 6187, E 6188, Y 6189, MF 6190; colori: G 6153, T 6155, DV 6156 |
| Carico 1,8 su 16 core. **RAM 15 GB, 4 GB disponibili** | ⚠ all-backend a 2 worker + Playwright potrebbe stare stretto |
| Docker | ✘ **non installato**. Servono per: prova immagine, `docker stop`, H-11, spike backup |
| `.claude/` e `CLAUDE.md` | ⚠ **non tracciati** (`git status`). I figli in `LibreFolio-worktrees/` non li ereditano, e i documenti dicono che il baseline deve già contenere gli agenti. `.claude/settings.local.json` ha path del Mac: non va committato |
| Script del vecchio coordinatore (`gate_*.sh`) | ⚠ usano `/Users/ea_enel/...` e `sysctl -n vm.loadavg` (su Linux: `/proc/loadavg`). Le cartelle `files/` dei figli (H `dry/`, J `files/j/j57c`, Z `z29s-draft`, E `parked/`, Y `scripts/y39a_e2e.sh`, W `parked/`) hanno lo stesso problema |
| Primo `./dev.py test` leggero | ✘ non fatto (non lanciato in questa fase) |
| Gallery: riferimenti del 18/10 fatti sul Mac | ⚠ il rendering dei font cambia su Linux: la prossima galleria va confrontata solo con una "prima" fatta qui lo stesso giorno |
| Dati reali del developer (per P1b, J-70, misure) | ✔ **presenti** (correzione del 21/10): `LibreFolio/backend/data/prod/sqlite/app.db` (6,5 MB, 19/10) e `app.db.before-1.3-squash`, arrivati col tar dal Mac. Non li ho letti. Per qualunque prova si lavora su una **copia** (skill `real-data-copy`), mai sull'originale. La copia `/tmp/librefolio-r2-realdata` non esiste più |

---

## 7. Piano di ripresa

Regole: al massimo **3 sessioni attive**, **un solo lotto per sessione**, **un solo slot pesante alla volta** (RAM 15 GB, nessuna misura ancora). Ogni lotto parte con un criterio di fatto scritto. Tutto ciò che è committato o fuso in dev passa da te prima.

### Ondata 0 — mettere in sicurezza (coordinatore soltanto, nessun figlio)

> **Stato al 21/10 ~11:35: ondata 0 FATTA** (approvata dal developer). Copia dei diff ✔, venv + corsia + primo giro leggero ✔, baseline Linux `all-backend` su `b844f83f2` **verde 7/7 in 25 min 42 s** ✔, `.claude/` nel git (`1a0586f0b`) ✔, treno 5 in dev (J-60, pezzo di A per H-61, E galleria) con gate leggero verde ✔, contabilità committata (`208199bf6`) ✔. `dev_release2` = `208199bf6`, **non pushato** (la push è tua). L'ondata 1 aspetta il tuo via.
1. **Copia di sicurezza leggera** del lavoro sporco: per ogni worktree sporco un `git diff` + elenco dei file non tracciati in una cartella di scratch. (Il tar da 25,9 GB c'è già; questa è la copia comoda da leggere.) Nessun file viene toccato.
2. **Ambiente**: symlink del venv (§6); corsie con `db populate --force --clean`; **primo giro leggero**: `services admin-bootstrap` (310 test, senza server), `front check`, Vitest dei 4 file di Y-39a sulla copia di Y.
3. **Baseline Linux**: `all-backend --fresh-run` su `b844f83f2`, da solo, con il carico sotto controllo. Serve a sapere se "verde sul Mac" è "verde qui".
4. **`.claude/` + `CLAUDE.md` nel git** (commit locale su `dev_release2`, escluso `settings.local.json`) *prima* di creare qualunque nuovo worktree o aggiornare una base. **Serve il tuo ok.**
5. **Treno 5** (commit/merge locali, serve il tuo ok): J (commit del journal → J-60 entra) · E (commit del checkpoint traduzioni + le 2 già pronte) · A (pezzo H-61). Gate: `api sync`, `front check`, `i18n check`, `mkdocs build` stretto + `check-links`, Vitest dei file toccati. L'all-backend lo vale già il punto 3 + il giro del treno.
6. **Contabilità** (1-2 ore, solo journal): ✅ alle voci già entrate; piano generale 1.3 aggiornato con Y-39/40, Z-29b/s/d/fx, H-61, backup; backlog Z-29 corretto; Y-41/Y-42/J-70 riportati in dev.
7. **Tu**: leggi il documento di backup, rispondi a §4-A (decisione 11) e §4-B (D-T28).

### Ondata 1 — sessioni **Y, H, Z**
*Prima di partire:* `npm ci` in `frontend/` dei tre worktree (i `node_modules` del Mac non funzionano su Linux), e una corsia per sessione (Y 6189, H 6181, Z 6186, `db populate --force --clean` nella loro cartella in `/tmp`).
| Sessione | Lotto | Passi | Fatto quando | Gate prima di entrare |
|---|---|---|---|---|
| **Y** | Y-39a | (1) Y è già FROZEN: commit intermedio sul branch di Y (preserva i 11 file). (2) merge di dev in Y (0 conflitti previsti). (3) Y rilancia i 4 file di rossi, i 31 vicini, `front check`. (4) **E2E sulla base fusa**: `fx-settings`, `fx-list`, `asset-list` (~25 min, uno slot). (5) checkpoint con Y-41/42 e righe CHANGELOG | E2E verdi sulla base fusa | `core-unit`, `component-unit`, `front-asset asset-list`, `front-fx` |
| **H** | H-61 CP1 | (1) merge di dev in H (richiesto da H; 0 conflitti previsti). (2) R1 `GET /api/v1/panel/status` + rimando a `access_control.md#setup-status`. (3) 18ª voce `platform.hosting_panel` in `gallerySecurity.ts` (`prettier` + `tsc`). (4) rilancio dei 3 gruppi rossi | `api panel-status` 20/20, `hosting-panel-routes`, `instance-block` verdi; resto di CP1 verde | `api backup-panel/backup/system-wake/system`, `config-audit`, `sleep-wake-*`, core-unit |
| **Z** | Z-29s-a (backend) | scrivere il codice sui rossi esistenti; la tabella comune letta da pytest **e** Vitest | `price-query-sampling`, `signal-aggregation`, `api assets-price`, Vitest di `timeSeriesAggregation` verdi; riviste da MF e Y | idem + `api sync` senza diff |

Ferme: A, B, E, J, MF, W, X, T, DV, G, coordinatore colori.
**Entra in dev** a fine ondata: Y-39a, H-61 CP1 (+ A), Z-29s-a → **treno 6**, con `all-backend` + core + component + il E2E di Y già fatto.

### Ondata 2 — **Y, Z, H**
| Sessione | Lotto | Fatto quando |
|---|---|---|
| Y | Y-39b: anteprima come asset detail, colore della linea di base anche sulle card (rispettando le condizioni di DV) | `chart-safety-unit`, `LineChart.test.ts`, prova nei due temi cambiando tema senza ricaricare; E2E `asset-list` |
| Z | Z-29b: lista Assets con `max_points`, `sample_like`, cache ridotta, lotti che tengono insieme scheda e bersagli | Vitest con la tabella di densità; E2E `asset-list` (**dopo** quello di Y, stesso spec: slot in fila) |
| H | H-61 CP2: biglietti Ed25519, registro `jti`, codici 401, vettori di prova nella guida | ~320 casi verdi; **revisione di sicurezza** (agente `security-review`) |

### Ondata 3 — **Z, E, J**
Z-29s (rendimento mobile) · E: E-25, poi E-26(b) (con A come revisore) · J: TC-23 (a), poi L1b. **A** fa A-62 come lavoro leggero senza slot (Vitest) quando serve. Y fa solo la prova di Z-29d ridotto.

### Ondata 4 — **Y, H, X/MF a scelta**
Y-40 (tre viste, anche cambi) · H-55 v2 (CSP) · uno tra N64 (X) e K3a (W). **Poi la galleria completa** in una pausa di tutta la macchina, annunciata, rigenerando prima e dopo qui su Linux.

### Cancelli finali (dal piano 1.3, §9)
Conversione colori neutri/stati completa · run completa con coverage · galleria completa · upgrade da DB 1.2 e ripristino backup · immagine Docker (**qui impossibile**: Docker assente) · revisione di sicurezza delle superfici nuove · `mkdocs build` stretto + `check-links` · `CHANGELOG [1.3.0]` · push e tag del developer.

### Quali lotti si possono rimandare dopo la 1.3 (raccomandazione)
- **MF**: P4, i pavimenti di data, P4b, MF-P1c.
- **W**: W3, W4/CP7, W5-W6, K2b/K2c, V-37b, W-B88, W-B86 oltre i 4 plugin stabili, Crédit Agricole sui report set. *(Restano: K3a, avviso minimo di W-B87.)*
- **X**: CP5, CP7/FE4, FE5a, CP12, X-R48b (e N64 se il tempo manca).
- **E**: C-70b, E-21, E-7. **J**: CP-8/9, R1, J-70, §29 punto 1. **Z**: Z-29fx, Z-29d oltre la parte ridotta.
- **B**: Litestream/F25, B-56, B9, BZ parte 2, B5b, B-33 (B resta fermo: aspetta §4-A).
- **Restano in 1.3**: H-61 (CP1+CP2), H-55 v2, catena Y/Z, E-25, E-26, J-60 (già pronto), TC-23, A-62, N69c/d se c'è tempo, K3a, colori, cancelli.

### Quali sessioni figlie servono davvero
Le sessioni Copilot sono finite: serve **un kickoff nuovo per ognuna** (lo stato sta nel piano del loro worktree e nella loro cartella `copilot-enel/session-state/<uuid>/files/`). In ordine: **Y, H, Z** (ondata 1), poi **E, J** (ondata 3), poi **X o W** (ondata 4). B, MF, T, DV, G e il coordinatore colori restano chiusi finché non c'è una decisione (§4-A, §4-B, D-P4). A è un revisore a chiamata.

---

## 8. Rischi e cose non verificate

**Rischi**
1. **Data di rilascio**: catena grafici ~8-9 giorni + backup "tutto assieme" 4-6 settimane + cancello colori ignoto. Senza il tetto di tempo di §4-A la 1.3 non ha una data credibile.
2. **Lavoro non committato** in 5 worktree. Il tar esiste, ma è un'unica copia grande.
3. **Un merge con l'albero sporco non parte** (Y: BACKLOG e runner; E: BACKLOG e `.translate-hashes.json`). Il commit di preservazione va fatto prima. `.translate-hashes.json` può confliggere dopo.
4. **Base lontana**: Y 200 commit indietro, B 199, X 192, W 187, H 179, T 175, DV 147, Z 102, E 52, J 24, MF 22. Simulazione `git merge-tree` dei branch committati contro dev: **0 conflitti** su tutti. Il lavoro sporco non è incluso nella simulazione.
5. **Linux ≠ Mac**: Node 26, RAM, font, nessun Docker, script con path del Mac, nessuna misura dei tempi.
6. **Ricostruire il contesto dei figli**: una sessione nuova non ricorda niente. Ogni kickoff dovrà dire lavoro sporco intoccabile, corsia, piano, cartella `files/`, cosa è stato deciso dopo l'ultimo messaggio.
7. **Colori**: la 1.3 non può uscire senza la conversione di neutri e stati, e nessuno ha misurato quanto manca.
8. **Trappola del processo**: i checkpoint dei figli dicono "gate verde" su basi vecchie; il coordinatore deve rifare la validazione sulla base fusa (regola del file `release-coordinator`).

**Non verificato**
- Il contenuto del tar da 25,9 GB; che `origin/dev_release2` coincida davvero col remoto (ref locale, niente fetch).
- Se Y ha mai lanciato l'E2E dopo le 14:28 (nessun log trovato), se MF ha ricevuto il GO su P4, se J ha ricevuto L1b (sì: 14:32) o TC-23 (no).
- La percentuale reale di completezza del cancello colori.
- Il codice di bozza di H CP2 (sta nella cartella di sessione di H, fuori dal worktree).
- Se hai già eseguito i comandi della nightly e pubblicato il messaggio #26.
- Che tutti i gate verdi del Mac siano verdi su Linux (non provato).
- Il conteggio "~150 voci non marcate ✅" è una stima con script, non una revisione.
- Cloud e business plan: fuori da questa analisi. Il messaggio non risposto al coordinatore cloud è nel REPORT, non l'ho riletto nel DB.

---

## 9. Cosa ti chiedo

1. **Approvi il piano (ondata 0 → 4)** così com'è, o con quali cambi?
2. **Ok a questi atti locali** dell'ondata 0: symlink del venv; commit di `.claude/` + `CLAUDE.md` su `dev_release2`; treno 5 (J, E, A).
3. **Due decisioni che sbloccano tutto**: backup (§4-A, decisione 11) e colori (D-T28).
4. Cosa metti **dopo la 1.3** tra quelli che ho proposto (§7).

Non avvio nulla finché non mi dai il via.
