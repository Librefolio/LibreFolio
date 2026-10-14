# Le sei analisi della 1.3: decisioni da prendere (14/10/2026)

> Scritto dal coordinatore della 1.3 per il developer, dopo le analisi di Piattaforma, Account e accessi, Plugin asset
> e ricerca, Import e transazioni, Numeri e analisi, Sospensione e risveglio. Ogni sessione è ferma e aspetta il via.
> Il testo completo delle analisi è nelle cartelle di sessione; qui ci sono solo le scelte, ognuna con il suo contesto.
>
> **Come rispondere**: «approvo tutte le raccomandazioni e autorizzo il codice per le sei sessioni», più le eccezioni
> («la 7 no, la 12 così…»). Il primo via libera al codice è tuo: lo inoltro alla lettera a ogni sessione.
>
> Le sigle fra parentesi servono solo a ritrovare la voce nelle analisi.

## Come leggere i punti

Ogni punto dice: com'è **oggi**, cosa si **propone**, **perché**, le **alternative**, e cosa cambia per **chi usa già
LibreFolio** (self-hosted, senza variabili d'ambiente nuove).

- 🔴 **cambia qualcosa che gli utenti di oggi vedono subito**, senza toccare la configurazione;
- 🟡 **cambia poco**, o solo in casi rari, o solo per gli admin;
- 🟢 **non cambia nulla per chi usa già LibreFolio**: vale solo con una variabile nuova (cloud, profilo gestito), è una
  funzione nuova o è interno.

## In breve: cosa cambia per chi usa già LibreFolio

Nessuna di queste scelte stravolge il prodotto. Le due più visibili:

- 🔴 **31 — i prezzi in tempo reale si fermano** a scheda nascosta e dopo 10 minuti senza toccare mouse o tastiera
  (riprendono subito al ritorno);
- 🔴 **26 — nel pannello dei lotti FIFO cambiano alcuni numeri** dei lotti in valuta estera già venduti (la divisione
  fra realizzato e non realizzato; il totale resta uguale, salvo un caso oggi sbagliato).

Le altre visibili sono piccole:

- 🟡 **1**: il campo «registrazione» delle impostazioni globali diventa a tre scelte;
- 🟡 **3**: un avviso nella nuova scheda «Sicurezza» dell'admin se la registrazione è aperta su un'istanza
  raggiungibile da internet (oggi la registrazione è aperta di default);
- 🟡 **4**: limite ai tentativi di login sbagliati (si spegne solo con una variabile, e allora la scheda «Sicurezza»
  lo segnala);
- 🟡 **11**: cambiando password, gli altri dispositivi devono rifare il login;
- 🟡 **20**: «+ Nuovo evento» smette di sovrascrivere in silenzio un evento esistente;
- 🟡 **22**: un salvataggio di eventi con una riga sbagliata non salva più a metà;
- 🟡 **27**: viene rifiutato il cambio di tipo di uno split che lascerebbe quote senza costo;
- 🟡 **28**: piccole correzioni nelle linee del valore nei giorni in cui si muove solo il cambio.

Il **riordino del codice** (§3) non si vede, ma è il rischio principale di regressioni: per questo ogni spostamento
passa dalla suite completa con gli stessi conteggi di prima.

## 1. Cosa parte appena dai il via

- **Primo treno** (gli spostamenti di file che sbloccano tutti, integrati uno dopo l'altro):
    1. Piattaforma sposta i servizi di sistema (scheduler, registro dei container, soglie della qualità dei dati, file
     caricati, anteprime) nelle cartelle `services/platform/` e `services/files/`;
    2. Plugin asset e ricerca dà a ogni famiglia di plugin il suo registro (prezzi, cambi, import, segnali, rischio);
    3. Account e accessi sposta i servizi degli account in `services/accounts/`.
- **In parallelo, da subito**:
    - Numeri e analisi divide il motore del PAC;
    - Import e transazioni sposta transazioni e broker, e corregge i difetti d'integrità;
    - Sospensione e risveglio scrive la pausa degli aggiornamenti automatici, da integrare appena pronta.
- Il resto segue l'ordine dei piani, a checkpoint.

## 2. Decisioni di prodotto

### Account e accessi

#### 1. Registrazione a tre modalità — 🟡 (D-A2)
- **Oggi**: in Impostazioni › Globali c'è un sì/no, «Consenti la registrazione», **acceso di default**. Non esistono
  inviti.
- **Proposta**: tre modalità.
    - **Aperta**: chiunque si registra, come il sì di oggi.
    - **Su invito**: serve un link generato dall'admin.
    - **Chiusa**: nessuno, come il no di oggi.
    - Il valore salvato si converte da solo.
    - La variabile `LIBREFOLIO_REGISTRATION`, se c'è, fissa la modalità e il campo diventa bloccato.
- **Perché**: il piano Famiglia del cloud, e chi ospita LibreFolio per amici, deve poter invitare una persona senza
  aprire la registrazione a tutto internet. È la base degli inviti (F13).
- **Alternative**: lasciare il sì/no e far funzionare gli inviti anche a registrazione chiusa. Nella pratica è la
  stessa cosa, ma meno chiara per l'admin.
- **Per chi usa già LibreFolio**: l'admin vede un menu a tre voci al posto dell'interruttore; nessun comportamento
  cambia.

**Decisione (14/10)**: approvata, senza note.

#### 2. «Chiusa» blocca anche gli inviti — 🟢 (D-A3)
- **Oggi**: gli inviti non esistono.
- **Proposta**: con la registrazione chiusa nemmeno un invito permette di creare un account. Per invitare, l'admin
  passa a «su invito».
- **Perché**: «chiusa» vuol dire chiusa; un vecchio link non deve aprire un account quando l'admin crede di aver
  chiuso tutto.
- **Alternative**: «chiusa» accetta gli inviti già emessi. Allora «chiusa» e «su invito» quasi non si distinguono più.

Nota dev: gli inviti per iniziare facciamo che sono dei messaggi con un url link e dentro questo url un tocken che il backend si aspetta, una volta usato esso deve scadere, in seguito lo inviamo anche per email ma come primo step facciamo così, potrebbe servire, se il sistema non è in grado di auto scoprirlo, assegnare in una variabile anche l'url esterno del server.

**Decisione (14/10)**: approvata. «Chiusa» blocca anche gli inviti.
- L'invito è un link con dentro un token monouso: usato una volta, scade. All'inizio si copia e si condivide a mano;
  con il servizio email si potrà anche spedire.
- Nella finestra dell'invito l'indirizzo del server è precompilato con quello del browser, e l'admin può modificarlo
  prima di condividere il link. Se lo modifica, un controllo dal browser verifica che a quell'indirizzo risponda davvero
  l'istanza.
- `LIBREFOLIO_PUBLIC_URL`, facoltativa, serve per i link costruiti fuori dal browser: riga di comando e, più avanti,
  email.

#### 3. Admin iniziale dalle variabili d'ambiente — 🟡 (D-A4, F02, K-5)
- **Oggi**: il primo che si registra diventa admin. Su un'istanza appena creata e raggiungibile da internet, chiunque
  arrivi per primo prende il controllo.
- **Proposta**: un'istanza vuota nasce già con l'admin «in attesa», se l'hoster imposta `LIBREFOLIO_ADMIN_EMAIL` e un
  token.
    - L'admin si attiva solo con un link monouso `/setup?token=…`, valido 72 ore: è il link «imposta la tua password»
    che il pannello del cloud manda al cliente.
    - La registrazione parte «su invito».
    - Se l'istanza ha già utenti, le variabili vengono ignorate, con un messaggio nei log.
    - Un token più corto di 32 caratteri blocca l'avvio con un errore chiaro.
- **Due piccoli cambi anche senza variabili**:
    - su un'istanza senza utenti la pagina di login mostra «Crea l'account amministratore» anche a registrazione chiusa
    (oggi il pulsante sparisce e l'istanza resta inutilizzabile: K-5);
    - l'admin vede un avviso se la registrazione è aperta e l'istanza si raggiunge da un indirizzo pubblico, cioè non
    da localhost o dalla rete locale. È nella specifica.
- **Perché**: senza questo, nel cloud una persona qualsiasi potrebbe precedere il cliente.
- **Alternative**:
    - la password dell'admin in una variabile d'ambiente (più semplice, ma la password resta scritta nella
    configurazione);
    - un'API con cui il pannello crea gli utenti (serve una credenziale permanente di amministrazione: più rischi).
- **Per chi usa già LibreFolio**: l'avviso, se la tua istanza è esposta con la registrazione aperta, che oggi è il
  default.

nota dev: si mi piace e si sposa bene con quello che dicevo prima sui tocken in url, la logica è che se la variabile viene passata, all'ora la prima iscrizione è su invito e l'invito è quello, così in ottica di librefolio cloud siamo sicuri che a usare l'istanza sia chi ha pagato perchè ha ricevuto il tocken.
però bisogna pensare a come fare se scade in quel caso... o forse possiamo pensarci dopo, rifrlettici

cmq se la variabile non è impostata, ovviamente deve funzionare comè ora

**Decisione (14/10)**: approvata.
- Con le variabili, il primo account è l'admin, che si attiva solo con il link del token: chi lo riceve è chi ha
  pagato.
- **Senza variabili** tutto funziona come oggi: il primo che si registra diventa admin. Restano solo le due piccole
  correzioni sopra: il pulsante «Crea l'account amministratore» su un'istanza vuota, e l'avviso di registrazione
  aperta, che va nella scheda «Sicurezza» del punto 4.
- **Se il link scade** prima dell'attivazione non serve distruggere l'istanza. Il pannello mette un token nuovo nella
  variabile e la riavvia; siccome l'istanza è ancora vuota, l'admin in attesa riparte con il token nuovo, valido altre
  72 ore. Ricrearla da zero funzionerebbe lo stesso.
- **Da segnare per il pannello del cloud** (repo privato): un'azione «reinvia il link di attivazione», cioè token nuovo,
  riavvio, email nuova.

#### 4. Limite ai tentativi di login sbagliati — 🟡 (D-A5, F15)
- **Oggi**: nessun limite: si possono provare password all'infinito.
- **Proposta**: dopo 10 tentativi sbagliati in 15 minuti sullo stesso nome utente, o 50 dallo stesso indirizzo, il
  login risponde «troppi tentativi, riprova fra qualche minuto». Un login riuscito azzera il contatore. Sempre attivo,
  senza variabili nuove.
- **Perché**: un'istanza esposta su internet è un bersaglio per chi prova le password a raffica. Nella specifica è «se
  c'è spazio», ma costa poco.
- **Effetti collaterali**:
    - chi conosce il tuo nome utente può bloccarti il login per 15 minuti, sbagliando apposta;
    - dietro un proxy configurato male tutti sembrano arrivare dallo stesso indirizzo, per questo quella soglia è alta;
    - i test E2E fanno molti login dallo stesso indirizzo: va verificato che non scatti (contano solo i login falliti).
- **Alternative**:
    - spento di default e acceso nel profilo gestito: rispetta alla lettera la regola «nessun cambiamento per il
    self-hosted»;
    - soglie impostabili da variabile.
- **Per chi usa già LibreFolio**: cambia qualcosa solo per chi sbaglia la password molte volte di fila.

nota dev: è un ottima proposta lato sicurezza, la metterei attiva di default e disattivabile solo tramite variabile di ambiente, principalmente per i test che così possono lavorare indisturbati. Sarebbe da aggiungere nel pannello amministratore una zona con l'audit di sicurezza, dove in generale mettere le cose sospette e come prima cosa, far comparire il messaggio "attenzione ..." se il limiti di login è disattivato, potrebbe essere un errore di configurazione che altrimenti passa inosservato

**Decisione (14/10)**: approvata, con due modifiche.
- Il limite è attivo di default e si spegne solo con una variabile d'ambiente, pensata per i test.
- Nasce una scheda **«Sicurezza»** in Impostazioni, solo per l'admin, che raccoglie le cose sospette, con un segnale
  sulla scheda quando c'è un avviso. Primi controlli:
  - «limite dei tentativi disattivato», che può essere un errore di configurazione;
  - «registrazione aperta su un indirizzo pubblico» (punto 3).

  Le altre sessioni potranno aggiungere i loro controlli.

#### 5. La variabile che spegne il popup delle donazioni resta nascosta — 🟢 (D-A7)
- **Oggi**: `LIBREFOLIO_DISABLE_DONATION_POPUP` spegne il popup, ma per tua scelta non è documentata (lo dice un
  commento nel codice).
- **Proposta**: resta così. Il profilo gestito spegne le donazioni per conto suo (punto 6).
- **Alternative**: documentarla, così chi fa self-hosting può spegnere il popup.

nota dev: no no è corretto che sia così, quelli selfosted ogni tanto devono vedersi ricordati di contribuire.

**Decisione (14/10)**: approvata. La variabile resta nascosta: chi fa self-hosting continua a vedere ogni tanto l'invito a
contribuire.

#### 6. Nel profilo gestito spariscono gli inviti a donare — 🟢 (D-A8)
- **Oggi**: «Buy Me a Coffee» compare in cinque posti:
    - il popup, che parte dopo almeno 10 accessi e 7 giorni dall'ultima volta, e comunque ogni 60 giorni;
    - la pagina di login;
    - l'intestazione;
    - il menu Aiuto;
    - la scheda «Supporta LibreFolio» in Impostazioni › Informazioni.
- **Proposta**: con `LIBREFOLIO_PROFILE=managed` spariscono tutti. Dove c'era il link compare «Supporto», verso
  `LIBREFOLIO_SUPPORT_URL`, se è impostato. I pulsanti per condividere LibreFolio sui social restano.
- **Perché**: chi paga un abbonamento non deve ricevere richieste di donazione. Vale per qualunque hoster, non solo per
  il nostro cloud.
- **Alternative**: tenere la scheda in Informazioni anche nel cloud; togliere anche la condivisione sui social.

Nota dev: si ok farlo scomparire, non serve mettere supporto, c'è già il bottone alle issue di github, però lascierei nelle impostazioni i link ai social per condividere il prodotto.

**Decisione (14/10)**: approvata, con una modifica. Nel profilo gestito spariscono tutti gli inviti a donare, senza un link
«Supporto» al loro posto: c'è già il pulsante delle segnalazioni su GitHub, quindi niente `LIBREFOLIO_SUPPORT_URL`. I
link social per condividere LibreFolio restano in Impostazioni.

#### 7. «Gestisci abbonamento» solo per gli admin; messaggio del limite senza nomi di piani — 🟢 (D-A9)
- **Proposta**:
    - il link `LIBREFOLIO_BILLING_URL` lo vede solo l'admin, che è chi paga;
    - superato il limite di utenti, il messaggio dice «limite di utenti raggiunto per questa istanza» (più il link all'abbonamento, se c'è), senza nominare il «piano Famiglia».
- **Perché**: il codice è pubblico e lo usano anche altri hoster; i nomi dei piani sono del cloud e possono cambiare.
- **Alternative**: un messaggio scrivibile da variabile d'ambiente; il link visibile a tutti gli utenti.

nota dev: si ok far vedere il billing solo all'amministratore, colui che paga, non mi è chiaro però come si passa l'url all'istanza e dove l'amministratore vede questa cosa o se la va a cercare.

**Decisione (14/10)**: approvata.
- L'indirizzo arriva con `LIBREFOLIO_BILLING_URL`, impostata dal pannello del cloud quando crea l'istanza, come le
  altre variabili.
- L'admin vede «Gestisci abbonamento» nella scheda Utenti, accanto al conteggio («3 / 5 utenti»), nel messaggio di
  limite raggiunto e, nel cloud, nella pagina di blocco del punto 12. Gli altri utenti non lo vedono.

#### 8. Come si conta il limite di utenti — 🟢 (D-A10)
- **Proposta**: `LIBREFOLIO_MAX_USERS` conta gli utenti attivi, gli inviti non scaduti e l'admin in attesa
  d'attivazione; i disattivati non contano. Non impostata, nessun limite.
    - Oltre il limite si bloccano i nuovi inviti, la registrazione e la riattivazione di un utente.
    - La riga di comando (`dev.py user create`) può superarlo, con un avviso, per il supporto.
- **Perché**: se gli inviti non contassero, con un limite di 5 si potrebbero spedire 10 inviti.
- **Alternative**: contare gli inviti solo quando vengono usati; vietare il superamento anche alla riga di comando.

Nota dev: serve una ulteriore pagina per l'amministratore che gli permette di elencare gli utenti attivi e gli inviti in volo. può eliminare quando vuole gli inviti in volo e non può creare più inviti di quanti il numero limite prevede. Di default, se la variabile è assente, il numero limite è infinito (caso self hosted)
Dovremmo invece ragionare su come può fare un amministratore ad eliminare un utente in teoria attivo, cosa succede ai suoi broker e alle sue transazioni.

**Decisione (14/10)**: approvata, con la pagina Utenti e la cancellazione degli utenti da parte dell'admin.
- **Pagina Utenti**, solo per l'admin: utenti attivi e inviti in corso. L'admin revoca un invito quando vuole e non
  può crearne oltre il limite. Senza `LIBREFOLIO_MAX_USERS` il limite non c'è (self-hosted).
- **Eliminare un utente**: vale la regola di oggi per chi elimina il proprio account.
  - I broker di cui era l'unico proprietario spariscono, con transazioni e file; da quelli condivisi sparisce solo il
    suo accesso.
  - Prima un'anteprima di cosa sparisce, poi la conferma con il nome utente.
  - Come prima scelta l'admin vede «Disattiva», che è reversibile e non tocca i dati.
- **Gli admin**:
  - nessuno può eliminare, disattivare o declassare l'ultimo admin attivo (la regola esiste già);
  - per eliminare un altro admin, prima va declassato a utente;
  - nel cloud, l'admin creato dalle variabili, cioè chi paga, non può essere eliminato, disattivato né declassato da
    nessuno; per andarsene chiude l'abbonamento dal pannello.

#### 9. Il campo «ultima versione vista» già nella migrazione degli account — 🟢 (D-A12)
- **Contesto**: «Novità dalla tua ultima versione» (C-54): al login, se la versione è cambiata, si apre il changelog
  sui capitoli nuovi. L'avevi rimandata a dopo la 1.2; entra solo se c'è spazio.
- **Proposta**: la colonna nel database entra subito, nella stessa migrazione degli inviti, anche se la funzione arriva
  dopo.
- **Perché**: una migrazione in meno più avanti, a costo quasi nullo.
- **Alternative**: aggiungerla quando si fa la funzione.

**Decisione (14/10)**: approvata, senza note.

#### 10. Un invito con un'email vale solo per quell'email — 🟢 (D-A16)
- **Proposta**: se l'admin scrive un'email nell'invito, ci si registra solo con quella. Senza email, il link vale per
  chi lo riceve.
- **Perché**: un link inoltrato per sbaglio, su WhatsApp o altrove, non deve far entrare un'altra persona.
- **Alternative**: l'email solo come promemoria.
nota dev: la rimanderei a più avanti, quando integriamo il servizio e mail ma anche fosse non sono convinto serva, anzi, il link è il link, ha una scadenza temporale, e comunque si può usare 1 sola volta, quindi non mi preoccuperei troppo, per altro un nuovo utente di default non vede i dati degli altri, solo nomi broker e nomi utenti.

**Decisione (14/10)**: respinta. Un invito non è legato a un'email: basta il link, perché scade e si usa una volta sola. Se
serve, se ne riparla con il servizio email.

#### 11. Cambiare password chiude le altre sessioni — 🟡 (D-A17)
- **Oggi**: una sessione dura 24 ore (impostazione globale). Cambiare la password non chiude le sessioni già aperte:
  un telefono perso, o una sessione rubata, resta dentro fino alla scadenza.
- **Proposta**: chiudono le altre sessioni:
    - il cambio o il reset della password;
    - la disattivazione o il declassamento di un utente.

  Il dispositivo da cui si cambia la password resta collegato. Le sessioni aperte prima dell'aggiornamento della 1.3
  restano valide: nessuno viene buttato fuori dall'aggiornamento.
- **Perché**: con il reset via email («password dimenticata») è la protezione standard. Su `TODO_FUTURI` («🔑
  Sessioni») avevi scritto «ci devo pensare».
- **Alternative**: chiudere le sessioni solo con il reset, non con il cambio volontario; un pulsante «esci da tutti i
  dispositivi».
- **Per chi usa già LibreFolio**: dopo un cambio di password, gli altri dispositivi chiedono di nuovo il login.
Nota dev: capisco che in caso di piscing abbia senso che al cambio pw tutti i device vengano sloggati, per farlo come si potrebbe fare? si invalida il l'oaut eccetto nel client in cui stai facendo il cambio pw, che il backend ti ritorna subito il nuovo o semplicemente ti rilogghi immediatamente, avendo appena mandato la pw i dati li avresti tutti, o come altro?

**Decisione (14/10)**: approvata. Come funziona:
- ogni utente ha un numero di «generazione» delle sessioni, scritto nel cookie di login;
- il cookie è firmato dal server: se qualcuno cambia il numero, la firma non torna e il cookie viene rifiutato, quindi
  non serve hasharlo;
- cambiare o reimpostare la password alza il numero, e la stessa risposta dà al dispositivo da cui lo fai un cookie
  nuovo: resti dentro senza riscrivere la password;
- gli altri dispositivi, alla richiesta successiva, tornano al login.

### Piattaforma

#### 12. Cosa resta permesso in sola lettura — 🟢 (H D4, D-A15)
- **Oggi**: la sola lettura non esiste.
- **Contesto**: il pannello del cloud imposta `LIBREFOLIO_READ_ONLY` quando la prova o l'abbonamento finiscono (D-18:
  «istanza in sola lettura, backup scaricabile, cancellazione dopo 30 giorni»). Nel self-hosted resta spenta.
- **Proposta**: un avviso fisso in alto; ogni modifica risponde con un messaggio chiaro. Restano permessi l'insieme
  delle due proposte:
    - da Piattaforma: accesso e uscita, cambio della password, preferenze personali (lingua, tema), onboarding, pulizia
    della cache, prezzo corrente, letture ed export;
    - da Account e accessi, in più: reset della password, attivazione dell'admin, cancellazione del proprio account;
    - da Sospensione e risveglio: il risveglio programmato.

  Bloccato tutto il resto: transazioni, broker, asset, import, sincronizzazioni a mano, impostazioni globali, nome e
  avatar. I prezzi di mercato continuano ad aggiornarsi da soli.
- **Perché**: chi smette di pagare deve poter vedere ed esportare i propri dati, e anche cancellarsi, ma non usare
  l'app.
- **Alternative**:
    - solo la lista di Piattaforma, che blocca anche la cancellazione dell'account e il reset della password;
    - permettere anche le modifiche al profilo.

Nota dev: non la farei così complicata modificando la ui, semplicemente impedirei il login ma venendo rimandati alla pagina di billing per l'amministratore, mentre agli altri utenti una modale che spiega che non è stato pagato e se non viene saldato il pagamento il server e relativi dati verranno liberati in x tempo, tipo 1 settimana, dando la possibilità di backuppare i dati scaricandoli. che ne pensi?

**Decisione (14/10)**: niente sola lettura dentro l'app. Quando l'abbonamento non è pagato, l'istanza si **blocca**.
- Dopo il login, l'admin vede una pagina di blocco con «Gestisci abbonamento» e lo scarico del backup completo.
- Gli altri utenti vedono una pagina che spiega che l'abbonamento non è pagato e quando istanza e dati verranno
  cancellati, e li invita a chiedere il backup all'amministratore. Nessun export per singolo utente.
- Restano permessi solo: accesso e uscita, la pagina di blocco, il backup per l'admin, la cancellazione del proprio
  account, il risveglio programmato.
- La data di cancellazione la decide il pannello del cloud e la passa all'istanza, che la mostra. Il business plan
  diceva 30 giorni, la tua nota una settimana: si sceglie nel cloud, senza toccare il codice.
- Cambiano di conseguenza le eccezioni di Account e accessi per la sola lettura (D-A15).

#### 13. Header di sicurezza — 🟢 (H D5, F15)
- **Oggi**: il server non manda header di sicurezza, a parte quelli della cache.
- **Proposta**:
    - **Sempre**:
        - `X-Content-Type-Options: nosniff`: il browser non indovina il tipo di un file;
        - `Referrer-Policy`: gli indirizzi delle pagine, con eventuali token dentro, non vengono passati ai siti esterni.
    - **Solo nel profilo gestito**:
        - `X-Frame-Options: SAMEORIGIN`: l'app non si può incorporare in un altro sito, una protezione dal clickjacking;
        - CSP in sola segnalazione: registra, non blocca nulla.
- **Perché**: è l'irrobustimento chiesto dalla specifica.
- **Alternative**: tutto per tutti. Romperebbe chi usa LibreFolio dentro un cruscotto homelab (Homarr, Heimdall,
  Organizr), che lo incorpora in un iframe.
- **Per chi usa già LibreFolio**: nulla di visibile.

nota dev: perdona la mia ignoranza, non so di cosa si stia parlando, cosa sono queste cose? se le implementiamo, sotto al cofano cosa guadagnamo? ci possono essere rallentamenti di performance?

**Spiegazione del coordinatore**: sono righe di testo che il server aggiunge a ogni risposta per dire al browser come
comportarsi. Pesano qualche centinaio di byte e non rallentano nulla di misurabile.
- `nosniff`: il browser non «indovina» il tipo di un file. Senza, un file caricato come immagine ma con dentro del
  codice potrebbe essere eseguito come pagina.
- `Referrer-Policy`: cliccando un link esterno, il sito esterno non riceve l'indirizzo da cui arrivi, che può
  contenere il token di un invito o di un reset.
- `X-Frame-Options`, solo nel profilo gestito: un altro sito non può mostrare LibreFolio in una cornice invisibile per
  farti cliccare pulsanti a tua insaputa.
- CSP in prova, solo nel profilo gestito: l'elenco delle fonti da cui possono arrivare script e stili. In prova non
  blocca nulla, segnala soltanto.

**Decisione (14/10)**: approvata, tutto come proposto.

#### 14. Versioni scritte a mano a 0.0.0 — 🟢 (H D6, C-84)
- **Oggi**: `pyproject.toml` e `frontend/package.json` dicono 1.1.0, fermi dal 05/08. Nessuno li legge: la versione
  mostrata viene dal tag git, o dal file `VERSION` nell'immagine Docker.
- **Proposta**: 0.0.0, con un commento: «la versione vera viene dal tag».
- **Perché**: un numero sbagliato confonde chi legge il repo e gli strumenti che analizzano le dipendenze.
- **Alternative**: aggiornarle a ogni rilascio, a mano o con la pipeline. Il numero è giusto, ma è un passo in più.

nota dev: si mi piace

**Decisione (14/10)**: approvata.

#### 15. `/system/info` dietro il login — 🟢 (H D14)
- **Oggi**: `GET /api/v1/system/info` risponde a chiunque, anche senza login, con le versioni di tutte le dipendenze e
  del sistema operativo.
- **Proposta**: serve il login. La versione dell'app resta pubblica su `/system/version`, nuovo.
- **Perché**: l'elenco delle versioni aiuta chi cerca vulnerabilità note da sfruttare.
- **Alternative**: lasciarlo pubblico ma senza le versioni delle dipendenze.
- **Per chi usa già LibreFolio**: niente nell'app, che lo chiama solo dopo il login (Informazioni, changelog,
  controllo aggiornamenti). Cambia solo per uno script esterno che lo leggeva senza login.

nota dev: facciamo che se non si è loggati il ritorno è minimo, l'equivalente del version che dicevi, ma senza creare un nuovo endpoint.

**Decisione (14/10)**: approvata con una modifica. Nessun endpoint nuovo: `/system/info` senza login risponde solo con il
minimo, cioè la versione dell'app; con il login, tutto come oggi.

#### 16. Metriche Prometheus, spente di default — 🟢 (H D9, F08)
- **Proposta**: `/metrics` con le richieste, i job dello scheduler, l'ultimo aggiornamento dei prezzi e la dimensione
  del database. Si accende con `LIBREFOLIO_METRICS_ENABLED`.
- **Perché**: il monitoraggio del cloud, e degli homelab con Grafana. Nella specifica è facoltativo.
- **Alternative**: rimandarlo.

Nota dev, è sicuramente una cosa figa, ma la rimanderei

**Decisione (14/10)**: rimandata, fuori dalla 1.3.

#### 17. Test del backend organizzati come il codice — 🟢 (TS1)
- **Oggi**: i test del backend sono divisi per tipo (API, servizi…), non per dominio; il catalogo del runner contiene
  236 percorsi.
- **Proposta**: per ora no; si rivaluta a riordino finito, con i numeri.
- **Perché**: costa molto, rende poco, e mentre le sessioni lavorano porterebbe conflitti su quasi tutti i test.
- **Alternative**: farlo alla fine della 1.3.

Nota dev: non credo sia una buona idea era stato pensato così per fare i test a strati, il riorganizzare dei test non mi aspetto cambi il paradigma, al massimo che splitti meglio i file di test, se serve.

**Decisione (14/10)**: respinta. I test restano organizzati a strati (API, servizi…), com'erano stati pensati; al più si
dividono meglio i file di test troppo grandi, quando serve.

### Plugin, asset e ricerca

#### 18. La chiave dei segreti dei plugin nei backup solo se lo zip ha una password — 🟢 (D-X2)
- **Contesto**: le impostazioni dei plugin, nuove nella 1.3, salvano i segreti (per esempio la chiave d'accesso a un
  fornitore a pagamento, nel self-hosted) cifrati nel database. La chiave che li cifra sta in `<cartella dati>/secrets/`.
  Il backup dalla UI, anche lui nuovo, è uno zip della cartella dei dati.
- **Proposta**:
    - con la password sullo zip, dentro c'è anche la chiave e il ripristino è completo;
    - senza password, la chiave resta fuori: il ripristino funziona, ma i segreti dei plugin vanno reinseriti.
- **Perché**: uno zip con il database e la chiave è un file con i segreti in chiaro, per chiunque lo trovi.
- **Alternative**: la chiave sempre dentro (comodo, meno sicuro); mai dentro (i segreti sempre da reinserire).

nota dev: chat, questo punto non l'ho capito, spiegamelo.

**Spiegazione del coordinatore** (da confermare):
- Nella 1.3 i plugin possono avere impostazioni, alcune segrete: per esempio la chiave d'accesso a un fornitore di
  prezzi a pagamento che chi fa self-hosting compra da sé.
- Questi segreti stanno nel database **cifrati**, cioè illeggibili senza una chiave. La chiave è un file a parte, nella
  cartella dei dati.
- Il backup nuovo scarica uno zip di tutta la cartella dei dati. Se nello zip ci sono sia il database sia la chiave,
  chi trova lo zip (una chiavetta persa, una copia su un cloud) legge tutti i segreti: la cifratura non servirebbe a
  niente.
- Da qui la proposta: con una password sullo zip la chiave entra, e il ripristino è completo. Senza password la chiave
  resta fuori: il ripristino funziona lo stesso, ma le chiavi dei plugin vanno reinserite a mano.

#### 19. Il profilo gestito, senza elenchi espliciti, non usa scraper — 🟢 (D-X4)
- **Contesto**: le fonti dei prezzi di oggi sono tutte scraper o API non ufficiali: Yahoo Finance, justETF, Borsa
  Italiana, lo scraper CSS. Le fonti dei cambi (BCE, Fed, Banca d'Inghilterra, Banca nazionale svizzera) sono
  ufficiali.
- **Proposta**: nel profilo gestito, se il pannello non dichiara quali fonti permettere, restano solo quelle non
  scraper. Per i cambi tutte; per i prezzi nessuna, finché non arriva il fornitore a pagamento o un elenco esplicito
  (la ricerca degli asset resta vuota). Il cloud metterà comunque il suo elenco, dopo il parere legale (D-15).
- **Perché**: la specifica chiede «scraper disattivati di default», e le licenze dei dati vanno rispettate.
- **Alternative**: nel profilo gestito, senza elenco, tutte le fonti permesse.

nota dev, in pratica il cerca nella versione gestita ha i badge degli attuali provider disattivi di default, corretto? e l'unico/unici attivi sono quelli con dati premium, vero?

**Risposta del coordinatore** (da confermare): quasi.
- Nel profilo gestito, se il pannello non dà un elenco di fonti permesse, le fonti di prezzo di oggi, che sono tutte
  scraper, non compaiono proprio nella ricerca: non come badge spenti, ma assenti. Restano i prezzi manuali e il
  calcolo interno per prestiti e obbligazioni a cedola fissa. Le fonti dei cambi delle banche centrali restano tutte.
- Attive saranno le fonti che il pannello mette nell'elenco: il fornitore premium quando arriva (ondata 3), più
  eventuali fonti gratuite che il parere legale permetterà.
- Un asset già collegato a una fonte non permessa mostra un avviso, con «Cambia fonte» o i prezzi manuali.
- Nel self-hosted non cambia nulla: tutte le fonti come oggi.

### Import e transazioni

#### 20. «+ Nuovo evento» non sovrascrive più un evento esistente — 🟡 (D-W1, V-22)
- **Oggi**: la finestra «+ Nuovo evento» si apre dal modulo della transazione o dalla pagina dell'asset (dividendo,
  split…). Se esiste già un evento dello stesso tipo nella stessa data, anche scaricato dal fornitore o collegato a
  transazioni, il salvataggio lo **modifica** invece di crearne uno nuovo, e la finestra dice «creato». Esempio: aggiungi
  un dividendo nel giorno in cui il fornitore ne ha già scaricato uno, e ne sovrascrivi importo e note.
- **Proposta di Import e transazioni**: un salvataggio senza id non sovrascrive mai. Arriva un errore con l'evento
  esistente e la finestra propone «usa quello».
- **La mia raccomandazione**:
    - il divieto vale per «+ Nuovo evento», dove l'intenzione è creare;
    - l'editor degli eventi e il CSV continuano ad aggiornare per data e tipo, ma non toccano un evento collegato a
    transazioni senza conferma.

  Con la proposta della sessione, il giro «esporta il CSV, modificalo, reimportalo» si romperebbe, se l'export non porta
  gli id: va verificato.
- **Alternative**: lasciare com'è e documentarlo; la proposta della sessione, più rigida.
- **Per chi usa già LibreFolio**: il salvataggio non modifica più un evento in silenzio, e chi lo faceva apposta
  riceve un messaggio.

#### 21. Per cancellare degli eventi serve indicare l'asset — 🟢 (D-W2, I-12)
- **Oggi**: la richiesta che cancella gli eventi accetta una lista di id, di qualunque asset. Una richiesta sbagliata,
  o costruita apposta, può cancellare eventi di altri asset.
- **Proposta**: la richiesta indica l'asset, e si cancellano solo i suoi eventi.
- **Perché**: sicurezza e integrità dei dati.
- **Per chi usa già LibreFolio**: nulla. L'unico chiamante è l'editor degli eventi, aggiornato insieme.

#### 22. Salvataggio degli eventi tutto o niente — 🟡 (D-W3, I-12)
- **Oggi**: un salvataggio di più eventi li scrive uno alla volta. Se una riga è sbagliata, le precedenti restano
  salvate e le successive no.
- **Proposta**: o tutte o nessuna, con l'errore della riga che non va.
- **Perché**: un salvataggio a metà è difficile da capire e da correggere.
- **Alternative**: lasciarlo com'è, ma dire nel messaggio quali righe sono state salvate.
- **Per chi usa già LibreFolio**: un CSV di eventi con una riga sbagliata non salva più nulla, finché la riga non è
  corretta.

#### 23. Tipi di evento in minuscolo: controllo e correzione dei dati — 🟢 (D-W7, I-09)
- **Oggi**: un tipo scritto in minuscolo o sconosciuto, per esempio da un CSV scritto a mano, viene salvato, e da quel
  momento ogni lettura di quell'evento va in errore 500.
- **Proposta**:
    - all'ingresso, il tipo si porta in maiuscolo e un tipo sconosciuto viene rifiutato con un messaggio chiaro;
    - una migrazione corregge i tipi già salvati in minuscolo, mentre quelli sconosciuti finiscono nel log.
- **Da decidere**: cosa fare degli eventi con un tipo sconosciuto già salvati. Lasciarli e segnalarli (continuano a
  dare errore), oppure eliminarli.
- **Alternative**: solo il controllo all'ingresso, senza toccare i dati salvati.

#### 24. K-1 chiusa senza codice — 🟢 (D-W15)
- **Contesto**: nella 1.2 il Bulk mostrava come «coppia» due cloni dello stesso tipo. La correzione è nell'interfaccia,
  ma i dati salvati prima potrebbero contenere coppie sbagliate. La copia del tuo database ne aveva 0.
- **Proposta**: chiuderla senza codice. La query per trovarle resta scritta nel piano, se servisse.
- **Alternative**: scrivere comunque una riparazione, per le altre installazioni.

#### 25. Domanda nuova: chi può modificare i dati condivisi degli asset — 🟢 se resta com'è
- **Oggi**: asset, prezzi manuali, eventi (dividendi, split) e classificazioni sono condivisi fra tutti gli utenti
  dell'istanza. Chiunque abbia fatto il login può crearli, modificarli, unirli e cancellarli, anche chi vede un broker
  solo in lettura. Un familiare che corregge uno split cambia i calcoli di tutti.
- **Proposta**: nella 1.3 resta così, perché gli utenti di un'istanza si fidano tra loro, più una voce nel backlog
  per decidere un modello.
- **Alternative**: solo gli admin; solo chi ha creato l'asset; solo chi ne ha delle posizioni.

### Numeri e analisi

#### 26. P&L dei lotti in valuta estera — 🔴 (D-J1, T-B5)
- **Contesto**: il pannello dei lotti FIFO mostra, per ogni lotto, il P&L **realizzato** (dalle vendite) e quello **di
  mercato** (la variazione di valore di quello che resta). Per un lotto tutto venduto, il «di mercato» dovrebbe essere
  zero.
- **Oggi**: il realizzato si calcola sulla differenza di prezzo in valuta, convertita al cambio della vendita, mentre il
  costo del lotto è convertito al cambio dell'acquisto. Così una parte dell'effetto del cambio finisce nel «di mercato»
  anche per un lotto chiuso.
    - Esempio: 100 USD comprati con il dollaro a 1,00 € e venduti a 110 USD con il dollaro a 0,90 €. Oggi: realizzato
    +9 €, di mercato −10 €, totale −1 €.
    - Peggio, per un lotto comprato in euro e venduto in dollari (dopo un trasferimento) i proventi sono letti come euro:
    110 USD diventano «110 €».
- **Proposta**: ogni lato nella sua valuta, alla sua data. Il costo si converte al cambio dell'acquisto, i proventi a
  quello della vendita.
    - Nel primo esempio: realizzato −1 €, di mercato 0, totale −1 €, lo stesso realizzato che mostra la Dashboard.
    - Nel secondo: proventi 99 €, totale −1 €.
- **Perché**: oggi i lotti esteri chiusi mostrano un «di mercato» che non ha senso, e il realizzato non coincide con la
  Dashboard. Il caso con due valute è proprio sbagliato.
- **Alternative**:
    - correggere solo il caso con due valute e lasciare la divisione di oggi per gli altri;
    - per le vendite in un'altra valuta mostrare «—» con un avviso.
- **Per chi usa già LibreFolio**: cambiano numeri già visti nel pannello dei lotti, per chi ha venduto titoli in
  valuta estera. Il totale di ogni lotto resta uguale, salvo il caso con due valute, che oggi è sbagliato.

#### 27. Cambiare il tipo di uno split con rettifiche collegate viene rifiutato — 🟡 (D-J2, P-10)
- **Contesto**: con uno split le quote in più entrano come rettifiche collegate all'evento, senza un costo proprio,
  perché il costo resta quello di partenza, ridistribuito.
- **Oggi**: se nell'editor degli eventi si cambia il tipo dello split, per esempio in dividendo, le rettifiche restano
  senza costo e senza più uno split che le giustifichi. Il motore le vede come quote comparse dal nulla, con costo
  sconosciuto: compare l'avviso «costo mancante» e i calcoli diventano parziali. È l'unico modo, dall'app, di creare un
  costo sconosciuto.
- **Proposta**: il cambio di tipo viene rifiutato, con un messaggio che elenca le rettifiche collegate. Prima si
  scollegano, o si sistemano.
- **Alternative**: tenere solo l'avviso di oggi e documentarlo.
- **Per chi usa già LibreFolio**: un'operazione rara, che rompeva i dati, viene rifiutata.

#### 28. Giorni in cui si muove solo il cambio di un titolo — 🟡 (D-J3, B11)
- **Contesto**: il motore del portafoglio ricalcola il valore solo nei giorni in cui succede qualcosa. Oggi contano
  le transazioni, i prezzi e i cambi delle valute tenute **in cassa**.
- **Oggi**: in un giorno senza prezzi nuovi in cui cambia solo il tasso di cambio di un titolo in valuta estera (per
  esempio un ETF in dollari durante una festa della sua borsa), il valore in euro resta quello del giorno prima.
- **Proposta**: anche i cambi delle valute dei titoli contano.
- **Perché**: il valore e le linee della crescita sono più giusti in quei giorni.
- **Alternative**: lasciarlo com'è, documentato.
- **Per chi usa già LibreFolio**: piccole variazioni, più corrette, nelle linee del valore in quei giorni. Il
  riferimento dei test va rigenerato, dopo aver scritto date e valori attesi.

#### 29. I due «Rolling Return» con lo stesso nome — 🟢 (D-J6, C-71)
- **Oggi**: due indicatori diversi hanno lo stesso nome. Quello della 1.1 usa una finestra in numero di osservazioni;
  il modo nuovo del grafico dell'asset usa una finestra in giorni di calendario.
- **Proposta**: due nomi distinti, «Rolling Return (osservazioni)» e «Rolling Return (giorni di calendario)». Nessuno
  dei due viene ritirato, perché le configurazioni salvate degli utenti usano quello vecchio.
- **Alternative**: ritirare quello vecchio, rompendo le configurazioni salvate dei grafici.

#### 30. L'avviso «nessun prezzo di mercato da oltre 2 settimane» — 🟢 (D-J15, V-11)
- **Oggi**: per un asset valutato al prezzo di una transazione, l'avviso conta le due settimane dalla prima
  transazione. Può comparire anche per un asset quotato ieri.
- **Proposta**: le due settimane si contano dall'ultima quotazione di mercato, così l'avviso compare solo quando è
  vero.
- **Alternative**: cambiare solo il testo dell'avviso.
- **Per chi usa già LibreFolio**: meno avvisi falsi.

### Sospensione e risveglio

#### 31. I prezzi in tempo reale si fermano quando nessuno guarda — 🔴 (Z D2, F26)
- **Oggi**: con aperta la lista degli asset o il dettaglio di un asset il cui grafico arriva a oggi, il browser chiede
  il prezzo corrente ogni 30 secondi (nel dettaglio anche ogni 60) **per sempre**, anche a scheda nascosta o a computer
  fermo. Ogni richiesta interroga il fornitore e salva il prezzo del giorno nel database.
- **Proposta**: gli aggiornamenti si fermano a scheda nascosta e dopo 10 minuti senza toccare mouse o tastiera.
  Compare «Aggiornamento in pausa» con «Riprendi»; al ritorno l'aggiornamento è immediato. Vale per tutti; più avanti i
  10 minuti saranno impostabili (0 = mai).
- **Perché**: nel cloud, finché una scheda resta aperta, la macchina non si spegne mai, e i costi crescono. Nel
  self-hosted si fanno meno chiamate ai fornitori (che possono bloccare chi esagera), meno scritture e si consuma meno
  batteria. Lo chiede la specifica.
- **Alternative**:
    - solo nel profilo gestito;
    - solo la pausa a scheda nascosta, senza il limite dei 10 minuti.
- **Per chi usa già LibreFolio**: chi tiene una pagina aperta su uno schermo, come un tabellone dei prezzi, la vede
  fermarsi dopo 10 minuti, finché non tocca qualcosa.

#### 32. Il polling conta come presenza dell'utente — 🟢 (Z D4)
- **Contesto**: per sospendersi da solo, il server deve capire quando nessuno lo usa. La specifica dice di contare le
  richieste dell'utente, esclusi i controlli di salute e il polling.
- **Il problema**: se il polling non conta, mentre un utente guarda i prezzi senza cliccare il server si crede solo,
  si sospende, e il polling successivo lo risveglia. Ricomincia ogni 30 secondi.
- **Proposta**: il polling conta. Con la pausa del punto 31 smette comunque: la macchina si sospende entro N+1 minuti a
  scheda nascosta, entro 10+N+1 a scheda visibile ma ferma.
- **Alternative**: alla lettera della specifica, con il rischio del ciclo sospensione e risveglio.
- **Per chi usa già LibreFolio**: niente: vale solo con le variabili della sospensione, che nel self-hosted restano
  spente.

#### 33. Il risveglio programmato risponde un po' alla volta — 🟢 (Z D7)
- **Contesto**: di notte il pannello del cloud sveglia l'istanza per aggiornare i prezzi, aspetta la fine e legge
  quando svegliarla la prossima volta. Il proxy di Fly chiude una connessione che resta 60 secondi senza dati, e un
  aggiornamento può durare di più.
- **Proposta**: la risposta parte subito e manda uno spazio ogni 15 secondi circa, finché il lavoro non finisce; poi
  arriva il risultato.
- **Alternative**:
    - una risposta immediata «ricevuto», più un secondo indirizzo che il pannello interroga finché il lavoro non è
    finito;
    - la rete privata di Fly, che però non sveglia da sola una macchina sospesa.
- **Per chi usa già LibreFolio**: niente: è un accordo tecnico con il pannello privato.

#### 34. Pause crescenti quando un fornitore dice «troppe richieste» — 🟢 (Z D9)
- **Oggi**: se un fornitore risponde «troppe richieste» (429), lo scheduler riprova al giro successivo (ogni 10 minuti,
  di default) e il fornitore continua a rifiutare, con il rischio di un blocco più lungo.
- **Proposta**: dopo un rifiuto quel fornitore va in pausa per un tempo che cresce (1, 2, 4… minuti, fino a un
  massimo); i job lo saltano finché la pausa non scade. Acceso di default.
- **Alternative**: spento di default e acceso da variabile, alla lettera della regola «nessun cambiamento».
- **Per chi usa già LibreFolio**: niente, finché un fornitore non rifiuta.

#### 35. Lo spegnimento ha un tempo massimo — 🟢 (Z D10, C-49)
- **Oggi**: allo stop (un `docker stop`, un riavvio) il server aspetta senza limite i job in corso e le richieste aperte.
  Docker, dopo 10 secondi, lo uccide, con il rischio di interrompere una scrittura nel database.
- **Proposta**: un tempo massimo di circa 8 secondi. I job si interrompono, le richieste si chiudono, lo stato si salva,
  e il server esce in ordine.
- **Alternative**: un tempo configurabile, con il default di oggi (nessun limite).
- **Per chi usa già LibreFolio**: niente di visibile; gli arresti diventano più puliti.

### Nuovo, dalla verifica di Account e accessi (14/10 sera)

#### 36. Cosa vede un utente dei dati degli altri — 🟡 (A-1, A-2)
- **Oggi**: al punto 10 hai scritto che un utente nuovo vede degli altri solo i nomi dei broker e degli utenti.
  Account e accessi l'ha verificato, in sola lettura: con il login, un utente vede anche
  - le email degli admin, dalla ricerca degli utenti;
  - nome e icona di tutti i broker, anche di quelli non condivisi con lui;
  - l'elenco, l'anteprima e lo scarico di **tutti i file caricati**, da chiunque: solo la cancellazione controlla il
    proprietario.

  Senza login, poi, si leggono le impostazioni globali: scheduler, durata della sessione, registrazione.
- **Proposta**: correggerlo nella 1.3.
  - Un file caricato lo vede solo chi l'ha caricato, o chi ha accesso al broker a cui appartiene.
  - Nomi e icone dei broker non condivisi solo per l'admin (prima si verifica dove li usa l'app).
  - Le email degli admin non escono dalla ricerca.
  - Le impostazioni globali solo con il login, dopo che la configurazione pubblica di Piattaforma porta fuori quello
    che serve alla pagina di login.
  - Chi lo fa: i file Piattaforma, i broker Import e transazioni, ricerca utenti e impostazioni Account e accessi.
- **Perché**: in un'istanza condivisa (famiglia, amici, cloud) i file possono essere documenti personali.
- **Alternative**: correggere solo i file e lasciare il resto com'è.
- **Per chi usa già LibreFolio**: chi condivide l'istanza smette di vedere i file e i broker degli altri.

## 3. Decisioni di coordinamento (già prese; correggibili)

- **Forma comune del riordino**. Perché: sei sessioni spostano file insieme, e serve una regola sola per non
  scontrarsi.
    - Un file che entra in una cartella di dominio tiene il suo nome (`services/accounts/auth_service.py`): meno righe
    toccate, meno conflitti, nessun nome nascosto da una variabile con lo stesso nome.
    - I moduli nuovi nati da un taglio prendono nomi brevi per tema.
    - Router e schemi grandi diventano cartelle per dominio (`api/v1/<dominio>/`, `schemas/<dominio>/`), con gli stessi
    URL e lo stesso client API generato.
    - La configurazione diventa una cartella con una sezione per sessione, così cinque sessioni non scrivono lo stesso
    file.
- **Proprietà**. Perché: un file, uno scrittore.
    - Gli eventi degli asset passano a Import e transazioni dopo che Plugin asset e ricerca ha diviso il router.
    - L'AI Export è di Numeri e analisi; la riga legale nel prompt la scrive Account e accessi.
    - I messaggi d'import tradotti (C-70) sono tutti di Import e transazioni.
    - La matematica dei cambi dentro i file dei plugin la scrive Numeri e analisi (regola 10: una sola casa per la
    matematica finanziaria).
- **Migrazioni del database**: la 005 è degli account, la 006 delle impostazioni dei plugin, poi le correzioni dei dati
  degli eventi. Chi integra per secondo ricollega la catena.
- **`npm ci` dal lock**: permesso a ogni sessione quando serve a un controllo. Mai `npm install`, che potrebbe cambiare
  le versioni.
- **Colori**: il coordinatore colori ha dato gli elenchi esatti dei suoi lotti. Le cartelle di asset, cambi e
  transazioni si spostano dopo il suo lotto A, quelle dei grafici dopo il lotto B. Tutto il resto è libero subito.
- **Il tuo cancello dei colori, letto per intero** (precisazione del coordinatore colori, 14/10 alle 22:05). Hai deciso
  che la 1.3 non esce con la conversione a metà dei neutri (fondi, testi, bordi) e degli stati (successo, avviso,
  errore, informazione). Questi colori però non stanno solo nelle pagine di cambi, asset e transazioni. Stanno anche
  nelle tabelle, nei pannelli di dashboard, rischio e broker, e nei grafici.
    - **Cosa serve prima del tag**: quasi tutta la conversione dei colori. Secondo la stima del workstream dei token (T)
    sono circa 11.500 classi in 276 file, in 30–40 lotti di sotto-agenti, più i quattro lotti della fattorizzazione
    dei colori. Restano fuori solo i colori per categoria (tipi di asset, ruoli dei broker) e le palette dei dati nei
    grafici, che aspettano un giro della designer.
    - **Le date**: la 1.3 non ha una data fissa, quindi nessuno scontro. Però la conversione dei colori diventa un
    secondo percorso critico, parallelo alle ondate 1 e 2, e potrebbe diventare il più lungo. La seguo a ogni treno e
    ti avviso se succede.
    - **Il riordino del codice resta fuori dal percorso critico**: con il coordinatore colori ho concordato la regola
    «chi parte prima». Prendiamo un file che la 1.3 deve dividere (per esempio la modale degli asset o il wizard
    d'import). Se la divisione non è ancora iniziata quando T arriva a convertirlo, T converte il file di oggi e la
    divisione si fa dopo; se è già iniziata, T lo lascia per ultimo. Mai due sessioni sullo stesso file insieme.
    - **Alternativa, per una release più corta**: limitare il cancello a primitivi, aree libere, stati, cambi, asset e
    transazioni (ondate W1–W4). Tabelle, dashboard, rischio e broker resterebbero ai colori vecchi dentro la cornice
    nuova, cioè proprio l'effetto che la tua decisione vuole evitare. Per questo consiglio la lettura per intero.

## 4. Cose che servono da te più avanti

- Una sola finestra per installare `cryptography` (impostazioni dei plugin), a corsie ferme. Facoltativa `tzdata`.
- Docker acceso quando Piattaforma arriva al lotto dell'immagine.
- Togliere il tag `test` da GHCR (C-26): è un'azione sul remoto.
- Lato pannello di controllo (repo privato): le macchine con `auto_stop_machines="off"` e `auto_start_machines=true`,
  perché è l'istanza a decidere quando sospendersi.
