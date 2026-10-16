# Le sei analisi della 1.3: decisioni da prendere (14/10/2026)

> Scritto dal coordinatore della 1.3 per il developer, dopo le analisi di Piattaforma, Account e accessi, Plugin asset
> e ricerca, Import e transazioni, Numeri e analisi, Sospensione e risveglio. Ogni sessione è ferma e aspetta il via.
> Il testo completo delle analisi è nelle cartelle di sessione; qui ci sono solo le scelte, ognuna con il suo contesto.
>
> **Come rispondere**: «approvo tutte le raccomandazioni e autorizzo il codice per le sei sessioni», più le eccezioni
> («la 7 no, la 12 così…»). Il primo via libera al codice è tuo: lo inoltro alla lettera a ogni sessione.
>
> Le sigle fra parentesi servono solo a ritrovare la voce nelle analisi.
>
> **Aggiunte del 15/10**: l'analisi di Backup e Docker (punti 38–43), quella di Email (44–45) e due punti di Import e
> transazioni (46–47), in fondo al §2, ognuna con il modo di rispondere.
>
> **Stato al 15/10, 10:50**: sotto ogni decisione già presa c'è ora una riga «Attuazione»: ✅ in `dev_release2`,
> 🟡 fatta e in attesa d'ingresso, ⏳ da fare. Il **punto 18 è superato dal 39**: si riparte dal 19.

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

**Attuazione (15/10)**: 🟡 fatta da Account e accessi: migrazione 006 `registration_mode` e `LIBREFOLIO_REGISTRATION` (A5a), l'impostazione «Registrazione» a tre scelte e le pagine dei link (A5b). Committata sul ramo di A (`7da2cd9a2`, `2b0715532`); entra in `dev_release2` dopo la finestra della galleria.

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

**Attuazione (15/10)**: 🟡 in A5a: con «chiusa» anche un invito valido viene rifiutato. Entra con A5.

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

**Attuazione (15/10)**: ⏳ lotto A7 di Account e accessi (`/setup`, link d'attivazione, avviso di registrazione aperta su un'istanza esposta).

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

**Attuazione (15/10)**: ⏳ lotto A8 di Account e accessi (limite su login e token, scheda «Sicurezza»).

#### 5. La variabile che spegne il popup delle donazioni resta nascosta — 🟢 (D-A7)
- **Oggi**: `LIBREFOLIO_DISABLE_DONATION_POPUP` spegne il popup, ma per tua scelta non è documentata (lo dice un
  commento nel codice).
- **Proposta**: resta così. Il profilo gestito spegne le donazioni per conto suo (punto 6).
- **Alternative**: documentarla, così chi fa self-hosting può spegnere il popup.

nota dev: no no è corretto che sia così, quelli selfosted ogni tanto devono vedersi ricordati di contribuire.

**Decisione (14/10)**: approvata. La variabile resta nascosta: chi fa self-hosting continua a vedere ogni tanto l'invito a
contribuire.

**Attuazione (15/10)**: nessun codice: la variabile resta com'è.

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

**Attuazione (15/10)**: ⏳ lotto A9 di Account e accessi (profilo gestito, la sua parte).

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

**Attuazione (15/10)**: 🟡 in parte in A5a: chi non è admin riceve il messaggio del limite senza conteggi né link; `LIBREFOLIO_BILLING_URL` esce solo dalle API degli admin. Il pulsante «Gestisci abbonamento» nella pagina di blocco lo aggiunge Piattaforma dopo l'ingresso di A5.

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

**Attuazione (15/10)**: 🟡 il conteggio (utenti attivi più inviti in attesa) e le API degli admin in A5a; la scheda Utenti in A6; la cancellazione di un utente da parte dell'admin ⏳ con la scheda Utenti.

#### 9. Il campo «ultima versione vista» già nella migrazione degli account — 🟢 (D-A12)
- **Contesto**: «Novità dalla tua ultima versione» (C-54): al login, se la versione è cambiata, si apre il changelog
  sui capitoli nuovi. L'avevi rimandata a dopo la 1.2; entra solo se c'è spazio.
- **Proposta**: la colonna nel database entra subito, nella stessa migrazione degli inviti, anche se la funzione arriva
  dopo.
- **Perché**: una migrazione in meno più avanti, a costo quasi nullo.
- **Alternative**: aggiungerla quando si fa la funzione.

**Decisione (14/10)**: approvata, senza note.

**Attuazione (15/10)**: ✅ nella migrazione 005 (A4, `e476d2ed4`): colonna `last_seen_version`.

#### 10. Un invito con un'email vale solo per quell'email — 🟢 (D-A16)
- **Proposta**: se l'admin scrive un'email nell'invito, ci si registra solo con quella. Senza email, il link vale per
  chi lo riceve.
- **Perché**: un link inoltrato per sbaglio, su WhatsApp o altrove, non deve far entrare un'altra persona.
- **Alternative**: l'email solo come promemoria.
nota dev: la rimanderei a più avanti, quando integriamo il servizio e mail ma anche fosse non sono convinto serva, anzi, il link è il link, ha una scadenza temporale, e comunque si può usare 1 sola volta, quindi non mi preoccuperei troppo, per altro un nuovo utente di default non vede i dati degli altri, solo nomi broker e nomi utenti.

**Decisione (14/10)**: respinta. Un invito non è legato a un'email: basta il link, perché scade e si usa una volta sola. Se
serve, se ne riparla con il servizio email.

**Attuazione (15/10)**: 🟡 in A5a: l'invito non porta un'email. Entra con A5.

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

**Attuazione (15/10)**: ✅ A4b (`dbf89cdd5`): il cambio password chiude gli altri dispositivi e lascia acceso quello da cui lo fai; un reset da riga di comando, una disattivazione o un declassamento chiudono tutto.

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

**Attuazione (15/10)**: 🟡 CP6 di Piattaforma, committato sul suo ramo (`2c3b00139`, `cb34327e9`): `LIBREFOLIO_BLOCKED`, `LIBREFOLIO_DELETION_DATE`, la pagina di blocco, poche chiamate permesse. Entra dopo la finestra. Il backup per l'admin e il risveglio entrano nell'elenco con i lotti di B e Z. Da sapere: chi non ha fatto login può capire che l'istanza è bloccata, senza vedere dati; resta così (scelta del coordinatore: allargare l'elenco non lo eviterebbe).

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

**Attuazione (15/10)**: ⏳ lotto CP7b di Piattaforma.

#### 14. Versioni scritte a mano a 0.0.0 — 🟢 (H D6, C-84)
- **Oggi**: `pyproject.toml` e `frontend/package.json` dicono 1.1.0, fermi dal 05/08. Nessuno li legge: la versione
  mostrata viene dal tag git, o dal file `VERSION` nell'immagine Docker.
- **Proposta**: 0.0.0, con un commento: «la versione vera viene dal tag».
- **Perché**: un numero sbagliato confonde chi legge il repo e gli strumenti che analizzano le dipendenze.
- **Alternative**: aggiornarle a ogni rilascio, a mano o con la pipeline. Il numero è giusto, ma è un passo in più.

nota dev: si mi piace

**Decisione (14/10)**: approvata.

**Attuazione (15/10)**: ✅ `pyproject.toml` a 0.0.0 (CP5a, `9deb0ea08`); 🟡 `frontend/package.json` con CP5b, committato, dopo la finestra.

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

**Attuazione (15/10)**: ✅ CP5a di Piattaforma (`9deb0ea08`): senza login `/system/info` risponde solo con la versione.

#### 16. Metriche Prometheus, spente di default — 🟢 (H D9, F08)
- **Proposta**: `/metrics` con le richieste, i job dello scheduler, l'ultimo aggiornamento dei prezzi e la dimensione
  del database. Si accende con `LIBREFOLIO_METRICS_ENABLED`.
- **Perché**: il monitoraggio del cloud, e degli homelab con Grafana. Nella specifica è facoltativo.
- **Alternative**: rimandarlo.

Nota dev, è sicuramente una cosa figa, ma la rimanderei

**Decisione (14/10)**: rimandata, fuori dalla 1.3.

**Attuazione (15/10)**: niente nella 1.3.

#### 17. Test del backend organizzati come il codice — 🟢 (TS1)
- **Oggi**: i test del backend sono divisi per tipo (API, servizi…), non per dominio; il catalogo del runner contiene
  236 percorsi.
- **Proposta**: per ora no; si rivaluta a riordino finito, con i numeri.
- **Perché**: costa molto, rende poco, e mentre le sessioni lavorano porterebbe conflitti su quasi tutti i test.
- **Alternative**: farlo alla fine della 1.3.

Nota dev: non credo sia una buona idea era stato pensato così per fare i test a strati, il riorganizzare dei test non mi aspetto cambi il paradigma, al massimo che splitti meglio i file di test, se serve.

**Decisione (14/10)**: respinta. I test restano organizzati a strati (API, servizi…), com'erano stati pensati; al più si
dividono meglio i file di test troppo grandi, quando serve.

**Attuazione (15/10)**: niente: i test restano a strati.

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

**Aggiornamento (15/10)**: la spiegazione sopra vale ancora, ma l'analisi di Backup e Docker l'ha resa più precisa nel
**punto 39** (e il formato della password nel **38**). Puoi saltare il 18 e rispondere al 39: copre anche questo.

**Decisione (15/10)**: assorbito dal **punto 39**, che pone la stessa domanda in modo più preciso: si decide lì.

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

**Aggiornamento (15/10)**: ancora aperto; serve al lotto del profilo gestito di Plugin asset e ricerca.

nota dev: si al togliere il search, ma almeno all'inizio lasciamo che se un utente  proprio vuole può setupparlo manualmente uno di questi provider, poi capiremo se legalmente è un azzardo o una zona grigia, essendo in fondo la sua macchina e offrendo noi i premium, diciamo che servirebbe più da tappa buchi per quei titoli di super nicchia.

**Decisione (15/10)**: nel profilo gestito gli scraper escono dalla ricerca, anche quando il pannello dà un elenco: l'elenco decide solo cosa è permesso. L'utente può comunque assegnarne uno a mano a un singolo asset, con l'avviso «fonte non ufficiale, a tuo rischio». I cambi delle banche centrali restano tutti; nel self-hosted non cambia niente.
**Attuazione (15/10)**: ⏳ nel piano di Plugin asset e ricerca (piano 03, §4.3), lotto del profilo gestito.

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
    - l'editor degli eventi e il CSV continuano ad aggiornare per data e tipo, ma non toccano un evento collegato a transazioni senza conferma.

  Con la proposta della sessione, il giro «esporta il CSV, modificalo, reimportalo» si romperebbe, se l'export non porta
  gli id: va verificato.
- **Alternative**: lasciare com'è e documentarlo; la proposta della sessione, più rigida.
- **Per chi usa già LibreFolio**: il salvataggio non modifica più un evento in silenzio, e chi lo faceva apposta
  riceve un messaggio.

- **Aggiornamento dall'analisi di W (15/10, lotto E1)**:
    - la premessa va corretta: un salvataggio senza id modifica solo un evento **manuale** con la stessa data e lo stesso tipo; uno del fornitore non viene mai sovrascritto. Il caso del fornitore nasce dalla finestra, che dopo il salvataggio rilegge il giorno e può collegare la transazione all'evento del fornitore (I-10 S4);
    - l'export degli eventi non porta gli id: il giro «esporta, modifica, reimporta» si regge su data e tipo, quindi la mia raccomandazione regge;
    - proposta di W, precisata: «+ Nuovo evento» crea sempre; se esiste già un evento, manuale o del fornitore, con  quella data e quel tipo, la finestra lo mostra e offre «Usa questo», «Crea comunque» o «Annulla». Due eventi nello stesso giorno sono ammessi già oggi, per esempio un dividendo ordinario e uno straordinario;
    - **domanda per te**: «Crea comunque» resta?

Nota dev: bhe chat, diciamo che gli eventi per ora come funzione sono un pò abbandonata, quindi non mi ci dedicherei troppo. Per ora abbiamo fatto che un evento automatico è tale se creato dal provider così che in caso di risincronizzazione scompaia, mentre se è manuale resta, ma poi mi pare che abbiamo aggiunto che se una transazione lo linka diventa come fosse manuale. Ad ora per altro penso che l'unico vero effetto sia per il calcolo dei lotti in caso di split, per cambiare il calcolo. Io di tutto questo testo che hai fatto non ho neanche capito il bug quale sia e come si forma, quindi già sarei portato a rimandare, magari spiegamelo un pò meglio prima

**Decisione (15/10, in chat)**: «+ Nuovo evento» non sovrascrive mai. Se esiste già un evento con la stessa data e lo stesso tipo, manuale o del fornitore, arriva un errore e la finestra offre «Modifica questo» (apre l'evento esistente con i suoi valori; solo per quelli manuali), «Usa questo» o «Annulla». Niente «Crea comunque»: due eventi dello stesso tipo nello stesso giorno non capitano. L'editor degli eventi e il CSV continuano ad aggiornare per data e tipo.
**Attuazione (15/10)**: 🟡 lotto E1 di Import e transazioni, in corso.

#### 21. Per cancellare degli eventi serve indicare l'asset — 🟢 (D-W2, I-12)
- **Oggi**: la richiesta che cancella gli eventi accetta una lista di id, di qualunque asset. Una richiesta sbagliata,
  o costruita apposta, può cancellare eventi di altri asset.
- **Proposta**: la richiesta indica l'asset, e si cancellano solo i suoi eventi.
- **Perché**: sicurezza e integrità dei dati.
- **Per chi usa già LibreFolio**: nulla. L'unico chiamante è l'editor degli eventi, aggiornato insieme.

- **Aggiornamento dall'analisi di W (15/10)**: confermata. Gli id di un altro asset tornano «non trovati». L'unico
  chiamante è l'editor degli eventi (una riga di X, aggiornata insieme).

nota dev: ma quindi non ho capito è un bug vero o fantasma? cmq se fosse vero sono daccordo nell'aggiungere la specifica sull'asset da indicare, per evitare errori.

**Decisione (15/10)**: sì. Il problema era vero solo nell'API (l'app manda sempre gli id dell'asset aperto): la protezione serve contro errori futuri.
**Attuazione (15/10)**: 🟡 lotto E1 di Import e transazioni, in corso.

#### 22. Salvataggio degli eventi tutto o niente — 🟡 (D-W3, I-12)
- **Oggi**: un salvataggio di più eventi li scrive uno alla volta. Se una riga è sbagliata, le precedenti restano
  salvate e le successive no.
- **Proposta**: o tutte o nessuna, con l'errore della riga che non va.
- **Perché**: un salvataggio a metà è difficile da capire e da correggere.
- **Alternative**: lasciarlo com'è, ma dire nel messaggio quali righe sono state salvate.
- **Per chi usa già LibreFolio**: un CSV di eventi con una riga sbagliata non salva più nulla, finché la riga non è
  corretta.

- **Aggiornamento dall'analisi di W (15/10)**: ogni elemento si controlla prima di scrivere, con un solo commit per gli
  eventi manuali. Il refresh dei fornitori continua a salvare a blocchi. Un asset inesistente fa fallire la richiesta,
  invece di dire «0 salvati».

Nota dev: si sono daccordo con la logica bulk che proponi, tutto o niente e se fallisce ti dice dove

**Decisione (15/10)**: sì, tutto o niente, con l'errore che dice quale riga.
**Attuazione (15/10)**: 🟡 lotto E1 di Import e transazioni, in corso.

#### 23. Tipi di evento in minuscolo: controllo e correzione dei dati — 🟢 (D-W7, I-09)
- **Oggi**: un tipo scritto in minuscolo o sconosciuto, per esempio da un CSV scritto a mano, viene salvato, e da quel
  momento ogni lettura di quell'evento va in errore 500.
- **Proposta**:
    - all'ingresso, il tipo si porta in maiuscolo e un tipo sconosciuto viene rifiutato con un messaggio chiaro;
    - una migrazione corregge i tipi già salvati in minuscolo, mentre quelli sconosciuti finiscono nel log.
- **Da decidere**: cosa fare degli eventi con un tipo sconosciuto già salvati. Lasciarli e segnalarli (continuano a
  dare errore), oppure eliminarli.
- **Alternative**: solo il controllo all'ingresso, senza toccare i dati salvati.

- **Aggiornamento dall'analisi di W (15/10)**: tutti i fornitori scrivono già i tipi in maiuscolo, quindi il controllo
  all'ingresso non li rompe e l'API non cambia. Per gli eventi con un tipo sconosciuto già salvati, che rendono in errore
  ogni lettura degli eventi di quell'asset, due strade:
    - **A**, prudente: lasciarli e scrivere nel log id, asset, data e importo;
    - **B**: cancellare quelli non collegati a transazioni, scrivendoli nel log; quelli collegati non si possono
      cancellare.

  Come per K-1, un conteggio sulla copia del tuo database aiuterebbe a scegliere.

Nota dev: si sono daccordo a fare upper e se ancora non va impedire il salvataggio, per quelli salvati male l'unica è cancellarli, tanto già ora non vengono visualizzati

**Decisione (15/10)**: all'ingresso il tipo passa in maiuscolo, e uno sconosciuto viene rifiutato. Tipi già salvati: quelli correggibili vanno in maiuscolo, gli altri si cancellano, dopo aver scollegato le transazioni. Lo fa una correzione dopo le migrazioni, non Alembic: il log di ogni riga si vede anche in Docker.
**Attuazione (15/10)**: 🟡 correzione committata sul ramo di Import e transazioni (`313dde70e`); entra con E1.

#### 24. K-1 chiusa senza codice — 🟢 (D-W15)
- **Contesto**: nella 1.2 il Bulk mostrava come «coppia» due cloni dello stesso tipo. La correzione è nell'interfaccia,
  ma i dati salvati prima potrebbero contenere coppie sbagliate. La copia del tuo database ne aveva 0.
- **Proposta**: chiuderla senza codice. La query per trovarle resta scritta nel piano, se servisse.
- **Alternative**: scrivere comunque una riparazione, per le altre installazioni.

nota dev: si sono daccordo, niente codice, parliamo comunque di un caso limite.

**Decisione (15/10)**: chiusa senza codice.
**Attuazione (15/10)**: ✅ K-1 chiusa nel backlog 38 (`13705dd05`).

#### 25. Domanda nuova: chi può modificare i dati condivisi degli asset — 🟢 se resta com'è
- **Oggi**: asset, prezzi manuali, eventi (dividendi, split) e classificazioni sono condivisi fra tutti gli utenti
  dell'istanza. Chiunque abbia fatto il login può crearli, modificarli, unirli e cancellarli, anche chi vede un broker
  solo in lettura. Un familiare che corregge uno split cambia i calcoli di tutti.
- **Proposta**: nella 1.3 resta così, perché gli utenti di un'istanza si fidano tra loro, più una voce nel backlog
  per decidere un modello.
- **Alternative**: solo gli admin; solo chi ha creato l'asset; solo chi ne ha delle posizioni.

nota dev: è corretto, l'istanza è condivisa apposta, è un rischio necessario che uno sbagli, è noto e accettato.

**Decisione (15/10)**: resta così. Una voce nel backlog (W-B24) per un modello futuro.

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

nota dev: aiutami a capire che sono un attimo confuso: davo per scontato che l'operazione corretta fosse fare i cambi di valuta in base alla data dell'operazione, e dopo che tutte queste operazioni sono state portate in valuta target, si applica l'algoritmo, lo stesso che se fossero state fatte tutte già in origine in quella valuta, ad ora quale sarebbe l'errore? negli esempi che mi porti non sono sicuro di aver capito la risposta attuale e quella futura, e quale delle 2 è corretta.

**Decisione (15/10, in chat)**: approvata. La proposta è proprio il metodo descritto qui sopra: ogni operazione convertita al cambio della sua data, poi il calcolo dei lotti. La Dashboard lo fa già; il pannello dei lotti no. In più: le altre parti del codice che fanno un calcolo simile vanno portate a una sola implementazione in `services/financial_math/`, con la regola corretta.
**Attuazione (15/10)**: ⏳ lotto CP-7 di Numeri e analisi; l'inventario è J-14 (lotti, riepilogo, AI Export, una copia della percentuale di guadagno nella pagina broker).

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

nota dev: si buona idea, per coerenza

**Decisione (15/10)**: sì.
**Attuazione (15/10)**: ⏳ lotto CP-14 di Numeri e analisi.

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

Nota dev: si si, mi pare corretto, bisogna ricalcolare ogni volta che cambia uno dei termini della formula, mi pare ovvio, credo che per ora non sia saltato fuori perchè i provider danno dati tutti i gironi, ma meglio correggere l'algoritmo.

**Decisione (15/10)**: sì.
**Attuazione (15/10)**: ⏳ lotto CP-6 di Numeri e analisi.

#### 29. I due «Rolling Return» con lo stesso nome — 🟢 (D-J6, C-71)
- **Oggi**: due indicatori diversi hanno lo stesso nome. Quello della 1.1 usa una finestra in numero di osservazioni;
  il modo nuovo del grafico dell'asset usa una finestra in giorni di calendario.
- **Proposta**: due nomi distinti, «Rolling Return (osservazioni)» e «Rolling Return (giorni di calendario)». Nessuno
  dei due viene ritirato, perché le configurazioni salvate degli utenti usano quello vecchio.
- **Alternative**: ritirare quello vecchio, rompendo le configurazioni salvate dei grafici.

nota dev: più che rinominare sarebbe da capire quello corretto e appliccarlo ovunque, ad ora in quali componenti troviamo le 2 varianti?

**Decisione (15/10, in chat)**: un solo Rolling Return, a giorni di calendario, ovunque. Quello vecchio (finestra in numero di quotazioni, nel menu degli indicatori e nell'AI Export) esce. Le configurazioni salvate, solo nel browser, si convertono una volta con la stessa finestra (30 → 30 giorni): sulle borse l'orizzonte passa da circa 42 a 30 giorni, una riga nel CHANGELOG. La matematica del rendimento va in `services/financial_math/`.
**Attuazione (15/10)**: ⏳ lotto CP-10a di Numeri e analisi. Trovato in più: Volatilità, Sharpe e Beta mostrano «giorni» ma contano le quotazioni, che per loro è giusto: va corretta solo l'etichetta (J-13).

#### 30. L'avviso «nessun prezzo di mercato da oltre 2 settimane» — 🟢 (D-J15, V-11)
- **Oggi**: per un asset valutato al prezzo di una transazione, l'avviso conta le due settimane dalla prima
  transazione. Può comparire anche per un asset quotato ieri.
- **Proposta**: le due settimane si contano dall'ultima quotazione di mercato, così l'avviso compare solo quando è
  vero.
- **Alternative**: cambiare solo il testo dell'avviso.
- **Per chi usa già LibreFolio**: meno avvisi falsi.

Nota dev: si mi pare ottima!

**Decisione (15/10)**: sì.
**Attuazione (15/10)**: ⏳ lotto CP-4 di Numeri e analisi.

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

Nota dev: mi pare un contro senso che in asset global sia ogni 30 e in detail ogni 60, al più lo invertirei.
Comunque sono daccordo che a schermata nascosta e dopo anche solo 2 min di mouse fermo, la richiesta di aggiornamenti venga mandata in pausa, ma appena la schermata ritorna attiva o il mouse si muove, se il tempo passato supera la soglia, mandiamo subito la richiesta senza scrivere nulla. e questo per quanto riguarda l'aggiornamento attivo, triggerato dall'utente mentre è connesso

**Decisione (15/10)**: pausa a scheda nascosta o dopo **2 minuti** senza mouse né tastiera. Al ritorno, se è passato più dell'intervallo, la richiesta parte subito da sola, senza clic. Intervalli invertiti: lista ogni 60 s, dettaglio ogni 30 s, con un solo ciclo nel dettaglio. Riguarda solo l'aggiornamento dal vivo nel browser; lo scheduler resta com'è.
**Attuazione (15/10)**: 🟡 Z1 di Sospensione e risveglio, in corso.

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

Nota dev: alla luce della risposta di prima, il backend direi che deve spegnersi o comnque andare a riposo, dopo 5 min dall'ultimo pacchetto ricevuto, solo non saprei come fare per farlo risvegliare quando ne arriva uno nuovo, tanto nel caso cloud che nel self hosted. In oltre, allo stato attuale abbiamo anche lo scheduler che ogni tanto arriva e deve lavorare, come possiamo fare, c'è una soluzione che ci permetta di non usare una seconda macchina esterna che dia i comandi on e off?

**Decisione (15/10, in chat)**: nel cloud il server si sospende dopo **5 minuti** senza richieste dell'utente (il polling conta come presenza), mai con lavoro in corso. Lo risveglia il proxy di Fly alla prima richiesta: nessuna seconda macchina. Al risveglio lo scheduler recupera da solo i giri persi, come previsto dall'inizio. Resta aperta la possibilità di un risveglio dall'esterno, per esempio a turno ogni 2 ore quando ci saranno le notifiche. Nel self-hosted non si sospende niente.

#### 33. Il risveglio programmato risponde un po' alla volta — 🟢 (Z D7)
- **Contesto**: di notte il pannello del cloud sveglia l'istanza per aggiornare i prezzi, aspetta la fine e legge
  quando svegliarla la prossima volta. Il proxy di Fly chiude una connessione che resta 60 secondi senza dati, e un
  aggiornamento può durare di più.
- **Proposta**: la risposta parte subito e manda uno spazio ogni 15 secondi circa, finché il lavoro non finisce; poi
  arriva il risultato.
- **Alternative**:
    - una risposta immediata «ricevuto», più un secondo indirizzo che il pannello interroga finché il lavoro non è finito;
    - la rete privata di Fly, che però non sveglia da sola una macchina sospesa.
- **Per chi usa già LibreFolio**: niente: è un accordo tecnico con il pannello privato.

Nota dev: come logica mi torna, ma come lo possiamo fare ora senza avere ancora l'istanza controller di fly.io?

**Decisione (15/10, in chat)**: `wake-sync` è un endpoint di ogni istanza (questo repository), acceso solo con `LIBREFOLIO_WAKE_TOKEN`: senza token non esiste. Esegue subito i lavori in scadenza e risponde con l'esito, un po' alla volta per il proxy di Fly. Lo chiamerà il pannello del cloud (repository privato) quando esisterà. **`next_wake_at` per ora no**: servirà quando il pannello terrà un calendario dei risvegli, e aggiungerlo dopo non rompe niente.

#### 34. Pause crescenti quando un fornitore dice «troppe richieste» — 🟢 (Z D9)
- **Oggi**: se un fornitore risponde «troppe richieste» (429), lo scheduler riprova al giro successivo (ogni 10 minuti,
  di default) e il fornitore continua a rifiutare, con il rischio di un blocco più lungo.
- **Proposta**: dopo un rifiuto quel fornitore va in pausa per un tempo che cresce (1, 2, 4… minuti, fino a un
  massimo); i job lo saltano finché la pausa non scade. Acceso di default.
- **Alternative**: spento di default e acceso da variabile, alla lettera della regola «nessun cambiamento».
- **Per chi usa già LibreFolio**: niente, finché un fornitore non rifiuta.

Nota dev: si questo retry esponenziale non è male come idea, a prescindere, da mettere sia nel frontend che nello scheduler.

**Decisione (15/10)**: sì, sia nello scheduler sia nel frontend: il polling rispetta la pausa del fornitore e rallenta a ogni errore.

#### 35. Lo spegnimento ha un tempo massimo — 🟢 (Z D10, C-49)
- **Oggi**: allo stop (un `docker stop`, un riavvio) il server aspetta senza limite i job in corso e le richieste aperte.
  Docker, dopo 10 secondi, lo uccide, con il rischio di interrompere una scrittura nel database.
- **Proposta**: un tempo massimo di circa 8 secondi. I job si interrompono, le richieste si chiudono, lo stato si salva,
  e il server esce in ordine.
- **Alternative**: un tempo configurabile, con il default di oggi (nessun limite).
- **Per chi usa già LibreFolio**: niente di visibile; gli arresti diventano più puliti.

Nota dev: si mi pare un ottima idea di coerenza.

**Decisione (15/10)**: sì, per tutti.

### Nuovo, dalla verifica di Account e accessi (14/10 sera)

#### 36. Cosa vede un utente dei dati degli altri — 🟡 (A-1, A-2)
- **Oggi**: al punto 10 hai scritto che un utente nuovo vede degli altri solo i nomi dei broker e degli utenti.
  Account e accessi l'ha verificato, in sola lettura: con il login, un utente vede anche
    - le email degli admin, dalla ricerca degli utenti;
    - nome e icona di tutti i broker, anche di quelli non condivisi con lui;
    - l'elenco, l'anteprima e lo scarico di **tutti i file caricati**, da chiunque: solo la cancellazione controlla il proprietario. Senza login, poi, si leggono le impostazioni globali: scheduler, durata della sessione, registrazione.
- **Proposta**: correggerlo nella 1.3.
    - Un file caricato lo vede solo chi l'ha caricato, o chi ha accesso al broker a cui appartiene.
    - Nomi e icone dei broker non condivisi solo per l'admin (prima si verifica dove li usa l'app).
    - Le email degli admin non escono dalla ricerca.
    - Le impostazioni globali solo con il login, dopo che la configurazione pubblica di Piattaforma porta fuori quello che serve alla pagina di login.
    - Chi lo fa: i file Piattaforma, i broker Import e transazioni, ricerca utenti e impostazioni Account e accessi.
- **Perché**: in un'istanza condivisa (famiglia, amici, cloud) i file possono essere documenti personali.
- **Alternative**: correggere solo i file e lasciare il resto com'è.
- **Per chi usa già LibreFolio**: chi condivide l'istanza smette di vedere i file e i broker degli altri.
Nota dev: mmm non sono convinto, tutto quello che descrivi è un problema solo se si inscrive qualcuno di indesiderato, e si iscrive qualcuno di indesiderato solo se il tocken di invito viene perso, e comunque vale per 1 persona sola... Posso essere daccordo che i file del broker siano scaricabili solo da un utente che ha almeno il view in quel broker, ma per i file statici comuni, email, asset comuni come loghi o foto, il rischio che qualcuno di indesiderato li ottenga è inferiore rispetto alla scomodità di averli non accessibili, impedirebbero a varie cose della ui di disegnarsi. Cosa ne pensi? vedi altri problemi che non vedo? La filosofia dovrebbe essere di nascondere dati a cui non dovresti avere accesso senza però rompere la ui perchè mancano degli asset da scaricare comuni.

**Decisione (15/10)**: approvata nella forma discussa in chat.
- **File dei broker** (report, estratti): lista, anteprima e scarico solo a chi ha almeno la vista su quel broker.
- **File comuni** (icone, loghi, foto degli asset, risorse statiche): visibili a ogni utente con il login, così la UI
  si disegna sempre.
- **File personali**: un'indicazione dello scopo al caricamento. Dai selettori di immagini il file è comune; dalla pagina
  File è personale, con un interruttore per condividerlo. Un file personale lo vedono chi l'ha caricato e l'admin.
  Per i file già caricati: le immagini diventano comuni, gli altri tipi personali.
- **Restano visibili** i nomi dei broker e degli utenti, e le email.
- **Registrazione**: il default diventa «su invito»; «aperta» solo per scelta dell'admin, segnalata nel pannello
  Sicurezza. Il primo account resta creabile finché l'istanza non ne ha nessuno. Le istanze già «aperte» tengono la loro
  scelta, con l'avviso.
- **Impostazioni globali** solo con il login, dopo che la configurazione pubblica porta fuori quello che serve alla
  pagina di login.
- Chi lo fa: i file personali e comuni Piattaforma, i file dei broker Import e transazioni, registrazione e impostazioni
  Account e accessi.
- **Precisazioni approvate il 15/10 sera** (analisi di Piattaforma): un'immagine personale scelta come icona di un
  oggetto condiviso (asset, broker) diventa comune, con un avviso; i file già caricati non si toccano, lo scopo si legge
  al volo (immagini comuni, altri tipi personali), senza migrazione; un file personale di un altro utente risponde 404,
  così non se ne conosce nemmeno l'esistenza. I report dei broker senza broker seguono la regola dei personali.

#### 37. Le regole della password, uguali dappertutto — 🟢 (A-6)
- **Oggi**: le regole della password (lunghezza, maiuscole, cifre…) sono scritte in quattro posti: l'indicatore di
  robustezza, la finestra del cambio password, la registrazione e la riga di comando. Il server, invece, chiede solo
  8 caratteri: chi usa l'API direttamente può scegliere una password che l'app rifiuterebbe.
- **Proposta**: le regole si scrivono una volta sola nel backend, che le applica anche all'API; il frontend le mostra
  prendendole da lì. Le password già salvate restano valide: le regole contano solo quando se ne sceglie una nuova.
- **Perché**: quattro copie prima o poi divergono, e un controllo solo nel browser si aggira.
- **Alternative**: lasciare le copie e allinearle a mano.
- **Per chi usa già LibreFolio**: niente di visibile nell'app, che le applica già.

nota dev: si sono daccordi in questa centralizzazione, fai in modo che il backend esponga le regole così che il frontend possa correttamente mostrarle e se si aggiornano si aggiorna anche nella ui, però teniamo l'indicatore di sicurezza.

**Decisione (15/10)**: approvata. Le regole della password stanno in un posto solo nel backend, che le espone; la UI
le mostra leggendole da lì, così un cambio si vede subito anche nella UI. L'indicatore di robustezza resta (A6c).

### Backup e Docker (analisi di B, 15/10)

> B ha verificato tutto sul codice: oggi il backup completo risponde «non ancora implementato», e la devWiki lo dava per fatto. Il disegno: uno zip con la forma della cartella dei dati, il ripristino provato sempre prima su una copia, poi
> un riavvio ordinato; Litestream spento finché non lo configuri. Il testo intero è nella cartella della sessione B, e
> andrà nel piano 07 al primo via.

#### 38. Il backup con password usa un formato di LibreFolio — 🟢 (D-B1)
- **Oggi**: dalla UI non si fa nessun backup. La specifica dice «opzione: zip protetto da password».
- **Proposta**: con la password, tutto lo zip va dentro una busta cifrata `.lfbackup`.
    - La password diventa una chiave con scrypt, un metodo lento apposta, così indovinarla costa molto; poi si cifra con AES-256-GCM.
    - Serve solo `cryptography`, che entra comunque per le impostazioni dei plugin: **nessuna dipendenza nuova**.
    - La busta si apre con LibreFolio: dalla UI, o con `dev.py backup decrypt`, anche dentro l'immagine Docker.
- **Perché**: lo zip con password «classico» si apre solo con 7-Zip o Keka, non con il Finder né con Esplora risorse.
  In più ricava la chiave in modo debole e porta una dipendenza nuova.
- **Il rischio**: la busta la costruiamo noi, con pezzi standard e un metodo noto. Passa dalla revisione di sicurezza,
  con dei casi di prova fissi.
- **Alternative**: lo zip con password classico (`pyzipper`); nessuna cifratura, solo un avviso forte.
- **Per chi usa già LibreFolio**: niente, è una funzione nuova.

Note dev: ho bisogno che mi spieghi meglio come l'utente viene a sapere della pw, il punto è che scarichiamo il backup chi lo scarica deve averne diritto, zipare serve principalmente per trasferire meno dati, la pw può aiutare, ma dobbiamo fornirla all'utente, quindi... ne vale la pena? riflettiamo su questo punto assieme.

**Decisione (15/10)**: approvata la busta, con l'estensione **`.lfbk`** al posto di `.lfbackup`. La password non la
genera LibreFolio: la sceglie chi fa il backup, e la ridà per ripristinarlo; se la perde, il backup non si apre più.
La password è facoltativa: senza, il backup è un normale `.zip`. Lotto B4, dopo il ripristino (B3) e la scheda (B5): è
l'unico pezzo di B che può slittare.

#### 39. La chiave d'istanza dentro un backup — 🟢 (D-B2, precisa il punto 18)
- **Oggi**: in `secrets/` c'è solo la chiave d'istanza. Ancora nessuna funzione la usa: la useranno le impostazioni dei
  plugin, per cifrare le chiavi d'accesso ai fornitori.
- **Proposta**:
    - la chiave entra nel backup solo se c'è la password, e solo se l'ha generata LibreFolio. Una chiave data con una variabile, per esempio dal pannello del cloud, non esce mai: la custodisce chi l'ha data;
    - al ripristino l'istanza tiene la sua chiave. I segreti dei plugin del backup si ricifrano con quella; se manca la  chiave vecchia, restano «impostato ma illeggibile: reinseriscilo».
- **Perché**: una chiave per istanza, mai due istanze con la stessa. E uno zip con i dati e la chiave insieme, senza
  password, vale come avere i segreti in chiaro (punto 18).
- **Alternative**: adottare la chiave del backup. È più semplice, ma due istanze finiscono con la stessa chiave, ed è
  impossibile quando la chiave arriva da una variabile.
- **Per chi usa già LibreFolio**: niente.

**Decisione (15/10)**: approvata. Nella scheda l'utente sceglie fra un backup «in chiaro» e uno «sicuro», e il testo
gli spiega la differenza: in chiaro, chi ha il file vede tutti i dati e, su un'altra istanza, le chiavi dei fornitori
vanno reinserite; sicuro, serve la password per aprirlo, non si recupera se la si perde, e porta con sé anche le chiavi
dei fornitori.

#### 40. Dopo un ripristino tutte le sessioni si chiudono — 🟢 (D-B3)
- **Proposta**: dopo un ripristino si rientra con un account dei dati ripristinati. La UI lo dice prima della conferma.
- **Perché**: con `JWT_SECRET` impostato, un cookie di prima potrebbe aprire, nei dati ripristinati, l'account di
  un'altra persona.
- **Alternative**: nessuna sicura.
- **Per chi usa già LibreFolio**: tocca solo chi ripristina.

**Decisione (15/10)**: approvata, con tre precisazioni.
- `JWT_SECRET` non cambia e non va nel backup. Il database ripristinato registra l'ora del ripristino, e ogni cookie
  emesso prima viene rifiutato, qualunque sia il segreto. Senza `JWT_SECRET` il riavvio chiude già le sessioni.
- L'anteprima del ripristino elenca per nome gli admin presenti nel backup e avvisa: «dopo il ripristino entri con uno
  di questi, con la password di allora». Se il backup non ha nessun admin, il ripristino si blocca.
- Recupero dell'admin: nel cloud l'email ci sarà, quindi il caso normale è «password dimenticata» fatta dall'admin
  stesso. Nei casi gravi l'admin scrive all'assistenza, che gli fa mandare l'email di recupero o gli manda direttamente
  il link di reset (`dev.py user reset-link`). In self-hosted ci sono i comandi da terminale (`reset-password`,
  `reset-link`). Un pulsante nel pannello che chiede il link all'istanza va nel backlog.

#### 41. Prima di un ripristino, un backup automatico — 🟢 (D-B4)
- **Proposta**: prima di sostituire i dati, LibreFolio fa uno zip dei dati attuali e lo tiene (solo l'ultimo),
  scaricabile dalla scheda Backup. Se il primo avvio dopo il ripristino fallisce, per esempio per una migrazione,
  rimette da solo i dati di prima.
- **Alternative**: tenere la cartella vecchia invece di uno zip: niente spazio in più, ma niente file da scaricare.
- **Per chi usa già LibreFolio**: niente.

nota dev: si è un ottimo modo di procedere, se tutto va bene il backup si cancella.

**Decisione (15/10)**: approvata, con una modifica. La copia dei dati fatta prima del ripristino serve solo a tornare
indietro: se il primo avvio dopo il ripristino va bene, viene cancellata; se fallisce, LibreFolio rimette da solo i
dati di prima.

#### 42. Si ripristinano anche le copie fatte a mano — 🟢 (D-B5)
- **Oggi**: la 1.2 non ha un backup; la guida dice di copiare a mano la cartella dei dati.
- **Proposta**: il ripristino accetta anche lo zip di una cartella dei dati fatto a mano, senza `manifest.json`: legge
  la versione dal database e lo segnala nel report.
- **Perché**: così «ripristinare un backup della 1.2», chiesto dalla specifica e dai cancelli di rilascio, diventa una
  cosa vera.
- **Per chi usa già LibreFolio**: chi ha una copia della cartella la porta nella 1.3 dalla UI.


nota dev: Non mi complicherei la vita, no, se uno vuole fare un ripristino a mano, va e modifica il docker-compose, noi occupiamoci solo dei flussi "standard"

**Decisione (15/10)**: respinta. Il ripristino dalla UI accetta solo i backup fatti da LibreFolio (con
`manifest.json`). Chi ha una copia a mano della cartella dei dati la rimette da sé, per esempio puntando il
docker-compose a quella cartella; all'avvio le migrazioni la portano alla versione nuova. Il passaggio dalla 1.2 alla
1.3 resta l'aggiornamento sul posto, già coperto dalle migrazioni e dalle correzioni dopo le migrazioni.

#### 43. Il limite al caricamento di un backup lo decide chi ospita — 🟢 (D-B6)
- **Proposta**: la variabile `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`; 0 vuol dire senza limite, ed è il default del
  self-hosted; 500 MB nel profilo gestito.
- **Perché**: nel cloud il cliente è admin, quindi il limite lo deve decidere l'hoster, non chi usa l'istanza.
- **Alternative**: un'impostazione nella UI, che però l'admin potrebbe alzare.
- **Per chi usa già LibreFolio**: niente.

nota dev: si mi piace.

**Decisione (15/10)**: approvata.


**Decise dal coordinatore, salvo tue obiezioni**:
- le proposte 6–9 del §10 del piano reggono sul codice: password facoltativa (formato al 38); scaricamento per il
  pannello con un token separato, spento se non impostato, mai con la chiave; senza un supervisore (Docker, systemd)
  l'app esce comunque e la UI chiede di riavviarla; Litestream copre solo il database, i file viaggiano negli zip;
- percorsi nuovi dell'API per backup e ripristino; via i 4 segnaposto di oggi, che nessuno usa;
- `backup_service.py`, che fa gli export di prezzi, eventi e cambi di un asset, prende il nome `series_export.py`
  (solo il nome);
- la prova «stessi totali» gira in un processo a parte, senza un secondo server;
- immagini anche arm64 (M-1) alla fine, solo se la build regge;
- la divisione di `backup.py` entra per prima; il lotto di W sugli eventi, che aspetta le decisioni 20–23, la troverà
  già fatta.

**Come rispondere su B**: «approvo 38–43 e autorizzo il codice di B», più le eccezioni. Se vuoi pensarci ancora sulla
38 e sulla 39, B può partire lo stesso: i primi tre lotti (divisione di `backup.py`, backup senza password, prova su
copia) non ne dipendono.

### Email (analisi di E, 15/10)

> E ha verificato sul codice: oggi non c'è nessun codice email, e l'opzione «verifica dell'email» delle impostazioni globali è un segnaposto che nessuno legge. Il disegno: SMTP solo da variabili o file, mai nel database né nella UI né nei backup; senza SMTP tutto funziona come oggi (l'admin copia i link). **Nessuna dipendenza nuova.** Il testo intero è nella cartella della sessione E, e andrà nel piano 08 al primo via.

#### 44. Cosa vuol dire «richiedi la verifica dell'email» — 🟢 (D-E7)
- **Oggi**: l'opzione c'è nelle impostazioni globali, ma è un segnaposto: non fa niente.
- **Proposta**:
    - vale per chi si registra mentre è accesa (non per il primo account): l'account nasce disattivo, riceve un link    valido 24 ore (si può rispedire), e il link lo attiva;
    - chi prova ad entrare prima vede «verifica la tua email», con «rispedisci»;
    - l'admin può attivarlo a mano dalla scheda Utenti;
    - gli account di oggi, e quelli creati da riga di comando, non vengono mai bloccati;
    - si può accendere solo se l'email è configurata;
    - nessuna migrazione del database.
- **Il lotto è l'ultimo di E**: se la release stringe, slitta alla 1.4 e l'opzione resta un segnaposto.
- **Alternative**: una colonna nuova nel database con la sua migrazione; oppure lasciarla segnaposto anche nella 1.3.
- **Per chi usa già LibreFolio**: niente, finché un admin non la accende.

nota dev: mi torna quello che scrivi, non ho capito cosa intendi però quando dici "chi entra prima"

**Decisione (15/10)**: approvata. «Chi prova ad entrare prima» è chi si è registrato e prova il login prima di aver
cliccato il link arrivato per email: al posto della sua pagina vede «verifica la tua email», con «rispedisci».
#### 45. I link nelle email dei visitatori solo con `LIBREFOLIO_PUBLIC_URL` — 🟢 (D-E3)
- **Proposta**: le email che partono da una richiesta senza login (password dimenticata, verifica, attivazione
  dell'admin) costruiscono il link solo con l'indirizzo dichiarato in `LIBREFOLIO_PUBLIC_URL`. Senza la variabile, la
  pagina di login resta com'è oggi («chiedi all'admin»). Gli invii fatti dall'admin usano anche l'indirizzo che vede nel
  browser.
- **Perché**: ricavare l'indirizzo dalla richiesta permetterebbe a un estraneo di far arrivare a un utente un link vero
  che punta a un sito suo («link avvelenato»), e di rubargli il token.
- **Alternative**: sempre e solo `LIBREFOLIO_PUBLIC_URL`, anche per l'admin.
- **Per chi usa già LibreFolio**: niente; per avere «password dimenticata» via email serve impostare la variabile, ed è
  scritto nella guida.

Nota dev: mmm ma sai che forse forse è meglio fare solo librefolio\_public\_url, in fondo è una questione di configurazione, al massimo facciamo che all'avvio parte un ping usando il valore impostato in quella variabile e se non raggiunge il server, sul pannello admin compare come altra notifica di miss configuration.

**Decisione (15/10)**: approvata l'alternativa, solo `LIBREFOLIO_PUBLIC_URL`, con un controllo dal browser.
- Ogni link dentro un'email, anche quelle mandate dall'admin, si costruisce solo con `LIBREFOLIO_PUBLIC_URL`. Senza la
  variabile non partono email con link; i link copiati dalla UI restano come oggi (l'indirizzo del browser).
- Il controllo non lo fa il server ma il **browser dell'admin**, perché conta da dove si apre il link: il client può
  parlare con l'istanza da un altro indirizzo (VPN, IP diretto). Usa la sonda dell'indirizzo di A6a: il browser chiede
  un codice firmato e lo verifica su `LIBREFOLIO_PUBLIC_URL`, quindi sa anche se risponde proprio questa istanza.
- Se non risponde, o risponde un'altra istanza, compare un avviso di configurazione nel pannello admin. Dice che vale
  per questo dispositivo: può essere un problema di DNS o di rete, da approfondire.

**Decise dal coordinatore, salvo tue obiezioni** (E):
- invio con la libreria standard in un thread, nessuna dipendenza nuova; nei test un server SMTP finto scritto nei test,
  mai email vere: le corsie dei test non prendono più la configurazione d'istanza dal `.env` (C-96, scritto da H);
- una configurazione SMTP sbagliata spegne l'email e lo dice nel log e all'admin, ma l'avvio continua;
- limite di invii per istanza in memoria, 50 l'ora di default, con `LIBREFOLIO_SMTP_MAX_PER_HOUR`; più
  `LIBREFOLIO_SMTP_REPLY_TO`, che serve al cloud;
- «password dimenticata»: risposta sempre uguale, lavoro in background, limiti per indirizzo IP e per nome, al più
  un'email ogni 5 minuti e 3 l'ora per account; lingua dell'account, poi quella dell'istanza;
- una scheda nuova «Email» nelle impostazioni, solo per gli admin: stato, problemi, «invia un'email di prova» al proprio
  indirizzo; mai host, utente, mittente o password;
- testi delle email nelle 4 lingue, nel backend;
- un'istanza bloccata (CP6 di H) non spedisce niente.

**Come rispondere su E**: «approvo 44–45 e autorizzo il codice di E», più le eccezioni. Il primo lotto (il servizio,
senza UI) non dipende da 44 e 45.

### Import e transazioni (15/10)

#### 46. Le metà di trasferimenti rimaste spaiate, già nei database — 🟡 (V-3, W-B6)
- **Oggi**: cancellare un broker toglie solo il collegamento alla metà di un trasferimento che sta su un altro broker.
  Resta una metà spaiata: i lotti di quell'asset vanno in errore e la Dashboard la conta come capitale portato da fuori.
  Il 13/10 hai deciso che la metà rimasta di un TRANSFER diventa una rettifica (ADJUSTMENT) con la stessa quantità e lo
  stesso costo. W lo scrive ora per le cancellazioni future, e per le altre coppie usa la regola che l'app applica già
  quando una coppia si divide (`SPLIT_TYPE_MAP`): trasferimento di cassa (CASH_TRANSFER) e cambio di valuta
  (FX_CONVERSION) diventano un deposito o un prelievo, secondo il segno, senza asset. In tutti i casi il collegamento va
  via e il resto della riga resta com'è: data, importo, valuta, descrizione, tag.
- **Proposta**: la stessa conversione per le metà spaiate già presenti nei database, come correzione all'avvio (il quadro
  delle correzioni dopo le migrazioni, piano 34): prima una copia del database, poi una transazione sola, i controlli
  (chiavi esterne, conteggi, nessuna metà spaiata rimasta) e il ritorno indietro se qualcosa non torna; una riga di log
  per ogni transazione convertita, anche in Docker.
    - Una metà con il suo costo diventa una rettifica a quel costo. Sul broker rimasto il capitale investito passa dal  valore di mercato all'arrivo al costo, e il guadagno di prima del trasferimento si conta su quel broker (esempio verificato da Numeri e analisi: investito 100 → 80, guadagno 20 → 40).
    - **Una metà senza costo** (dati vecchi: oggi l'app non ne crea più) diventa una rettifica senza costo, segnalata come «costo mancante» con il suo avviso, così l'utente lo inserisce (esempio: investito 100 → 0, guadagno 20 → 120).
    **Domanda per te**: oppure usare come costo il prezzo di mercato del giorno d'arrivo? È più comodo, ma è un costo
inventato.
- Nelle cancellazioni nuove il costo non si perde mai: prima di cancellare il broker si calcola il costo medio della metà che parte, come già fa l'app quando il costo è «Auto». Il cambio dei numeri per chi condivide un broker è scritto nella conferma della cancellazione e nella guida.
- **Prima di decidere puoi vedere cosa cambierebbe nel tuo database**, a server fermo:
  `python -m backend.app.db.post_migration --dry-run` (non scrive niente; elenca le righe, con e senza costo).
- **Perché**: senza, chi ha già cancellato un broker con dei trasferimenti tiene i lotti in errore.
- **Alternative**: convertirle alla lettura, senza toccare i dati; oppure lasciarle, e mostrarle come problema da
  sistemare a mano.
- **Per chi usa già LibreFolio**: chi ha delle metà spaiate vede i lotti tornare calcolati e la Dashboard senza quel
  capitale fasullo. Chi non ne ha non vede niente.
- La correzione entra solo con il tuo ok; il resto del lotto non la aspetta.

nota dev: credo di averti già risposto, comunque si, se una transazione di coppia si rompe, la cosa giusta è trasformare la metà che rimane affinchè dal punto di vista del broker rimasto, continui ad avere lo stesso senso di prima, confermami che la tua proposta mantiene questa filosofia.

**Decisione (15/10)**: approvata; la proposta segue questa filosofia. Per il broker rimasto, la metà che resta ha lo
stesso senso di prima: un trasferimento ricevuto diventa una rettifica in entrata con la stessa quantità e lo stesso
costo; un trasferimento di cassa o un cambio diventa un deposito o un prelievo. Una metà senza costo resta senza costo,
con l'avviso «costo mancante»: nessun costo inventato dal prezzo di mercato. Entrata il 15/10 con W
(`orphan_pair_halves`). Una metà ricevuta senza costo oggi nasce solo da dati vecchi: modulo, Bulk e backend chiedono
il costo; il lotto N2 di W permette di correggere le sole note di quelle righe.

#### 47. Le unità che escono da un broker quando sparisce quello che le riceve — 🟡 (V-3, J-11)
- **Il caso**: il broker A compra 10 titoli X a 20; il 3/10 ne trasferisce 4 al broker B (X vale 25); poi B viene
  cancellato. Su A resta la gamba in uscita del trasferimento, che per come è fatto un trasferimento non porta un costo.
  Guardiamo A il 5/10, con X a 30:
    - **oggi**: Dashboard +80 (le unità escono al valore di mercato), lotti in errore, posizione di 6 unità con 60 di
    guadagno;
    - **applicando alla lettera la decisione del 13/10** (rettifica in uscita senza costo): Dashboard **−20** e lotti
    **−20**, perché le unità uscite contano come perse a prezzo zero. Sembra una perdita, ma l'utente ci ha guadagnato.
- **Proposta (di Numeri e analisi)**: la gamba diventa una rettifica in uscita **con il costo** medio con cui le unità
  partono, calcolato dalla stessa funzione che l'app usa già per il costo «Auto». La Dashboard la legge come
  un'uscita al costo: guadagno 60, come la posizione. Il guadagno di prima del trasferimento viaggia con le unità, come
  succede dalla parte di chi le riceve. Serve una regola nuova nel calcolo FIFO dei lotti: un lotto di Numeri e
  analisi, con un test rosso prima.
- **Intanto** (decisione del coordinatore): si convertono solo le gambe in arrivo; quelle in uscita restano come oggi
  (Dashboard +80, lotti in errore) finché non rispondi.
- **La stessa domanda vale per la divisione di una coppia** (comando già esistente): oggi la gamba in uscita diventa una
  rettifica senza costo, e il guadagno scende del costo delle unità spostate. Se «dividere» vuol dire «non era un
  trasferimento, le unità sono state cancellate», è giusto così; altrimenti vale la stessa regola. Una tua riga copre
  tutti e due i casi.
- **Alternative**: applicare alla lettera la decisione del 13/10 (−20 e −20; sconsigliato); lasciare le gambe in uscita
  come oggi.
- **Per chi usa già LibreFolio**: solo chi ha cancellato o cancellerà un broker che riceveva trasferimenti, o chi divide
  una coppia.

**Decisione (15/10)**: approvata la proposta di Numeri e analisi: «si va mantenuto lo stesso principio nel senso
opposto». È lo stesso principio della 46 visto dall'altra parte: per il broker rimasto, la gamba che resta mantiene lo
stesso senso di prima. Le unità uscite da A portano con sé il loro costo, quindi la gamba in uscita diventa una
rettifica in uscita **con il costo** medio con cui le unità partono, calcolato dalla funzione del costo «Auto».
Nell'esempio: Dashboard e lotti con guadagno 60, come la posizione. Vale per la cancellazione del broker che riceve,
per le gambe in uscita già spaiate nei database e per «dividi la coppia». Serve la regola nuova nel calcolo FIFO dei
lotti: un lotto di Numeri e analisi con il test rosso prima; la conversione delle cancellazioni e dei dati già presenti
la fa Import e transazioni, sopra quella regola.

### Cruscotto e grafici (analisi di Y, 15/10)

#### 48. Un indicatore comune «Aggiornamento…» — 🟢 (C-85, D-Y10)
- **Oggi**: è una tua richiesta del 14/10: «quando un pacchetto è in volo non si ha chiaro che si sta attendendo la
  risposta». Ogni pagina che ricarica i dati fa a modo suo, e spesso non si capisce che sta aspettando il server.
- **Proposta**: un indicatore unico: i dati vecchi restano visibili ma attenuati, con un piccolo badge «Aggiornamento…»
  con la rotellina, e l'attributo di accessibilità `aria-busy`. Prima su Dashboard, pagina broker, Rischio e lotti.
  Si armonizza con «Aggiornamento in pausa» dei prezzi dal vivo (Z1).
- **Alternative**: scheletri grigi al posto dei dati; una barra sottile in cima alla pagina.
- **Per chi usa già LibreFolio**: vede sempre i dati di prima mentre arrivano i nuovi.

Nota dev: no non mi piace che i dati vengano sporcati o che compare un badge per ora farei che nelle pagine, quando si cambia il periodo temporale il pulsante di aggiorna diventa grigio e l'icona inizia a ruotare, come fosse stata premuta, e questa cosa in tutte le pagine che hanno l'aggiorna, tanto i dati di query sono sempre in cima.

La vera domanda che ti faccio è, ci sono pagine in cui questo non è possibile e se si, in quelle cosa potremmo riusare per evitare di essere invasivi?

**Decisione (15/10)**: respinta la proposta del badge; vale la regola del developer. Quando una pagina aspetta il
server (cambio del periodo o altro ricaricamento), il pulsante «Aggiorna» della barra in cima alla pagina diventa grigio
e la sua icona gira, come se fosse stato premuto. I dati restano come sono, senza attenuazione e senza badge. Quel
pulsante dovrebbe essere l'unico «Aggiorna» della pagina: un pezzo che si ricarica da solo fa girare quello, non uno
suo. Tutte le pagine con un periodo hanno già il pulsante in cima (Dashboard, broker, asset, cambi); i pulsanti
«Aggiorna» dentro i pannelli (per esempio quelli del Rischio) si verificano uno per uno nel lotto di Y. Il PAC
(«Calcola») e il wizard d'import tengono i loro indicatori.

#### 49. La liquidità negativa nel grafico dell'allocazione — 🟡 (54-1, D-Y11)
- **Oggi**: con un saldo di liquidità negativo, le quote positive sommano più di 100 %. Il grafico dell'allocazione nel
  tempo ha l'asse fermo a 100 e taglia la cima; tooltip e torta scartano le voci negative, quindi la liquidità negativa
  non compare da nessuna parte.
- **Proposta**: mostrarla sotto lo zero. L'asse va oltre il 100 % quando serve e il tooltip ha una riga negativa; nella
  torta restano le quote positive, con una nota «liquidità negativa: −X».
- **Alternativa**: Numeri e analisi la toglie dal totale nel backend, e il grafico non la vede.
- **Per chi usa già LibreFolio**: tocca solo chi ha liquidità negativa.
nota dev: parliamo del grafico a torta vero? o cosa?

**Decisione (15/10)**: approvata la proposta. Il grafico è soprattutto quello dell'allocazione nel tempo della
Dashboard: la liquidità negativa si disegna sotto lo zero, l'asse va oltre il 100 % quando serve, il tooltip ha la riga
negativa. Nella torta restano le quote positive, con la nota «liquidità negativa: −X». Il backend non la toglie dal
totale: il debito resta visibile.

#### 50. Il PAC sul telefono (difetto 5) — 🟢 (D-Y12)
- **Oggi**: sul telefono la tabella dei target del PAC non sta nella larghezza: i nomi sono tagliati, gli input Target %
  escono a destra, «Actions» sta sopra gli input. Le colonne insieme chiedono più di 500 px.
- **Proposta**: prima la cura generale delle tabelle sul telefono (C-38, la colonna «Azioni» e quella di selezione
  fisse in `DataTable`); se non basta, un layout da telefono apposta per il PAC.
- **Per chi usa già LibreFolio**: niente.

nota dev: intanto facciamo la cura generale, ho anche altre note di problemi che avevo preso, se non basta poi ne riparliamo e vedremo.

**Decisione (15/10)**: approvata la cura generale delle tabelle sul telefono (C-38, lotto Y7). Il layout da telefono
apposta per il PAC si decide dopo, se non basta, insieme alle altre note del developer.

### Le domande della notte 15→16/10 (P1–P26), decise il 16/10

Le domande nate di notte dai lotti dei figli. Il testo intero di ogni domanda è nel registro notturno del coordinatore;
qui resta la decisione.

| Punto | Lotto | Decisione del developer (16/10) |
|---|---|---|
| P1 | E4b | Il riquadro con i comandi per l'admin resta sotto il modulo «password dimenticata», **in un pannello chiuso** |
| P2 | J-17 | Una rettifica **non è mai un prezzo**. **Acquisti e vendite** restano fonti di prezzo. Un asset senza nessuna osservazione, nemmeno un prezzo vecchio, si valuta **al costo, come stima dichiarata** («valutato al costo, nessun prezzo»); con un prezzo vecchio vince quello, segnato come stantio |
| P3 | Y11, decisione 48 | Approvato. «Aggiorna» gira solo per le domande «grandi» decise nella UI: un componente tiene la lista delle richieste in volo, riceve un segnale all'inizio e uno alla fine (riuscita o no), si ferma quando sono rientrate tutte o dopo un timeout lungo. Non gira per l'aggiornamento dei prezzi |
| P4 | W-B34 | La lista degli accessi di un broker **resta aperta**, per decisione |
| P5 | W-B30 | Svuotare un costo manuale **lo cancella** |
| P6 | W-B36b | Sì: in aggiornamento valgono le regole dei tipi, per i campi che cambiano |
| P7 | B3 | Con l'istanza bloccata è bloccato anche il ripristino, nella UI e via API; un ripristino confermato prima del blocco **aspetta lo sblocco** |
| P8 | B5b | Nessun messaggio quando il ripristino riesce; se fallisce, il motivo sulla stessa schermata. Si conferma scrivendo **una parola vera a caso di 6–10 lettere**, senza copia-incolla (controllo solo nella pagina) |
| P9, P10, P10b, P14 | Y7, colori | Visti sul server di prova: vanno bene |
| P11 | B3 | Al ripristino si **revocano i link monouso** (inviti, reset, verifiche), con un solo avviso |
| P12 | B4 | scrypt **`2^15`**; password con le regole e l'indicatore della registrazione, **almeno 12 caratteri** |
| P13 | barra delle Impostazioni | **(a) + (b)**: la barra scorre con la rotella, con una sfumatura sul bordo quando ci sono schede nascoste; le cinque schede dell'admin raggruppate sotto «Amministrazione» con una seconda barra, i link diretti (`?tab=users`…) restano validi. Cornice di A8 |
| P15 | E5b | Sì a un pulsante **«Conferma»** nella pagina di verifica. *Da chiarire*: i testi delle email in un file a parte, modificabile, che il codice si limita a riempire |
| P16 | A7, F02 | Nel cloud **il token lo crea il pannello di controllo** e lo passa per variabile; il self-hosted resta com'è stato costruito; senza email nulla cambia. Con l'istanza bloccata la creazione dell'admin è bloccata anche lei (coordinatore) |
| P17 | E5b | Sì: nel profilo cloud il limite per client legge `Fly-Client-IP` (contratto ad H) |
| P18 | A | Le email sono **uniche senza distinzione di maiuscole** (migrazione 009 di A) |
| P19 | Y, J CP-13a | Sì: il rendimento che recupera una perdita diventa un campo del backend |
| P20 | X CP13 | Via «Prezzo manuale / import»; «Segnalacelo» ci **manda un'email con i dati** della ricerca |
| P21 | J-24 | Ogni importo si converte **al cambio del giorno della sua transazione**, e ogni calcolo si fa nella valuta del report. In più: verificare che tutta la matematica stia in `financial_math` e rivedere gli algoritmi troppo contorti (audit del 16/10) |
| P22 | J CP-3 | Va bene così: **ogni broker risponde del suo tratto**, anche con una perdita dopo il trasferimento |
| P23 | TS1 | **No** ai test speculari: i test sono già tutti nelle cartelle giuste |
| P24 | H-3 | *Aperto*: serve più contesto (dove sta la chiave, che cosa protegge, perché nel cloud è più sicuro) |
| P25 | Y-12 | Sì: il test del selettore «Value presentation» dei lotti si riscrive |
| P26 | J-26 | La sonda dell'AI Export si fa su **una copia dei dati demo** del developer, utente `alfy`. Procedura nella skill `real-data-copy` |

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
- **Migrazioni del database**: la 005 e la 006 sono degli account (token monouso; modalità di registrazione), la 007
  delle impostazioni dei plugin, poi le correzioni dei dati degli eventi (riallineato il 15/10). Chi integra per secondo
  ricollega la catena.
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

- ~~Una sola finestra per installare `cryptography`~~ **fatto il 15/10** (`dc9a5d232`, `cryptography 50.0.2`). Facoltativa
  `tzdata`.
- Docker acceso quando Piattaforma arriva al lotto dell'immagine, e poi per Litestream (Backup e Docker). **Le build Docker
  qui falliscono dentro la VPN aziendale**: la prova dell'immagine 1.3 va fatta fuori dalla VPN, con gli script di H.
- Togliere il tag `test` da GHCR (C-26): è un'azione sul remoto.
- Lato pannello di controllo (repo privato): **una chiave d'istanza diversa per ogni istanza**, generata a caso e mai
  ricavata da una parola d'ordine. Con la stessa chiave, i segreti cifrati di un'istanza sarebbero leggibili da
  un'altra. Serve anche un'azione «reinvia il link di attivazione» (punto 3).
- Lato pannello di controllo (repo privato): le macchine con `auto_stop_machines="off"` e `auto_start_machines=true`,
  perché è l'istanza a decidere quando sospendersi.

### Le decisioni del 16/10 dopo l'audit della matematica (MF)

| Punto | Decisione del developer (16/10) |
|---|---|
| Lotti dell'audit | **Tutti i 16 lotti (A–P) nella 1.3**, in un workstream dedicato (MF) accanto a J |
| D-MF2 | La detenzione di una posizione arrivata con un trasferimento parte **dall'arrivo nel broker**; uno split non la azzera più |
| D-MF3 | Una rettifica negativa di dividendo o interesse **riduce il reddito** anche nei lotti |
| D-MF4 | La cassa che arriva con un trasferimento interno o un cambio porta con sé **la sua divisione fra capitale e rendimenti** |
| D-MF5 | Con prelievi netti, se la card MWRR non ha dati **sparisce anche la linea** del grafico |
| D-MF6 | Variazione del P&L a un giorno, effetto timing, G/L % dei gruppi **dal backend**; le misure interattive (lotti selezionati, intervalli scelti) restano nel browser, dichiarate |
| D-MF7 | Con NAV ≤ 0 il peso sul NAV mostra **«—»** |
| D-MF1 | *Aperto*: togliere `holdings` dal sommario del broker via API (il developer ha chiesto chiarimenti) |
| C-97 | Quantità a **10 decimali**, prezzi a **12**, importi a 6 (issue #43) |
| C-99 | Manuale admin ristrutturato, variabili d'ambiente **divise per categoria**, a fine 1.3 |
