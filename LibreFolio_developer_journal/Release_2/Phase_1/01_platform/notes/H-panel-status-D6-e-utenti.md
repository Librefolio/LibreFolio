# H — `panel/status`: `users_over_limit` e `instance_key` (D6) — analisi, nessun codice (26/10/2026)

Letto in sola lettura nel ramo `e-alfy-h-piattaforma` (`88459a302` + H5-5, H5-6): `schemas/hosting_panel.py`, `api/v1/panel.py`,
`platform/instance_key.py`, `plugin_settings/crypto.py`, `plugin_secrets_check.py`, `config_audit.py`, `api/v1/system/wake.py`,
`api/v1/instance_block.py`, il contratto L3 (§D6) e il contratto istanza-coordinatore. Il mio diario ha H-3 e P24 alle righe 3419 e 6015.

## Il riassunto, per il developer

- **`users_over_limit`**: piccolo, lo faccio appena A5-7 mette `over_limit_state`. Un lotto di mezza giornata (campo, test, doc).
- **D6 senza H-3: sì, si può.** H-3/P24 non c'entra: riguarda il *generare* una chiave nuova quando il file manca (self-hosted). Nel managed la chiave
  è sempre configurata e non si genera mai. E H-3 non dà quello che D6 chiede: **un riferimento con cui confrontare la chiave**. Oggi nessuno sa quale
  chiave «dovrebbe» essere: l'istanza ha solo quella che le danno.
- Il riferimento si può avere in **tre modi**; consiglio il **secondo**, con una rete di sicurezza presa dal primo (sotto).
- **Costo**: un lotto medio, come H5-4 con più test, solo per «il campo + la protezione dei backup». Un secondo lotto, come H5-3, per «l'istanza non serve i dati»
  (la parte di D6 che il developer ha confermato il 23/10): ma **consiglio di non farla** (motivo sotto).
- **Rischio principale**: un falso `mismatch` ferma i backup notturni di un'istanza sana, in silenzio. Si cura con una regola: `mismatch` solo con una prova.

## 1. `users_over_limit: bool` (R-2, lotto A5-7)

Cosa faccio quando A5-7 è nel ramo:

1. `PanelStatusResponse.users_over_limit: bool` (obbligatorio, come `users_used`; descrizione: «vero quando gli utenti attivi superano il limite valido, ad
   esempio dopo il passaggio a un piano più piccolo; un solo sì o no, mai chi»). Il valore: `user_limit_service.over_limit_state(session)` di A, non lo calcolo io.
2. `api/v1/panel.py`: una riga nella risposta (la funzione di A prende la stessa sessione di `user_usage`).
3. Le chiavi esatte: la risposta passa da **sette a otto chiavi** (nove con D6, vedi sotto). Si aggiornano insieme: `api panel-status` (41), `await-restore-mode`, il
   confronto dello schema OpenAPI, `api/index.md` («exactly seven keys»), `security.md`, `hosting_panel_api` (tabella e JSON). `api sync` dopo.
4. Ora **non c'è** `over_limit_state` nel codice (`grep` su `backend/app`): finché A5-7 non entra non scrivo il campo: un valore fisso a `false` sarebbe una bugia per il pannello, quindi aspetto.

Un dubbio piccolo: **«vale vero quando gli attivi superano il limite valido»**. `users_used` conta anche inviti vivi e attesa di verifica; `users_over_limit` guarda solo gli
attivi, come dici. Va bene: i due numeri dicono due cose diverse (posti occupati / sono troppi quelli che già usano). Lo scrivo nella descrizione del campo.

## 2. D6: `instance_key: ok | mismatch` senza H-3

### Che cosa significa «sbagliata»

L'istanza ha la chiave che le arriva (`LIBREFOLIO_INSTANCE_KEY` o `_FILE`). Una chiave **malformata** ferma già l'avvio (`config_audit.py:386`). Una chiave **valida ma diversa**
da quella con cui sono stati scritti i dati (segreti dei plugin cifrati, `key_id` per riga) fa partire l'istanza: i segreti non si leggono più, e il log lo dice solo se ce ne sono
(`platform.plugin_secrets`, H-15).
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

### Tre modi per avere il riferimento (ordine di costo)

| | Il riferimento | Dove sta | Dice `mismatch` quando | Limite |
|---|---|---|---|---|
| **R1** | i segreti già salvati (`key_id` per riga, X) | nel DB, già c'è | **nessuno** dei segreti salvati si legge con la chiave di ora | senza segreti salvati non può dire nulla; con un ripristino che ha lasciato qualche segreto illeggibile (B: `secrets_unreadable`) le righe miste non devono dare un falso `mismatch`, quindi la regola è «nessuna riga leggibile», non «una illeggibile» |
| **R2** | un **valore di controllo** della chiave (KCV): HMAC di una frase fissa con una sottochiave dedicata, `derive_key("instance.key-check.v1")` | un file nella cartella dei dati, `secrets/instance.key.check`, 0600 (la cartella `secrets/` esiste già per la chiave generata) | il valore di ora è diverso da quello scritto | alla prima volta non c'è niente da confrontare: si scrive (fiducia al primo avvio). Cura nel punto «perché non falso» sotto |
| **R3** | una variabile di configurazione `LIBREFOLIO_INSTANCE_KEY_ID`, calcolata dal coordinatore dalla sua custodia | nell'ambiente | l'impronta di ora è diversa dalla variabile | difende solo se il coordinatore la prende da un registro **diverso** dalla chiave (se la calcola dalla stessa custodia sbagliata, sbaglia in due) e chiede al cloud un lavoro e un algoritmo condiviso |

**Consiglio: R2, con R1 come guardia della prima scrittura.**

- Il file del KCV sta sul **volume dei dati**, come i dati che la chiave protegge. Un ripristino non lo tocca (la cartella `secrets/` non è mai nei backup, `ARCHIVED_FOLDERS`),
  e B ricifra comunque i segreti con la chiave di ora: quindi nessun accoppiamento con B né con X, nessuna migrazione, nessun cambio a `001`/`005`.
- Il confronto è una funzione pura di chiave e file (microsecondi), **calcolata a ogni richiesta** di `panel/status` e dei job: niente stato in memoria da invalidare (la lezione di H5-5: un
  valore letto una volta all'avvio resta vecchio).
- **Alla prima volta** (nessun file): se ci sono segreti salvati e **nessuno** si legge con la chiave di ora → `mismatch` e **non si scrive nulla** (altrimenti il file fisserebbe la chiave
  sbagliata come quella giusta); altrimenti si scrive il KCV e `ok`. Un'istanza 1.2 che passa alla 1.3 con la chiave già sbagliata ma senza segreti non si può scoprire: è il limite vero,
  e va scritto nella doc.
- **Un cambio voluto della chiave** (rotazione, «ricreare la chiave perdendo i segreti», deciso da assistenza e admin) ha bisogno di una via esplicita, altrimenti il `mismatch` non si
  chiude mai: o un comando (`./dev.py instance-key accept`, self-hosted) o, nel managed dove non c'è una shell, una variabile **per un solo avvio** (nome da decidere, ad esempio
  `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1`) che riscrive il KCV e lo dice nel log. È una scelta di prodotto, la chiede il contratto («nessuna scelta automatica»).

### Che cosa fa `mismatch` (la parte di D6 confermata il 23/10)

Il contratto dice quattro effetti. Il costo e il mio consiglio per ciascuno:

| Effetto | Costo | Consiglio |
|---|---|---|
| `panel/status` risponde con `instance_key: "ok" \| "mismatch"`, mai l'impronta | una riga nello schema e nella rotta | **sì** |
| i job di backup del pannello rifiutati con `409` (come `backup_restore_interrupted`, B-33) | un codice nuovo (`backup_instance_key_mismatch`), il controllo dopo la credenziale | **sì**: è quello che protegge le 7 copie |
| `wake-sync` non fa nulla e risponde con lo stato (come `restore_interrupted`) | un valore in più di `WakeSyncResponse.status` | **sì** (il cloud già non manda `wake-sync` in quel caso) |
| **l'istanza non serve i dati** (423 a tutti, pagina dedicata) | come H5-3: un motivo in più della guardia, la pagina e 3 chiavi × 4 lingue, i test, la doc | **no, almeno non ora** |

Perché «non serve i dati» non lo consiglio: con la chiave sbagliata i dati finanziari sono **leggibili** (sono in chiaro nel DB); si perdono solo i segreti dei plugin. Chiudere il
cliente fuori dal suo portafoglio per un segreto di un plugin è un danno più grosso del problema, e i tre effetti sopra bastano a proteggere i backup. **Ma il developer ha confermato D6
con quella frase il 23/10**: dividere D6 è una decisione sua, non mia né del coordinatore. Se la vuole intera, è un secondo lotto (come H5-3, stessa guardia e stesso tipo di test).

### Perché dovrebbe essere affidabile e che cosa può andare storto

- **Falso `mismatch` = backup fermi su un'istanza sana, in silenzio.** È il rischio peggiore, perché il cloud si fida del campo. Regole: `mismatch` solo con una **prova** (il KCV diverso,
  o segreti salvati e nessuno leggibile); mai per un errore di lettura del file (si registra un avviso e si risponde `ok`: fallire aperto, perché un file rotto non deve fermare i backup);
  la via di uscita sopra.
- **Falso `ok`**: istanza senza segreti e senza KCV (prima volta). Non c'è nulla da proteggere in quel momento; il KCV scritto subito dopo protegge da lì in avanti.
- **Più worker**: la scrittura del KCV usa lo schema già usato per `instance.key` (file temporaneo e `link`, vince il primo), quindi due worker non si pestano.
- **Riservatezza**: il KCV è l'HMAC di una frase fissa con una sottochiave: non si ricava la chiave. Il file è 0600 nella cartella 0700. La risposta dice solo `ok` o `mismatch`.
- **Il backup dell'admin dall'interfaccia** non è fermato (solo i job del pannello): l'admin vede già l'errore dei segreti nella scheda Sicurezza.

### Il lavoro, in pezzi

| Pezzo | Dove | Note |
|---|---|---|
| `platform/instance_key_check.py`: KCV, scrittura sicura, `state()` → `ok`/`mismatch` | nuovo modulo di H | funzioni pure, nessun import dei servizi di X |
| un controllo `platform.instance_key` in `config_audit`/scheda Sicurezza (+ log all'avvio) | H | 3 chiavi × 4 lingue; così anche il self-hosted lo vede |
| `PanelStatusResponse.instance_key`; `api/v1/panel.py` | H | nove chiavi (con `users_over_limit`) |
| `409 backup_instance_key_mismatch` sull'avvio del job; `wake-sync` | H (dipendenza del router) | il percorso del 409 di B-33 è il modello |
| comando/variabile per accettare un cambio voluto | H + `dev.py` (superficie condivisa) | da decidere |
| test (test-author), doc (`hosting_panel_api`, `hosting_instances`, `security.md`, `backup_moving`), `contratto-istanza` del cloud | H, cloud | il cloud toglie «D6 non ancora nel codice» |

Stima: **un lotto medio** per R2 + i tre effetti leggeri (somiglia a H5-4 più H5-5), **un secondo lotto** solo se il developer vuole anche «non serve i dati».

### Domande per il developer (solo queste)

1. D6 in due tempi: prima il campo, il 409 dei job e il `wake-sync` fermo; il «non serve i dati» dopo o mai? (consiglio: dopo o mai)
2. Come si accetta un cambio voluto della chiave nel managed? (consiglio: una variabile per un solo avvio, il coordinatore la imposta quando assistenza e admin hanno deciso)
3. Il riferimento: R2 (file nel volume, consiglio) o R3 (il coordinatore passa l'impronta)?
