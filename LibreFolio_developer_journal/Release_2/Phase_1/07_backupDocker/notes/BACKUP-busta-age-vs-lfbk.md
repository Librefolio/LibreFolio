# Backup L3 — la busta: `.lfbk` versione 2 o `age`? (22/10/2026)

Per il developer. Spiega i due disegni e dove differiscono. In breve: **la tua idea è giusta, ed è proprio quella che
fanno tutti e due.** La differenza è solo *come è fatto il file*, non *come funziona la protezione*.

---

## 1. La tua idea, detta con le parole della crittografia

> «Lo zip con una password, e la password nel pacchetto cifrata con la chiave pubblica.»

Si chiama **cifratura a busta** (envelope encryption), ed è il modo standard di cifrare un file per un destinatario:

1. l'istanza inventa una **chiave del file** casuale (la «password», ma scelta dalla macchina: 16 o 32 byte a caso,
   molto più forte di qualunque password umana);
2. cifra lo zip con quella chiave (veloce, anche per centinaia di MB);
3. chiude la chiave del file con la **chiave pubblica** del cliente, e la mette **in testa al file**;
4. butta via la chiave del file: da quel momento nemmeno l'istanza può riaprire lo zip.

Per aprire: il coordinatore, con la **chiave privata**, apre solo la testa e tira fuori la chiave del file; la manda alla
macchina nuova insieme allo zip ancora cifrato; la macchina apre lo zip.

```
┌──────────────────────── file di backup ────────────────────────┐
│ TESTA: la chiave del file, chiusa con la chiave PUBBLICA        │ ← solo il coordinatore la apre (chiave privata)
├────────────────────────────────────────────────────────────────┤
│ CORPO: lo zip, cifrato con la chiave del file, a blocchi        │ ← lo apre chi ha la chiave del file
└────────────────────────────────────────────────────────────────┘
```

**Tutte e due le opzioni sono esattamente questo.** Non c'è una password umana (non serve: la chiave del file casuale
fa lo stesso lavoro, meglio), ma lo schema è il tuo.

---

## 2. Opzione (a) — `.lfbk` versione 2 (il nostro formato)

Oggi i backup «sicuri» dalla UI sono `.lfbk` **versione 1**: la chiave dei blocchi nasce dalla **password** dell'admin
(scrypt), e i blocchi sono cifrati con AES-256-GCM. La versione 2 cambia solo la testa:

```
┌───────────── .lfbk v2 ─────────────┐
│ "LFBK", versione 2, tipo X25519     │
│ dimensione dei blocchi, nonce       │   testa: 148 byte, binaria
│ kid  (impronta della chiave pubbl.) │
│ E    (chiave pubblica effimera)     │
│ W    (chiave del file, chiusa)      │
├─────────────────────────────────────┤
│ blocchi AES-256-GCM (come oggi v1)  │   corpo: identico alla v1
└─────────────────────────────────────┘
```

- **Come si chiude la chiave del file**: scambio X25519 tra una chiave effimera e la pubblica del cliente → HKDF-SHA256
  con parametri **scelti da noi** (`info = "librefolio-lfbk/v2/x25519-wrap"`, salt = le due chiavi) → AES-256-GCM.
  È lo stesso schema del destinatario X25519 di `age`, ricopiato.
- **Pro**: poco codice nuovo (circa 100 righe sopra la busta v1 già rivista); un solo formato per i backup con password e
  quelli a chiave pubblica; la testa ha dimensione fissa, facile per il coordinatore.
- **Contro**: il **disegno** della testa è nostro. I vettori di prova controllano che il codice faccia ciò che *abbiamo
  deciso*, non che la decisione sia giusta. E il file si apre **solo con LibreFolio** (o con un nostro script).

---

## 3. Opzione (b) — il formato `age` v1 (standard)

`age` è uno strumento e un formato pubblico (specifica C2SP), scritto da crittografi e usato in molti progetti. Il file:

```
┌──────────────── file age ────────────────┐
│ age-encryption.org/v1                     │
│ -> X25519 <chiave pubblica effimera>      │   testa: testo leggibile,
│ <chiave del file chiusa, 16 byte + tag>   │   una «stanza» per destinatario
│ --- <MAC della testa>                     │
├───────────────────────────────────────────┤
│ nonce (16 byte)                           │   corpo: blocchi da 64 KiB,
│ blocchi ChaCha20-Poly1305 (STREAM)        │   ChaCha20-Poly1305
└───────────────────────────────────────────┘
```

- **Come si chiude la chiave del file**: X25519 + HKDF-SHA256 con i parametri **della specifica**
  (`info = "age-encryption.org/v1/X25519"`) + ChaCha20-Poly1305. La testa ha anche un MAC che la protegge tutta.
- **«Scriverlo noi»** vuol dire: niente libreria `age` per Python (l'unica, `pyrage`, lavora tutto in memoria e ha un
  solo manutentore); il nostro codice produce file **esattamente in quel formato** usando `cryptography`, che abbiamo già.
  Circa 200-300 righe.
- **Pro**: il disegno non è nostro, è già stato rivisto. Abbiamo **due arbitri esterni**: i vettori di prova ufficiali
  di `age` e il programma `age` stesso (un test apre i nostri file con `age -d`; se sbagliamo un byte, se ne accorge).
  In emergenza si apre un backup con il comando standard, **senza il nostro codice**. _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- **Contro**: più codice da scrivere (la cifratura a blocchi di `age` è diversa dalla nostra: non si riusa la v1); nel
  prodotto convivono due formati (i backup con password restano `.lfbk` v1); 1-2 giorni in più.

---

## 4. Le differenze, una accanto all'altra

| | (a) `.lfbk` v2 | (b) `age` v1 |
|---|---|---|
| Schema a busta (la tua idea) | sì | sì |
| Chi ha deciso i dettagli della testa | noi (copiando `age`) | la specifica pubblica |
| Cifratura dei blocchi | AES-256-GCM, come la v1 di oggi | ChaCha20-Poly1305, blocchi da 64 KiB |
| Codice nuovo | ~100 righe | ~200-300 righe |
| Come si prova che è giusto | i nostri vettori | i vettori ufficiali **e** il programma `age` |
| Aprire un backup senza LibreFolio | no | sì, `age -d` |
| Coordinatore che apre solo la chiave del file | testa binaria fissa, facile | legge la stanza X25519 della testa, come dice la specifica |
| Backup con password (UI admin) | stessa famiglia `.lfbk` | restano `.lfbk` v1: due formati |
| Tempo | più breve | +1-2 giorni |
| Rischio vero | un errore nel *disegno* che nessuno controlla da fuori | un errore di *codice*, che il confronto con `age` scopre |

---

## 5. Raccomandazione

Tutte e due sono sicure se fatte bene, e (a) copia già lo schema di `age`. La scelta è fra:
- **semplicità** (a): meno codice, un solo formato, tutto in casa;
- **verificabilità** (b): formato standard, un arbitro esterno, il backup si apre anche senza di noi.

Il coordinatore consiglia **(b)**. Se
preferisci (a), la differenza di rischio è piccola, purché la revisione di sicurezza indipendente guardi proprio la testa.

B mette lo stesso confronto, con i numeri reali del codice, nella sua specifica (passo B1); niente codice della busta
finché non scegli.
