# Review E - Round 3

**Disponibile:** 2026-09-09, `http://127.0.0.1:6041`.
**Build:** R3 debug, index SHA256
`e5f091dd6d5521e473281fdbbde6d01140fcef20008615edc4b4516bf6906256`.
**Dati:** ripristinato lo stato originale dopo la review delle 12:36, con
upload/sidecar e CSV invariati. Ricaricare la pagina per caricare il nuovo bundle.

## Social - About e popup

Qualsiasi utente autenticato; nessun dato di portafoglio necessario.

1. Impostazioni > About: cinque icone X, Reddit, Facebook, Instagram e TikTok,
   senza tooltip. Ogni icona apre la sua modale.
2. Cambiare lingua dell'interfaccia e riaprire: messaggio e indicazioni seguono
   EN/IT/FR/ES. Ogni social usa un testo specifico; X ha gli hashtag nella seconda riga.
3. Reddit mostra titolo breve e corpo separati. Copia e vai richiede un post di
   testo; se il sito non precompila il corpo, incollare il contenuto gia' copiato.
4. Copia e vai usa il colore del social. Il link pubblico del progetto e' sempre
   nella copia, senza campo URL. La schermata originale resta aperta.
5. Facebook apre la condivisione del link: il messaggio si incolla manualmente.
   Instagram e TikTok aprono il sito dopo la copia: non supportano la precompilazione
   di didascalie da questo pulsante. Creare il proprio contenuto e incollare il testo.
6. Clipboard negata o popup bloccato: feedback esplicito, senza finto successo.
   Nessuna pubblicazione automatica.

Il popup donazione riusa le stesse azioni. Il normale server TEST ne disabilita la
comparsa automatica; sulla build debug resta il percorso esistente
`window.librefolioDebug.showDonationPopup()`. Non usare la produzione per mostrarlo.

## Broker

Usare un proprio broker e nomi sintetici.

1. Aggiungi broker con un nome gia' presente: compare l'errore localizzato.
2. Chiudi e conferma lo scarto; scegli di nuovo Aggiungi: form nuovo senza errore precedente.
3. Inserisci un nuovo nome e salva: creazione riuscita, toast verde e nuova scheda.
   Il toast eliminazione gia' approvato resta invariato.

## Aggiornamenti

Sidebar > versione > Verifica aggiornamenti. Se il controllo riesce e la versione
e' corrente: «Sei aggiornato alla versione piu' recente!» e, a capo,
«Versione rilevata online: v...». Errori di rete o disponibilita' non diventano
messaggi di aggiornamento riuscito.

## Gia' approvato nella review precedente

Selezione file, creazione asset, inspector, bulk, Files e header desktop/mobile:
nessun nuovo cambiamento richiesto in R3. Le relative voci restano nel changelog
di preparazione v1.1.1. Questa checklist non registra in anticipo l'accettazione
umana degli ultimi dettagli.
