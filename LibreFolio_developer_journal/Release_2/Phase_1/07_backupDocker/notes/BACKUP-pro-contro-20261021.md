# Backup del cloud — pro e contro per decidere (21/10/2026)

Per il developer. Riassume e mette a confronto tre documenti del 19-20/10: `litestream-domande-20261019.md`, `l3-litestream-ricerca-20261020.md` e `backup-architettura-cloud-20261020.md` (tutti in `copilot-enel/session-state/928ffa97…/files/`). Non è una consulenza legale.
Le cifre di lavoro sono quelle del documento di architettura. Dove ho ricalcolato io lo dico. Quello che ho riverificato oggi sul web porta *(verificato 21/10)*, quello che non ho potuto verificare porta *(non verificato)*.

---

## 1. La domanda, in una frase

**Quanto vogliamo perdere, al massimo, se il disco di un cliente muore — e chi deve poter aprire le copie?**
La seconda metà è la più importante: decide quasi tutto il resto (§4).

---

## 2. Cosa c'è già e cosa manca

**Già in `dev_release2` (backup F01):**
- uno zip completo (DB + file caricati + report dei broker + `manifest.json`), fatto su richiesta dalla UI, dalla CLI o dal pannello;
- la versione `.lfbk` con password (cifrata);
- il token del pannello per avviare, scaricare e cancellare i backup;
- la prova su una copia prima del ripristino, lo scambio all'avvio, il ritorno indietro automatico.

**Manca:**
1. **Lo zip del pannello viaggia in chiaro.** Il codice lo dice: "the hosting panel's routes never encrypt" (`panel.py:10`). Chi ruba il token di backup scarica tutti i dati del cliente.
2. **Nessuna copia continua.** Oggi si perde fino all'ultimo zip: con uno a notte, **fino a 24 ore**.
3. **Nessuna rotta di ripristino per il pannello.** Se il volume muore, il pannello non può rimettere i dati da solo: serve un admin del cliente che carichi lo zip dalla UI, oppure un intervento a mano sul volume. **Questo buco c'è con qualunque opzione** (anche con L3).
4. **Nessuno script che riporta i file** (upload, report) dall'ultimo zip su un volume vuoto.

**Esempio concreto.** Il cliente Mario lavora fino alle 18:00. Alle 18:30 il disco del suo server muore. L'ultimo zip è delle 03:00 della notte. Mario perde 15 ore di lavoro. Poi bisogna trovare chi ricarica lo zip.

---

## 3. Fatti verificati oggi *(21/10)*

| Fatto | Fonte |
|---|---|
| **Litestream non cifra più lato client.** L'ultima versione è la v0.5.17 (31/8/2026). La cifratura `age` è stata tolta con la riscrittura "LTX" del 2025 e il codice oggi rifiuta la configurazione. La guida ufficiale dice che sarà reimplementata "per pagina", **senza data** (tracciata nella issue #458). Resta solo la cifratura del fornitore dello storage (SSE-C/SSE-KMS) | litestream.io/docs/migration, github.com/benbjohnson/litestream/releases |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
| **Nessuno strumento di backup incrementale cifra con chiave pubblica** (restic, kopia, rclone, borg, Litestream: no; duplicity e Duplicacy sì, con limiti) | ricerca del 20/10 *(non riverificata oggi)* |

**Conseguenza.** "Una stessa chiave per Litestream e per gli zip del pannello" non si può fare. Con Litestream la chiave per riaprire le copie deve stare sull'istanza. Con L3 non ci deve mai stare.

---

## 4. Il nodo di fondo: chi tiene la chiave per riaprire le copie?

| | **K1 — l'istanza** | **K2 — solo il pannello** |
|---|---|---|
| Come | cifratura simmetrica: la stessa chiave scrive e legge | cifratura a chiave pubblica: l'istanza ha solo il "lucchetto aperto", la chiave privata sta nel vault del pannello |
| Ripristino | l'istanza si ripara **da sola** al primo avvio | **il pannello guida** il ripristino (decifra e rimanda lo zip) |
| Se qualcuno compromette l'istanza | legge anche **tutta la storia** delle copie | legge i dati di oggi (che ha comunque in chiaro) ma **non la storia** e non cancella le copie recenti |
| Se qualcuno ruba il token di backup | dipende dall'opzione | scarica un file **illeggibile** |
| Strumenti che lo fanno | Litestream (SSE-C), restic | solo codice nostro (L3), o duplicity/Duplicacy |

**Esempio.** La chiave K1 è la chiave di casa copiata: ce l'hanno la casa e la portineria; se entri dalla portineria, apri tutto. K2 è una cassetta delle lettere: chiunque può imbucare, solo il postino con la chiave del pannello apre.

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

**Costo di K2:** il ripristino dipende dal pannello. Se la macchina del coordinatore e la copia offline delle chiavi vanno perse, **le copie sono perse**. Serve una copia offline delle chiavi e un ripristino manuale di emergenza.

---

## 5. Le opzioni

**RPO** = quanti dati puoi perdere al massimo. "Da sveglia" = mentre il cliente lavora; "a fine sessione" = quando l'istanza si addormenta.

### Opzione 0 — niente di nuovo nella 1.3 (solo L1 + L2 + snapshot dei volumi)
Lo zip del pannello resta in chiaro, uno a notte; gli snapshot dei volumi sono la rete.
- **Pro:** nessun lavoro in più, nessun rischio sul ripristino. L1/L2 (H-61, già in corso) limitano chi può chiedere lo zip.
- **Contro:** il buco n.1 resta aperto: un token rubato dà uno zip in chiaro. RPO fino a 24 h. Il ripristino a volume vuoto resta manuale.
- **RPO:** 24 h. **Lavoro:** zero. **Rischio 1.3:** nullo.

### Opzione 1 — L3 sola, più lo zip dopo ogni sessione (la "versione minima coerente")
L'istanza cifra lo zip verso una chiave pubblica (una coppia di chiavi per istanza). Il pannello chiede lo zip dopo ogni sessione (la macchina è stata sveglia, il backup la tiene sveglia pochi secondi e poi si riaddormenta). Più: la rotta di ripristino del pannello e il modo "ripristino in corso" su volume vuoto.
- **Pro:** chiude il buco n.1 (file illeggibili senza la chiave) **e** il buco n.3 (ripristino guidato). Piccolo e isolato: non tocca lo scambio all'avvio. Nessuna dipendenza nuova (estende il formato `.lfbk`). **È anche il primo pezzo dell'Opzione 2:** niente lavoro buttato.
- **Contro:** RPO = una sessione, non cinque minuti. Se il disco muore a metà sessione, perdi quella sessione. Ogni backup fa lavorare la macchina.
- **RPO:** a fine sessione ~0, a metà sessione fino a una sessione. **Lavoro:** circa 13-17 giorni di prodotto, più una parte del lavoro sul pannello (la riga 9 vale 8-10 giorni per l'opzione intera). *(Stima mia: somma le righe 0, 1, 4, 5 e una parte di 7-8 della tabella del §5 del documento di architettura. Il lato pannello non l'ho stimato.)* **Rischio 1.3:** basso-medio.

### Opzione 2 — "replica cifrata" fatta dall'app (architettura B, consigliata dal documento)
L'istanza stessa manda a un bucket DB e file nuovi, cifrati verso il pannello (L3): 60 secondi dopo l'ultima modifica, al massimo ogni 5 minuti, e **sempre prima di sospendersi**. Il bucket ha un blocco di 3 giorni. In più, ogni notte, lo zip L3 nell'archivio del pannello (7 giornalieri, 4 settimanali, 3 mensili).
- **Pro:**
  - RPO ≤ 5 minuti da sveglia e **0 a fine sessione**.
  - Ritorno a qualunque punto degli ultimi 3 giorni ("com'era ieri alle 18").
  - Solo il pannello decifra (K2). Un'istanza compromessa non legge la storia né cancella le copie recenti.
  - Niente Litestream, niente programmi nuovi nell'immagine (si riusa `VACUUM INTO` e il formato `.lfbk`).
  - Per i self-hosted: replica su S3 **o su una cartella** (un NAS), sempre cifrata.
  - Salva anche **file e report**, non solo il DB.
- **Contro:**
  - **Formato nostro su un percorso critico.** Se ha un difetto, lo scopriamo noi. Mitigazione: il ripristino passa sempre da uno zip standard e dal controllo su copia già provati, e gli zip notturni sono una seconda via indipendente.
  - 29-37 giorni di prodotto + 8-10 sul pannello = **4-6 settimane di calendario**.
  - Non è "al secondo": con modifiche continue, un punto ogni 5 minuti.
  - Il ripristino dipende dal pannello (K2).
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
  - Lo spike richiede **Docker**, che qui non c'è.
- **RPO:** ≤ 5 min / 0. **Rischio 1.3:** medio.

### Opzione 3 — Litestream + copia dei file (architettura A)
Litestream replica il DB al secondo con SSE-C (chiave sull'istanza); i file con la nostra copia; gli zip notturni con L3.
- **Pro:** DB al secondo; ripristino davvero automatico; strumento noto; ADR-0002 lo prevedeva già.
- **Contro:**
  - Due modelli di chiave (K1 per Litestream, K2 per gli zip) e un'istanza compromessa legge 3 giorni di storia.
  - Tocca lo scambio all'avvio (`apply.py:653-657` fermerebbe l'avvio, perché l'avviatore diventa Litestream).
  - D6 e D1-D10 ancora aperte.
  - La cifratura è "solo SSE-C" e **non c'è data** per quella a chiave pubblica *(verificato 21/10)*.
  - +13 MB nell'immagine, un avviatore nuovo, spike con Docker.
  - 37-47 giorni di prodotto.
- **RPO:** DB ~1-60 s / 0, file minuti. **Rischio 1.3:** alto.

### Opzione 4 — restic (architettura C)
Snapshot deduplicati ogni pochi minuti, password sull'istanza.
- **Pro:** formato maturo, deduplicazione, poco codice nostro.
- **Contro:** solo cifratura simmetrica (K1), quindi L3 serve comunque per gli zip; un programma esterno nell'immagine, contro lo spirito della decisione 38; l'istanza compromessa legge tre mesi di storia; memoria usata *(non verificato)*.
- **RPO:** ≤ 5 min / 0. **Lavoro:** 28-35 giorni. **Rischio 1.3:** medio.

### Confronto

| | O0 niente | **O1 L3 + zip a sessione** | **O2 replica app (B)** | O3 Litestream (A) | O4 restic (C) |
|---|---|---|---|---|---|
| RPO da sveglia | 24 h | una sessione | **≤ 5 min** | ~1-60 s (DB) | ≤ 5 min |
| RPO a fine sessione | 24 h | ~0 | **0** | 0 | 0 |
| Ritorno a un momento passato | 1 zip al giorno | 1 zip a sessione | **ogni punto, 3 giorni** | al secondo, 3 giorni | ogni punto, 3 giorni |
| Chi decifra | nessuno (in chiaro) | solo il pannello | **solo il pannello** | istanza + pannello | istanza + pannello |
| Token rubato → file | leggibile | **illeggibile** | **illeggibile** | illeggibile (zip) | illeggibile (zip) |
| Istanza compromessa legge la storia | — | no | **no** | **sì (3 giorni)** | **sì (3 mesi)** |
| Si ripara senza di te | no | sì, guidata | sì, guidata | sì, da sola | sì, da sola |
| Tocca lo scambio all'avvio | no | no | no | **sì** | sì |
| Programmi nuovi nell'immagine | no | no | no | Litestream + avviatore | restic + avviatore |
| Include file e report | zip | zip | **sì, in continuo** | file con copia nostra | sì |
| Self-hosted | zip | zip | S3 **o cartella** | S3 (SFTP/cartella in chiaro) | S3 con password |
| Lavoro prodotto | 0 | ~13-17 g | **29-37 g** | 37-47 g | 28-35 g |
| Calendario | 0 | ~2-3 settimane | **4-6 settimane** | più lungo | ~4-5 settimane |
| Rischio per la 1.3 | nullo | basso-medio | medio | alto | medio |
| Serve Docker per provare | no | poco | sì (spike) | sì | sì |

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

---

## 6. Il compromesso vero: tempo, non soldi

- Il documento stima **4-6 settimane** per l'Opzione 2, solo se si parte entro una settimana con lo spike. Il 19/10 si parlava di "1.3 fra circa due settimane": **le due cose non stanno insieme**.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- La tua frase "deve uscire tutta assieme, ben architettata" si può leggere in due modi:
  1. **tutta assieme come funzione** (DB + file + report, un solo disegno, un solo interruttore) — l'Opzione 2 lo fa;
  2. **tutta nella 1.3** — questo è il vincolo che costa la data.

  Si può avere la prima senza la seconda: **la funzione esce intera in 1.3.1** (variabile spenta di default, "nessuna metà"), e nella 1.3 entra solo il pezzo piccolo che chiude i buchi reali (L1 + L2 + L3 + ripristino guidato).

### Tre calendari possibili

```
A) 1.3 con Opzione 2 dentro      →  il backup aggiunge 4-6 settimane al tag
B) 1.3 con Opzione 1; Opzione 2 in 1.3.1  →  il backup aggiunge ~2-3 settimane al tag; la replica esce dopo, in 1.3.1
C) 1.3 con Opzione 0; tutto in 1.3.1  →  il backup non sposta il tag; la 1.3.1 ha L3 + ripristino + replica
```
*(Non do date assolute: dipendono dal resto della 1.3. Il lavoro sul backup può correre in parallelo alla catena grafici Y/Z, che da sola vale ~8-9 giorni, quindi le settimane sopra non si sommano tutte al calendario del resto. Come e quanto si sovrappongono lo vedremo dopo lo spike.)*

---

## 7. Pro e contro per scegliere

| Se per te conta soprattutto… | Allora |
|---|---|
| Non ritardare la 1.3 | **O0** o **O1** |
| Chiudere subito il buco "zip in chiaro" senza rischi sul ripristino | **O1** |
| Ridurre la perdita a ≤ 5 minuti per il lancio del cloud | **O2** (dopo O1, in 1.3.1) |
| Un solo disegno per DB + file + report | **O2** |
| L'istanza che si ripara da sola, senza pannello | **O3** (ma con K1: storia leggibile da un'istanza compromessa) |
| Niente strumenti esterni nell'immagine pubblica | **O1/O2** |
| Valore per chi si ospita da solo | **O2** (cartella o S3, cifrata) |

**Il mio consiglio** (è tuo, io lo propongo): **O1 nella 1.3, O2 subito dopo, come 1.3.1** — perché
1. il primo pezzo di O2 è L3, quindi O1 non è lavoro da buttare, ma una prima tappa;
2. L3 + ripristino guidato chiudono i due buchi che toccano la sicurezza *adesso*;
3. la replica continua serve al lancio del cloud, non al tag;
4. non si tocca il codice più delicato della release (scambio all'avvio) a ridosso del tag;
5. Litestream resta fuori, finché non cifra a chiave pubblica.

Controargomento onesto: due rilasci e due revisioni di sicurezza invece di una; e se la 1.3 fosse comunque ferma 4-6 settimane per i colori e la catena grafici, aspettare costerebbe meno di quanto sembra.

---

## 8. Le 12 decisioni del documento di architettura, semplificate

Le risposte tra parentesi sono quelle consigliate dal documento, adattate al calendario B del §6.

| # | Decisione | Consiglio |
|---|---|---|
| 1 | Architettura A, B o C | **B** (O2) |
| 2 | Chi decifra la copia continua: istanza o solo pannello | **solo pannello (K2)** |
| 3 | Quando copiare | 60 s dopo l'ultima modifica, max ogni 5 min, sempre prima di sospendersi |
| 4 | Conservazione | replica 3 giorni, archivio 7/4/3 |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
| 6 | Chiave L3: una per istanza o una per tutto | **una per istanza**, busta con più destinatari da subito (la chiave del cliente arriverà dopo) |
| 7 | Self-hosted | replica nell'immagine pubblica, S3 e cartella, niente SFTP |
| 8 | Litestream | fuori dalla 1.3 |
| 9 | Volume vuoto | l'istanza parte in "ripristino in corso" quando il pannello lo segnala; mai partire vuoti sopra un backup buono |
| 10 | "Com'era ieri" | tramite assistenza nella 1.3; il pulsante dopo |
| 11 | Se manca un pezzo alla data limite | **la funzione intera va in 1.3.1**, nessuna metà |
| 12 | Informativa privacy | bozza del documento, rivista da un consulente |

**Questione a parte, la 6:** una sola chiave L3 per tutto il pannello significa che una chiave rubata apre **tutti i backup di tutti i clienti, passati e futuri**. Una per istanza limita il danno a un cliente, come già fai per `JWT_SECRET` e per le altre chiavi.

---

## 9. Privacy, in breve

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- **GDPR art. 32** (inquadramento, non parere): chiede cifratura, disponibilità e resilienza, ripristino tempestivo e prove regolari. Le opzioni 1 e 2 coprono cifratura e ripristino; la prova regolare è il test T3 prima del lancio e una prova mensile. Titolare/responsabile e trasferimenti fuori UE: con un consulente.

---

## 10. Cosa resta da provare prima di fidarsi

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
2. `VACUUM INTO` e compressione sui **tuoi dati reali** (13 MB di DB): quanto pesa un punto, quanto dura.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
4. Quanto spazio serve sul volume durante un punto in preparazione più il ripristino.
5. Un ripristino completo a volume vuoto (test T3) con i totali di controllo uguali.
6. Peso e memoria del client S3 (`boto3` è grande; alternativa: firma S3 a mano con `httpx`).
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

**Strumenti:** lo spike richiede **Docker** (qui non è installato) e i tuoi dati reali (qui non ci sono). Si possono fare sul Mac, oppure si installa Docker su questa macchina e si porta una copia dei dati.

---

## 11. Cosa mi serve da te per chiudere

Quattro risposte bastano:
1. **Calendario:** A, B o C del §6?
2. **Chi decifra:** K2 (solo pannello), come consigliato? Accetti che il ripristino passi dal pannello e che serva una copia offline delle chiavi?
3. **Chiave L3:** una per istanza?
4. **Self-hosted:** la replica va nell'immagine pubblica (S3 e cartella) o solo nel cloud?

Le altre 8 decisioni del §8 seguono da queste. Nessun lavoro sul backup parte finché non rispondi.
