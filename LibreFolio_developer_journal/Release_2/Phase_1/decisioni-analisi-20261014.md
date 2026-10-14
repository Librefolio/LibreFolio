# Le sei analisi della 1.3: decisioni da prendere (14/10/2026)

> Scritto dal coordinatore della 1.3 per il developer, dopo le analisi di Piattaforma, Account e accessi, Plugin asset
> e ricerca, Import e transazioni, Numeri e analisi, Sospensione e risveglio. Ogni sessione è ferma e aspetta il via.
> Il testo completo delle analisi è nelle cartelle di sessione; qui ci sono solo le scelte.
>
> **Come rispondere**: «approvo tutte le raccomandazioni e autorizzo il codice per le sei sessioni», più le eccezioni
> («la 7 no, la 12 così…»). Il primo via libera al codice è tuo: lo inoltro alla lettera a ogni sessione.
>
> Le sigle fra parentesi servono solo a ritrovare la voce nelle analisi.

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

## 2. Decisioni di prodotto (raccomandazione: sì, salvo dove scritto)

### Account e accessi
1. La registrazione passa da sì/no a tre modalità: aperta, su invito, chiusa. Una variabile d'ambiente, se c'è, la
   fissa e blocca il campo nelle impostazioni. (D-A2)
2. «Chiusa» blocca anche gli inviti. (D-A3)
3. L'admin creato dalle variabili d'ambiente nasce solo su un'istanza vuota, con un token di almeno 32 caratteri.
   (D-A4)
4. Limite ai tentativi di login sempre attivo, con soglie larghe e senza variabili nuove. Le soglie non devono
   scattare nei test E2E, che fanno molti login dallo stesso indirizzo. (D-A5)
5. La variabile nascosta che spegne il popup delle donazioni resta nascosta e invariata. (D-A7)
6. Nel profilo gestito spariscono tutti gli inviti a donare; al loro posto «Supporto», se c'è il link. La
   condivisione sui social resta. (D-A8)
7. «Gestisci abbonamento» lo vedono solo gli admin. Il messaggio del limite utenti è generico, senza nomi di piani:
   il nome del piano è del cloud, non del core. (D-A9)
8. Il limite utenti conta gli utenti attivi, gli inviti in attesa e l'admin in attesa; la riga di comando può
   superarlo con un avviso. (D-A10)
9. Il campo «ultima versione vista» entra già nella migrazione degli account, per «Novità dalla tua ultima
   versione». (D-A12)
10. Un invito con un'email vale solo per quell'email. (D-A16)
11. Cambiare o reimpostare la password chiude le altre sessioni aperte. Su `TODO_FUTURI` avevi scritto «ci devo
    pensare»; con il reset via email diventa necessario. (D-A17)

### Piattaforma
12. **Sola lettura** (abbonamento scaduto): resta permesso l'insieme delle due proposte.
    - Da Piattaforma: accesso e uscita, cambio della password, preferenze personali, onboarding, pulizia della cache,
      prezzo corrente, letture ed export.
    - Da Account e accessi: reset della password, attivazione dell'admin, cancellazione del proprio account.
    - Da Sospensione e risveglio: il risveglio programmato.
    - Tutto il resto risponde con un messaggio chiaro. (H D4, D-A15)
13. Header di sicurezza.
    - Sempre: protezione dal riconoscimento del tipo di file e dai riferimenti verso altri siti.
    - Solo nel profilo gestito: divieto di incorporare l'app in un altro sito e CSP in prova, perché in un homelab
      l'app sta spesso in un cruscotto. (H D5)
14. Le versioni scritte a mano in `pyproject.toml` e `package.json` vanno a 0.0.0, con un commento: la versione vera
    viene da git. (H D6)
15. `/system/info`, oggi pubblico con le versioni delle dipendenze e del sistema, va dietro il login; la versione
    resta pubblica su `/system/version`. (H D14)
16. Le metriche Prometheus ci sono, spente di default. (H D9)
17. I test del backend riorganizzati come il codice: proposta no, si rivaluta a riordino finito con i numeri.
    (TS1)

### Plugin, asset e ricerca
18. La chiave che cifra i segreti dei plugin entra negli zip di backup solo se protetti da password. Senza password,
    dopo un ripristino i segreti si reinseriscono. (D-X2)
19. Il profilo gestito senza elenchi espliciti non usa nessuno scraper: la ricerca resta vuota finché il cloud non
    mette il suo elenco o non arriva il fornitore a pagamento. (D-X4)

### Import e transazioni
20. **«+ Nuovo evento» oggi può sovrascrivere un evento esistente** con la stessa data e lo stesso tipo.
    - La proposta della sessione è che un salvataggio senza id non sovrascriva mai.
    - Raccomandazione: il divieto vale per la creazione dalla finestra «+ Nuovo evento», che sul conflitto propone di
      aprire l'evento esistente. Il CSV e l'editor in blocco continuano ad aggiornare per data e tipo, ma mai un evento
      collegato a transazioni senza conferma. Altrimenti il giro «esporta, modifica, reimporta» del CSV si rompe se
      l'export non porta gli id. (D-W1, V-22)
21. Per cancellare degli eventi serve indicare l'asset, così una richiesta non ne tocca altri. (D-W2)
22. Il salvataggio degli eventi è tutto o niente. (D-W3)
23. Una migrazione dati porta in maiuscolo i tipi di evento già salvati: oggi un tipo in minuscolo dà un errore 500.
    (D-W7)
24. K-1 (coppie di tipi sbagliate nel Bulk) si chiude senza codice: la copia del tuo DB della 1.2 ne aveva 0.
    (D-W15)
25. **Nuova domanda**: oggi qualsiasi utente con login modifica i dati globali di un asset (eventi, prezzi manuali).
    - Proposta: nella 1.3 resta così, perché in un'istanza gli utenti sono una famiglia.
    - Va però una voce nel backlog: chi può modificare i dati condivisi.

### Numeri e analisi
26. **P&L dei lotti con valuta estera**: ogni lato nella sua valuta alla sua data. Il costo si converte al cambio
    d'apertura, i proventi al cambio di chiusura.
    - Esempio: 100 USD comprati con il dollaro a 1,00 € e venduti a 110 USD con il dollaro a 0,90 €.
      - Oggi: realizzato +9 €, «di mercato» −10 € su un lotto chiuso.
      - Con la regola: realizzato −1 €, di mercato 0.
      - Il totale resta −1 €, ed è lo stesso realizzato che mostra la Dashboard.
    - Per un lotto aperto in euro e venduto in dollari oggi i proventi sono sbagliati (110 USD letti come 110 €): la
      regola li corregge. (D-J1, T-B5)
27. Riclassificare uno split che ha rettifiche collegate senza costo viene rifiutato, con un messaggio che le elenca.
    Oggi è l'unico modo, dall'app, di creare un costo sconosciuto. (D-J2, P-10)
28. I giorni in cui cambia solo il cambio della valuta di un titolo contano come giorni che muovono il valore. Cambiano
    il valore e le linee in quei giorni; il riferimento dei test si rigenera dopo aver dichiarato date e valori.
    (D-J3, B11)
29. I due «Rolling Return» con lo stesso nome prendono due nomi distinti, senza ritirarne nessuno. (D-J6, C-71)
30. L'avviso «nessun prezzo di mercato da oltre 2 settimane» per un asset quotato ieri: si corregge la regola (la
    tolleranza parte dall'ultima quotazione), non il testo. (D-J15, V-11)

### Sospensione e risveglio
31. La pausa degli aggiornamenti automatici vale per tutti, anche nel self-hosted: si ferma a scheda nascosta e dopo
    10 minuti senza input (0 = mai), e lo chiede la specifica. (Z D2)
32. **Il polling conta come presenza dell'utente**, a differenza di quanto dice alla lettera la specifica.
    - Altrimenti la macchina si sospenderebbe mentre l'utente guarda i prezzi e si risveglierebbe ogni 30 secondi.
    - Con la pausa del punto 31 la macchina si sospende comunque: entro N+1 minuti a scheda nascosta, entro 10+N+1 a
      scheda visibile ma ferma. (Z D4)
33. Il risveglio programmato risponde in streaming quando dura oltre i 60 secondi del proxy di Fly: è un contratto con
    il pannello privato. (Z D7)
34. L'attesa crescente quando un fornitore risponde «troppe richieste» è accesa di default. (Z D9)
35. Lo spegnimento ha un tempo massimo per tutti, circa 8 secondi: è la cura del backend che non si ferma al segnale
    di stop. (Z D10)

## 3. Decisioni di coordinamento (già prese; correggibili)

- **Forma comune del riordino**:
  - un file che entra in un pacchetto tiene il suo nome, cambia solo il pacchetto;
  - i moduli nuovi nati da un taglio hanno nomi brevi per tema;
  - router e schemi grandi diventano pacchetti per dominio (`api/v1/<dominio>/`, `schemas/<dominio>/`), con gli
    stessi URL;
  - la configurazione diventa un pacchetto con una sezione per sessione, così cinque sessioni non scrivono lo stesso
    file.
- **Proprietà**:
  - gli eventi degli asset passano a Import e transazioni dopo che Plugin asset e ricerca ha diviso il router;
  - l'AI Export è di Numeri e analisi;
  - la riga legale nel prompt la scrive Account e accessi;
  - i messaggi d'import tradotti (C-70) sono tutti di Import e transazioni;
  - la matematica dei cambi nei file dei plugin la scrive Numeri e analisi.
- **Migrazioni**: la 005 è degli account, la 006 delle impostazioni dei plugin, poi le migrazioni dati degli eventi.
  Chi integra per secondo ricollega la catena.
- **`npm ci` dal lock**: permesso a ogni sessione quando serve a un controllo. Mai `npm install`.
- **Colori**: il coordinatore colori ha dato gli elenchi esatti dei suoi lotti. Le cartelle degli asset, dei cambi e
  delle transazioni si spostano dopo il suo lotto A, quelle dei grafici dopo il lotto B. Tutto il resto è libero
  subito.

## 4. Cose che servono da te più avanti

- Una sola finestra per installare `cryptography` (impostazioni dei plugin), a corsie ferme. Facoltativa `tzdata`.
- Docker acceso quando Piattaforma arriva al lotto dell'immagine.
- Togliere il tag `test` da GHCR (C-26): è un'azione sul remoto.
- Lato pannello di controllo (repo privato): le macchine con `auto_stop_machines="off"` e `auto_start_machines=true`,
  perché è l'istanza a decidere quando sospendersi.
