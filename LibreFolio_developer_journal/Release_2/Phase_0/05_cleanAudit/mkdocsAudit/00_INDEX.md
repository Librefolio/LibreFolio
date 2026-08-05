# Audit MkDocs EN vs codice — indice

> **Release 2 · Phase 0 · 05_cleanAudit**
>
> Modalita': sola verifica. Nessuna correzione di codice, documentazione o traduzioni
> fa parte di questo audit.

## Baseline

| Campo | Valore |
|---|---|
| Acquisito | `2026-08-05T10:54:55+02:00` |
| Branch | `dev_release2` |
| Commit HEAD | `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103` |
| Stato worktree | Dirty; elenco completo in [00_BASELINE](00_BASELINE.md) |
| Impronta manifest | `ea01e8f86bd36a9b36f68e83336ee0e174ff35e6d67336922420d8471f235107` |
| Pagine in scope | 182 pagine inglesi pubblicate, non-developer |

Il confronto usa il worktree alla baseline, non soltanto `HEAD`: l'altro stream di
cleanup aveva modifiche locali gia' presenti. Alla chiusura l'audit segnala ogni drift
successivo che potrebbe invalidare una prova.

## Scope confermato

Inclusi:

- tutte le pagine pubblicate `mkdocs_src/docs/**/*.en.md`, tranne
  `mkdocs_src/docs/developer/**`;
- le cinque pagine utente AI Export;
- comportamento backend, frontend, API, CLI e test necessario a verificare una claim.

Esclusi per ora:

- guida developer, anche se pubblicata;
- traduzioni IT/FR/ES, output `site/`, materiale MkDocs non pubblicato;
- funzionalita' Risk Analysis beta: la loro assenza dalla documentazione pubblica non
  e' un reperto;
- correzioni dei reperti.

La guida developer ripartira' solo dopo autorizzazione esplicita dell'utente e con una
nuova baseline.

## Criterio di evidenza

Ogni reperto deve indicare pagina/heading/linea, claim, controprova nel sorgente con
file/linea, classificazione, gravita' e confidenza. Le classificazioni sono:

| Tipo | Significato |
|---|---|
| Contraddizione | La pagina afferma un comportamento incompatibile con il codice corrente. |
| Dettaglio obsoleto | Il comportamento esiste ma nomi, percorso o parametri non coincidono piu'. |
| Omissione | Una capacita' o vincolo osservabile manca dalla pagina pertinente. |
| Limite non documentato | Il codice impone un vincolo che la pagina lascia intendere assente. |
| Navigazione/link | Nav, link o riferimento a sorgente non porta a una destinazione valida. |
| Non verificabile | La claim non e' dimostrabile dal repository locale; non e' trattata come bug. |

Gravita': `critical` = rischio dati/sicurezza/operativita'; `major` = guida a un esito
sbagliato; `minor` = imprecisione senza esito funzionale; `info` = miglioramento o
incertezza da confermare.

## Copertura e report

Legenda severita' nella colonna risultati: `C/M/m/i` =
`critical` / `major` / `minor` / `info`.

| Report | Pagine | Risultati (`C/M/m/i`) | Stato |
|---|---:|---:|---|
| [01 — User core](01_user-core.md) | 28/28 | 11 (`0/7/3/1`) | Completato |
| [02 — Transactions, brokers, import](02_transactions-brokers-import.md) | 38/38 | 9 (`1/5/3/0`) | Completato |
| [03 — FX e market data](03_fx-market-data.md) | 15/15 | 6 (`1/3/2/0`) | Completato |
| [04 — AI Export](04_ai-export.md) | 5/5 | 3 (`0/1/2/0`) | Completato |
| [05 — Admin e operazioni](05_admin-installation-operations.md) | 8/8 | 14 (`4/7/2/1`) | Completato |
| [06A — Teoria: strumenti e fondamenti](06a-financial-theory-instruments.md) | 34/34 | 7 (`0/3/3/1`) | Completato |
| [06B — Teoria: indicatori e benchmark](06b-financial-theory-indicators.md) | 27/27 | 5 (`0/1/3/1`) | Completato |
| [06C — Teoria: performance e rischio](06c-financial-theory-performance-risk.md) | 20/20 | 4 (`0/3/1/0`) | Completato |
| [07 — Sito, community, gallery](07_site-community-gallery.md) | 7/7 | 5 (`0/3/1/1`) | Completato |
| **Totale non-developer** | **182/182** | **64 (`6/33/20/5`)** | **Completato** |
| Developer guide | 103 pagine EN-only | Non auditata | Sospeso su richiesta |

Il conteggio `64` e' il numero di reperti nei report: una stessa correzione di
prodotto puo' comparire in piu' pagine quando ciascuna superficie documentale induce
un errore distinto. Non sommare automaticamente i reperti come 64 bug indipendenti.

Per una lettura per investimento tecnico, vedi
[08 - Tassonomia delle funzionalita' promesse](08-functionality-gap-taxonomy.md):
separa estensioni di sistemi esistenti, nuove integrazioni e capacita' gia' presenti ma
non documentate, senza aggiungere nuovi reperti.

## Priorita' di lettura

I sei reperti `critical` non sono semplici problemi editoriali: la documentazione
promette protezioni, un comando o una capacita' che non funzionano nel worktree
attuale.

| Priorita' | Report | Reperto | Motivo |
|---:|---|---|---|
| 1 | [05](05_admin-installation-operations.md) | A1, A2 | Global Settings espone registrazione disabilitabile e verifica email, ma nessuna delle due protezioni e' applicata. |
| 2 | [02](02_transactions-brokers-import.md) | F3 | Generic CSV documenta `TRANSFER`/`FX_CONVERSION`/`CASH_TRANSFER`, ma il plugin li rifiuta: import guidato verso un esito impossibile. |
| 3 | [03](03_fx-market-data.md) | F1 | SNB e' presentato come daily mentre il provider produce medie mensili; impatta aspettative su serie e conversioni. |
| 4 | [05](05_admin-installation-operations.md) | B3, B4 | Un comando MkDocs documentato fallisce e l'URL di bootstrap documentato restituisce 404. |

I report restano la fonte per direzione di correzione e citazioni. Questo indice non
propone modifiche o ordini di implementazione.

## Correlazioni e deduplica

- **Global Settings vs. comportamento server**: [05 A1-A2](05_admin-installation-operations.md)
  conferma dal manuale admin gli stessi difetti funzionali gia' emersi nel clean audit
  API. Vanno trattati come un unico intervento di prodotto, poi la pagina admin va
  riallineata al comportamento scelto.
- **Catalogo AI Export**: [04 R-01/R-02](04_ai-export.md) e
  [03 F4](03_fx-market-data.md) toccano catalogo/posizione UI AI Export in superfici
  diverse. Non sono duplicati editoriali: uno riguarda conteggio e collocazione del
  menu, l'altro task FX esposti; la fonte di verita' condivisa e' il catalogo corrente.
- **UI evoluta piu' rapidamente del manuale**: [01](01_user-core.md),
  [02](02_transactions-brokers-import.md), [03](03_fx-market-data.md) e
  [06B](06b-financial-theory-indicators.md) concentrano tab, wizard, colonne,
  default e preset rimasti a una revisione UI precedente.
- **Teoria con claim implementative**: le pagine puramente didattiche sono state
  classificate fuori standard di codice; [06A](06a-financial-theory-instruments.md)
  e [06C](06c-financial-theory-performance-risk.md) registrano solo divergenze dove
  il testo dichiara esplicitamente semantica LibreFolio.

## Validazione di chiusura

- `./dev.py mkdocs build` ha completato con successo alla baseline.
- Nav i18n: 182/182 pagine EN non-developer sono referenziate dalla nav pubblicata;
  nessuna pagina in scope e' orfana, nessuna voce nav manca della sorgente EN.
- Ogni report contiene una tabella di copertura; la partizione dei nove report e'
  esattamente l'insieme delle 182 pagine in scope.
- `git diff --check` sui report non ha rilevato errori di whitespace. I link Markdown
  aggiunti dai report e le citazioni di percorso sono stati controllati; riferimenti a
  percorsi assenti compaiono solo come controprove intenzionali di reperti (per
  esempio `financial_math.py` inesistente).
- `./dev.py mkdocs check-links` ha segnalato `${lang` da
  `AboutTab.svelte:145`; [01](01_user-core.md) ha tracciato la regex e confermato che
  e' un falso positivo su un template literal annidato, non un link utente rotto.
- Nessun cambiamento di stato dei path Git e' emerso dopo il manifest baseline. Le
  prove restano quindi riferite al worktree dirty dichiarato, non a `HEAD` puro.

## Limite deliberato

La guida developer non e' stata letta ne' confrontata, come richiesto. Dopo il via
esplicito dell'utente servono una nuova baseline e tre report separati: backend/API,
frontend e cross-cutting. Non riusare automaticamente le citazioni di questo audit
per dichiarare valida la developer guide.
