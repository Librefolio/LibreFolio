# Recap — sera del 22/10/2026 (ondata 4, il developer fuori)

## 1. In breve (23/10, 14:30) — ONDATA 4 CHIUSA

- **Treno 9** in `dev_release2` (`77986b11f`, 23/10 mattina) e **treno 10** in `dev_release2` (`61a6c828b`, 23/10
  14:2x): backup L3 (B), H-62 con D7, B-33, revisione di sicurezza curata, lotto di A (contatori email, tempo vero,
  riquadro giallo, tooltip). Gate completo verde su entrambi. Locale, non pushato (origin è a `8484d7c5f`, già in `dev`
  con la PR #59 e sul server come `v1.2.1-3007-g96c7fe7fe`).
- Venv condiviso allineato al lock nuovo (FastAPI 0.159, SQLAlchemy 2.1.6, SQLModel 0.0.48, Pydantic 2.14, pyrage 1.4.0).
- **Ondata 5**: brief in `../ondata5/BRIEF-ondata5.md`, domande tutte risposte, aggiunte dal feedback della checklist e i
  lotti di documentazione: aspetta il via del developer. Sessioni e worktree tenuti per riusarli (developer).

## 2. Partenza

- 18:25, base `dev_release2` = `8484d7c5f` (backlog con le risposte sulle 26 voci).
- Le tue indicazioni: continua e fai lavorare gli agenti, **finisci l'ondata 4 se riesci, non avviare la prossima,
  aspettami in ogni caso**; le ultime domande del backlog le riprendiamo dopo.
- Limiti, come sempre: commit solo sui rami dei lotti e sul candidato; `dev_release2` non si muove; niente push; niente
  sessioni nuove (non servono: l'ondata 4 ha le sue).

## 3. Avanzamento per sessione

| Sessione | Lotto dell'ondata 4 | Stato | Commit sul ramo (da `295a09c86`) |
|---|---|---|---|
| H | H-55 + R4 + R5, H-18, poi **H-62** | H-55/R5/H-18 nel candidato; **H-62 finito** (con i ganci di B), in revisione di sicurezza | `900a7acf2` `ace89e254` `424a5a724` `706a6fa2f` `02df25227` |
| B | Backup L3 | ✅ finito (CP1, CP2, B4, B-33, B5, SEC-1…5) | `a7237f95d` `bbfe61a53` `77e28a330` `8d9f41478` `533fbe8c1` (uniti nel ramo di H) |
| Y | Y-41 schede, #49 | ✅ finito | `70bac0a91` `63f8a295d` |
| X | Y-41 dettagli, N64b/c/d, #50 | ✅ finito | `a231f4e94` `879ccb8fd` |
| Z | testid + E2E Z-29d | ✅ finito | `df6db2316` `f1ff33539` |
| W | Q-N78-1k, beta/RowSkips, W-BS, rifiuto coppia di rettifiche | ✅ finito | `a76435188` `dd211d0bc` `55060d489` `4a6ebceb5` |
| A | N69c/d + E2E esclusivo | ✅ finito (UserRow aspetta E7-Q4/Q5) | `9dfa84a10` `5ca14b813` |
| J | J-68, J-71, J-62, B12, J-8 | ✅ finito (R1 in ondata 5) | `f15149029` `ea5049410` `b5983a8ea` `8505761da` `a90016363` |
| D | aggiornamento completo delle dipendenze Python | ✅ finito | `ad9f4a8bb` |
| MF | revisione della cura di W | ✖️ superata (rifiuto in ingresso al posto del calcolo) | `0f36a4508` `101f04bc2` |
| E | i 5 testi | ⏸️ aspetta le tue risposte | — |

## 4. Diario

- 18:23 — B: CP2 verificato (89 + 272 + 225 + 3 + 176 test verdi) e committato in due commit.
- 18:25 — backlog con le risposte sulle 26 voci committato in `dev_release2` (`8484d7c5f`, locale).
- 18:28 — MF: nota del piano chiusa (`101f04bc2`).
- 18:2x — a H i nomi dei ganci di B; a B il lavoro successivo.
- 18:28–18:30 — candidato del treno 9: 9 merge; conflitti solo nel backlog (X, J, W), risolti tenendo i ✅ dei lotti e le righe
  della classificazione delle voci vicine. Un mio errore: il primo merge di W era stato committato con i segni di
  conflitto dentro; il candidato è solo mio e non pubblicato, l'ho riportato al merge di J e rifatto pulito.
- 18:30 — gate del treno 9 avviato; alle 18:43 è in coda sul lock dietro ai test di H (è normale: un comando pesante alla volta).
- 19:3x — H: CHECKPOINT READY H-62 (53 file; 169 test backend nuovi, 4 «Needs B» in rosso fino ai ganci di B). Verifica
  del coordinatore in coda sul lock; poi commit, merge di B nel ramo di H, H collega i ganci.
- 20:45 — gate del treno 9 finito: **tutto verde** (api sync senza differenze, colori, front check 0/0, i18n, orfani,
  all-backend, all-frontend, check-links) **tranne `mkdocs build` strict**: un avviso, il link `settings.md#registration` di
  `users.en.md` (A, N69c) verso un'ancora che esiste solo in inglese. Rimandato ad A.
- 20:5x — H-62 verificato (tutto verde tranne i 4 «Needs B» attesi; Vitest 193/193) e committato `38de218b6`; ramo di B unito
  in quello di H `d40e8f11e` senza conflitti. H collega i ganci.
- 21:0x — A: link senza l'ancora non tradotta (`926ec30cf`); rientrato nel candidato → **`8b0375db1`**, `mkdocs build` strict e
  `check-links` verdi: **treno 9 tutto verde**. H: ganci di B collegati, verificati e committati (`81e5dcbb6`); H ha finito
  l'ondata 4. Partita la revisione di sicurezza indipendente (Opus, sola lettura) su backup + H-62.
- 21:1x — revisione di sicurezza (Opus, sola lettura) finita: **nessun HIGH o MEDIUM**; 6 LOW e 5 INFO
  (`SEC-review-backup-H62.md`). LOW smistati: H (magic `LFBK` prima di scrivere, gara su stage ripetuto, secondo SIGTERM,
  doc del 503), B dopo il lavoro in corso (zip in chiaro tolto subito, lettore `.tar` che accetta dati dopo la fine,
  caricamento buono cancellato troppo presto, file orfano, permessi della chiave della CLI).
- 21:33 — H: cure della revisione (punti 3, 5, 6, 9) verificate e committate `c12f36c78` (panel-restore 123, hosting-panel-routes 39,
  await-restore-mode 27, backup-restore 166). B: checkpoint B-33 + SEC-1 + B4 + SEC-2 + B5 in verifica, poi 6 commit in fila.
  Deciso da me: `GET /backup/restore/status` con lo stato illeggibile resta 500 ma con il codice `restore_state_unreadable`
  (come il pannello e il contratto §5), non il 409 proposto da B.
- 21:38 — B: 6 commit (`129ed0f8c` B-33, `5982b161d` SEC-1, `fdcfeeb5e` B4, `7b194ecd5` SEC-2, `afc56ac01` B5, `a7cade9bd`
  piano), 11 categorie verdi + doc. 21:4x — B unito di nuovo in H (`03cbca6c6`): **round trip L3 verde** (3/3). In parallelo:
  H fa il blocco d'avvio di B-33, B i punti 3-5 della revisione e il codice `restore_state_unreadable`.
- 22:07 — B: SEC-3/4/5 e il 500 `restore_state_unreadable` con `reason` verificati e committati `3334f69ee` (8 categorie +
  Vitest 1143 verdi). **B ha finito l'ondata 4.** Resta: H chiude il blocco d'avvio di B-33, poi unisco B in H e H adatta
  la rotta del pannello alle nuove firme; poi il candidato del treno 10 (backup).
- 22:07 → 09:40 — notte: H in attesa del suo agente della doc, rimasto appeso (lock sparito da `/tmp`, nessun processo). Sbloccato al mattino.
- 18:3x — coordinatore cloud: posizione su H-3 e B-33 (niente ripristino automatico per B-33: contraddice la regola «server
  raggiungibile, niente ripristino»). Scritte nel contratto L3 come D6/D7 «proposta». Contratto corretto: lo scarico è
  `…/jobs/{job_id}/file`, non `…/download` (il codice aveva ragione).
- 18:4x — al cloud avevo detto per errore che il prodotto non crea un admin dalle variabili: lo crea (F02). Corretto.

## 5. Treno / candidato

- `train9-candidate` = **`8b0375db1`** (era `1f532df0b` + la correzione di A), base `8484d7c5f`. **Verde.** Gate (18:30–20:45): verde tranne `mkdocs build` strict (1 avviso, A, ancora `#registration` solo in inglese): A cura,
  poi rifaccio solo la build della doc sul candidato (log `gate-train9/summary.txt`).

## 6. Già deciso da me (puoi cambiarlo)

- **B12**: la classificazione l'aveva scartata («mai visto»), ma J l'aveva già curata nell'ondata 4 (`8505761da`: una
  vendita futura consumava un lotto ancora aperto oggi). Tengo la cura, il backlog lo dice.
- **Gate col venv di D**: il candidato porta il nuovo lock; il venv condiviso si allinea solo dopo il tuo via sul treno.
- **Revisione MF della cura di W**: superata dalla tua decisione (rifiuto in ingresso); P4 e floor restano in ondata 5.
- **B-33**: B fa adesso la parte che non tocca i file di H; il blocco dell'avvio e la pagina dopo il merge di H-62.

- **Codice d'errore dello stato illeggibile** (admin): 500 `restore_state_unreadable` con `reason`, come il pannello e il
  contratto, invece del 409 proposto da B; il frontend dell'admin lo riconosce e smette di interrogare all'infinito.

## 7. Domande pendenti

1. **I 5 testi di E** (dal piano dell'ondata 4, §9; senza risposta resta tutto com'è, con i testi «consigliati»):
   E-26-q1 (testo A con il motivo, consigliato, o B corto); E-26-q2 (riquadro verde, consigliato, o giallo); E-25-q1 (senza
   «Torna all'accesso», consigliato, o con); E7-Q4 (hover + pannello, consigliato, solo hover, solo pannello); E7-Q5 (testi
   fr/es del badge).
2. **Coordinatore cloud**: ha risposto, vedi 3 e 4.
3. **D6 e D7 del contratto L3** (casi hosted, proposte del cloud, in `BACKUP-contratto-L3.md` §10): D6 chiave che non
   corrisponde → istanza ferma, `instance_key: mismatch` in `panel/status`, backup del pannello rifiutati, scelta a mano;
   D7 ripristino illeggibile → istanza ferma, avviso, **nessun ripristino automatico**, scelta a mano con l'admin
   (alternativa: automatico con freno). Consiglio: sì a tutte e due come proposte.
4. **Proteggere l'admin creato dalle variabili nel managed** (chiesto dal cloud): l'admin F02 esiste (creato in attesa da
   `bootstrap_admin_service.py`); l'aggancio `user_service.account_protection` e il 409 `ACCOUNT_PROTECTED` sono pronti, ma
   oggi non proteggono nessuno. Vuoi che nel profilo `managed` l'admin titolare non si possa eliminare, disattivare o
   declassare? (Consiglio: sì, è un lotto piccolo; la CLI resta sopra la protezione.)
5. **Due note della revisione di sicurezza** (nessuna cura proposta): nel modo «ripristino in corso» il pannello può
   annullare anche un ripristino confermato dalla CLI; il modo si fida solo di `LIBREFOLIO_AWAIT_RESTORE` (nessun controllo
   che il volume sia vuoto). Consiglio: lasciare così, è il disegno concordato con il cloud.
6. **Le ultime domande del backlog** (ondata 6: C-42/W-B46, X-R78, Y-32, G-14, Y-15, M-22): quando vuoi.

## 8. Seguiti da registrare

- A: la patch di `_consolidate.py` per `exclusive_because` con più worker Playwright (salvata, non provata con 4 worker).
- X-50t: traduzione della pagina Yahoo «Fund details» (debito di traduzione, a fine release).
- Il blocco in testa al backlog conta ancora come «ondata 6» alcune voci che J ha chiuso: da riallineare al prossimo
  riordino.

## 9. Consumi

| Ora | 5 ore | Settimana | Commento |
|---|---|---|---|
| 18:30 | 26 % | 17 % | ampio margine; solo B e H lavorano, più il gate |
| 23/10 09:40 | 0 % (finestra nuova) | 20 % | la notte ha consumato poco: solo B, H, il gate e la revisione |
