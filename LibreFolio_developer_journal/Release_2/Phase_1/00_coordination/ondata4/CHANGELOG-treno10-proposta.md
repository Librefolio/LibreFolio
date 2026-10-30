# CHANGELOG del treno 10 — proposta (da approvare, non ancora nel file)

Righe in inglese per il capitolo `## [Unreleased]`, scritte dalle proposte di B, H e A e dai messaggi di commit. Restano
fuori le correzioni di cose non ancora rilasciate (per esempio lo zip in chiaro durante il sigillo, SEC-1…5) e il lavoro
interno.

## ✨ Added

- **Sealed nightly backups.** With `LIBREFOLIO_BACKUP_RECIPIENTS` (one or two `age1…` public keys), a backup is a `.tar`
  holding the encrypted archive, its random password encrypted with age for those keys, and a plain manifest: the instance
  itself cannot open it again. `./dev.py backup keygen` makes a key pair; the guide shows how to open a sealed backup by
  hand with `age`. (B, L3)
- **Hosting providers can restore a nightly backup onto a new machine.** With `LIBREFOLIO_AWAIT_RESTORE` a new instance
  waits for its data instead of offering a fresh setup; the panel uploads the backup with a signed ticket of scope
  `backup:restore`, checks it, confirms and restarts; the customer sees a waiting page on the login background, in four
  languages. (H-62)
- **An interrupted restore no longer serves data it cannot vouch for.** When the state of a restore cannot be read, the
  instance shows a page that asks for the administrator (with a link to the instance's support when one is set), keeps
  every checked copy, and `./dev.py backup pending --recover` lets the administrator choose between the data of before and
  a new restore. (B-33, B + H)
- Backup jobs report the archive's SHA-256; a restore report says that the accounts and credentials come from the backup,
  and warns when the confirming administrator is not in it. The guide explains nightly copies with restic or Backrest.
  (B, L3-1)
- **Activation and password-reset emails share one limit per network**, `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` (20 an
  hour), beside the instance's hourly budget; wrong passwords never spend it. When an email is held, the page says how
  many minutes to wait, in a yellow box. (A, E-26)
- In the Users list, an info icon next to «Waiting for verification» explains what it means. (A, E-7)

## Approvata dal developer il 23/10

Senza la riga sul profilo `managed`.
