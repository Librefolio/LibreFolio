# B · turno 1 — analisi del passo B1 (busta L3), 22/10/2026

> **SUPERATA** il 22/10 pomeriggio da `BACKUP-decisioni-20261022.md` §10. Il developer ha scelto una terza via:
> il `.lfbk` v1 con una password casuale, la password cifrata con `pyrage`, i due file in un `.tar`. Le varianti (a) e
> (b) qui sotto cadono. Il contratto nuovo è `LibreFolio_prj/BACKUP-contratto-L3.md`.

Sessione figlia B, Opus. Worktree `e-alfy-miniature-telegram`, HEAD `c042f2481` = `dev_release2` (verificato), albero
pulito. **Nessun file del repo toccato.** Solo letture, più una prova di `cryptography` in una cartella temporanea
(risultati in §1.4).

Letto: `envelope.py` (320 righe), gli usi della busta (`restore_jobs.py:208, 237-275`, `staging.py:311-385`,
`jobs.py:42, 155-157`, `job_views.py:14, 116`, `backup_cli.py` ×6), `config/hosting_panel.py:85-115` (il formato delle
chiavi del pannello), `PIANO-backup-L3.md`, `BACKUP-decisioni-20261022.md`, `PIANO-ondata4.md` (domande 3-8),
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

---

## 1. Le due varianti a confronto

### 1.1 Cosa sono, in una riga

- **(a) `.lfbk` versione 2** (`PIANO-backup-L3.md` §3.1): la busta di oggi più 96 byte di intestazione (`kid`, `E`, `W`).
  X25519 + HKDF + AES-256-GCM per chiudere una chiave del file di 32 byte; i blocchi sono quelli di oggi (AES-GCM, 1 MiB).
  Formato nostro.
- **(b) `age` v1** (spec C2SP `age-encryption.org/v1`): scriviamo e leggiamo il formato standard in Python con
  `cryptography`: intestazione di testo, un destinatario `X25519`, una MAC dell'intestazione, poi i blocchi
  ChaCha20-Poly1305 da 64 KiB. La chiave del file è di **16 byte**. Un file nostro si apre con il comando `age` e
  viceversa.

Le due varianti soddisfano il requisito del coordinatore cloud: **dall'intestazione si ricava solo la chiave del file**.
Con (a) bastano i primi 148 byte; con (b) l'intestazione di testo, 168 byte nel nostro caso, che finisce alla riga `---`.
Il coordinatore non legge mai i blocchi e non vede mai byte in chiaro.

### 1.2 Tabella

| | (a) `.lfbk` v2 | (b) `age` v1 |
|---|---|---|
| **Righe di prodotto (stima)** | ~130 in `envelope.py` (intestazione v2 ~40, sigillo ~35, apertura con la privata ~25, apertura con la chiave del file ~10, `kid` e controlli ~20) | ~300 in un modulo nuovo `instance_backup/age_envelope.py`: lettore rigoroso dell'intestazione ~80, bech32 ~45, destinatario X25519 ~30, MAC ~10, flusso ChaCha20 ~50 (riusa `_chunks` e `_NewFile` di oggi), chiavi `age1…`/`AGE-SECRET-KEY-1…` ~30, apertura con la chiave del file ~15, errori ~40 |
| **Smistamento fuori dalla busta** | quasi nulla: `is_envelope` vede `LFBK`, la versione la smista `envelope.py` | un `envelope_kind(path) → "lfbk" \| "age" \| None` al posto di `is_envelope` in 6 punti (`restore_jobs` ×2, `staging` ×1, `backup_cli` ×3) più il suffisso in `jobs.py` e `job_views.py` |
| **Test** | ~20 casi nostri: vettori, chiave sbagliata, intestazione manomessa, `S` zero, limiti, v1 ancora leggibile, CLI | gli stessi ~20 **più i vettori ufficiali**: dei ~147 file C2SP/CCTV ne valgono per noi **~66** (14 `x25519*`, ~28 `stream*`, `stanza*`, `hmac*`, `header*`, `version_unsupported`, `empty`), ciascuno provato **due volte** (con l'identità e con la sua `file key`) ≈ **130 casi**; più ~10 vettori bech32 di BIP-173; più 2 prove con il comando `age` (il nostro file aperto da `age -d`, un file di `age -r` aperto da noi) |
| **Chi verifica che è giusto** | solo noi: i vettori li genera lo stesso codice che li legge (prova circolare). Il coordinatore cloud li riscrive dalla nostra specifica | i vettori e il comando `age` vengono da fuori: un errore nostro diventa un rosso. **Anche il coordinatore cloud prova il suo codice sui vettori ufficiali**, non sui nostri |
| **Chi può aprire un backup senza LibreFolio** | nessuno: serve la nostra CLI o lo script del coordinatore | chiunque abbia la privata: `age -d -i chiave.txt backup.zip.age > backup.zip` (Arch, Debian, Ubuntu, brew, Windows) |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
| **`kid` nell'intestazione** | sì (`SHA-256(P)[:16]`) | **no**: `age` non dice il destinatario (scelta del formato). Il `kid` va nella vista del lavoro (`sealed_kid`); il coordinatore prova «è dell'istanza giusta» aprendo la chiave del file con la privata, una prova **più forte** del confronto di un'etichetta (§2.5) |
| **Chiave del file sulla rotta** | 32 byte, 43 caratteri base64url | 16 byte, **22 caratteri** base64url |
| **Variabile `LIBREFOLIO_BACKUP_PUBLIC_KEY`** | 43 caratteri base64url, come le chiavi del pannello | consiglio `age1…` (62 caratteri bech32), quello che stampa `age-keygen` |
| **Busta con password di oggi (v1)** | intatta, byte per byte | intatta, byte per byte (non la tocca nessuno) |
| **Più destinatari dopo** («pannello + password del cliente», decisioni §4) | una v3 nostra, libera | `age` ha più destinatari X25519, ma **vieta scrypt (password) insieme ad altri**: «pannello + password» non si fa; «pannello + chiave del cliente» sì |
| **Post-quantum dopo** | da progettare | `age` ha già il destinatario ibrido `mlkem768x25519` (18 vettori `hybrid*`): lo si aggiunge quando `cryptography` lo espone |
| **Dipendenze** | nessuna (`cryptography`) | **nessuna** (`cryptography`: X25519, HKDF, HMAC, ChaCha20Poly1305). La domanda 3 del piano dice «aggiungere una dipendenza»: **non serve**. Il comando `age` serve **solo ai test** |
| **Rischi principali** | formato fatto in casa, nessun riscontro esterno; più lavoro per la revisione SEC | lettore dell'intestazione di testo (grammatica rigorosa: base64 canonico, righe da 64, MAC) = superficie d'attacco nuova, **coperta però riga per riga dai ~40 vettori `stanza/header/hmac/x25519`**; due formati nel codice invece di uno; bech32 da scrivere; chiave del file a 128 bit (scelta standard di `age`) |
| **Giorni** (B1 + B2) | 2-3 + 3-4 | 2-3 + **4-5** (+1 per lettore rigoroso, bech32, banco dei vettori C2SP) |

### 1.3 Il mio consiglio: **(b)**, come il coordinatore

Il motivo più forte non è «è uno standard». È **chi controlla il nostro lavoro**. Con (a) l'unico riscontro della
crittografia sono vettori che produciamo noi stessi. Con (b) lo sono ~66 vettori ufficiali e un programma scritto da
altri. Il costo è circa un giorno in più e un modulo di ~300 righe invece di ~130.

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

Cosa si perde: il `kid` dentro il file (vedi §2.5: si recupera meglio) e la «password + pannello» nella stessa busta
in futuro.

**La proposta (a) è comunque solida**: l'ho riletta e non ha errori (nonce zero lecito su `K_w` nuova, `aad` che copre
`kid` ed `E`, intestazione intera come `aad` dei blocchi, `S` zero già rifiutata da `cryptography`). Se il developer
sceglie (a), farei due ritocchi:

- un layout v2 proprio, senza i 41 byte di campi scrypt messi a zero;
- il controllo della chiave del file all'apertura: oggi si accorgerebbe solo al primo blocco, cioè dopo la copia su
  disco; meglio un controllo prima.

### 1.4 Misure fatte (scratchpad, `cryptography` 50.0.2 del venv condiviso)

- `X25519.exchange` con la pubblica tutta zero o di ordine basso → `ValueError` (già rifiutata dalla libreria: un test
  la fissa comunque).
- Velocità su 200 MB: AES-GCM 1 MiB ≈ 950 MB/s, AES-GCM 64 KiB ≈ 3,2 GB/s, ChaCha20-Poly1305 64 KiB ≈ 1,9 GB/s. Un
  backup da 500 MB si cifra in meno di mezzo secondo con l'una o con l'altra: **la velocità non decide**.
- Sovraccarico di (b): 168 byte di intestazione + 16 di nonce + 16 di tag ogni 64 KiB → 128 KB su 500 MB (0,025 %).
- Comando `age`: **non installato** su questa macchina (`which age` vuoto). Per la prova di interoperabilità serve
  `pacman -S age` (lo fa il developer: alle sessioni è vietato installare) e `apt-get install age` nella CI.
- Vettori C2SP/CCTV `age/testdata`: ~147 file, licenza a scelta 0BSD / CC0 / Unlicense (si copiano nel repo senza
  attribuzione). Ogni file dice `expect`, `payload` (sha256 del testo), `identity` e **`file key`**: provano
  direttamente anche l'apertura «con la sola chiave del file», che è il cuore del nostro ripristino.

---

## 2. La specifica consigliata, per intero (bozza di (b), in inglese come andrà nella doc)

> Diventerà `mkdocs_src/docs/developer/backend/backup_envelope.md` (la doc per sviluppatori del backend usa `.md` senza
> suffisso di lingua, es. `developer/backend/email.md`; la riga di navigazione in `mkdocs.yml` è un file condiviso:
> la propongo al coordinatore). Il contratto delle rotte e del modo (`PIANO-backup-L3.md` §3.5-3.6, domande 4-6 già
> approvate) non dipende dal formato: lo scrivo nel B1 vero e proprio, con la sola differenza di `file_key` (22
> caratteri con (b)).

### 2.1 Scope

A **sealed backup** is a backup archive (`.zip`) encrypted to one X25519 public key so that the instance that made it
cannot read it back. The file is a standard **age v1** file (`age-encryption.org/v1`, C2SP), binary (never ASCII
armored), with exactly one `X25519` recipient stanza. LibreFolio implements the format itself with `cryptography`
(no new dependency); conformance is proven by the C2SP/CCTV vectors and by the `age` reference tool.

The password envelope (`.lfbk`, `LFBK` version 1, scrypt + AES-256-GCM) is **unchanged, byte for byte**. The two are told
apart by their first bytes: `LFBK` or `age-encryption.org/v1\n`.

### 2.2 Keys

- **Recipient (public key)**: 32-byte X25519 public key, written as **`age1…`** — Bech32 (BIP-173 checksum, not
  Bech32m), HRP `age`, lowercase, 62 characters. Read from `LIBREFOLIO_BACKUP_PUBLIC_KEY`. Not a secret: no `_FILE`
  variant. One key in 1.3.
- **Identity (private key)**: 32-byte X25519 scalar, written as **`AGE-SECRET-KEY-1…`** — Bech32, HRP
  `AGE-SECRET-KEY-`, uppercase. Never in the instance's environment, never in a log, a `repr`, an error message.
  Files written by `backup keygen` use the `age-keygen` layout (`# created: …`, `# public key: age1…`, then the key
  line), mode `0600`, never overwritten; `age-keygen` files are accepted as they are.
- **Key id** `kid` = `hex(SHA-256(raw 32-byte public key))[:32]` (16 bytes). **Not in the file** (age names no
  recipient): it is reported by the job view (`sealed_kid`) and stored by the coordinator next to the object.
- Any X25519 key pair works.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- **Fail closed**: a `LIBREFOLIO_BACKUP_PUBLIC_KEY` that is set but not a valid `age1…` key → startup check
  `backup.public_key` in error, and `POST /api/v1/backup/panel/jobs` → `503 backup_panel_unavailable`. Never a clear zip.

### 2.3 File layout (what LibreFolio writes)

```
age-encryption.org/v1\n
-> X25519 <b64(E)>\n                 # E: ephemeral share, 32 bytes → 43 chars
<b64(W)>\n                           # W: wrapped file key, 32 bytes → 43 chars (one short line)
--- <b64(MAC)>\n                     # MAC: 32 bytes → 43 chars
<payload nonce: 16 bytes>
<STREAM chunks>
```

`b64` is standard base64 (`+/`), **no padding, canonical** (age's encoding). The header is 168 bytes here.
The file name is `librefolio-backup-YYYYMMDD-HHMMSS.zip.age`, media type `application/octet-stream`.

### 2.4 Algorithms (per the age v1 spec; constants are ASCII)

```
file_key  = 16 random bytes
e         = random X25519 scalar;  E = X25519(e, 9)
S         = X25519(e, P)                       # all-zero S → refuse (cryptography raises ValueError)
wrap_key  = HKDF-SHA256(ikm=S, salt=E || P, info="age-encryption.org/v1/X25519", L=32)
W         = ChaCha20-Poly1305(wrap_key).encrypt(nonce=12 zero bytes, file_key, aad="")          # 32 bytes
mac_key   = HKDF-SHA256(ikm=file_key, salt="", info="header", L=32)
MAC       = HMAC-SHA256(mac_key, header bytes up to and including "---")                       # the space and MAC excluded
nonce     = 16 random bytes
pay_key   = HKDF-SHA256(ikm=file_key, salt=nonce, info="payload", L=32)
chunk_i   = ChaCha20-Poly1305(pay_key).encrypt(i as 11-byte big-endian || flag, plaintext_i, aad="")
            # plaintext_i: 64 KiB; flag 0x01 on the last chunk only; the last chunk may be full;
            # it is empty only when the whole payload is empty (one empty chunk)
```

The chunking is exactly today's `_chunks` (one chunk read ahead, the last one flagged, one empty chunk for an empty
file).

### 2.5 Three ways to open

1. **With the identity** (the cloud coordinator, the CLI `--private-key-file`): parse the header → for each `X25519`
   stanza: `S = X25519(s, E)`, `wrap_key` with `salt = E || P(s)`, try to decrypt `W` (a failed tag means «not this
   stanza», not an error) → `file_key` → **verify the MAC** → done. No stanza opens → `wrong_private_key`.
   This is also the coordinator's «the right instance» check (architecture §6): it proves the file opens with that
   instance's key, which is stronger than comparing a label.
2. **With the file key** (the restored instance, the panel restore route, the CLI `--file-key-file`): parse the header
   → `mac_key` from the given key → MAC mismatch → **`wrong_file_key` at once**, before any payload byte is read or any
   disk space is used → read the nonce → `pay_key` → decrypt the chunks. The instance needs neither `kid` nor `P`.
3. **With the reference tool**: `age -d -i key.txt backup.zip.age > backup.zip`.

**What the coordinator sends to the new machine**: the file, still encrypted, and `file_key` as base64url without
padding (**22 characters**). The private key never leaves the coordinator.

### 2.6 Reader limits and strictness (refused before any work)

- Header at most **16 KiB**; at most **32 stanzas**; each argument 1..64 visible ASCII characters; body lines exactly 64
  characters except a shorter final one; base64 canonical (no padding, no trailing bits); `LF` line ends only (no `CR`).
- An `X25519` stanza has exactly one argument, a 32-byte share, and a 32-byte body; otherwise `header failure`.
- Unknown stanza types are ignored (age rule) on the identity path; any grammatically valid header is accepted on the
  file-key path.
- An `scrypt` stanza (a password age file) → `envelope_unsupported` (LibreFolio password backups are `.lfbk`).
- ASCII armor (`-----BEGIN AGE ENCRYPTED FILE-----`) → `envelope_unsupported`.
- Payload: a missing or short nonce, a chunk shorter than its tag, no final chunk, data after the final chunk, an empty
  final chunk after a full one, a failed tag → `envelope_damaged`; nothing is left at the destination (today's `.part`
  rule).
- Upload kind: `kind` grows a third value, **`sealed`**, so that the admin UI does not ask a password for a file that
  only a key opens (see question Q5).

### 2.7 Error codes

| Code | When |
|---|---|
| `file_key_required` | a sealed file without `file_key` (panel route, `start_check`) |
| `file_key_invalid` | `file_key` is not 22 base64url characters / 16 bytes |
| `wrong_file_key` | the header MAC does not verify with the given key (the upload stays, for another attempt) |
| `wrong_private_key` | CLI only: no stanza opens with the given identity |
| `envelope_damaged` | header grammar, MAC after a good unwrap, or any payload failure |
| `envelope_unsupported` | armor, an scrypt-only file, a version line other than `age-encryption.org/v1` |

### 2.8 Test vectors

1. **C2SP/CCTV `age/testdata`**, copied into `backend/test_scripts/test_services/fixtures/age_cctv/` (0BSD/CC0) with a
   README naming the upstream commit. All ~147 files are present; the harness runs ~66 of them (`x25519*`, `stream*`,
   `stanza*`, `hmac*`, `header*`, `version_unsupported`, `empty`) on both the identity path and the `file key` path,
   and checks `expect` and the `payload` hash. It skips `armor*`, `scrypt*` and `hybrid*` and names each skip with its
   reason.
2. **Our vectors** `backup_sealed_vectors.json` (same folder; copied as is by the cloud coordinator). They are made by
   a script that uses `cryptography` only (`scripts/…/gen_backup_vectors.py`) and contain:
   - a test identity and its recipient (marked TEST ONLY), and the `kid`;
   - a fixed `e`, `file_key` and payload nonce; a 3-chunk plaintext, one of them full, and a short text;
   - the expected file in hex, its `sha256`, `W`, the MAC and `file_key` in base64url;
   - the negatives: a wrong file key (`wrong_file_key`), an edited header (`envelope_damaged`), a cut payload;
   - one **v1 password `.lfbk`**, which must stay readable.
3. **Interop** (needs `age` on the PATH): our file → `age -d -i` → same bytes; `age -r age1…` → our file-key path
   and identity path → same bytes. Required in CI; locally a visible SKIP when `age` is missing.

### 2.9 Steps for the cloud coordinator (in clear)

1. Read the object's first 16 KiB.
2. Parse the header as in §2.6.
3. Find the `X25519` stanza and compute `S = X25519(s_i, E)`.
4. Derive `wrap_key` with `salt = E || P_i` and the info string of §2.4.
5. Decrypt `W` with ChaCha20-Poly1305 and a zero nonce → `file_key` (16 bytes).
6. Verify the MAC.
7. Send `file_key` as 22 base64url characters together with the encrypted file.

Test this code on the CCTV `x25519*` vectors, which give `identity` and the expected `file key`, and on our JSON.

---

## 3. Cosa faccio dopo la scelta (indipendente dal formato o quasi)

Parti che **non dipendono** dal formato. Le posso fare appena arriva il via al B1, anche prima della scelta:

- Il contratto delle rotte del pannello e del modo «ripristino in corso» (§3.5-3.6 del piano), con le domande 4-6 già
  approvate. Cambia una sola cosa a seconda del formato: la lunghezza di `file_key`.
- `file_sha256` e `sealed_kid` nella vista del lavoro (B2, `job_views.py`).
- I due avvisi del rapporto di stage, con la parte UI (B3).
- La doc self-hosted «Backups with backrest or restic» (B4).

Dopo la scelta:

- **(b)**: la specifica in inglese nel repo, lo script dei vettori, la copia dei vettori CCTV (serve il tuo ok a
  scaricarli da GitHub: ~147 file piccoli, alcuni compressi), le domande sotto.
- **(a)**: la specifica del §3.1 con i due ritocchi, lo script dei vettori.

## 4. Domande per il developer

- **Q1 (decide tutto il B1)**: formato della busta a chiave pubblica: **(b) `age` v1**, consigliato, oppure (a) `.lfbk` v2.
- **Q2 (se (b))**: la variabile in formato `age1…` (consigliato: si incolla quello che stampa `age-keygen`) oppure 43
  caratteri base64url come le chiavi del pannello.
- **Q3 (se (b))**: nome del file `…zip.age` (consigliato: dice cosa c'è dentro e cosa lo apre) oppure `.lfbk` anche per
  questi.
- **Q4**: il comando `age` per la prova di interoperabilità. In locale lo installi tu (`sudo pacman -S age`): alle
  sessioni è vietato. Nella CI la prova è obbligatoria. In locale, se `age` manca, la prova si salta in modo visibile.
  Va bene così?
- **Q5**: il caricamento di un file sigillato nella UI dell'admin. Consiglio: `kind: "sealed"` e un messaggio
  «questo backup si apre solo dal pannello del fornitore o dalla CLI con la chiave privata», senza chiedere la password.
  Alternativa: la UI accetta anche un file con la chiave privata (lo sconsiglio: porta la privata nel browser).
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
