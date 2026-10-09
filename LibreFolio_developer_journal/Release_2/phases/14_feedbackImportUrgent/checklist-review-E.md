# Checklist portabile - Gruppo E

Questa checklist usa soltanto account e dati sintetici propri. Non richiede
file personali, directory di sessione, screenshot o log precedenti.
Stato delle revisioni: [manifest di integrazione](manifest-integrazione-E.md).

## Ambiente

Usare un'istanza TEST isolata, nella corsia concordata con il coordinatore:

```bash
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py front build --debug
LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py server --test --host 127.0.0.1 --no-scheduler --no-reload
```

Non fermare processi estranei, usare force o inizializzare un DB contenente la
review di altri. La build debug abilita il percorso esistente
`window.librefolioDebug.showDonationPopup()`; non passare in produzione per
mostrare il popup, disabilitato automaticamente dal server TEST.

## Prove manuali

| ID | Account/fixture | Click reali | Atteso |
|----|----------------|-------------|--------|
| E1/E2 | Utente autenticato, proprio asset sintetico con descrizione e distribuzioni | Importa un report riferito all'asset; review > Ispeziona/modifica; salva solo nome, riapri | Descrizione/distribuzioni restano; cancellazione esplicita distinta |
| E1 valuta | Stesso asset con un prezzo manuale proprio | Modifica valuta nel wizard; annulla, poi conferma se si vuole provare il wipe | Dialogo davanti al form, valori interpolati; annulla non elimina dati |
| E3 | Broker proprio con saldo EUR sintetico sufficiente | Bulk > Aggiungi; scegli broker prima del tipo FX; date e importi distinti; Applica, riapri, salva | Form completo, date e decimali conservati; saldo insufficiente rifiutato senza parziali |
| E4 | Identificativo sintetico non presente, poi asset creato esplicitamente | Parser Generic CSV; Crea/collega; secondo import o refresh | Prima creazione manuale spiegata; match univoco successivo, ambiguo mai forzato |
| R1 file | Due broker propri, almeno sei report nel primo | Upload nel primo; pagina Seleziona; seleziona su piu' pagine, fold/unfold | Default cinque, controlli accessibili, solo destinatari aperti, scelte conservate |
| E7/E8 | Batch sintetico con deficit giornaliero e FX retrodatata | Click righe nel warning; cambia sort e pagina | Gruppo completo evidenziato; primo match nell'ordine attuale; checkbox indipendenti, coppie unite |
| E5/R3 broker | Un broker proprio con nome sintetico | Aggiungi duplicato; chiudi/scarta; nuova aggiunta, nome diverso; elimina il nuovo | Errore localizzato e azzerato al reopen, toast verde creazione/eliminazione soltanto dopo successo |
| E9 | Utente autenticato | Versione sidebar > Verifica aggiornamenti | Esito positivo in due righe con vera versione online; errore non equivale ad aggiornato |
| U1 | Asset con provider, risposte differite nei test se necessarie | Cambia provider/parametri durante probe; chiudi/riapri sezione | Risultati vecchi non sovrascrivono contesto o modifiche manuali |
| U4 | File autorizzati con uploader diversi | Ordina/filtra per Caricato da, cambia lista/griglia e ricarica URL | Avatar/nome e multiselezione, scelte conservate, assente diverso da ID ignoto |
| U9 | Pagina lunga, desktop/mobile | Scorri giu'/su; apri menu/modale; cambia pagina | Header senza salti, pin focus/menu/modale, cleanup e reduced motion |
| U7/R4 | Qualsiasi utente autenticato; nessun portafoglio richiesto | About > ogni icona; IT e altre lingue; Copia e vai; popup debug | Messaggi specifici, icona circolare 40x40 non compressa, Chiudi/Copia e vai, origine conservata |

Per ricreare il CSV manualmente usare il contratto del
[developer guide Generic CSV](../../../../mkdocs_src/docs/developer/backend/brim/generic_csv.md):
un file per broker, sette colonne standard; valori indipendenti di propria
invenzione, non trascritti da un ledger reale. Le regressioni registrate in
`frontend/e2e/transactions/` generano gia' report minimi e identita' proprie.

## Limiti social da mostrare, non nascondere

- X: testo, hashtag e URL pubblico.
- Reddit: titolo breve e corpo separati; incolla il corpo gia' copiato se il sito
  non accetta i parametri. Nessuna promessa di pubblicazione automatica.
- Facebook: dialogo link; testo da incollare nel messaggio.
- Instagram: Crea (+), media, didascalia da incollare.
  Il candidato `/create/select/` non e' adottato: la risposta pubblica
  identifica un profilo, non un ingresso affidabile al compositore.
- TikTok: pagina Upload, login/media se richiesti, didascalia da incollare.
- Clipboard negata: niente navigazione social. Popup bloccato dopo copia: avviso
  esplicito. Nessun account, URL privato d'istanza o dato finanziario nel payload.

## Registrazione del feedback

Per ogni prova annotare revisione/hash del bundle, ruolo, formato desktop/mobile,
esito e richiesta eventuale nel round pertinente. Non inserire dati personali.
Un test automatico verde non sostituisce l'accettazione del dev; un'accettazione
non sostituisce lo SHA di integrazione o lo stato archivio.

**Feedback 2026-09-09, 15:51:** badge e sottotesti confermati dal dev. Ultima
richiesta su Crea Instagram investigata senza modificare il bundle; limite
documentato nel Round 4, non trasformato in una falsa funzionalita' completata.
