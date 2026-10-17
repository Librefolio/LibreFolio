# Proposte UX — U1, U4, U7, U9

Aggiornato alle approvazioni del dev del 2026-09-08, ore 17:08.
U1, U4, U7 e U9 implementati; U7 include il raffinamento del 2026-09-09.
La review R2 ha confermato le superfici R1; la review R3 ha approvato X/Reddit,
broker e aggiornamenti. Round 4 disponibile sulla 6041: sfondo social non
comprimibile, TikTok su Carica e istruzioni concrete per il testo copiato su FB/IG/TikTok.
Checklist corrente: [REVIEW-E-R4.md](REVIEW-E-R4.md).
Checklist R3: [REVIEW-E-R3.md](REVIEW-E-R3.md).
Checklist precedente: [REVIEW-E-R2.md](REVIEW-E-R2.md).
U4 e U9 qui sotto includono le varianti richieste dal dev, che superano i disegni A.

## U1 — Stato della configurazione provider

Non cambia il layout del form. Corregge reset e risposte fuori ordine.

```text
Asset A / configuration A
[Test configuration]  Passed
Current price / history / duration belong to A

Change identifier, provider or parameters -> configuration B
[Test configuration]  Not tested
Old result / duration / provider URL disappear

Response from A arrives late
-> ignored; does not overwrite B or a manual edit
```

Invarianti: esito condiviso fra test automatico e manuale; parametri azzerati
quando rimossi; chiusura/riapertura e A-B-A non recuperano risultati vecchi;
una modifica manuale durante una richiesta non viene sovrascritta.

Stato: implementato. Resta il giro operativo controllato sulle risposte tardive.
Non richiede un nuovo redesign.

## U4 — Colonna uploader nella pagina Files

```text
Files                                 [Grid | List] [Upload] [Refresh]
[Static resources] [Broker reports]

[Name: report________________]

Name                     Uploaded by [sort][filter]     Size     Date
report-a.pdf             [A] Alice             ...      ...
report-b.pdf             [B] Bob               ...      ...
legacy.pdf               [#17] Name unavailable ...     ...
```

```text
Column filter: Uploaded by
  [Search users_____________________]
  [x] Select all
  [ ] [avatar] Alice
  [ ] [avatar] Bob
  [ ] [user] User #17 - name unavailable
  [ ] [user] No uploader information
```

```text
Mobile table: same column, horizontal table scroll.
Filter panel: same multi-selection/avatar/name pattern as the asset filter.
Grid: keeps the uploader filter applied from the table, without extra controls.
```

- Filtro su chi ha caricato il file, NON sul proprietario del broker.
- Colonna ordinabile; filtro multiutente nel pannello colonna gia' generalizzato.
- Nessuna toolbar uploader separata.
- Il passaggio lista/griglia non deve perdere il filtro applicato.
- Tutti, ID non risolvibile e uploader assente sono tre stati distinti.
- Errore nel caricamento dei nomi non elimina i file gia' autorizzati.
- Nessun nuovo permesso; picker e DataTable mantengono i default attuali.

Approvato: colonna, ordinamento, filtro multiplo avatar/nome. Default condivisi invariati.

## U7 — Supporto nel popup e in About, variante aggiornata 2026-09-09

Solo DonationPopup e About. Nessun social nuovo nell'header o login pubblico.

```text
+-------------------------------------------------+
| LibreFolio                                      |
| Support LibreFolio                              |
| Existing message                               |
|                                                 |
| [Coffee] Buy me a coffee                         |
| ---------------- Or share --------------------- |
| [ X ] [ Reddit ] [ Facebook ] [ Instagram ]     |
|                    [ TikTok ]                  |
| Icons open the suggested-message dialog         |
|                                                 |
|                                      [Not now] |
+-------------------------------------------------+
```

In About: stesso blocco dopo sito/repository/licenza, prima delle informazioni
di sistema. Su mobile i pulsanti vanno su righe separate.

```text
Social dialog - second modal
+-------------------------------------------------+
| [X icon] Share on X                        [x]  |
| [Titolo breve: solo Reddit]                     |
| [Messaggio specifico per social e lingua UI]    |
| [Hint reale sulle possibilita' del sito]        |
|                                                 |
| [Chiudi]          [Copia e vai - colore social] |
+-------------------------------------------------+
Original popup stays open underneath
```

Approvazione diretta del dev: icone social, logo corretto anche nella modale,
Chiudi a sinistra e Copia e vai a destra. Nessun campo URL o pulsante Open
separato. Il link pubblico del progetto e' sempre aggiunto alla copia, mai
l'indirizzo privato dell'istanza. Dopo copia riuscita si apre il social in nuova
scheda. Origine conservata; errori clipboard/pop-up espliciti, mai finto "condiviso".

Round 3: nessun tooltip sulle icone; X ha hashtag nella seconda riga; Reddit ha
titolo e corpo separati. Facebook non precompila il messaggio; Instagram e TikTok
non hanno un intento pubblico per precompilare didascalie da questo pulsante:
il testo viene copiato e il sito aperto, con istruzioni trasparenti nella modale.

Round 4: TikTok apre direttamente Carica (login se necessario), non il feed.
Facebook richiede incolla nel messaggio; Instagram richiede Crea (+), foto/video
e incolla didascalia. Nessuna immagine/video generato o pubblicato dall'app.

Le chiusure originarie del popup restano invariate: Non ora e caffe'.
La modale secondaria ha invece chiusura esplicita e ritorno del focus.
DonationPopup e' disabilitato dal normale server TEST: serve il percorso di
review TEST previsto, non la produzione.

Approvato: gerarchia caffe'/social/fallback e collocazione About.
Eventuali raffinamenti dopo la prova della nuova UI.

## U9 — Header desktop e mobile

```text
TOP / NEW ROUTE / SCROLL UP
+--------------------------------------+
| [menu] [coffee] [theme] [EN] [help]   |
+--------------------------------------+
| Page content                         |
```

```text
SCROLL DOWN
Header moves above viewport; layout height stays unchanged
+--------------------------------------+
| Page content continues               |
| No jump by one header height         |
```

```text
MENU / FOCUS / MODAL OPEN
+--------------------------------------+
| Header remains visible and usable    |
+--------------------------------------+
```

- Stesso comportamento su desktop e mobile, come richiesto dal dev.
- Soglie iniziali proposte: 8 px cumulativi in discesa, 4 px in salita.
- Sempre visibile nella fascia iniziale pari alla propria altezza.
- Pin con focus, menu lingua/help, sidebar e modali; ricalibrazione al rilascio.
- Reset su navigazione/resize; safe-area, scroll annidati e reduced motion.
- Nessun salto di layout, flicker o controllo focalizzato fuori schermo.

Approvato: entrambi i formati, stessi pin e assenza di salti.

## Riferimenti estesi originali

File A in sola lettura:

- `/Users/ea_enel/.copilot/session-state/3d6a8e57-b148-4001-af9f-b924bd18417f/plan.md`
- `/Users/ea_enel/.copilot/session-state/3d6a8e57-b148-4001-af9f-b924bd18417f/files/ascii-u4-files-v1.md`
- `/Users/ea_enel/.copilot/session-state/3d6a8e57-b148-4001-af9f-b924bd18417f/files/ascii-u7-support-v1.md`
- `/Users/ea_enel/.copilot/session-state/3d6a8e57-b148-4001-af9f-b924bd18417f/files/ascii-u9-header-v1.md`
