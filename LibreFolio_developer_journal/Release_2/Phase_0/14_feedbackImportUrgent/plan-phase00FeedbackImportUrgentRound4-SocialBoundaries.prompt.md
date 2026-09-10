# Round 4 - Geometria delle icone e limiti della condivisione

**Data:** 2026-09-09.
**Origine:** feedback diretto del dev delle 15:18, con screenshot/HTML TikTok.
**Precedente:** [Round 3](plan-phase00FeedbackImportUrgentRound3-SocialFeedback.prompt.md).
**Stato:** ✅ pronto tecnico 2026-09-09; dati originali ripristinati e R4 servita.
**Accettato dal dev:** badge e sottotesti confermati il 2026-09-09 alle 15:51.
**Ultima richiesta:** ingresso diretto Crea Instagram, esito nella sezione 4.
**Promozione dello stream:** condizionata dal dev a quest'ultima rifinitura;
non registrata come autorizzazione di merge.
**Integrato con SHA:** no. **Archiviato:** no.
**Consegna portabile:** [manifest](manifest-integrazione-E.md) e
[checklist](checklist-review-E.md). Accettazione dev, integrazione e archivio distinti.

## Accettazione operativa registrata

Il dev ha provato tutti e cinque i social: le destinazioni si aprono; X e Reddit
ora funzionano come richiesto. Broker e controllo aggiornamenti sono approvati.
Non riaprire questi percorsi, salvo verificare che i ritocchi non li alterino.

Alle 15:51 il dev conferma anche le icone circolari e il sottotesto esplicativo.
Chiede ancora se Instagram puo' aprire direttamente Crea, prima di promuovere lo
stream. Questa richiesta e' distinta dalla precompilazione della didascalia.

## 1. Badge social - ✅ completato 2026-09-09

Il contenitore `h-10 w-10` con `flex-shrink:1` si restringeva accanto a istruzioni
lunghe, diventando ovale. Mantenerlo 40x40, circolare e non comprimibile. Il testo
deve andare a capo, non essere nascosto; chiusura sempre raggiungibile.

> **Note implementazione (2026-09-09):** `shrink-0` e `rounded-full` sul badge,
> colonne testo `min-w-0 flex-1`, chiusura non comprimibile. Hook geometria dedicato.
> Test-author incaricato della geometria reale per tutti i social in italiano,
> desktop e mobile; nessun falso test di layout in jsdom.

> **Note implementazione (2026-09-09, verifica):** il browser misura badge 40x40,
> SVG 24x24, testo italiano lungo che va a capo senza clipping e chiusura nel
> viewport per tutti i cinque social, desktop e mobile. La prova aspetta la
> geometria finale della transizione, non una durata arbitraria; solo il testo
> effettivamente lungo deve occupare piu' righe.

## 2. Facebook, Instagram e TikTok - ✅ ricerca e ritocchi completati 2026-09-09

- **Facebook:** il dialogo pubblico condivide il link, non precompila il messaggio.
  I parametri ufficiali del Share Dialog non prevedono il testo dell'utente.
  Non usare `quote` come scorciatoia non affidabile o aggirare le regole Meta.
- **Instagram:** il sito richiede Crea (+), scelta di foto/video e didascalia.
  L'API di pubblicazione richiede account professionale, autorizzazioni e media:
  tutto fuori da questo mandato. Nessun percorso di precompilazione browser
  verificato per un semplice testo/link.
- **TikTok:** verificato il percorso pubblico `https://www.tiktok.com/upload`;
  senza login rimanda all'accesso preservando quella destinazione. Aprire Carica,
  non la home, e indicare scelta video/incolla. Nessun upload automatico.
- **Web Share API:** puo' aprire il pannello di condivisione del dispositivo, ma
  non seleziona una specifica app e non garantisce che l'app ricevente accetti il
  testo. Non sostituisce in modo equivalente i pulsanti social approvati.

Riferimenti:
[Meta Share Dialog](https://developers.facebook.com/documentation/sharing/reference/share-dialog/),
[Instagram Content Publishing](https://developers.facebook.com/documentation/instagram-platform/content-publishing),
[TikTok Upload](https://www.tiktok.com/upload),
[TikTok Content Posting](https://developers.tiktok.com/docs/en/content-posting-api-get-started),
[MDN Navigator.share](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share).

> **Note implementazione (2026-09-09):** TikTok punta a Upload. Facebook/Instagram/
> TikTok mantengono il testo completo e il link pubblico negli appunti; hint e
> toast successivo spiegano il passo manuale concreto. Il toast certifica la copia,
> non la pubblicazione. X/Reddit, palette, dialogo, protezioni opener/Referer e
> gestione dei fallimenti restano invariati. Nessuna API/account/media introdotta.

> **Note implementazione (2026-09-09, verifica):** 5 test builder e 41 componenti
> passati. La destinazione TikTok `/upload`, il payload completo negli appunti e
> l'assenza di Referer sono verificati nei browser desktop/mobile con intercetto
> del solo sito esterno. I toast spiegano il passo manuale senza affermare che
> esista un post gia' preparato/pubblicato. Il limite FB/Instagram non e' un
> difetto dichiarato risolto.

## 3. Verifica, changelog e handoff - ✅ completato tecnico 2026-09-09

Richiedere solo una finestra mirata dopo consegna dei test: unit supporto/builder,
geometria browser e destinazione Upload. Non eseguire nuovi run mentre la coda e'
al coordinatore. Prima di test che preparano dati, ricontrollare lo stato originale
E e conservarlo coerentemente in privato; mai usare uno snapshot storico come
stato corrente. Ripristinare dopo i test mantenendo il nuovo bundle.

Aggiornare il changelog in preparazione v1.1.1 e la checklist in italiano.
La consegna deve separare il badge corretto dal limite esterno di precompilazione:
Facebook/Instagram non diventano post precompilati grazie a questi ritocchi.

> **Note implementazione (2026-09-09, 15:38):** VIA R4 completo ricevuto dal
> coordinatore; autore idle prima dei run. Nuovo backup privato coerente dello
> stato corrente, non riuso del backup R3. Verificato PID/cwd 94074 prima di
> fermare esclusivamente E; originale messo da parte a handle chiusi. TEMP
> popolato senza force, build/API sync completati con zero errori/warning.
> I quattro E2E mirati (badge/reflow e TikTok/privacy nei due formati) passano.
> X/Reddit/broker/update non modificati né riaperti.

> **Note implementazione finali (2026-09-09):** tutti gli upload/sidecar e
> i due CSV corrispondono al nuovo backup R4; hash DB freddo identico prima/dopo
> ripristino. Il temporaneo e' stato rimosso dal percorso operativo solo dopo
> stop del processo E e verifica handle chiusi. Backup e risultati restano privati;
> nessuno e' incluso nel manifest. Build R4 mantenuta e servita su 6041/PID 4932,
> cwd E, no scheduler/reload/force.
>
> Index on-disk e GET/:
> `99a7587a1a1ff3b09a3a676fa01151bcbb98f351f26ce9fe3d4f72e730e75b05`.
> Traduzioni: 2566 chiavi complete nelle quattro lingue. Dopo il successivo
> Round 5, il manifest finale copre 116 path modificati: 109 nel pacchetto E
> (101 file applicativi/test/documentazione + 8 file journal14) e 7 registri
> del coordinatore esclusi (4 file09, 2 wiki, `TODO_FUTURI.md`). La riga
> directory journal14 non e' un file. Rimandi journal risolvibili. Nessun
> merge, staging, commit o archiviazione effettuato.
> L'accettazione umana R4 resta aperta, separata dalla consegna tecnica.

## 4. Ingresso diretto a Crea su Instagram - verifica conclusa 2026-09-09

**Esito:** non adottato; nessun ingresso web pubblico affidabile dimostrato.
Non e' un fix implementato o una limitazione dichiarata accettata dal dev.

Il candidato [instagram.com/create/select/](https://www.instagram.com/create/select/)
e' stato controllato con una richiesta pubblica senza account o cookie personali.
La risposta HTML identifica una pagina **profilo**, non un compositore:
`og:type=profile`, canonical `/create/` e app link iOS
`instagram://user?username=create`. Sostituire la home con questo indirizzo
potrebbe quindi aprire un profilo estraneo. HTTP 200 o un parametro di ritorno
dal login non bastano a dimostrare una funzionalita' di creazione.

La ricerca pubblica non ha fornito un contratto supportato equivalente a
TikTok Upload. Questo non prova come si comporti ogni sessione Instagram
autenticata: non sono stati aperti account personali o simulati esiti del
compositore remoto. Gli schemi nativi dipendenti dall'app non sono un sostituto
affidabile del flusso web desktop/mobile.

> **Note implementazione (2026-09-09):** mantenuto il flusso gia' consegnato:
> copia della didascalia, apertura Instagram, Crea (+), media e incolla.
> Nessun parametro di precompilazione, nuovo codice, traduzione, build, test
> o riavvio. La build R4 e i dati della review restano invariati.
>
> **Note tracciamento (2026-09-09):** piano principale, manifest e checklist E
> aggiornati con accettazioni puntuali e limite verificato. Richiesta al
> coordinatore la riconciliazione dei need canonici 09/master/README/TODO e wiki,
> di sua ownership; nessuna copia delle versioni storiche del worktree E.

→ Seguito bloccante:
[Round 5 - autenticazione pubblica GHCR](plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md).
