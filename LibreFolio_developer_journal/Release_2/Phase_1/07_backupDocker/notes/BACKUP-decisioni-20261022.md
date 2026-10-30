# Backup del cloud — decisioni del developer (21-22/10/2026)

Esito del brainstorming del 21-22/10 fra il developer e la sessione «compagno di ragionamento». Chiude le 4 domande di
`BACKUP-pro-contro-20261021.md` §11 e **sostituisce** l'architettura B di `backup-architettura-cloud-20261020.md`.
Schema visivo e analisi degli attacchi: `BACKUP-schema-20261021.md`. Nessun codice scritto, nessun commit.

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

---

## 1. L'obiettivo, riformulato dal developer

Ricreare l'istanza su un pod nuovo da uno storage esterno, con ripristino completo (DB, file caricati, report dei
broker). Non servono backup «troppo all'indietro»: **una copia ogni notte, 7 in tutto**. Il developer accetta di perdere
fino a 24 ore di dati (il lavoro inserito dopo l'ultima copia) in caso di guasto.

## 2. Le quattro risposte del §11

| # | Domanda | Decisione |
|---|---|---|
| 1 | Calendario | **Opzione 1 nella 1.3** (L3 + «ripristino in corso» + rotta di ripristino). **Nessuna replica continua in programma**: l'Opzione 2 e Litestream escono dal piano. Calendario B ridotto: ~13-17 giorni di prodotto, ~2-3 settimane in parallelo con la catena grafici |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_
| 4 | Self-hosted | **Niente replica nell'immagine pubblica.** Lo zip notturno (già esistente) in una cartella; una pagina di documentazione per chi vuole metterci sopra backrest/restic. *(Proposta accettata implicitamente: il developer non ha obiettato.)* |

## 3. Il disegno

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

## 4. Le chiavi

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_
- La busta `.lfbk` attuale si tiene (AES-256-GCM a blocchi, controlli, `.part`); si aggiunge un secondo tipo di
  chiave nell'intestazione: «chiave del file casuale, chiusa con la pubblica» accanto a «scrypt dalla password». Il
  backup che l'admin scarica dalla UI resta con password. Più avanti: più destinatari (pannello + password del cliente).
- Il ripristino nell'istanza deve accettare «busta + chiave del file» oltre a «busta + password».

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

## 6. Condizioni d'uso

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

## 7. Lavoro che ne deriva

**Prodotto (1.3, ~13-17 giorni):** L3 (busta a chiave pubblica, `kid`, keygen) · modo «ripristino in corso» su
volume vuoto · rotta di ripristino del pannello **solo con biglietto L2 di scopo `backup:restore`, mai il token L1** ·
ripristino da «busta + chiave del file» · nel rapporto di stage: elenco degli amministratori contenuti nel backup,
avviso «si entra con le credenziali del backup, le sessioni di oggi si chiudono», avviso forte se l'account che
conferma non esiste nel backup · CSP `script-src` **applicata** (oggi solo rapporto, H-52) · documentazione self-hosted
(zip in cartella + backrest/restic) · test E2E di ripristino.

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

**Dopo la 1.3 (TODO futuri):** rotta `admin:reset` del pannello (link di reset password all'email dell'abbonato, per
l'admin rimasto fuori dopo un ripristino; al lancio l'assistenza rimette la copia della notte prima) · secondo fattore
per gli admin delle istanze (prima del lancio del cloud) · parser dei report in sottoprocesso con limiti di tempo e
memoria, più post-check pydantic nelle classi astratte · scansione automatica delle dipendenze · pulsante «com'era
ieri» · più destinatari nella busta.

## 8. Nota di sicurezza per il report finale

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`, `devJournal/coordinamento/`)_

## 10. La busta del backup notturno (decisione del developer, 22/10 pomeriggio)

Sostituisce, per la parte «busta», quanto scritto sopra su «busta a chiave pubblica» e «chiave del file» (§3 passo 4, §7):
il risultato per l'utente e per la sicurezza non cambia, cambia come è fatto il file. **Nessuna crittografia nuova
scritta da noi.**

**Ogni notte, sull'istanza:**
1. l'istanza fa il backup sicuro che esiste già, il `.lfbk` con password (scrypt + AES-256-GCM a blocchi, rivisto in B4),
   con una **password casuale di 32 byte** generata dalla macchina per quel backup;
2. cifra **solo la password** con `age` (libreria `pyrage`, binding Python di `rage`, Rust) verso la **chiave pubblica
   dell'istanza** (la privata la ricava solo il coordinatore dalla madre, §4);
3. mette i due file in un **`.tar` non compresso** (il `.lfbk` è già compresso e cifrato: gzip non guadagna nulla) e lo
   consegna al coordinatore, che lo archivia (ultime 7 copie buone).

**Al ripristino:**
1. il coordinatore prende il `.tar` dall'archivio e con la chiave privata apre **solo la password** (`pyrage`, standard);
2. manda alla macchina nuova, in modo «ripristino in corso», il `.lfbk` ancora cifrato e nella richiesta la password;
3. l'istanza usa il ripristino con password che esiste già (prova su una copia, rapporto, applicazione al riavvio).

**Perché:** zero codice crittografico nostro (`pyrage` per 32 byte, il `.lfbk` già rivisto per i dati); il ripristino con
password esiste già; il coordinatore non vede mai i dati in chiaro (passano solo file cifrati e la password: la stessa
fiducia della vecchia «chiave del file»); un furto del bucket trova solo file cifrati; in emergenza si apre la
password con `age -d` e ripristina con la CLI di LibreFolio. **Nomi:** il `.lfbk` non è mai stato rilasciato, quindi
resta **versione 1** (niente «v2»).

**Da concordare** fra il lotto B (prodotto) e il coordinatore cloud, in un contratto comune scritto
(`BACKUP-contratto-L3.md`, in questa cartella): nome e struttura del `.tar` e dei due file, formato della chiave pubblica
(`age1…`) e nome della variabile, forma della rotta di ripristino del pannello (biglietto L2 `backup:restore`, `.lfbk`
nel corpo, password nel campo), modo «ripristino in corso», `sha256` del `.tar` nel lavoro finito, codici d'errore, la
chiave d'istanza fuori dal backup (decisione 39), i vettori di prova comuni.
