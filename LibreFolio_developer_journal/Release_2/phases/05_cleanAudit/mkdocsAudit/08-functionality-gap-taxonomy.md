# 08 - Tassonomia delle funzionalita' promesse dal manuale

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Sintesi di secondo livello dei reperti in [00_INDEX](00_INDEX.md). Non e' un
> nuovo audit del codice e non aggiunge reperti: riclassifica i 64 gia' dimostrati
> nei report `01`-`07`.

## Scopo

La domanda non e' "quale pagina e' imprecisa?", ma:

> Se volessimo rendere letteralmente vera una promessa del manuale, basta estendere
> un sistema esistente, serve una nuova integrazione, oppure la funzionalita' esiste
> gia' e manca solo la sua documentazione?

Questa tassonomia non raccomanda di mantenere ogni promessa attuale. In molti casi la
soluzione piu' sicura resta correggere il testo al comportamento reale. Le voci nei
primi due blocchi indicano cosa servirebbe **solo se si decide di preservare la
promessa documentata**.

Le funzionalita' di Risk Analysis sono beta e sono escluse: l'assenza di
documentazione pubblica per tali superfici non e' un reperto.

## Regole di classificazione

| Blocco | Criterio |
|---|---|
| 1. Estensione di sistema esistente | Backend/frontend/servizio/validator/parser pertinente esiste gia'; serve wiring, parametro, regola, UI o comportamento aggiuntivo. |
| 2. Nuovo sistema, libreria o integrazione | Il repository non possiede il prerequisito essenziale: sorgente dati esterna, parser/formato, consegna email o piattaforma operativa. |
| 3. Esiste ma non e' documentato | Comportamento osservabile e' gia' implementato; il manuale lo omette, lo nega o lo descrive in modo incompleto. |

Le correzioni esclusivamente editoriali (default, label, percorso, link o wording) non
sono forzate in un blocco funzionale. Sono elencate alla fine per evitare che questa
classificazione venga letta come un nuovo backlog di 64 feature.

## Riepilogo

| Esito | Reperti originali | Significato |
|---|---:|---|
| 1. Estensione di sistema esistente | 13 | Possibile lavoro di prodotto senza introdurre un nuovo dominio tecnico. |
| 2. Nuovo sistema/libreria/integrazione | 4 | Richiede decisione architetturale, dipendenze o operativita' esterna. |
| 3. Esiste ma non e' documentato | 25 | Priorita' documentale: nessuna implementazione prodotto necessaria. |
| Ambiguo | 1 | Prima decidere se la pagina e' refuso o requisito prodotto. |
| Correzione solo documentale/routing/default | 21 | Fuori dai tre blocchi: il comportamento utile non e' assente. |
| **Totale** | **64** | Corrisponde esattamente a [00_INDEX](00_INDEX.md). |

## 1. Funzionalita' da estendere per rendere vera la promessa

| Riferimento | Promessa da rendere vera | Sistema gia' disponibile | Estensione minima | Stato remediation |
|---|---|---|---|---|
| [01 R-11](01_user-core.md) | Preferenza `Date Format` | Preferences utente, i18n e formattazione gia' esistono | Aggiungere preferenza e applicarla ai renderer data; non richiede integrazione esterna. | In attesa (tier S4) |
| [02 F3](02_transactions-brokers-import.md) | Generic CSV importa `TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER` | Pipeline transazioni composte, `link_uuid` e promote esistono | Far emettere al parser le coppie/legami richiesti e passarle alla pipeline batch. | In attesa (tier S6) |
| [02 F4](02_transactions-brokers-import.md) | Quota percentuale assegnabile anche a Editor | Sharing, ruoli e `validate_share_for_role` esistono | Modificare la regola di autorizzazione e coprirne gli invarianti di accesso. | In attesa (tier S5) |
| [02 F6](02_transactions-brokers-import.md) | eToro importa XLSX | Pattern XLSX gia' presente in plugin fratelli Directa/Intesa | Riutilizzare il pattern di parsing XLSX nel provider eToro; non serve una nuova famiglia BRIM. | In attesa (tier S4) |
| [03 F2](03_fx-market-data.md) | Impostazioni grafico FX persistenti | Store grafico e pattern `localStorage` esistono | Serializzare/idratare il `chartSettingsStore` con chiave di contesto. | ✅ Implementato (2026-08-05) |
| [03 F3](03_fx-market-data.md) | Import FX rifiuta header valuta incompatibile | Importer FX riceve gia' base/quote della pagina | Confrontare header CSV con `displayBase`/`displayQuote` prima di salvare. | ✅ Implementato (2026-08-05) |
| [03 F4](03_fx-market-data.md) | Tre task AI Export FX con i nomi documentati | Catalogo AI Export estendibile | Aggiungere/rinominare l'Analysis richiesta nel catalogo e nei contratti; altrimenti correggere la pagina ai due task reali. | In attesa (tier S5) |
| [05 A1](05_admin-installation-operations.md) | `enable_registration=false` blocca registrazioni | Accessor `is_registration_enabled()` gia' esiste | Invocarlo nell'endpoint `register()` e decidere il caso del primo utente. | ✅ Implementato (2026-08-05) |
| [05 A3](05_admin-installation-operations.md) | `max_file_upload_mb` vale anche per report broker | Helper limite upload gia' usato per file statici | Applicare lo stesso controllo all'endpoint broker upload. | ✅ Implementato (2026-08-05) |
| [05 B1](05_admin-installation-operations.md) | `--workers` calcolato automaticamente | Logica CPU-based presente in altro comando `dev.py` | Definire e riusare una formula esplicita per `server --workers`. | ✅ Implementato (2026-08-05) |
| [06A R-03](06a-financial-theory-instruments.md) | ADJUSTMENT positivo senza override crea lotto a costo zero | `TransactionService` e validazione cost basis esistono | Introdurre una policy esplicita per costo zero/omissione, invece del rifiuto attuale. | In attesa (tier S5) |
| [06B B1](06b-financial-theory-indicators.md) | Benchmark composto seleziona frequenze di capitalizzazione | `CompoundSignal` locale e parametri ChartSignal esistono | Aggiungere `compoundingFrequency` e calcolo coerente al segnale/registry. | In attesa (tier S6) |
| [06C F1](06c-financial-theory-performance-risk.md) | CASH_TRANSFER conserva split capitale/rendimenti K/R | `portfolio_engine` gia' calcola entrambe le gambe | Bufferizzare/produrre il rapporto K/R della partenza per classificare correttamente l'arrivo. | In attesa (tier S6) |

### Nota di prodotto

Le voci `03 F4`, `06A R-03` e `06B B1` non sono correzioni meccaniche: il codice
attuale puo' essere intenzionale. Prima di implementarle va confermato che la promessa
del manuale e', in effetti, il requisito di prodotto desiderato.

### Nota di remediation — banda S1-S3 (2026-08-05)

Le 5 voci segnate `✅ Implementato` sono state chiuse da una fleet di agenti
paralleli che ha eseguito la banda di complessita' S1-S3 del backlog trasversale
[14](../14_backlog_per_complessita.md), non da un ciclo dedicato a questa
tassonomia. `05 A1` e' lo stesso difetto gia' tracciato come voce 2.4 in quel
backlog: due audit indipendenti, quello documentale e quello di codice, sono
convergenti sulla stessa riga (`api/v1/auth.py:189`).

`03 F3` merita anche una correzione di gravita', non solo di stato: era stato
classificato come gap documentale, ma la verifica di codice svolta durante la
remediation ha stabilito che si trattava di **corruzione silenziosa dei dati** —
un header CSV di una coppia valutaria diversa non veniva ne' invertito ne'
rifiutato, e i dati sbagliati arrivavano comunque al callback di import. Il fix
aggiunge un rifiuto bloccante visibile; il caso negativo e' ora coperto da un
test E2E dedicato.

`05 A1` ha prodotto una conseguenza operativa che non era prevedibile dall'audit
documentale: rendere *effettiva* l'impostazione ha reso l'intera suite di test API
dipendente dal suo valore, perche' quasi ogni test crea il proprio utente via
`POST /auth/register`. Un `enable_registration` lasciato a `false` da un run
interrotto — prima del tutto innocuo, perche' nessuno leggeva l'impostazione — ora
fa fallire ~50 test con un messaggio che non indica la causa reale. E' stata
aggiunta una fixture di sessione in `backend/test_scripts/conftest.py` che
ripristina il valore all'avvio. Dettaglio completo nella voce A1 del
[report 05](05_admin-installation-operations.md).

Le altre 8 voci del blocco restano fuori banda (tier S4-S6) e non sono state
toccate in questo ciclo. Cronaca completa in
[15 - Esecuzione S1-S3](../15_esecuzione_s1_s3.md).

Resta una correzione solo editoriale, non di remediation: `cli_tools.en.md`
descriveva ancora `--workers` con il comportamento manuale precedente. ✅ Corretta il
2026-08-05 sul solo testo EN (`auto` o `0` attivano il calcolo, un intero lo forza);
le versioni IT/FR/ES della pagina restano da riallineare nel batch multilingua.

## 2. Funzionalita' assenti che richiedono nuovi sistemi, librerie o integrazioni

| Riferimento | Promessa da rendere vera | Prerequisito assente | Cosa servirebbe |
|---|---|---|---|
| [02 F5](02_transactions-brokers-import.md) | Wizard/BRIM accetta PDF, incluso Revolut | Nessun provider BRIM legge PDF; i flussi sono CSV/XLSX | Libreria di estrazione PDF, normalizzazione affidabile delle tabelle, gestione errori e un parser/provider PDF. |
| [03 F1](03_fx-market-data.md) | SNB fornisce rate daily | L'integrazione SNB corrente espone solo medie mensili | Nuova sorgente daily svizzera oppure provider alternativo/fallback e relative semantiche di priorita'/storicita'. Correggere la pagina a "monthly" resta l'alternativa a costo nullo. |
| [05 A2](05_admin-installation-operations.md) | Email verification impedisce accesso fino alla conferma | Non esiste infrastruttura mail/token/verifica | Delivery SMTP/provider, token lifecycle, template, endpoint/UI di verifica, rate limiting e policy privacy/security. |
| [07 R1](07_site-community-gallery.md) | Opzione "Cloud" disponibile accanto al self-hosting | LibreFolio Cloud e' roadmap, non prodotto operativo | Piattaforma hosted multi-tenant, provisioning, dominio/deploy, gestione account, sicurezza/operazioni e probabilmente billing/supporto. |

Queste quattro voci richiedono una decisione di architettura e ownership operativa.
Non vanno trasformate in "piccole correzioni documentali" senza scegliere se il
prodotto debba davvero offrire la capacita'.

## 3. Funzionalita' esistenti ma non documentate

### User core - dashboard, asset, impostazioni

| Riferimento | Capacita' reale non esposta correttamente | Stato remediation EN |
|---|---|---|
| [01 R-04](01_user-core.md) | Vista Performance delle Positions espone le colonne reali, molto piu' ampie delle quattro descritte. | ✅ Aggiornato |
| [01 R-05](01_user-core.md) | Vista Holdings espone otto colonne ulteriori rispetto alla pagina. | ✅ Aggiornato |
| [01 R-06](01_user-core.md) | Time Delta Selector implementa i periodi reali 1W-5Y, non gli esempi 1D/YTD/ALL. | ✅ Aggiornato |
| [01 R-08](01_user-core.md) | Data Editor rileva e accetta anche CSV separato da virgola. | ✅ Aggiornato |
| [01 R-09](01_user-core.md) | justETF ha fallback di current price per valute non EUR. | ✅ Aggiornato |
| [01 R-10](01_user-core.md) | Settings include un tab Profile distinto dalle tre aree dichiarate. | ✅ Aggiornato |
| [01 R-13](01_user-core.md) | Image Crop offre preset Asset Icon 256x256. | ✅ Aggiornato |

### Transactions, import e broker

| Riferimento | Capacita' reale non esposta correttamente | Stato remediation EN |
|---|---|---|
| [02 F1](02_transactions-brokers-import.md) | Wizard BRIM reale a quattro step, con resolution/staging come sezioni dello stesso flusso. | ✅ Aggiornato |
| [02 F2](02_transactions-brokers-import.md) | Parser ereditato da `default_import_plugin` del Broker, con override per file. | ✅ Aggiornato |
| [02 F7](02_transactions-brokers-import.md) | Directa supporta anche XLSX, omesso dalla tabella capacita'. | ✅ Gia' allineato |
| [02 F8](02_transactions-brokers-import.md) | Dedup usa il modello/campi reali, non la descrizione semplificata e incoerente delle due pagine. | ✅ Aggiornato |
| [02 F9](02_transactions-brokers-import.md) | Schwab scarta le righe riepilogo tramite data non valida e mostra warning visibile. | ✅ Aggiornato |

### Admin, deployment e sito pubblico

| Riferimento | Capacita' reale non esposta correttamente | Stato remediation EN |
|---|---|---|
| [05 A4](05_admin-installation-operations.md) | `default_theme` e' presente in schema, servizio e UI ma assente dalla tabella Global Settings. | ✅ Aggiornato |
| [05 A5](05_admin-installation-operations.md) | `scheduler_timezone` esiste ed e' usato; non e' semplicemente "server local time". | ✅ Aggiornato |
| [05 B7](05_admin-installation-operations.md) | Gallery Playwright puo' avviare/riusare test server; non richiede sempre server manuale. | ✅ Aggiornato |
| [05 B9](05_admin-installation-operations.md) | Esistono immagine GHCR e percorso `docker-compose.prod.yml`. | ✅ Aggiornato |
| [05 B11](05_admin-installation-operations.md) | Il caveat backup SQLite/WAL e' gia' noto nel filesystem host, ma manca nel percorso Docker. | ✅ Aggiornato |
| [05 B12](05_admin-installation-operations.md) | `./dev.py install` svolge un quarto step, root npm install. | ✅ Aggiornato |
| [07 R2](07_site-community-gallery.md) | CRYPTO e' gia' supportato end-to-end, non "coming soon". | ✅ Aggiornato |

### Financial theory e motori di calcolo

| Riferimento | Capacita' reale non esposta correttamente | Stato remediation EN |
|---|---|---|
| [06A R-04](06a-financial-theory-instruments.md) | `AssetType.INDEX` e' read-only, selezionabile e senza transazioni. | ✅ Aggiornato |
| [06A R-05](06a-financial-theory-instruments.md) | Crédit Agricole genera controparte WITHDRAWAL per cedole e premi di scadenza. | ✅ Aggiornato |
| [06A R-06](06a-financial-theory-instruments.md) | justETF genera eventi DIVIDEND da chart data. | ✅ Gia' allineato |
| [06A R-07](06a-financial-theory-instruments.md) | Scheduled Investment gestisce late interest/grace period dopo maturity. | ✅ Aggiornato |
| [06B B0](06b-financial-theory-indicators.md) | Benchmark sintetici sono calcolati client-side, senza round-trip backend. | ✅ Aggiornato |
| [06C F2](06c-financial-theory-performance-risk.md) | WAC multi-valuta sceglie una valuta target deterministica diversa dalla "piu' frequente" dichiarata. | ✅ Aggiornato |

## Ambiguo prima della pianificazione

| Riferimento | Perche' non e' forzato in un blocco |
|---|---|
| [06A R-02](06a-financial-theory-instruments.md) | La frase sui DIVIDEND di Scheduled Investment sembra un copy-paste da `interest.en.md`. Se e' refuso, e' correzione documentale; se e' requisito voluto, l'enum eventi e la pipeline Scheduled Investment esistono gia' e diventerebbe estensione del blocco 1. |

## Fuori dai tre blocchi: correzioni editoriali o di routing

Questi 21 reperti restano importanti per qualita' del manuale, ma non indicano
funzionalita' assente o nascosta:

| Area | Riferimenti | Motivo |
|---|---|---|
| User core | `01 R-02`, `R-03`, `R-12` | KPI/versione descritti con label o formule obsolete. |
| FX | `03 F5`, `F6` | Azioni menu e preset gia' esistenti, con elenco UI impreciso. |
| AI Export | `04 R-01`, `R-02`, `R-03` | Conteggio, posizione menu e semantica Entity Directory: correggere testo al contratto corrente. |
| Admin | `05 B2`, `B3`, `B4`, `C1` | Commento CLI, comando/URL non validi e terminologia cache. |
| Sito | `07 R3`, `R4`, `R5` | CDN fallback/config JS, URL morto e framing non verificabile. |
| Financial theory | `06A R-01`, `06B B2-B4`, `06C F4-F5` | Percorso file, default benchmark o link/help routing. |

## Uso consigliato

1. Correggere o confermare le promesse del blocco 2 prima di aprire task tecnici:
   sono decisioni di prodotto/infrastruttura.
2. Per il blocco 1, trasformare ogni riga scelta in un piano tecnico mirato, con test
   del comportamento promesso e aggiornamento della pagina corrispondente.
3. Per il blocco 3, il manuale inglese e' stato aggiornato il 2026-08-05:
   23 voci corrette e 2 gia' allineate. La pipeline traduzioni e la validazione
   completa restano rinviate al batch multi-lingua richiesto dall'utente.
4. Non usare questo file per archiviare i 21 fix editoriali: restano nei report
   originali con riga, fonte e direzione di correzione.
